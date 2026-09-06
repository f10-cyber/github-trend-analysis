import sys
import os
import json
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from fastapi import FastAPI, HTTPException
import redis
from processing.scoring import get_engagement_ranking, get_trending_ranking
from processing.extract_topics_spacy import get_top_topics_for_category

app = FastAPI(title="GitHub Trend Analysis API")

VALID_CATEGORIES = ["web-dev", "ai", "data-science", "cyber-security", "mobile"]

redis_client = redis.Redis(
    host=os.getenv("REDIS_HOST", "localhost"),
    port=int(os.getenv("REDIS_PORT", 6379)),
    decode_responses=True,
)

CACHE_TTL_SECONDS = 3600  # 1 jam, sesuai saran panduan Tahap 10

def cache_get(key):
    try:
        value = redis_client.get(key)
        return json.loads(value) if value else None
    except redis.RedisError:
        return None

def cache_set(key, value, ttl=CACHE_TTL_SECONDS):
    try:
        redis_client.setex(key, ttl, json.dumps(value))
    except redis.RedisError:
        pass

def validate_category(category: str):
    if category not in VALID_CATEGORIES:
        raise HTTPException(
            status_code=404,
            detail=f"Kategori '{category}' tidak ditemukan. Pilihan: {VALID_CATEGORIES}"
        )

@app.get("/health")
def health():
    return {"status": "ok"}

@app.get("/trending/{category}")
def trending(category: str, periode: int = 30):
    validate_category(category)
    cache_key = f"trending:{category}:{periode}"
    cached = cache_get(cache_key)
    if cached:
        return {**cached, "cached": True}

    results = get_trending_ranking(category, days=periode)
    response = {
        "category": category,
        "periode_hari": periode,
        "data": [
            {
                "name": name,
                "github_url": url,
                "stars": stars,
                "growth_per_day": round(growth, 2),
                "data_days_available": actual_days,
                "limited_data": limited,
            }
            for name, url, stars, growth, actual_days, limited in results
        ],
    }
    cache_set(cache_key, response)
    return {**response, "cached": False}

@app.get("/engagement/{category}")
def engagement(category: str):
    validate_category(category)
    cache_key = f"engagement:{category}"
    cached = cache_get(cache_key)
    if cached:
        return {**cached, "cached": True}

    results = get_engagement_ranking(category)
    response = {
        "category": category,
        "data": [
            {
                "name": name,
                "github_url": url,
                "stars": stars,
                "forks": forks,
                "contributors": contributors,
                "commits_30d": commits_30d,
                "score": round(score, 1),
            }
            for name, url, stars, forks, contributors, commits_30d, score in results
        ],
    }
    cache_set(cache_key, response)
    return {**response, "cached": False}

@app.get("/topik/{category}")
def topik(category: str):
    validate_category(category)
    cache_key = f"topik:{category}"
    cached = cache_get(cache_key)
    if cached:
        return {**cached, "cached": True}

    results = get_top_topics_for_category(category)
    response = {
        "category": category,
        "data": [
            {"topik": phrase, "frekuensi": count}
            for phrase, count in results
        ],
    }
    cache_set(cache_key, response, ttl=21600)  # topik jarang berubah, cache 6 jam
    return {**response, "cached": False}
