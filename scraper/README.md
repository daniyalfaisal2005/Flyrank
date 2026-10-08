# The polite scraper (W5 · A9)

A small, polite scraping pipeline: it downloads the first three catalogue pages of Books to Scrape,
visits all 60 book pages, turns messy HTML into clean, checked JSON records, survives a broken page
without crashing, and ends every run with a short report.

## Target classification

- **Which site:** https://books.toscrape.com/ — a public practice sandbox built so people can learn web scraping on it.
- **Why:** the site exists for exactly this purpose; it is the only kind of site this assignment touches.
- **How much:** the first 3 catalogue pages only (20 books each = 60 book detail pages, then stop).
- **What data:** per book — title, product URL, price text, availability text, rating text, description, source page, fetch time; plus the normalized numeric price.
- **Why this is appropriate:** Books to Scrape is an official sandbox for practice; no real user data, no accounts, no paywalls, and the scope is deliberately small (3 pages).

**robots.txt check:** `GET https://books.toscrape.com/robots.txt` returned **404 — no robots file found**.
A missing file is not permission; it is just a missing file. Permission here comes from the site's own
stated purpose as a scraping sandbox.

I will not reuse this code on another site without checking its rules and terms first.

## Lane & install

**Python lane** (Python 3.10+). Dependencies: `requests`, `beautifulsoup4`, `pydantic`.

```powershell
pip install -r scraper/requirements.txt
```

## How to run (one command)

```powershell
py -3 scraper/src/main.py
```

Produces `scraper/output/books.json` (60 records) and `scraper/output/run-report.json`.
A second run reads from the local cache and produces the same 60 records — no duplicates.

To prove failure handling on your own machine (adds one deliberately broken URL — the run still finishes):

```powershell
py -3 scraper/src/main.py --demo-failure
```

## Record schema

Every record is validated against a Pydantic schema (`BookRecord`) before it is stored.
A record that fails validation never reaches `books.json` — it lands in `errors.json` with the reason.

| Field | Type | Required | Notes |
| --- | --- | --- | --- |
| `title` | string | yes | non-empty |
| `product_url` | string | yes | absolute `https://` URL — also the record's identity (dedupe key) |
| `price_text` | string | yes | raw scraped value, e.g. `£51.77` — kept as the receipt |
| `price_gbp` | number | yes | normalized float, e.g. `51.77` — must be > 0 |
| `availability_text` | string | yes | e.g. `In stock (22 available)` |
| `rating_text` | string | yes | one of `One`…`Five` |
| `description` | string or null | **no** | `null` when the page has none — never invented |
| `source_page` | string | yes | the catalogue page the book was found on (provenance) |
| `fetched_at` | string | yes | ISO-8601 UTC timestamp of the fetch (provenance) |

## Politeness rules this scraper follows

- **User-agent:** `FlyRankInternship-A9/1.0 (+link to this repo)` — a site owner checking their logs can find out who is calling.
- **Timeout:** 10 seconds — a request gives up instead of hanging forever.
- **Status check:** only `200` counts as a page; anything else is a failed fetch, never parsed as HTML.
- **Delay:** at least 500 ms between real requests to the site; cached pages need no delay.
- **Cache:** every page is saved to `scraper/cache/` once; development restarts read the saved copy, so the site feels our fiftieth restart exactly once.
- **Retries:** at most one retry, only on timeouts and `5xx`. A `404` is never retried (the page is gone), and a `403` is never retried (the site said no).

## A real run report

```json
{
  "started_at": "2026-10-08T20:56:21Z",
  "duration_seconds": 0.59,
  "pages_fetched": 0,
  "cache_hits": 64,
  "valid_records": 60,
  "invalid_records": 0,
  "failed_pages": 0,
  "failed_urls": []
}
```

(From a fully cached rerun — `pages_fetched: 0` is honest: this run sent no network requests.
A fresh clone's first run fetches 63 pages: 3 catalogue + 60 book pages.)

**Failure proof:** run with `--demo-failure` and the same report shows `"failed_pages": 1` while
`books.json` still holds the same 60 good records — one broken page never takes the run down.

## Why this assignment needed no browser

The data is already in the HTML the server sends — a plain HTTP request is enough to receive it,
so a browser would only add cost (rendering, memory, and time) without adding any data.

## Ethics note

Use an official API when one exists; never bypass logins, paywalls, or blocks; collect only what you
need. Web pages are untrusted input — check everything you scrape before you store it.

## Known limitation

The scraper trusts the page's current HTML structure: if Books to Scrape renamed its CSS classes
(for example `price_color`), extraction would fail loudly rather than adapt. That is deliberate for
this scope — selectors are aimed at the product area specifically so a structural change is caught
by validation (`errors.json`) instead of silently storing wrong data.
