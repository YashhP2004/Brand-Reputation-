from typing import List, Dict, Any

from fastapi import FastAPI, Request, BackgroundTasks
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

import db
from main import run_analysis


app = FastAPI(title="Brand Reputation Analyzer API")

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")


def _company_id_variants(cid: str) -> List[str]:
    space_to_us = cid.replace(' ', '_')
    us_to_space = cid.replace('_', ' ')
    hy_to_us = cid.replace('-', '_')
    us_to_hy = cid.replace('_', '-')
    variants = {
        cid,
        cid.lower(),
        space_to_us,
        us_to_space,
        hy_to_us,
        us_to_hy,
        space_to_us.lower(),
        us_to_space.lower(),
        hy_to_us.lower(),
        us_to_hy.lower(),
        cid.title().replace(' ', '_'),
        cid.title().replace('-', '_'),
    }
    return list(variants)

def _company_filter(cid: str) -> Dict[str, Any]:
    variants = _company_id_variants(cid)
    # Build case-insensitive regex variants as well
    name = cid.replace('_', ' ')
    alt = cid.replace(' ', '_')
    regex_opts = {'$regex': f"^{name}$|^{alt}$|{name}|{alt}", '$options': 'i'}
    return {
        '$or': [
            {'company_id': {'$in': variants}},
            {'company': {'$in': variants}},
            {'companyId': {'$in': variants}},
            {'company_id': regex_opts},
            {'company': regex_opts},
            {'companyId': regex_opts},
        ]
    }


def _sanitize_value(value):
    import math
    from datetime import datetime, date
    if value is None:
        return None
    if isinstance(value, float) and math.isnan(value):
        return None
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, list):
        return [_sanitize_value(v) for v in value]
    if isinstance(value, dict):
        return {k: _sanitize_value(v) for k, v in value.items()}
    return value


def _sanitize_docs(docs: List[Dict[str, Any]]):
    cleaned = []
    for d in docs:
        cleaned.append({k: _sanitize_value(v) for k, v in d.items()})
    return cleaned


def _fetch_mentions_unified(company_id: str, sources: List[str]):
    m = db.get_collection('mentions')
    if m is None:
        return None
    cid_filter = _company_filter(company_id)
    source_fields = ['source', 'type', 'platform', 'channel', 'category', 'sourceType']
    # Case-insensitive match for any of the expected values across possible fields
    or_source_ci = []
    for field in source_fields:
        for val in sources:
            or_source_ci.append({field: {'$regex': f"^{val}$", '$options': 'i'}})
    query = { '$and': [ cid_filter, {'$or': or_source_ci} ] }
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
    cid_filter = _company_filter(company_id)
    try:
        docs = list(m.find(cid_filter).sort('_id', -1))
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


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/dashboard/{company_id}", response_class=HTMLResponse)
async def dashboard(request: Request, company_id: str):
    company_name = company_id.replace('_', ' ').title()
    return templates.TemplateResponse("dashboard.html", {"request": request, "company_id": company_id, "company_name": company_name})


def _list_companies():
    if not db.is_enabled():
        return []
    try:
        companies = []
        ids: List[str] = []
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
        if not ids:
            candidates = set()
            for name in ["sentiments", "mentions", "news_mentions", "reddit_mentions", "twitter_mentions", "keywords", "themes"]:
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


@app.get("/api/companies")
async def api_companies():
    return JSONResponse(_list_companies())


@app.post("/api/analyze")
async def api_analyze(payload: Dict[str, Any], background: BackgroundTasks):
    company_name = payload.get('company_name')
    keywords = payload.get('keywords', '')
    if not company_name:
        return JSONResponse({'error': 'Company name is required.'}, status_code=400)
    keywords_list = [k.strip() for k in keywords.split(',') if k.strip()]
    background.add_task(run_analysis, company_name, keywords_list)
    company_id = company_name.replace(' ', '_').lower()
    return JSONResponse({'message': f'Analysis started for {company_name}.', 'company_id': company_id}, status_code=202)


@app.get("/api/analysis_status/{company_id}")
async def analysis_status(company_id: str):
    if db.is_enabled():
        try:
            s_col = db.get_collection('sentiments')
            if s_col is not None and s_col.find_one({'company_id': company_id}):
                return JSONResponse({'status': 'complete'})
        except Exception:
            pass
    return JSONResponse({'status': 'pending'})


@app.get("/api/health")
async def api_health():
    status: Dict[str, Any] = { 'mongo': 'disabled' }
    if db.is_enabled():
        try:
            database = db.get_db()
            status['mongo'] = 'connected' if database is not None else 'error'
            stats: Dict[str, Any] = {}
            for name in ['company_profiles', 'companies', 'mentions', 'sentiments', 'news_mentions', 'reddit_mentions', 'twitter_mentions', 'keywords', 'themes']:
                try:
                    col = db.get_collection(name)
                    stats[name] = col.estimated_document_count() if col is not None else 0
                except Exception:
                    stats[name] = 'err'
            status['counts'] = stats
        except Exception:
            status['mongo'] = 'error'
    return JSONResponse(status)


@app.get("/api/sentiment/{company_id}")
async def api_sentiment(company_id: str):
    if not db.is_enabled():
        return JSONResponse({'positive': 0, 'neutral': 0, 'negative': 0})
    try:
        s_col = db.get_collection('sentiments')
        if s_col is not None:
            doc = s_col.find_one({'company_id': company_id}, sort=[('date', -1)])
            if doc:
                return JSONResponse({'positive': int(doc.get('positive', 0)), 'neutral': int(doc.get('neutral', 0)), 'negative': int(doc.get('negative', 0))})
    except Exception:
        pass
    return JSONResponse({'positive': 0, 'neutral': 0, 'negative': 0})


