import os
import time
import requests
import psycopg2
from multiprocessing import Pool
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

def fetch_repos(query, per_page=50):
    url = "https://api.github.com/search/repositories"
    params = {"q": query, "sort": "stars", "order": "desc", "per_page": per_page}
    response = requests.get(url, headers=HEADERS, params=params)
    response.raise_for_status()
    return response.json()["items"]

def get_connection():
    return psycopg2.connect(
        host=os.getenv("POSTGRES_DB_HOST", "localhost"),
        port=os.getenv("POSTGRES_DB_PORT", "5432"),
        user=os.getenv("POSTGRES_USER"),
        password=os.getenv("POSTGRES_PASSWORD"),
        dbname=os.getenv("POSTGRES_DB"),
    )

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

def process_category(item):
    category, query = item
    conn = get_connection()
    repos = fetch_repos(query)
    for repo in repos:
        save_to_db(repo, category, conn)
    conn.close()
    return f"{category}: saved {len(repos)} repos"

def run_sequential():
    start = time.time()
    for item in CATEGORIES.items():
        result = process_category(item)
        print(f"  {result}")
    elapsed = time.time() - start
    print(f"Sequential total time: {elapsed:.2f}s")
    return elapsed

def run_parallel():
    start = time.time()
    with Pool(processes=5) as pool:
        results = pool.map(process_category, CATEGORIES.items())
    for r in results:
        print(f"  {r}")
    elapsed = time.time() - start
    print(f"Parallel total time: {elapsed:.2f}s")
    return elapsed

if __name__ == "__main__":
    print("Running SEQUENTIAL:")
    seq_time = run_sequential()

    print("\nRunning PARALLEL:")
    par_time = run_parallel()

    print(f"\nSpeedup: {seq_time / par_time:.2f}x faster with parallel processing")
