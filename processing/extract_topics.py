import os
import re
import html
import psycopg2
from collections import defaultdict
from sklearn.feature_extraction.text import TfidfVectorizer
from dotenv import load_dotenv

load_dotenv()

CUSTOM_STOPWORDS = [
    "use", "used", "using", "code", "run", "running", "free", "list",
    "book", "new", "just", "like", "make", "need", "want", "way",
    "example", "examples", "simple", "easy", "great", "good", "best",
    "project", "repository", "repo", "file", "files", "folder",
    "install", "installation", "setup", "usage", "getting", "started",
    "feature", "features", "support", "supported", "available",
    "contributing", "contribute", "contributors", "license", "licensed",
    "documentation", "docs", "readme", "table", "contents", "click",
    "star", "stars", "fork", "forks", "issue", "issues", "pull", "request",
    "page", "url", "build", "add", "added", "path", "version", "bug",
    "reproduce", "reproduced", "reproducing", "steps", "expected",
    "actual", "behavior", "behaviour", "response", "line", "lines",
    "user", "users", "api", "app", "apps", "application", "applications",
    "server", "client", "current", "currently", "does", "doesn", "did",
    "didn", "error", "errors", "problem", "problems", "work", "works",
    "working", "trying", "try", "tried", "help", "please", "thanks",
    "thank", "hi", "hello", "question", "questions", "answer", "answers",
]

def get_connection():
    return psycopg2.connect(
        host=os.getenv("POSTGRES_DB_HOST", "localhost"),
        port=os.getenv("POSTGRES_DB_PORT", "5432"),
        user=os.getenv("POSTGRES_USER"),
        password=os.getenv("POSTGRES_PASSWORD"),
        dbname=os.getenv("POSTGRES_DB"),
    )

def clean_text(text):
    text = html.unescape(text)
    text = re.sub(r"```.*?```", " ", text, flags=re.DOTALL)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"&\w+;", " ", text)
    text = re.sub(r"!\[.*?\]\(.*?\)", " ", text)
    text = re.sub(r"\[.*?\]\(.*?\)", " ", text)
    text = re.sub(r"http\S+", " ", text)
    text = re.sub(r"[#*`_>\[\]()!|:=/\\-]", " ", text)
    text = re.sub(r"\b(img|href|src|alt|td|tr|br|md|div|span|width|height|align|style|class|badge|shields|svg|png|jpg|gif|com|www|github|io|nbsp|amp)\b", " ", text)
    text = re.sub(r"\d+", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip().lower()

def repo_name_tokens(full_name):
    parts = re.split(r"[/_\-\.]", full_name.lower())
    return set(p for p in parts if p)

def get_docs_by_category():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT category, name, COALESCE(readme, ''), COALESCE(issues_text, '')
        FROM repositories
    """)
    rows = cur.fetchall()
    conn.close()

    by_category = defaultdict(list)
    all_name_tokens = set()
    for category, name, readme, issues_text in rows:
        combined = readme + " " + issues_text
        by_category[category].append(clean_text(combined))
        all_name_tokens |= repo_name_tokens(name)
    return by_category, all_name_tokens

def extract_top_keywords(docs, extra_stopwords, top_n=10):
    stop_words = list(TfidfVectorizer(stop_words="english").get_stop_words())
    stop_words += CUSTOM_STOPWORDS
    stop_words += list(extra_stopwords)
    vectorizer = TfidfVectorizer(
        stop_words=stop_words,
        max_features=500,
        ngram_range=(1, 2),
        min_df=2,
        max_df=0.7,
    )
    tfidf_matrix = vectorizer.fit_transform(docs)
    scores = tfidf_matrix.sum(axis=0).A1
    terms = vectorizer.get_feature_names_out()
    ranked = sorted(zip(terms, scores), key=lambda x: x[1], reverse=True)
    return ranked[:top_n]

def main():
    by_category, all_name_tokens = get_docs_by_category()
    for category, docs in by_category.items():
        print(f"\n=== {category} ({len(docs)} repos) ===")
        top_keywords = extract_top_keywords(docs, all_name_tokens)
        for term, score in top_keywords:
            print(f"  {term}: {score:.2f}")

if __name__ == "__main__":
    main()
