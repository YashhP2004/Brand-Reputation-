# config.py

import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Wikipedia Settings
WIKI_USER_AGENT = os.getenv("WIKI_USER_AGENT")

# NewsAPI Settings
NEWS_API_KEY = os.getenv("NEWS_API_KEY")

# Reddit PRAW Settings
REDDIT_CLIENT_ID = os.getenv("REDDIT_CLIENT_ID")
REDDIT_CLIENT_SECRET = os.getenv("REDDIT_CLIENT_SECRET")
REDDIT_USER_AGENT = os.getenv("REDDIT_USER_AGENT")

# General Scraping Settings
# Number of items to fetch from each source
REDDIT_LIMIT = int(os.getenv("REDDIT_LIMIT", "100"))
NEWS_LIMIT = int(os.getenv("NEWS_LIMIT", "100"))
TWITTER_LIMIT = int(os.getenv("TWITTER_LIMIT", "100"))

# MongoDB Settings
MONGODB_URI = os.getenv("MONGODB_URI")
MONGODB_DB_NAME = os.getenv("MONGODB_DB_NAME", "brand_reputation")