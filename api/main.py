import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from fastapi import FastAPI, HTTPException
from processing.scoring import get_engagement_ranking, get_trending_ranking
from processing.extract_topics_spacy import get_top_topics_for_category

app = FastAPI(title="GitHub Trend Analysis API")

VALID_CATEGORIES = ["web-dev", "ai", "data-science", "cyber-security", "mobile"]

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
    results = get_trending_ranking(category, days=periode)
    return {
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

@app.get("/engagement/{category}")
def engagement(category: str):
    validate_category(category)
    results = get_engagement_ranking(category)
    return {
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

@app.get("/topik/{category}")
def topik(category: str):
    validate_category(category)
    results = get_top_topics_for_category(category)
    return {
        "category": category,
        "data": [
            {"topik": phrase, "frekuensi": count}
            for phrase, count in results
        ],
    }
