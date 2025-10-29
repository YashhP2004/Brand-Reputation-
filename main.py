# main.py

import pandas as pd
from datetime import datetime
import config
from scrapers.wikipedia_s import get_company_profile
from scrapers import new_api_s, reddit_s, twitter_s
from processors import data_processor
import argparse
from typing import Dict, Any, List

import db

def run_analysis(company_name: str, keywords_list: list):
    """
    Main function to scrape all sources for a given company and save the data.
    """
    print(f"--- Starting analysis for: {company_name} at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ---")
    
    company_id = company_name.replace(" ", "_").lower()

    # Ensure DB indexes if Mongo is enabled
    if db.is_enabled():
        db.ensure_indexes()

    # --- 1. Scrape Data ---
    print("Scraping Wikipedia for company profile...")
    profile_df = get_company_profile(company_name, config.WIKI_USER_AGENT)
    
    # --- 2. Save/Update Central Company Profile in MongoDB ---
    if db.is_enabled():
        try:
            # Always upsert a minimal company row so it appears in lists
            companies_col = db.get_collection("companies")
            companies_col.update_one({"company_id": company_id}, {"$set": {"company_id": company_id, "Name": company_name}}, upsert=True)
        except Exception as e:
            print(f"Mongo: failed to upsert company entry: {e}")
    if not profile_df.empty:
        if db.is_enabled():
            try:
                profiles = db.get_collection("company_profiles")
                record: Dict[str, Any] = {**profile_df.iloc[0].to_dict(), "company_id": company_id}
                profiles.update_one({"company_id": company_id}, {"$set": record}, upsert=True)
                # Also update display name if available
                try:
                    companies = db.get_collection("companies")
                    companies.update_one({"company_id": company_id}, {"$set": {"Name": profile_df.iloc[0].get('Name', company_name)}})
                except Exception:
                    pass
            except Exception as e:
                print(f"Mongo: failed to upsert company profile: {e}")
        else:
            print("Warning: MongoDB is not configured; company profile not saved.")

    # --- 3. Scrape News, Reddit, and Twitter ---
    print(f"Using keywords: {keywords_list}")
    news_df = new_api_s.get_news_mentions(company_name, keywords_list, config.NEWS_API_KEY, config.NEWS_LIMIT)
    reddit_df = reddit_s.get_reddit_mentions(company_name, keywords_list, config.REDDIT_CLIENT_ID, config.REDDIT_CLIENT_SECRET, config.REDDIT_USER_AGENT, config.REDDIT_LIMIT)
    twitter_df = twitter_s.get_twitter_mentions(company_name, keywords_list, config.TWITTER_LIMIT)

    # --- 4. Store Mentions in MongoDB ---
    today_str = datetime.now().strftime('%Y-%m-%d')
    for df, name in [(news_df, "news"), (reddit_df, "reddit"), (twitter_df, "twitter")]:
        if not df.empty:
            # Write mentions to MongoDB (consolidated 'mentions' collection)
            if db.is_enabled():
                try:
                    # Prefer consolidated collection
                    m_col = db.get_collection("mentions")
                    col = m_col if m_col is not None else db.get_collection(f"{name}_mentions")
                    docs: List[Dict[str, Any]] = []
                    for _, row in df.iterrows():
                        doc = row.to_dict()
                        doc["company_id"] = company_id
                        if m_col is not None:
                            doc["source"] = name  # 'news' | 'reddit' | 'twitter'
                        docs.append(doc)
                    if docs:
                        # Insert ignoring duplicates where unique index exists
                        try:
                            col.insert_many(docs, ordered=False)
                        except Exception:
                            # Some may be duplicates; continue silently
                            pass
                except Exception as e:
                    print(f"Mongo: failed to insert {name} mentions: {e}")
            else:
                print(f"Warning: MongoDB is not configured; {name} mentions not saved.")

    # --- 5. Process Data and Perform Sentiment Analysis ---
    text_sources = []
    if not news_df.empty and 'title' in news_df.columns:
        text_sources.append(news_df['title'])
    if not reddit_df.empty and 'text' in reddit_df.columns:
        text_sources.append(reddit_df['text'])
    if not twitter_df.empty and 'text' in twitter_df.columns:
        text_sources.append(twitter_df['text'])

    if text_sources:
        all_text = pd.concat(text_sources, ignore_index=True).dropna()
        if not all_text.empty:
            all_text_df = pd.DataFrame(all_text, columns=['text'])
            
            print("Extracting keywords and themes...")
            keywords_df, themes_df = data_processor.extract_keywords_and_themes(all_text_df, 'text')
            print("Extracted keywords and themes.")

            if db.is_enabled():
                try:
                    k_col = db.get_collection("keywords")
                    k_docs = []
                    for _, row in keywords_df.iterrows():
                        rec = row.to_dict()
                        rec["company_id"] = company_id
                        rec["date"] = today_str
                        k_docs.append(rec)
                    if k_docs:
                        k_col.insert_many(k_docs, ordered=False)
                except Exception as e:
                    print(f"Mongo: failed to insert keywords: {e}")
                try:
                    t_col = db.get_collection("themes")
                    t_docs = []
                    for _, row in themes_df.iterrows():
                        rec = row.to_dict()
                        rec["company_id"] = company_id
                        rec["date"] = today_str
                        t_docs.append(rec)
                    if t_docs:
                        t_col.insert_many(t_docs, ordered=False)
                except Exception as e:
                    print(f"Mongo: failed to insert themes: {e}")

            print("Performing sentiment analysis...")
            sentiment_df = data_processor.analyze_sentiment(all_text_df, 'text')
            print("Computed sentiment analysis results.")
            if db.is_enabled():
                try:
                    s_col = db.get_collection("sentiments")
                    total = {"positive": 0, "neutral": 0, "negative": 0}
                    for _, row in sentiment_df.iterrows():
                        for k in total.keys():
                            if k in row and pd.notna(row[k]):
                                try:
                                    total[k] += int(float(row[k]))
                                except Exception:
                                    pass
                    s_col.insert_one({"company_id": company_id, "date": today_str, **total})
                except Exception as e:
                    print(f"Mongo: failed to insert sentiments: {e}")
        
    print(f"--- Analysis for {company_name} complete. ---\n")

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Run brand reputation analysis for a company.")
    parser.add_argument("--company", type=str, required=True, help="The name of the company to analyze.")
    parser.add_argument("--keywords", type=str, default="", help="Comma-separated keywords.")
    args = parser.parse_args()
    
    keyword_list = [k.strip() for k in args.keywords.split(',') if k.strip()]
    run_analysis(args.company, keyword_list)