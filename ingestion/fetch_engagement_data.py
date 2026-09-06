import os
import requests
import psycopg2
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv

load_dotenv()

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
HEADERS = {"Authorization": f"token {GITHUB_TOKEN}"}

def get_connection():
    return psycopg2.connect(
        host=os.getenv("POSTGRES_DB_HOST", "localhost"),
        port=os.getenv("POSTGRES_DB_PORT", "5432"),
        user=os.getenv("POSTGRES_USER"),
        password=os.getenv("POSTGRES_PASSWORD"),
        dbname=os.getenv("POSTGRES_DB"),
    )

def fetch_contributor_count(full_name):
    url = f"https://api.github.com/repos/{full_name}/contributors"
    params = {"per_page": 1, "anon": "false"}
    response = requests.get(url, headers=HEADERS, params=params)
    if response.status_code != 200:
        return 0
    if "Link" in response.headers:
        link = response.headers["Link"]
        for part in link.split(","):
            if 'rel="last"' in part:
                try:
                    return int(part.split("page=")[-1].split(">")[0])
                except (ValueError, IndexError):
                    pass
    return len(response.json())

def fetch_last_commit_date(full_name):
    url = f"https://api.github.com/repos/{full_name}/commits"
    params = {"per_page": 1}
    response = requests.get(url, headers=HEADERS, params=params)
    if response.status_code != 200 or not response.json():
        return None
    return response.json()[0]["commit"]["committer"]["date"]

def fetch_commit_count_last_30_days(full_name):
    since = (datetime.now(timezone.utc) - timedelta(days=30)).isoformat()
    url = f"https://api.github.com/repos/{full_name}/commits"
    params = {"since": since, "per_page": 100}
    response = requests.get(url, headers=HEADERS, params=params)
    if response.status_code != 200:
        return 0
    return len(response.json())

def main():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT repo_id, name FROM repositories")
    repos = cur.fetchall()
    print(f"Fetching engagement data for {len(repos)} repos...")

    for repo_id, full_name in repos:
        contributors = fetch_contributor_count(full_name)
        last_commit = fetch_last_commit_date(full_name)
        commit_count_30d = fetch_commit_count_last_30_days(full_name)
        cur.execute("""
            UPDATE repositories
            SET contributors = %s, last_commit_date = %s, commits_30d = %s
            WHERE repo_id = %s
        """, (contributors, last_commit, commit_count_30d, repo_id))
        conn.commit()
        print(f"  {full_name}: {contributors} contributors, {commit_count_30d} commits/30d")

    conn.close()

if __name__ == "__main__":
    main()
