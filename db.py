import threading
from typing import Optional

from pymongo import MongoClient, ASCENDING, errors

import config

_client_lock = threading.Lock()
_client: Optional[MongoClient] = None


def _ensure_client() -> Optional[MongoClient]:
    global _client
    if _client is not None:
        return _client
    if not config.MONGODB_URI:
        return None
    with _client_lock:
        if _client is None:
            try:
                _client = MongoClient(config.MONGODB_URI, serverSelectionTimeoutMS=5000)
                # Trigger server selection to fail fast if misconfigured
                _client.admin.command("ping")
            except Exception:
                _client = None
    return _client


def is_enabled() -> bool:
    return _ensure_client() is not None


def get_db():
    client = _ensure_client()
    if client is None:
        return None
    return client[config.MONGODB_DB_NAME]


def get_collection(name: str):
    db = get_db()
    if db is None:
        return None
    return db[name]


def ensure_indexes() -> None:
    db = get_db()
    if db is None:
        return
    try:
        # Legacy/previous collections
        db["company_profiles"].create_index([("company_id", ASCENDING)], unique=True)
        db["news_mentions"].create_index([("company_id", ASCENDING), ("url", ASCENDING)], unique=True)
        db["reddit_mentions"].create_index([("company_id", ASCENDING), ("url", ASCENDING)], unique=True)
        db["twitter_mentions"].create_index([("company_id", ASCENDING), ("url", ASCENDING)], unique=True)
        # Current consolidated collections
        db["companies"].create_index([("company_id", ASCENDING)], unique=True)
        db["mentions"].create_index([("company_id", ASCENDING), ("source", ASCENDING), ("url", ASCENDING)], unique=True)
        db["mentions"].create_index([("company_id", ASCENDING), ("source", ASCENDING)])
        db["keywords"].create_index([("company_id", ASCENDING), ("date", ASCENDING)])
        db["themes"].create_index([("company_id", ASCENDING), ("date", ASCENDING)])
        db["sentiments"].create_index([("company_id", ASCENDING), ("date", ASCENDING)])
    except errors.PyMongoError:
        # Avoid crashing app if index creation fails; operations will still attempt
        pass


