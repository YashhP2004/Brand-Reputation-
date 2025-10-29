# Flask REST API for Brand Reputation Analyzer
from flask import Flask, jsonify, request, render_template
import threading
from main import run_analysis # Import the run_analysis function
import db

app = Flask(__name__)

def _company_id_variants(cid: str):
    # Normalize and provide common variants used historically
    norm = cid.replace(' ', '_').lower()
    return list({
        norm,
        cid,
        cid.lower(),
        cid.replace(' ', '_'),
        cid.replace('_', ' '),
        cid.title().replace(' ', '_'),
    })

def _sanitize_value(value):
    import math
    if value is None:
        return None
    if isinstance(value, float) and math.isnan(value):
        return None
    if isinstance(value, list):
        return [_sanitize_value(v) for v in value]
    if isinstance(value, dict):
        return {k: _sanitize_value(v) for k, v in value.items()}
    return value

def _sanitize_docs(docs):
    cleaned = []
    for d in docs:
        cleaned.append({k: _sanitize_value(v) for k, v in d.items()})
    return cleaned

def _fetch_mentions_unified(company_id: str, sources: list[str]):
    """Flexible query against unified 'mentions' collection supporting various field names."""
    m = db.get_collection('mentions')
    if m is None:
        return None
    cid_variants = _company_id_variants(company_id)
    source_fields = ['source', 'type', 'platform', 'channel']
    or_source = [{field: {'$in': sources}} for field in source_fields]
    # Build query: company_id in variants AND (any source field matches)
    query = {
        '$and': [
            {'company_id': {'$in': cid_variants}},
            {'$or': or_source}
        ]
    }
    try:
        docs = list(m.find(query).sort('_id', -1))
        for d in docs:
            d.pop('_id', None)
        return _sanitize_docs(docs)
    except Exception:
        return []

def _infer_source_from_url(url: str) -> str:
    u = (url or '').lower()
    if 'reddit.com' in u:
        return 'reddit'
    if 'twitter.com' in u or 'x.com' in u:
        return 'twitter'
    return 'news'

def _fetch_mentions_inferred(company_id: str, wanted: str):
    m = db.get_collection('mentions')
    if m is None:
        return None
    cid_variants = _company_id_variants(company_id)
    try:
        docs = list(m.find({'company_id': {'$in': cid_variants}}).sort('_id', -1))
        result = []
        for d in docs:
            src = d.get('source') or d.get('type') or d.get('platform') or d.get('channel')
            if not src:
                src = _infer_source_from_url(str(d.get('url', '')))
            if str(src).lower() == wanted:
                d.pop('_id', None)
                result.append(d)
        return _sanitize_docs(result)
    except Exception:
        return []

def get_companies():
    """Gets a list of companies from MongoDB only."""
    if not db.is_enabled():
        return []
    try:
        companies = []
        ids = []
        # Preferred: 'companies' collection
        companies_col = db.get_collection("companies")
        if companies_col is not None:
            docs = list(companies_col.find({}, {"_id": 0, "company_id": 1, "Name": 1}))
            ids = [d.get("company_id") for d in docs] if docs else []
            if ids:
                for d in docs:
                    cid = d.get("company_id")
                    display_name = d.get("Name") or cid.replace('_', ' ').title()
                    companies.append({'id': cid, 'display_name': display_name})
                return sorted(companies, key=lambda x: x['display_name'])
        # Legacy: 'company_profiles'
        if not ids:
            profiles = db.get_collection("company_profiles")
            if profiles is not None:
                ids = profiles.distinct("company_id") or []
        # Fallback if no companies yet: derive from data collections
        if not ids:
            candidates = set()
            for name in [
                "sentiments",
                "mentions",  # unified
                "news_mentions",
                "reddit_mentions",
                "twitter_mentions",
                "keywords",
                "themes",
            ]:
                col = db.get_collection(name)
                if col is None:
                    continue
                try:
                    vals = col.distinct("company_id")
                    for v in vals:
                        if v:
                            candidates.add(v)
                except Exception:
                    pass
            ids = list(candidates)
        # Persist minimal entries into 'companies' for future loads
        if ids and companies_col is not None:
            try:
                for cid in ids:
                    companies_col.update_one({"company_id": cid}, {"$setOnInsert": {"company_id": cid, "Name": cid.replace('_', ' ').title()}}, upsert=True)
            except Exception:
                pass
        for cid in ids:
            display_name = cid.replace('_', ' ').title()
            companies.append({'id': cid, 'display_name': display_name})
        return sorted(companies, key=lambda x: x['display_name'])
    except Exception:
        return []
    return []

