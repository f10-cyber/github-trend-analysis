import os
import re
import html
import spacy
import psycopg2
from collections import defaultdict, Counter
from dotenv import load_dotenv

load_dotenv()

nlp = spacy.load("en_core_web_sm", disable=["ner"])

GENERIC_WORDS = {
    "use", "code", "run", "free", "list", "book", "new", "way", "example",
    "project", "repository", "repo", "file", "folder", "issue",
    "feature", "support", "license", "documentation", "doc",
    "table", "content", "star", "fork", "pull",
    "request", "page", "url", "build", "path", "version", "bug",
    "step", "behavior", "response", "user", "api", "app",
    "application", "server", "client", "error",
    "problem", "work", "question", "answer",
    "thing", "something", "someone", "everything",
    "time", "lot", "bit", "part", "case", "chapter", "lesson",
    "tutorial", "section", "finding", "bsd", "mit", "apache", "gpl",
    "gplv", "lgpl", "mpl", "isc", "unlicense", "copyright",
}

def get_connection():
    return psycopg2.connect(
        host=os.getenv("POSTGRES_DB_HOST", "localhost"),
        port=os.getenv("POSTGRES_DB_PORT", "5432"),
        user=os.getenv("POSTGRES_USER"),
        password=os.getenv("POSTGRES_PASSWORD"),
        dbname=os.getenv("POSTGRES_DB"),
    )

def basic_clean(text):
    text = html.unescape(text)
    text = re.sub(r"```.*?```", " ", text, flags=re.DOTALL)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"&\w+;", " ", text)
    text = re.sub(r"!\[.*?\]\(.*?\)", " ", text)
    text = re.sub(r"\[.*?\]\(.*?\)", " ", text)
    text = re.sub(r"http\S+", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()

def repo_name_tokens(full_name):
    parts = re.split(r"[/_\-\.]", full_name.lower())
    return set(p for p in parts if p)

def is_valid_chunk(chunk):
    if chunk.root.pos_ not in ("NOUN", "PROPN"):
        return False
    if all(tok.is_stop or tok.pos_ == "PRON" for tok in chunk):
        return False
    return True

def lemmatize_phrase(chunk):
    words = [tok.lemma_.lower() for tok in chunk if tok.pos_ in ("NOUN", "PROPN", "ADJ")]
    phrase = " ".join(words)
    phrase = re.sub(r"[^a-z\s]", "", phrase).strip()
    phrase = re.sub(r"\s+", " ", phrase)
    return phrase

def is_valid_phrase(phrase, name_tokens):
    words = phrase.split()
    if len(words) < 1 or len(words) > 3:
        return False
    if any(w in GENERIC_WORDS for w in words):
        return False
    if any(w in name_tokens for w in words):
        return False
    if any(len(w) <= 2 for w in words):
        return False
    return True

def extract_noun_phrases(text, name_tokens, max_chars=200000):
    text = text[:max_chars]
    doc = nlp(text)
    phrases = []
    for chunk in doc.noun_chunks:
        if not is_valid_chunk(chunk):
            continue
        phrase = lemmatize_phrase(chunk)
        if is_valid_phrase(phrase, name_tokens):
            phrases.append(phrase)
    return phrases

def get_all_repo_name_tokens():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT name FROM repositories")
    names = [row[0] for row in cur.fetchall()]
    conn.close()
    tokens = set()
    for name in names:
        tokens |= repo_name_tokens(name)
    return tokens

def get_top_topics_for_category(category, top_n=10):
    """Dipanggil dari API: hitung topik NLP untuk satu kategori saja."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT COALESCE(readme, ''), COALESCE(issues_text, '')
        FROM repositories WHERE category = %s
    """, (category,))
    rows = cur.fetchall()
    conn.close()

    name_tokens = get_all_repo_name_tokens()
    counter = Counter()
    for readme, issues_text in rows:
        combined = basic_clean(readme + " " + issues_text)
        phrases = extract_noun_phrases(combined, name_tokens)
        counter.update(phrases)

    return counter.most_common(top_n)

def get_all_docs_by_category():
    """Dipakai buat mode standalone (python3 processing/extract_topics_spacy.py)."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT category, name, COALESCE(readme, ''), COALESCE(issues_text, '')
        FROM repositories
    """)
    rows = cur.fetchall()
    conn.close()

    by_category = defaultdict(list)
    for category, name, readme, issues_text in rows:
        by_category[category].append((readme, issues_text))
    return by_category

def main():
    by_category = get_all_docs_by_category()
    name_tokens = get_all_repo_name_tokens()
    for category, docs in by_category.items():
        print(f"\n=== {category} ===")
        counter = Counter()
        for readme, issues_text in docs:
            combined = basic_clean(readme + " " + issues_text)
            phrases = extract_noun_phrases(combined, name_tokens)
            counter.update(phrases)
        for phrase, count in counter.most_common(10):
            print(f"  {phrase}: {count}")

if __name__ == "__main__":
    main()
