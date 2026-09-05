CREATE TABLE IF NOT EXISTS repositories (
    repo_id BIGINT PRIMARY KEY,
    name TEXT NOT NULL,
    category TEXT NOT NULL,
    description TEXT,
    readme TEXT,
    html_url TEXT NOT NULL,
    forks INTEGER DEFAULT 0,
    contributors INTEGER DEFAULT 0,
    last_commit_date TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS star_snapshots (
    id SERIAL PRIMARY KEY,
    repo_id BIGINT REFERENCES repositories(repo_id),
    stars INTEGER NOT NULL,
    snapshot_date DATE NOT NULL DEFAULT CURRENT_DATE,
    UNIQUE (repo_id, snapshot_date)
);
