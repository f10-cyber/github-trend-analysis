import os
import requests
import psycopg2
from dotenv import load_dotenv

load_dotenv()

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
HEADERS = {"Authorization": f"token {GITHUB_TOKEN}"}

def get_connection():
    return psycopg2.connect(
        host="localhost",
        port=os.getenv("POSTGRES_DB_PORT", "5432"),
        user=os.getenv("POSTGRES_USER"),
        password=os.getenv("POSTGRES_PASSWORD"),
        dbname=os.getenv("POSTGRES_DB"),
    )

def fetch_issues(full_name, per_page=20):
    url = f"https://api.github.com/repos/{full_name}/issues"
    params = {"state": "all", "per_page": per_page, "sort": "created", "direction": "desc"}
    response = requests.get(url, headers=HEADERS, params=params)
    if response.status_code != 200:
        return ""
    items = response.json()
    texts = []
    for item in items:
        if "pull_request" in item:
            continue
        title = item.get("title") or ""
        body = item.get("body") or ""
        texts.append(title + " " + body)
    return " ".join(texts)

def main():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT repo_id, name FROM repositories WHERE issues_text IS NULL")
    repos = cur.fetchall()
    print(f"Fetching issues for {len(repos)} repos...")

    for repo_id, full_name in repos:
        text = fetch_issues(full_name)
        cur.execute("UPDATE repositories SET issues_text = %s WHERE repo_id = %s", (text, repo_id))
        conn.commit()
        print(f"  {full_name}: {len(text)} chars from issues")

    conn.close()

if __name__ == "__main__":
    main()
