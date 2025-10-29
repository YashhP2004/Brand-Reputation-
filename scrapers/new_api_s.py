# scrapers/new_api_s.py

import pandas as pd
# Corrected the import statement back to the standard one
from newsapi import NewsApiClient

def get_news_mentions(company_name, keywords, api_key, limit=100):
    """
    Fetches news articles mentioning the company and keywords from NewsAPI.
    """
    if not api_key:
        print("NewsAPI key not found. Skipping news scraping.")
        return pd.DataFrame()

    newsapi = NewsApiClient(api_key=api_key)
    
    # Combine company name and keywords for a broader search query
    query = f'"{company_name}" OR ({" AND ".join(keywords)})'
    
    try:
        all_articles = newsapi.get_everything(q=query,
                                              language='en',
                                              sort_by='relevancy',
                                              page_size=limit)
        
        data = []
        for article in all_articles['articles']:
            data.append({
                'source': article['source']['name'],
                'title': article['title'],
                'url': article['url'],
                'published_at': article['publishedAt'],
                'text': article.get('description', '') or '' # Ensure text is not None
            })
        
        df = pd.DataFrame(data)
        print(f"Found {len(df)} news articles for {company_name}.")
        return df

    except Exception as e:
        print(f"An error occurred while fetching news for {company_name}: {e}")
        return pd.DataFrame()