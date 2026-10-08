# My 10x Solution — Daniyal Faisal

**PagePulse** — watches the web pages you care about, remembers every check, and reports
only what changed. FastAPI + Postgres + Supabase Auth + APScheduler + fpdf2. Capstone of
the FlyRank Backend Track, in `capstone/` of this repository.

---

## 1. What is the problem you are solving?

People who must not miss a change on a handful of web pages — a product price, a stock
line, a policy paragraph, an exam-date announcement — check those pages by hand, over and
over, and usually notice the change too late. Clicking through 10 pages and reading them
takes roughly **20 minutes a day**, and nothing remembers what the page said or exactly
when it changed. PagePulse watches those pages every 15 minutes, stores every check, and
shows only what changed — reviewing all 10 pages takes about **30 seconds a day**. That is
the 10x: same coverage, a tenth of the time, plus a permanent history and a weekly PDF.

The 10x number, one line: *finding a page change by hand took ~20 minutes a day; with
PagePulse it takes ~30 seconds a day.*

---

## 2. How did you implement your solution?

In plain words: you sign up with email/password (Supabase), add URLs to watch, and the API
stores them in Postgres. A background scheduler runs every 15 minutes and politely fetches
each URL (custom user-agent, 10 s timeout, 500 ms delay), records the HTTP status, the
response time, and a SHA-256 hash of the page's visible text, and flags a *change* when the
hash differs from the last successful check. Failed fetches are recorded as failures and
never crash the cycle. Summaries (uptime %, change counts) are the expensive aggregation,
so they are cached for 60 seconds and invalidated after every check cycle. A weekly PDF
report gives one row per watch: 7-day checks, uptime, changes, last check. Every route
except signup/login/health requires a Bearer token, and each user sees only their own
watches.

**The 5+ concepts (concept → where it lives):**

| # | Concept | Where in the code |
|---|---------|-------------------|
| 1 | API endpoints | `src/routes/` — watches CRUD, history, summary, jobs, reports |
| 2 | Database | `sql/init.sql`, `src/db.py` — `watches` + `checks` tables |
| 3 | Authentication | `src/auth.py`, `src/deps.py`, `src/routes/auth.py` — Supabase JWT |
| 4 | Background/cron jobs | `src/main.py` (APScheduler lifespan), `src/checker.py` |
| 5 | Reporting (PDF) | `src/reports.py`, `src/routes/reports.py` — fpdf2 |
| 6 | Caching logic | `src/summaries.py` — 60 s TTL cache + invalidation |
| 7 | Web scraping pipeline (swap) | `src/fetcher.py` — polite page fetcher |

Six concepts come from the core table; **1 swap** is used (max 2):
**Swap 1 — web scraping** replaces nothing weak in the core set; it adds the only way to
observe an external page's state — a pure API/database solution cannot read a page.

**Non-goal (what I deliberately did NOT build):** no real-time notifications — no email,
SMS, or webhook alerts. Changes appear in the app and in the PDF only. It is the shiny
feature that would have broken the scope guard; it is parked in the README under
"Future ideas".

**Scope:** exactly 5 core features (auth, watch CRUD, scheduled checker, history+cached
summary, PDF report), ~1 week of part-time work because every part was reused from earlier
program assignments (auth, CRUD+Postgres, background job, scraper, PDF).

---

## 3. How to run it

Setup once: `pip install -r capstone/requirements.txt`, copy `capstone/.env.example` to
`capstone/.env` and add your Supabase URL/key.

Start on a clean machine — two commands:

1. `docker compose -f capstone/docker-compose.yml up -d` (Postgres on :5433)
2. `py -3 -m uvicorn src.main:app --host 127.0.0.1 --port 8001` from `capstone/` (API on
   :8001 + scheduler)

Demo path: `py -3 capstone/scripts/seed.py` (prints demo login, creates 5 sandbox watches)
→ open `http://127.0.0.1:8001/docs` → Authorize → `POST /jobs/run-now` →
`GET /watches/1/summary` twice (cached `MISS` then `HIT`) → `POST /reports/weekly` → open
the PDF from `capstone/output/reports/`. Full walkthrough: `capstone/README.md`.

---

## 4. Requirements tick

- [x] Problem written down; a stranger understands it from this document
- [x] At least 5 concepts implemented — 7 (6 core + 1 swap), table in README and above
- [x] Maximum 2 swaps — 1 used, one-line reason above
- [x] Starts with documented commands on a clean machine — two commands in README
- [x] Demo data seeded; README 5-minute demo path tested (18/18 checks pass)
- [x] No secrets in the repo; `.gitignore` covers `.env` and generated artifacts
      (verified: `.env` has never appeared in git history)
- [x] Repository public on GitHub; capstone in its own clearly named `capstone/` folder
- [x] Commit history follows the milestone pattern — 8 commits, M1 → M5, one message each
- [x] $0 stack — every service has a free tier, no credit card
- [x] Scope guard — 5 core features, 1 explicit non-goal, one problem / one solution
- [x] Overview document named exactly `My 10x Solution - Daniyal Faisal.md`

Not built (optional stretch, out of scope): live deployment, demo video, test suite.