## Removed filesystem helpers; MongoDB-only mode

# --- HTML Page Routes ---

@app.route('/')
def index():
    """Renders the main page."""
    return render_template('index.html')

@app.route('/dashboard/<company_id>')
def dashboard(company_id):
    """Renders the dashboard for a specific company."""
    company_name = company_id.replace('_', ' ').title()
    return render_template('dashboard.html', company_id=company_id, company_name=company_name)

# --- API Routes ---

@app.route('/api/analyze', methods=['POST'])
def api_analyze():
    """Triggers the analysis for a new company."""
    data = request.get_json()
    company_name = data.get('company_name')
    keywords = data.get('keywords', '')

    if not company_name:
        return jsonify({'error': 'Company name is required.'}), 400

    company_id = company_name.replace(" ", "_").lower()

    # Prepare the list of keywords
    keywords_list = [k.strip() for k in keywords.split(',') if k.strip()]
    
    # --- THIS IS THE CRITICAL SECTION ---
    # We create a thread to run the analysis in the background.
    # The 'args' tuple must contain exactly the arguments that run_analysis expects.
    # In this case, it's two arguments: company_name (string) and keywords_list (list).
    thread = threading.Thread(target=run_analysis, args=(company_name, keywords_list))
    thread.start()

    return jsonify({'message': f'Analysis started for {company_name}.', 'company_id': company_id}), 202

@app.route('/api/health')
def api_health():
    status = { 'mongo': 'disabled' }
    if db.is_enabled():
        try:
            database = db.get_db()
            status['mongo'] = 'connected' if database is not None else 'error'
            stats = {}
            for name in [
                'company_profiles', 'sentiments', 'news_mentions', 'reddit_mentions', 'twitter_mentions', 'keywords', 'themes'
            ]:
                try:
                    col = db.get_collection(name)
                    stats[name] = col.estimated_document_count() if col is not None else 0
                except Exception:
                    stats[name] = 'err'
            status['counts'] = stats
        except Exception as e:
            status['mongo'] = 'error'
    return jsonify(status)

@app.route('/api/analysis_status/<company_id>')
def analysis_status(company_id):
    """Checks if the analysis for a company is complete."""
    if db.is_enabled():
        try:
            s_col = db.get_collection('sentiments')
            if s_col is not None:
                doc = s_col.find_one({'company_id': company_id})
                if doc:
                    return jsonify({'status': 'complete'})
        except Exception:
            pass
    return jsonify({'status': 'pending'})

@app.route('/api/companies')
def api_companies():
    return jsonify(get_companies())

## Removed CSV reading; MongoDB-only mode

@app.route('/api/sentiment/<company_id>')
def api_sentiment(company_id):
    if not db.is_enabled():
        return jsonify({'positive': 0, 'neutral': 0, 'negative': 0})
    try:
        s_col = db.get_collection('sentiments')
        if s_col is not None:
            doc = s_col.find_one({'company_id': company_id}, sort=[('date', -1)])
            if doc:
                return jsonify({
                    'positive': int(doc.get('positive', 0)),
                    'neutral': int(doc.get('neutral', 0)),
                    'negative': int(doc.get('negative', 0))
                })
    except Exception:
        pass
    return jsonify({'positive': 0, 'neutral': 0, 'negative': 0})

