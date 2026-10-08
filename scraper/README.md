# Stage 0 result
GET https://books.toscrape.com/robots.txt -> HTTP 404
no robots file found

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

**robots.txt check:** `GET https://books.toscrape.com/robots.txt` returned **404 — no robots file found**. A missing file is not permission; it is just a missing file. Permission here comes from the site's own stated purpose as a scraping sandbox.

I will not reuse this code on another site without checking its rules and terms first.

## Politeness rules this scraper follows

- Honest user-agent: `FlyRankInternship-A9/1.0` (with a link to this repository)
- Timeout of 10 seconds on every request — never wait forever
- Status code checked before parsing — only `200` counts as a page
- At least 500 ms of delay between real requests to the site
- Cached pages are read locally — no delay needed, the site never feels a development restart

## How to run

```powershell
py -3 scraper/src/main.py
```

(Install dependencies first: `pip install -r scraper/requirements.txt`)

## Record schema

See Stage 4 — every record is validated against a Pydantic schema before it is stored in `output/books.json`; failing records land in `output/errors.json` with the reason.

## Ethics note

Use an official API when one exists; never bypass logins, paywalls, or blocks; collect only what you need.

## Known limitations

(this section is finished in Stage 6)
