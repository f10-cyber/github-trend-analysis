import os
import psycopg2
from datetime import date, timedelta
from dotenv import load_dotenv

load_dotenv()

def get_connection():
    return psycopg2.connect(
        host=os.getenv("POSTGRES_DB_HOST", "localhost"),
        port=os.getenv("POSTGRES_DB_PORT", "5432"),
        user=os.getenv("POSTGRES_USER"),
        password=os.getenv("POSTGRES_PASSWORD"),
        dbname=os.getenv("POSTGRES_DB"),
    )

def get_engagement_ranking(category, top_n=10):
    """
    Skor engagement = (stars * 0.4) + (forks * 0.3) + (kontributor * 0.2) + (commits_30d * 0.1)
    Bobot ini sesuai contoh di panduan: stars & forks dianggap paling
    menunjukkan popularitas, kontributor & aktivitas commit menunjukkan
    seberapa hidup proyeknya.
    """
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT r.repo_id, r.name, r.html_url, r.forks, r.contributors, r.commits_30d,
               COALESCE(s.stars, 0) AS stars
        FROM repositories r
        LEFT JOIN LATERAL (
            SELECT stars FROM star_snapshots
            WHERE repo_id = r.repo_id
            ORDER BY snapshot_date DESC LIMIT 1
        ) s ON true
        WHERE r.category = %s
    """, (category,))
    rows = cur.fetchall()
    conn.close()

    scored = []
    for repo_id, name, url, forks, contributors, commits_30d, stars in rows:
        score = (stars * 0.4) + (forks * 0.3) + (contributors * 0.2) + (commits_30d * 0.1)
        scored.append((name, url, stars, forks, contributors, commits_30d, score))

    scored.sort(key=lambda x: x[-1], reverse=True)
    return scored[:top_n]

def get_trending_ranking(category, days=30, top_n=10):
    """
    Skor trending = (stars_sekarang - stars_N_hari_lalu) / N_hari
    Catatan: karena histori stars baru mulai dikumpulkan, kalau data
    N hari lalu belum ada, kita pakai snapshot paling awal yang tersedia
    dan tandai sebagai data terbatas.
    """
    conn = get_connection()
    cur = conn.cursor()
    cutoff = date.today() - timedelta(days=days)

    cur.execute("""
        SELECT r.repo_id, r.name, r.html_url
        FROM repositories r
        WHERE r.category = %s
    """, (category,))
    repos = cur.fetchall()

    scored = []
    for repo_id, name, url in repos:
        cur.execute("""
            SELECT stars, snapshot_date FROM star_snapshots
            WHERE repo_id = %s ORDER BY snapshot_date DESC LIMIT 1
        """, (repo_id,))
        latest = cur.fetchone()
        if not latest:
            continue
        stars_now, latest_date = latest

        cur.execute("""
            SELECT stars, snapshot_date FROM star_snapshots
            WHERE repo_id = %s AND snapshot_date <= %s
            ORDER BY snapshot_date DESC LIMIT 1
        """, (repo_id, cutoff))
        old = cur.fetchone()

        if old:
            stars_old, old_date = old
            actual_days = (latest_date - old_date).days or 1
            limited_data = False
        else:
            cur.execute("""
                SELECT stars, snapshot_date FROM star_snapshots
                WHERE repo_id = %s ORDER BY snapshot_date ASC LIMIT 1
            """, (repo_id,))
            stars_old, old_date = cur.fetchone()
            actual_days = (latest_date - old_date).days or 1
            limited_data = True

        growth_per_day = (stars_now - stars_old) / actual_days
        scored.append((name, url, stars_now, growth_per_day, actual_days, limited_data))

    conn.close()
    scored.sort(key=lambda x: x[3], reverse=True)
    return scored[:top_n]

CATEGORIES = ["web-dev", "ai", "data-science", "cyber-security", "mobile"]

def main():
    for category in CATEGORIES:
        print(f"\n{'='*50}")
        print(f"KATEGORI: {category.upper()}")
        print(f"{'='*50}")

        print("\n--- Top 10 Engagement ---")
        for i, (name, url, stars, forks, contributors, commits_30d, score) in enumerate(get_engagement_ranking(category), 1):
            print(f"{i}. {name} (score: {score:.1f}) | stars={stars} forks={forks} contributors={contributors} commits/30d={commits_30d}")
            print(f"   {url}")

        print("\n--- Top 10 Trending (30 hari) ---")
        results = get_trending_ranking(category, days=30)
        if results and results[0][5]:
            print("[Catatan: histori stars baru mulai dikumpulkan, growth dihitung dari data yang tersedia]")
        for i, (name, url, stars, growth, actual_days, limited) in enumerate(results, 1):
            print(f"{i}. {name} (growth: {growth:+.2f} stars/hari selama {actual_days} hari) | stars={stars}")
            print(f"   {url}")

if __name__ == "__main__":
    main()
