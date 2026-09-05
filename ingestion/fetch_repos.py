import os
import requests
import psycopg2
from dotenv import load_dotenv

load_dotenv()

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
HEADERS = {"Authorization": f"token {GITHUB_TOKEN}"}

CATEGORIES = {
    "web-dev": "topic:web-development stars:>1000",
    "ai": "topic:artificial-intelligence stars:>1000",
    "data-science": "topic:data-science stars:>1000",
    "cyber-security": "topic:cyber-security stars:>1000",
    "mobile": "topic:mobile stars:>1000",
}

def fetch_repos(query, per_page=10):
    url = "https://api.github.com/search/repositories"
    params = {"q": query, "sort": "stars", "order": "desc", "per_page": per_page}
    response = requests.get(url, headers=HEADERS, params=params)
    response.raise_for_status()
    return response.json()["items"]

def save_to_db(repo, category, conn):
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO repositories (repo_id, name, category, description, html_url, forks, created_at)
        VALUES (%s, %s, %s, %s, %s, %s, NOW())
        ON CONFLICT (repo_id) DO UPDATE SET
            forks = EXCLUDED.forks,
            description = EXCLUDED.description
    """, (repo["id"], repo["full_name"], category, repo["description"], repo["html_url"], repo["forks"]))
    cur.execute("""
        INSERT INTO star_snapshots (repo_id, stars)
        VALUES (%s, %s)
        ON CONFLICT (repo_id, snapshot_date) DO UPDATE SET stars = EXCLUDED.stars
    """, (repo["id"], repo["stargazers_count"]))
    conn.commit()

def main():
    conn = psycopg2.connect(
        host="localhost",
        port=os.getenv("POSTGRES_DB_PORT", "5432"),
        user=os.getenv("POSTGRES_USER"),
        password=os.getenv("POSTGRES_PASSWORD"),
        dbname=os.getenv("POSTGRES_DB"),
    )
    for category, query in CATEGORIES.items():
        print(f"Fetching category: {category}")
        repos = fetch_repos(query)
        for repo in repos:
            save_to_db(repo, category, conn)
        print(f"  Saved {len(repos)} repos")
    conn.close()

if __name__ == "__main__":
    main()