@app.route('/api/live_sentiment/')
def api_live_sentiment():
    """Returns latest sentiment for the given company_id via query param.
    Mirrors /api/sentiment/<company_id> for frontend compatibility.
    """
    company_id = request.args.get('company_id', '')
    if not company_id:
        return jsonify({'positive': 0, 'neutral': 0, 'negative': 0}), 400
    return api_sentiment(company_id)

@app.route('/api/themes/<company_id>')
def api_themes(company_id):
    if not db.is_enabled():
        return jsonify([])
    try:
        t_col = db.get_collection('themes')
        if t_col is not None:
            latest = t_col.find({'company_id': company_id}).sort('date', -1)
            rows = list(latest)
            if rows:
                return jsonify([r.get('theme') for r in rows if r.get('theme')])
    except Exception:
        pass
    return jsonify([])

@app.route('/api/keywords/<company_id>')
def api_keywords(company_id):
    if not db.is_enabled():
        return jsonify([])
    try:
        k_col = db.get_collection('keywords')
        if k_col is not None:
            docs = list(k_col.find({'company_id': company_id}).sort('date', -1))
            if docs:
                for d in docs:
                    d.pop('_id', None)
                return jsonify(docs)
    except Exception:
        pass
    return jsonify([])

# Data table endpoints
@app.route('/api/news/<company_id>')
def api_news(company_id):
    if not db.is_enabled():
        return jsonify([])
    try:
        # Prefer unified 'mentions' collection (supports various field names)
        unified = _fetch_mentions_unified(company_id, ['news', 'article'])
        if unified is not None and len(unified) > 0:
            return jsonify(unified)
        inferred = _fetch_mentions_inferred(company_id, 'news')
        if inferred is not None and len(inferred) > 0:
            return jsonify(inferred)
        col = db.get_collection('news_mentions')
        if col is not None:
            docs = list(col.find({'company_id': {'$in': _company_id_variants(company_id)}}).sort('_id', -1))
            for d in docs:
                d.pop('_id', None)
            return jsonify(_sanitize_docs(docs))
    except Exception:
        pass
    return jsonify([])

@app.route('/api/reddit/<company_id>')
def api_reddit(company_id):
    if not db.is_enabled():
        return jsonify([])
    try:
        unified = _fetch_mentions_unified(company_id, ['reddit'])
        if unified is not None and len(unified) > 0:
            return jsonify(unified)
        inferred = _fetch_mentions_inferred(company_id, 'reddit')
        if inferred is not None and len(inferred) > 0:
            return jsonify(inferred)
        col = db.get_collection('reddit_mentions')
        if col is not None:
            docs = list(col.find({'company_id': {'$in': _company_id_variants(company_id)}}).sort('_id', -1))
            for d in docs:
                d.pop('_id', None)
            return jsonify(_sanitize_docs(docs))
    except Exception:
        pass
    return jsonify([])

@app.route('/api/twitter/<company_id>')
def api_twitter(company_id):
    if not db.is_enabled():
        return jsonify([])
    try:
        unified = _fetch_mentions_unified(company_id, ['twitter', 'x'])
        if unified is not None and len(unified) > 0:
            return jsonify(unified)
        inferred = _fetch_mentions_inferred(company_id, 'twitter')
        if inferred is not None and len(inferred) > 0:
            return jsonify(inferred)
        col = db.get_collection('twitter_mentions')
        if col is not None:
            docs = list(col.find({'company_id': {'$in': _company_id_variants(company_id)}}).sort('_id', -1))
            for d in docs:
                d.pop('_id', None)
            return jsonify(_sanitize_docs(docs))
    except Exception:
        pass
    return jsonify([])

if __name__ == '__main__':
    # Disable the Flask auto-reloader to avoid crashes during background analysis
    # and when transformers downloads trigger file changes under site-packages.
    app.run(debug=True, use_reloader=False)