import threading
from typing import Optional

from pymongo import MongoClient, ASCENDING, errors
import ssl
import certifi

import config

_client_lock = threading.Lock()
_client: Optional[MongoClient] = None
_last_error: Optional[str] = None


def _ensure_client() -> Optional[MongoClient]:
    global _client
    global _last_error
    if _client is not None:
        return _client
    if not config.MONGODB_URI:
        _last_error = "missing_uri"
        return None
    
    # Sanitize URI: strip whitespace and remove quotes
    uri = config.MONGODB_URI.strip()
    if uri.startswith('"') and uri.endswith('"'):
        uri = uri[1:-1]
    elif uri.startswith("'") and uri.endswith("'"):
        uri = uri[1:-1]
    # Handle accidental inclusion of key name inside value, e.g. "MONGODB_URI=mongodb+srv://..."
    if uri.lower().startswith("mongodb_uri="):
        uri = uri.split("=", 1)[1].strip()
    
    # Validate URI format
    if not (uri.startswith("mongodb://") or uri.startswith("mongodb+srv://")):
        _last_error = f"Invalid URI format: URI must start with mongodb:// or mongodb+srv://. Got: {uri[:50]}..."
        return None
    
    with _client_lock:
        if _client is None:
            try:
                base_kwargs = {
                    "tls": True,
                    "serverSelectionTimeoutMS": 5000,
                    "connectTimeoutMS": 20000,
                    "socketTimeoutMS": 20000,
                    "maxPoolSize": 50,
                    "retryWrites": True,
                    "w": "majority",
                }
                ca_file = None
                try:
                    ca_file = certifi.where()
                except Exception:
                    ca_file = None
                attempts = []
                if ca_file:
                    strict_opts = dict(base_kwargs)
                    strict_opts["tlsCAFile"] = ca_file
                    strict_opts["tlsAllowInvalidCertificates"] = False
                    attempts.append(strict_opts)
                    relaxed_ocsp = dict(strict_opts)
                    relaxed_ocsp["serverSelectionTimeoutMS"] = 10000
                    relaxed_ocsp["tlsDisableCertificateRevocationCheck"] = True
                    relaxed_ocsp["tlsDisableOCSPEndpointCheck"] = True
                    attempts.append(relaxed_ocsp)
                else:
                    attempts.append(dict(base_kwargs))
                    relaxed_no_ca = dict(base_kwargs)
                    relaxed_no_ca["serverSelectionTimeoutMS"] = 10000
                    relaxed_no_ca["tlsDisableCertificateRevocationCheck"] = True
                    relaxed_no_ca["tlsDisableOCSPEndpointCheck"] = True
                    attempts.append(relaxed_no_ca)
                insecure_opts = dict(base_kwargs)
                insecure_opts["serverSelectionTimeoutMS"] = 10000
                insecure_opts["tlsAllowInvalidCertificates"] = True
                insecure_opts["tlsAllowInvalidHostnames"] = True
                insecure_opts["tlsDisableCertificateRevocationCheck"] = True
                insecure_opts["tlsDisableOCSPEndpointCheck"] = True
                attempts.append(insecure_opts)
                for opts in attempts:
                    try:
                        _client = MongoClient(uri, **opts)
                        _client.admin.command('ping')
                        _last_error = None
                        break
                    except (errors.ServerSelectionTimeoutError, ssl.SSLError) as _ssl_err:
                        _client = None
                        _last_error = f"connect_error: {type(_ssl_err).__name__}: {str(_ssl_err)[:200]}"
                        continue
            except Exception as e:
                _client = None
                _last_error = f"connect_error: {type(e).__name__}: {str(e)[:200]}"
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


def get_status() -> dict:
    return {
        "uri_present": bool(config.MONGODB_URI),
        "db_name": config.MONGODB_DB_NAME,
        "enabled": is_enabled(),
        "last_error": _last_error,
    }


