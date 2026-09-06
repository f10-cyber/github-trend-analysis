import os
import streamlit as st
import requests

API_BASE = os.getenv("API_BASE_URL", "http://localhost:8000")

CATEGORIES = {
    "Web Dev": "web-dev",
    "AI": "ai",
    "Data Science": "data-science",
    "Cyber Security": "cyber-security",
    "Mobile": "mobile",
}

st.set_page_config(page_title="GitHub Trend Analysis", layout="wide")
st.title("📊 GitHub Trend Analysis System")
st.caption("Top repo trending, topik, dan engagement per kategori")

def fetch(endpoint):
    try:
        response = requests.get(f"{API_BASE}{endpoint}", timeout=30)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        st.error(f"Gagal mengambil data dari API: {e}")
        return None

category_label = st.selectbox("Pilih kategori", list(CATEGORIES.keys()))
category = CATEGORIES[category_label]

tab_trending, tab_topik, tab_engagement = st.tabs(["🔥 Trending", "🏷️ Topik", "⭐ Engagement"])

with tab_trending:
    data = fetch(f"/trending/{category}?periode=30")
    if data:
        if data["data"] and data["data"][0]["limited_data"]:
            st.info(
                f"Histori bintang baru {data['data'][0]['data_days_available']} hari "
                "terkumpul, jadi angka pertumbuhan masih terbatas. Makin lama sistem "
                "jalan, makin akurat."
            )
        for i, repo in enumerate(data["data"], 1):
            with st.container(border=True):
                col1, col2 = st.columns([4, 1])
                with col1:
                    st.markdown(f"**{i}. {repo['name']}**")
                    st.write(f"⭐ {repo['stars']:,} stars | 📈 {repo['growth_per_day']:+.2f} stars/hari")
                with col2:
                    st.link_button("Buka di GitHub", repo["github_url"])

with tab_topik:
    data = fetch(f"/topik/{category}")
    if data:
        cols = st.columns(2)
        for i, item in enumerate(data["data"]):
            with cols[i % 2]:
                st.metric(label=item["topik"], value=item["frekuensi"])

with tab_engagement:
    data = fetch(f"/engagement/{category}")
    if data:
        for i, repo in enumerate(data["data"], 1):
            with st.container(border=True):
                col1, col2 = st.columns([4, 1])
                with col1:
                    st.markdown(f"**{i}. {repo['name']}** — skor: {repo['score']:,}")
                    st.write(
                        f"⭐ {repo['stars']:,} | 🍴 {repo['forks']:,} | "
                        f"👥 {repo['contributors']} kontributor | "
                        f"📝 {repo['commits_30d']} commit/30hari"
                    )
                with col2:
                    st.link_button("Buka di GitHub", repo["github_url"])
