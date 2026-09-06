import os
import base64
import requests
import psycopg2
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

def fetch_readme(full_name):
    url = f"https://api.github.com/repos/{full_name}/readme"
    response = requests.get(url, headers=HEADERS)
    if response.status_code != 200:
        return None
    content = response.json().get("content", "")
    try:
        return base64.b64decode(content).decode("utf-8", errors="ignore")
    except Exception:
        return None

def main():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT repo_id, name FROM repositories WHERE readme IS NULL")
    repos = cur.fetchall()
    print(f"Fetching README for {len(repos)} repos...")

    for repo_id, full_name in repos:
        readme = fetch_readme(full_name)
        if readme:
            cur.execute("UPDATE repositories SET readme = %s WHERE repo_id = %s", (readme, repo_id))
            conn.commit()
            print(f"  {full_name}: README saved ({len(readme)} chars)")
        else:
            print(f"  {full_name}: no README found")

    conn.close()

if __name__ == "__main__":
    main()
