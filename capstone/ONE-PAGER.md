# PagePulse — one-pager (Capstone M1)

## The problem (3 sentences)

People who care about a handful of web pages — a product price, a stock status, a policy
line, an exam-date announcement — check them by hand, over and over, and usually notice a
change too late. Clicking through 10 pages, reading them, and remembering what they said
takes roughly 20 minutes a day, and nothing records what changed or exactly when. PagePulse
watches those pages on a schedule, remembers every check, and reports only what actually
changed.

## Who has this problem

Freelancers, interns, small-site owners, students watching deadline/announcement pages, and
anyone monitoring a competitor's price — people with a small, fixed set of pages they must
not miss, but no enterprise monitoring budget.

## The 10x claim

Checking 10 pages by hand takes about **20 minutes a day**; PagePulse checks them every 15
minutes and shows only the diff — reviewing what changed takes about **30 seconds a day**.
That is the 10x: same coverage, a tenth of the time, plus a permanent history.

## The 5+ concepts (from the concept rule)

| # | Concept | Type | Where it will live |
|---|---|---|---|
| 1 | API endpoints | core | `src/routes/` — watches CRUD, history, summary, run-now, report |
| 2 | Database | core | Postgres — `watches` + `checks` tables (survives restart) |
| 3 | Authentication | core | Supabase verify dependency — protected routes, per-user data |
| 4 | Background/cron jobs | core | APScheduler interval job (every 15 minutes) |
| 5 | Reporting (PDF) | core | fpdf2 — weekly status PDF per user |
| 6 | Caching logic | core | TTL cache of expensive per-watch summaries (HIT/MISS logged) |
| 7 | Web scraping pipeline | swap #1 | polite fetcher (user-agent, timeout, delay, status check) |

Swap reason: **web scraping replaced nothing core** — it stands in for the polite-collection
version of "background data acquisition": the checker collects page bodies externally, which
a pure API/database solution would not do. Only 1 of the allowed 2 swaps is used; all six
other concepts come from the core table.

## The one explicit non-goal

**No real-time notifications.** PagePulse will not send email, SMS, or webhook alerts.
Changes appear only in the app (history/summary) and in the generated PDF report. Push
notifications are the shiny feature that would balloon scope — they are written down here
and kept out of the build.

## Stack

Python · FastAPI (:8001) · Postgres in Docker (:5433, $0/local) · Supabase Auth (free tier)
· APScheduler · fpdf2 — no credit card, no paid service.
