# Brand Reputation Analyzer

A comprehensive brand reputation analysis tool that scrapes mentions from NewsAPI, Reddit, and Twitter, performs sentiment analysis using RoBERTa-HAN, extracts keywords and themes using spaCy NLP, and stores all data in MongoDB Atlas.

## Features

- **Multi-source Data Collection**: Scrapes mentions from NewsAPI, Reddit, and Twitter
- **Sentiment Analysis**: Uses RoBERTa-HAN model for accurate sentiment classification
- **Keyword & Theme Extraction**: Leverages spaCy NLP for extracting relevant keywords and themes
- **MongoDB Integration**: All data stored in MongoDB Atlas cloud database
- **FastAPI Backend**: High-performance ASGI server with Uvicorn
- **Real-time Dashboard**: Interactive web dashboard with charts and visualizations

## Prerequisites

- Python 3.8+
- MongoDB Atlas account (free tier works)
- API Keys:
  - NewsAPI key (from https://newsapi.org/)
  - Reddit API credentials (PRAW)
  - Wikipedia API (no key required, but user agent needed)

## Installation

1. **Clone the repository**
   ```bash
   git clone <your-repo-url>
   cd brand-reputation-analyzer
   ```

2. **Create and activate virtual environment**
   ```bash
   python -m venv venv
   venv\Scripts\activate  # Windows
   # or
   source venv/bin/activate  # Linux/Mac
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   python -m spacy download en_core_web_sm
   ```

4. **Set up environment variables**
   Create a `.env` file in the root directory:
   ```env
   # MongoDB
   MONGODB_URI=your_mongodb_atlas_connection_string
   MONGODB_DB_NAME=brand_reputation

   # NewsAPI
   NEWS_API_KEY=your_newsapi_key

   # Reddit PRAW
   REDDIT_CLIENT_ID=your_reddit_client_id
   REDDIT_CLIENT_SECRET=your_reddit_client_secret
   REDDIT_USER_AGENT=your_app_name

   # Wikipedia
   WIKI_USER_AGENT=your_app_name

   # Limits (optional, defaults shown)
   REDDIT_LIMIT=100
   NEWS_LIMIT=100
   TWITTER_LIMIT=100
   ```

## Usage

### Running with FastAPI (Recommended)

```bash
python -m uvicorn api_server:app --reload --port 8000
```

Then open http://127.0.0.1:8000 in your browser.

### Running with Flask (Alternative)

```bash
python app.py
```

Then open http://127.0.0.1:5000 in your browser.

### Running Analysis

1. Navigate to the web interface
2. Enter a company name
3. Optionally add keywords (comma-separated)
4. Click "Analyze"
5. Wait for the analysis to complete (check status automatically)
6. View results in the dashboard

## Project Structure

```
brand-reputation-analyzer/
├── api_server.py          # FastAPI application (recommended)
├── app.py                 # Flask application (legacy)
├── main.py                # Main analysis orchestration
├── config.py              # Configuration from environment variables
├── db.py                  # MongoDB connection and indexing
├── requirements.txt       # Python dependencies
├── scrapers/              # Data scraping modules
│   ├── new_api_s.py      # NewsAPI scraper
│   ├── reddit_s.py       # Reddit PRAW scraper
│   ├── twitter_s.py      # Twitter scraper
│   └── wikipedia_s.py     # Wikipedia scraper
├── processors/            # Data processing modules
│   ├── data_processor.py # Keyword and theme extraction
│   └── sentiment.py      # Sentiment analysis using RoBERTa-HAN
├── templates/             # HTML templates
│   ├── index.html
│   └── dashboard.html
└── static/                # CSS and JavaScript
    ├── css/
    └── js/
```

## Data Storage

All data is stored in MongoDB Atlas collections:
- `companies` - Company listing metadata
- `company_profiles` - Detailed company profiles from Wikipedia
- `mentions` - Unified mentions from all sources
- `news_mentions` - Legacy news mentions collection
- `reddit_mentions` - Legacy Reddit mentions collection
- `twitter_mentions` - Legacy Twitter mentions collection
- `keywords` - Extracted keywords with frequencies
- `themes` - Extracted themes
- `sentiments` - Sentiment analysis results

## API Endpoints

- `GET /` - Main homepage
- `GET /dashboard/{company_id}` - Company dashboard
- `POST /api/analyze` - Start analysis for a company
- `GET /api/companies` - List all analyzed companies
- `GET /api/sentiment/{company_id}` - Get sentiment metrics
- `GET /api/keywords/{company_id}` - Get top keywords
- `GET /api/themes/{company_id}` - Get themes
- `GET /api/news/{company_id}` - Get news mentions
- `GET /api/reddit/{company_id}` - Get Reddit mentions
- `GET /api/twitter/{company_id}` - Get Twitter mentions
- `GET /api/health` - MongoDB connection status
- `GET /api/debug/mentions/{company_id}` - Debug endpoint for mentions

## Technologies Used

- **Backend**: FastAPI, Flask, Uvicorn
- **Database**: MongoDB Atlas (PyMongo)
- **NLP**: spaCy, Transformers (RoBERTa-HAN)
- **ML Framework**: PyTorch
- **Data Processing**: Pandas
- **Web Scraping**: NewsAPI, PRAW (Reddit), Wikipedia API
- **Frontend**: Vanilla JavaScript, Chart.js, D3.js

## License

MIT License - feel free to use for your projects.

## Contributing

Pull requests are welcome! Please open an issue first to discuss major changes.

