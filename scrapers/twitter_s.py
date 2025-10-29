# scrapers/twitter_scraper.py

import pandas as pd
from itertools import islice

def get_twitter_mentions(company_name: str, keywords: list, limit: int) -> pd.DataFrame:
    """
    Fetches Tweets mentioning the company or keywords using snscrape.
    Note: snscrape has compatibility issues with Python 3.13, so this is a placeholder implementation.
    """
    print("Warning: Twitter scraping is currently disabled due to snscrape compatibility issues with Python 3.13.")
    print("To enable Twitter scraping, consider using Python 3.11 or 3.12, or implement an alternative Twitter API solution.")
    
    # Return empty DataFrame as placeholder
    return pd.DataFrame(columns=['id', 'username', 'date', 'text', 'likes', 'retweets', 'url'])

# Alternative implementation for when snscrape is working:
"""
try:
    import snscrape.modules.twitter as sntwitter
    
    def get_twitter_mentions(company_name: str, keywords: list, limit: int) -> pd.DataFrame:
        query = f'"{company_name}" OR ' + ' OR '.join(f'"{k}"' for k in keywords)
        query += " lang:en" # Filter for English tweets
        
        tweets = []
        try:
            # Using islice to limit the number of tweets
            scraper = sntwitter.TwitterSearchScraper(query)
            for tweet in islice(scraper.get_items(), limit):
                tweets.append({
                    'id': tweet.id,
                    'username': tweet.user.username,
                    'date': tweet.date,
                    'text': tweet.rawContent,
                    'likes': tweet.likeCount,
                    'retweets': tweet.retweetCount,
                    'url': tweet.url,
                })
        except Exception as e:
            print(f"An error occurred with snscrape: {e}")

        return pd.DataFrame(tweets)
        
except ImportError as e:
    print(f"snscrape import error: {e}")
    # Fallback implementation
    def get_twitter_mentions(company_name: str, keywords: list, limit: int) -> pd.DataFrame:
        print("Twitter scraping not available due to import error.")
        return pd.DataFrame(columns=['id', 'username', 'date', 'text', 'likes', 'retweets', 'url'])
"""