@app.get("/api/keywords/{company_id}")
async def api_keywords(company_id: str):
    if not db.is_enabled():
        return JSONResponse([])
    try:
        k_col = db.get_collection('keywords')
        if k_col is not None:
            raw = list(k_col.find(_company_filter(company_id)).sort('date', -1))
            mapped = []
            for d in raw:
                d.pop('_id', None)
                # Map common field variants to expected keys
                k = d.get('keyword') or d.get('word') or d.get('term') or d.get('key') or d.get('name')
                c = d.get('count')
                if c is None:
                    for alt in ['frequency', 'freq', 'value', 'n']:
                        if alt in d:
                            c = d.get(alt)
                            break
                if k is not None and c is not None:
                    mapped.append({'keyword': k, 'count': c})
            if not mapped:
                # Fallback to raw if mapping failed
                mapped = [{k: v for k, v in d.items() if k != '_id'} for d in raw]
            return JSONResponse(_sanitize_docs(mapped))
    except Exception:
        pass
    return JSONResponse([])


@app.get("/api/debug/mentions/{company_id}")
async def debug_mentions(company_id: str):
    if not db.is_enabled():
        return JSONResponse({"error": "mongo disabled"}, status_code=500)
    info: Dict[str, Any] = {"company_id": company_id, "variants": _company_id_variants(company_id)}
    filt = _company_filter(company_id)
    samples: Dict[str, Any] = {}
    for name in ["mentions", "news_mentions", "reddit_mentions", "twitter_mentions"]:
        col = db.get_collection(name)
        try:
            if col is None:
                samples[name] = {"count": 0, "sample": []}
                continue
            count = col.count_documents(filt)
            docs = list(col.find(filt).sort('_id', -1).limit(3))
            for d in docs:
                d.pop('_id', None)
            samples[name] = {"count": count, "sample": _sanitize_docs(docs)}
        except Exception as e:
            samples[name] = {"error": str(e)}
    info["collections"] = samples
    return JSONResponse(info)

@app.get("/api/themes/{company_id}")
async def api_themes(company_id: str):
    if not db.is_enabled():
        return JSONResponse([])
    try:
        t_col = db.get_collection('themes')
        if t_col is not None:
            rows = list(t_col.find(_company_filter(company_id)).sort('date', -1))
            themes = [r.get('theme') for r in rows if r.get('theme')]
            return JSONResponse(themes)
    except Exception:
        pass
    return JSONResponse([])


@app.get("/api/news/{company_id}")
async def api_news(company_id: str):
    if not db.is_enabled():
        return JSONResponse([])
    try:
        unified = _fetch_mentions_unified(company_id, ['news', 'article'])
        if unified is not None and len(unified) > 0:
            return JSONResponse(unified[:100])
        inferred = _fetch_mentions_inferred(company_id, 'news')
        if inferred is not None and len(inferred) > 0:
            return JSONResponse(inferred[:100])
        col = db.get_collection('news_mentions')
        if col is not None:
            docs = list(col.find(_company_filter(company_id)).sort('_id', -1).limit(100))
            for d in docs:
                d.pop('_id', None)
            return JSONResponse(_sanitize_docs(docs))
        # Last resort: return any mentions for the company regardless of source
        m = db.get_collection('mentions')
        if m is not None:
            any_docs = list(m.find(_company_filter(company_id)).sort('_id', -1).limit(100))
            for d in any_docs:
                d.pop('_id', None)
            return JSONResponse(_sanitize_docs(any_docs))
    except Exception:
        pass
    return JSONResponse([])


@app.get("/api/reddit/{company_id}")
async def api_reddit(company_id: str):
    if not db.is_enabled():
        return JSONResponse([])
    try:
        unified = _fetch_mentions_unified(company_id, ['reddit'])
        if unified is not None and len(unified) > 0:
            return JSONResponse(unified[:100])
        inferred = _fetch_mentions_inferred(company_id, 'reddit')
        if inferred is not None and len(inferred) > 0:
            return JSONResponse(inferred[:100])
        col = db.get_collection('reddit_mentions')
        if col is not None:
            docs = list(col.find(_company_filter(company_id)).sort('_id', -1).limit(100))
            for d in docs:
                d.pop('_id', None)
            return JSONResponse(_sanitize_docs(docs))
        m = db.get_collection('mentions')
        if m is not None:
            any_docs = list(m.find(_company_filter(company_id)).sort('_id', -1).limit(100))
            for d in any_docs:
                d.pop('_id', None)
            return JSONResponse(_sanitize_docs(any_docs))
    except Exception:
        pass
    return JSONResponse([])


@app.get("/api/twitter/{company_id}")
async def api_twitter(company_id: str):
    if not db.is_enabled():
        return JSONResponse([])
    try:
        unified = _fetch_mentions_unified(company_id, ['twitter', 'x'])
        if unified is not None and len(unified) > 0:
            return JSONResponse(unified[:100])
        inferred = _fetch_mentions_inferred(company_id, 'twitter')
        if inferred is not None and len(inferred) > 0:
            return JSONResponse(inferred[:100])
        col = db.get_collection('twitter_mentions')
        if col is not None:
            docs = list(col.find(_company_filter(company_id)).sort('_id', -1).limit(100))
            for d in docs:
                d.pop('_id', None)
            return JSONResponse(_sanitize_docs(docs))
        m = db.get_collection('mentions')
        if m is not None:
            any_docs = list(m.find(_company_filter(company_id)).sort('_id', -1).limit(100))
            for d in any_docs:
                d.pop('_id', None)
            return JSONResponse(_sanitize_docs(any_docs))
    except Exception:
        pass
    return JSONResponse([])


# Note: Run with: uvicorn api_server:app --reload


