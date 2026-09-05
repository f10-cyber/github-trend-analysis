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
    "tutorial", "section", "finding", "bsd", "mit", "apache", "gpl", "gplv", "lgpl", "mpl", "isc", "unlicense", "copyright",
}

def get_connection():
    return psycopg2.connect(
        host="localhost",
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
    # Buang kalau ada pronoun/determiner sendirian, atau root-nya bukan kata benda
    if chunk.root.pos_ not in ("NOUN", "PROPN"):
        return False
    # Buang kalau semua token di chunk itu stopword/pronoun
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

def main():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT category, name, COALESCE(readme, ''), COALESCE(issues_text, '')
        FROM repositories
    """)
    rows = cur.fetchall()
    conn.close()

    by_category = defaultdict(Counter)
    all_name_tokens = set()
    for _, name, _, _ in rows:
        all_name_tokens |= repo_name_tokens(name)

    for category, name, readme, issues_text in rows:
        combined = basic_clean(readme + " " + issues_text)
        phrases = extract_noun_phrases(combined, all_name_tokens)
        by_category[category].update(phrases)

    for category, counter in by_category.items():
        print(f"\n=== {category} ===")
        for phrase, count in counter.most_common(10):
            print(f"  {phrase}: {count}")

if __name__ == "__main__":
    main()
