# scrapers/reddit_scraper.py

import praw
import pandas as pd

def get_reddit_mentions(company_name: str, keywords: list, client_id: str, client_secret: str, user_agent: str, limit: int) -> pd.DataFrame:
    """
    Fetches Reddit posts and comments mentioning the company or keywords.
    """
    try:
        reddit = praw.Reddit(client_id=client_id,
                             client_secret=client_secret,
                             user_agent=user_agent)
    except Exception as e:
        print(f"Error connecting to Reddit API: {e}")
        return pd.DataFrame()
        
    query = f'"{company_name}" OR ' + ' OR '.join(f'"{k}"' for k in keywords)
    
    # Search in popular subreddits, can be expanded
    subreddits_to_search = "all" 
    
    mentions = []
    
    try:
        submissions = reddit.subreddit(subreddits_to_search).search(query, limit=limit)
        for submission in submissions:
            mentions.append({
                'type': 'post',
                'id': submission.id,
                'subreddit': submission.subreddit.display_name,
                'title': submission.title,
                'text': submission.selftext,
                'score': submission.score,
                'url': submission.permalink,
                'created_utc': submission.created_utc
            })
    except Exception as e:
        print(f"Error fetching data from Reddit: {e}")

    return pd.DataFrame(mentions)