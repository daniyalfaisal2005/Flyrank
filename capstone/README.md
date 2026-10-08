# PagePulse — capstone

**Watches the web pages you care about, remembers every check, and reports only what changed.**
Polite scheduled checking, change history, cached summaries, and a weekly PDF report.

Stack: FastAPI · Postgres (Docker) · Supabase Auth · APScheduler · fpdf2 — $0.

## Concept table (requirement: 5+ concepts)

| # | Concept | Type | Where it lives |
|---|---------|------|----------------|
| 1 | API endpoints | core | `src/routes/` — watches CRUD, history, summary, jobs, reports |
| 2 | Database | core | Postgres — `watches` + `checks` tables (`sql/init.sql`, `src/db.py`) |
| 3 | Authentication | core | Supabase JWT verify — `src/auth.py`, `src/deps.py`, `src/routes/auth.py` |
| 4 | Background/cron jobs | core | APScheduler interval job — `src/main.py` (lifespan), `src/checker.py` |
| 5 | Reporting (PDF) | core | fpdf2 weekly report — `src/reports.py`, `src/routes/reports.py` |
| 6 | Caching logic | core | 60 s TTL summary cache with invalidation — `src/summaries.py` |
| 7 | Web scraping pipeline | **swap #1/2** | polite fetcher — `src/fetcher.py` (UA, timeout, 500 ms delay) |

**Non-goal (scope guard):** no real-time notifications (no email/SMS/webhooks) — changes
appear in the app and in the PDF only.

## Start (clean machine)

Setup (once):
1. `pip install -r capstone/requirements.txt`
2. copy `capstone/.env.example` to `capstone/.env` and fill in your `SUPABASE_URL` / `SUPABASE_KEY`

Run (two commands):
1. `docker compose -f capstone/docker-compose.yml up -d` → Postgres on **:5433**
2. `py -3 -m uvicorn src.main:app --host 127.0.0.1 --port 8001` (from `capstone/`) → API on **:8001** + scheduler

Swagger UI: http://127.0.0.1:8001/docs

## Demo path (5 minutes)

```text
1. py -3 capstone/scripts/seed.py        # demo account + 5 sandbox watches (prints login)
2. Open http://127.0.0.1:8001/docs → Authorize → login (demo credentials from step 1)
3. POST /jobs/run-now                    # one background check cycle now
4. GET  /watches/1/summary  (twice)       # first call cached:MISS, second cached:HIT
   GET  /watches/1/history               # every check, status, content hash, timing
5. POST /reports/weekly                   # PDF written to capstone/output/reports/
```

The scheduler also runs automatically every 15 minutes (`CHECK_INTERVAL_MINUTES` in `.env`).

## Endpoints

| Method + path | Auth | Notes |
|---|---|---|
| `POST /auth/signup` | no | 201, Supabase user |
| `POST /auth/login` | no | 200, returns access token |
| `POST /watches` | Bearer | 201; validates http(s) URL, 400 on duplicate |
| `GET /watches` | Bearer | only *your* watches (per-user rows) |
| `DELETE /watches/{id}` | Bearer | 204 / 404 |
| `GET /watches/{id}/history?limit=20` | Bearer | newest first |
| `GET /watches/{id}/summary` | Bearer | uptime%, changes, `cached: HIT\|MISS` |
| `POST /jobs/run-now` | Bearer | runs one check cycle synchronously |
| `POST /reports/weekly` | Bearer | 201, PDF path in response |
| `GET /health` | no | server + database status |

## Design notes

- **Politeness:** custom User-Agent, 10 s timeout, 500 ms delay between fetches; only
  `active` rows are checked; failed fetches are recorded, never crash the cycle.
- **Change detection:** SHA-256 of the page's *visible text* — a watch "changed" only when
  the text hash differs from the last successful check (layout/dynamic attributes ignored).
- **Failure demo:** the seed includes a deliberately broken URL so you can see failure
  handling (recorded `ok=false`, cycle keeps running).
- **Cache:** summaries are the expensive aggregation; cached 60 s per watch, invalidated
  after every check cycle so numbers never go stale across runs.
- **PDF:** one row per watch — 7-day checks, uptime %, change count, last check date
  (see `output/reports/sample-weekly-report.pdf` for a committed example).

## Target / ethics

Scraping targets are the official practice sandboxes (`books.toscrape.com`,
`quotes.toscrape.com`) which exist to be scraped politely. No real-world sites are
targeted. Production use must respect each site's robots.txt and terms of service.

## Future ideas (explicitly not built)

Real-time notifications (email/webhook alerts), per-watch custom intervals, page-diff
screenshots, browser extension, team accounts — each would break the 3-week / 5-feature
scope guard, so they stay here.
