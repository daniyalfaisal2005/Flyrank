CREATE TABLE IF NOT EXISTS watches (
    id SERIAL PRIMARY KEY,
    user_id TEXT NOT NULL,
    url TEXT NOT NULL,
    label TEXT NOT NULL,
    active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (user_id, url)
);

CREATE TABLE IF NOT EXISTS checks (
    id SERIAL PRIMARY KEY,
    watch_id INTEGER NOT NULL REFERENCES watches(id) ON DELETE CASCADE,
    checked_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    status_code INTEGER,
    ok BOOLEAN NOT NULL,
    changed BOOLEAN NOT NULL DEFAULT FALSE,
    content_hash TEXT,
    response_ms INTEGER,
    error TEXT
);

CREATE INDEX IF NOT EXISTS checks_watch_id_checked_at_idx
    ON checks (watch_id, checked_at DESC);
