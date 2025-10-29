# processors/data_processor.py
import pandas as pd
from collections import Counter
import spacy
from .sentiment import SentimentModel # Import the new class


# Load the spaCy model once
try:
    nlp = spacy.load("en_core_web_sm")
except OSError:
    print("Downloading spaCy model 'en_core_web_sm'. This may take a moment.")
    from spacy.cli import download
    download("en_core_web_sm")
    nlp = spacy.load("en_core_web_sm")

def extract_keywords_and_themes(df: pd.DataFrame, text_column: str) -> tuple:
    """
    Extracts named entities (as keywords) and common adjectives (as themes) from text.
    Returns a tuple of (keywords_df, themes_df)
    """
    all_text = ' '.join(df[text_column].dropna())
    doc = nlp(all_text)
    
    # Extract keywords (Organizations, Products, People)
    keywords = [ent.text for ent in doc.ents if ent.label_ in ('ORG', 'PRODUCT', 'PERSON')]
    
    # Extract themes (adjectives)
    themes = [token.lemma_.lower() for token in doc if token.pos_ == 'ADJ']
    
    # Get top 15 of each
    top_keywords = pd.DataFrame(Counter(keywords).most_common(15), columns=['keyword', 'count'])
    top_themes = pd.DataFrame(Counter(themes).most_common(15), columns=['theme', 'count'])
    
    return top_keywords, top_themes

def analyze_sentiment(df, text_column):
    """
    Analyzes the sentiment of each text entry in a DataFrame column.
    """
    model = SentimentModel()
    sentiments = df[text_column].apply(model.predict)
    sentiment_counts = sentiments.value_counts().reindex(['positive', 'neutral', 'negative'], fill_value=0)
    return pd.DataFrame([sentiment_counts])