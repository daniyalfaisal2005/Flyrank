"""The polite scraper (W5 - A9). Entry point: py -3 scraper/src/main.py"""

from __future__ import annotations

import json
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup
from pydantic import BaseModel, ValidationError, field_validator

BASE_DIR = Path(__file__).resolve().parent.parent
CACHE_DIR = BASE_DIR / "cache"
OUTPUT_DIR = BASE_DIR / "output"

BASE_URL = "https://books.toscrape.com"
USER_AGENT = "FlyRankInternship-A9/1.0 (+https://github.com/daniyalfaisal2005/Flyrank)"
TIMEOUT = 10
DELAY = 0.5

_session = requests.Session()
_session.headers.update({"User-Agent": USER_AGENT})


class FetchError(Exception):
    """A page could not be fetched. status is None for network errors."""

    def __init__(self, message: str, status: int | None = None):
        super().__init__(message)
        self.status = status


def _iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


class RunStats:
    """Honest counters for the end-of-run report."""

    def __init__(self) -> None:
        self.started_at = datetime.now(timezone.utc)
        self.pages_fetched = 0
        self.cache_hits = 0
        self.failed_urls: list[dict] = []

    def record_failure(self, url: str, reason: str) -> None:
        self.failed_urls.append({"url": url, "reason": reason})

    def duration_seconds(self) -> float:
        return round((datetime.now(timezone.utc) - self.started_at).total_seconds(), 2)


stats = RunStats()


def _request(url: str):
    """One polite GET with a single retry on timeouts and 5xx errors.

    404 (gone) and 403 (denied) are never retried - asking again would turn
    a polite robot into a pest.
    """
    last_error = ""
    for attempt in (1, 2):
        try:
            resp = _session.get(url, timeout=TIMEOUT)
        except requests.RequestException as exc:
            last_error = f"network error: {exc}"
            if attempt == 1:
                time.sleep(1)
                continue
            raise FetchError(f"{last_error} (after retry)") from exc

        if resp.status_code == 200:
            return resp
        if resp.status_code >= 500 and attempt == 1:
            last_error = f"HTTP {resp.status_code}"
            time.sleep(1)
            continue
        raise FetchError(f"HTTP {resp.status_code} for {url}", status=resp.status_code)
    raise FetchError(f"{last_error} for {url}")


def fetch(url: str, cache_name: str) -> tuple[str, bool, str]:
    """Fetch a URL politely, reading the local cache when possible.

    Returns (html, from_cache, fetched_at). fetched_at is the provenance
    timestamp: the moment the network response arrived, or the cache file's
    mtime when the saved copy was reused.
    Raises FetchError on failure.
    """
    cache_path = CACHE_DIR / cache_name
    cache_path.parent.mkdir(parents=True, exist_ok=True)

    if cache_path.exists():
        html = cache_path.read_text(encoding="utf-8")
        fetched_at = _iso(datetime.fromtimestamp(cache_path.stat().st_mtime, timezone.utc))
        stats.cache_hits += 1
        print(f"CACHE HIT  {cache_name}  size={len(html)}")
        return html, True, fetched_at

    resp = _request(url)

    # The site serves UTF-8 but omits the charset header, so requests would
    # fall back to ISO-8859-1 and mangle characters like £ - decode explicitly.
    html = resp.content.decode("utf-8")
    now = datetime.now(timezone.utc)
    cache_path.write_text(html, encoding="utf-8")
    stats.pages_fetched += 1
    print(f"FETCH      {cache_name}  size={len(html)}  status=200")
    time.sleep(DELAY)
    return html, False, _iso(now)


def stage1() -> None:
    url = f"{BASE_URL}/catalogue/page-1.html"
    html, from_cache, fetched_at = fetch(url, "catalogue-page-1.html")
    state = "cache" if from_cache else "network"
    print(f"stage1 ok  page saved ({len(html)} bytes, source={state}, at={fetched_at})")


CATALOGUE_PAGES = 3


def discover_book_urls() -> list[dict]:
    """Follow the catalogue's own 'next' links for the first 3 pages.

    Returns one entry per discovered book: {"product_url", "source_page"}.
    """
    page_url = f"{BASE_URL}/catalogue/page-1.html"
    page_num = 0
    discovered: list[dict] = []

    while page_url and page_num < CATALOGUE_PAGES:
        page_num += 1
        html, _, _ = fetch(page_url, f"catalogue-page-{page_num}.html")
        soup = BeautifulSoup(html, "html.parser")

        for a in soup.select("article.product_pod h3 a[href]"):
            discovered.append(
                {"product_url": urljoin(page_url, a["href"]), "source_page": page_url}
            )

        next_a = soup.select_one("li.next a[href]")
        if next_a and page_num < CATALOGUE_PAGES:
            page_url = urljoin(page_url, next_a["href"])
        else:
            page_url = None

    unique = list({e["product_url"]: e for e in discovered}.values())
    print(
        f"catalogue_pages={page_num} discovered={len(discovered)} unique_urls={len(unique)}"
    )
    return unique


RATING_WORDS = {"One", "Two", "Three", "Four", "Five"}


def extract_record(book: dict) -> dict:
    """Fetch one book page and pull the eight raw fields from it."""
    url = book["product_url"]
    slug = urlparse(url).path.rstrip("/").split("/")[-2]
    html, _, fetched_at = fetch(url, f"books/{slug}.html")
    soup = BeautifulSoup(html, "html.parser")

    main = soup.select_one(".product_main")
    if main is None:
        raise FetchError(f"no product area found at {url}")

    title_el = main.select_one("h1")
    price_el = main.select_one(".price_color")
    avail_el = main.select_one(".availability")
    rating_el = main.select_one("p.star-rating")

    rating_text = None
    if rating_el is not None:
        rating_text = next(
            (c for c in rating_el.get("class", []) if c in RATING_WORDS), None
        )

    description_el = soup.select_one("#product_description + p")

    return {
        "title": title_el.get_text(strip=True) if title_el else None,
        "product_url": url,
        "price_text": price_el.get_text(strip=True) if price_el else None,
        "availability_text": avail_el.get_text(" ", strip=True) if avail_el else None,
        "rating_text": rating_text,
        "description": description_el.get_text(strip=True) if description_el else None,
        "source_page": book["source_page"],
        "fetched_at": fetched_at,
    }


def stage3(book_list: list[dict] | None = None) -> list[dict]:
    books = discover_book_urls() if book_list is None else book_list
    records = []
    for i, book in enumerate(books, start=1):
        try:
            records.append(extract_record(book))
        except FetchError as exc:
            print(f"SKIP       {book['product_url']}  ({exc})")
            stats.record_failure(book["product_url"], str(exc))
        if i % 10 == 0:
            print(f"  ... {i}/{len(books)} book pages processed")

    if records:
        print("sample raw record:")
        for key, value in records[0].items():
            shown = value if not isinstance(value, str) or len(value) <= 80 else value[:77] + "..."
            print(f"  {key}: {shown}")
    print(f"detail_pages={len(records)}")
    return records


class BookRecord(BaseModel):
    """The schema of a finished record. Every record must pass this before storage."""

    title: str
    product_url: str
    price_text: str
    price_gbp: float
    availability_text: str
    rating_text: str
    description: str | None = None
    source_page: str
    fetched_at: str

    @field_validator("title", "price_text", "availability_text", "rating_text")
    @classmethod
    def must_not_be_blank(cls, value: str) -> str:
        if not value or not value.strip():
            raise ValueError("must not be empty")
        return value.strip()

    @field_validator("product_url", "source_page")
    @classmethod
    def must_be_https(cls, value: str) -> str:
        if not value.startswith("https://"):
            raise ValueError("must be an absolute https:// URL")
        return value

    @field_validator("price_gbp")
    @classmethod
    def must_be_positive(cls, value: float) -> float:
        if value <= 0:
            raise ValueError("price must be greater than zero")
        return value

    @field_validator("rating_text")
    @classmethod
    def known_rating(cls, value: str) -> str:
        if value not in RATING_WORDS:
            raise ValueError(f"unknown rating {value!r}")
        return value

    @field_validator("fetched_at")
    @classmethod
    def iso_timestamp(cls, value: str) -> str:
        if not re.match(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$", value):
            raise ValueError("must be an ISO-8601 UTC timestamp")
        return value


def normalize(raw: dict) -> dict:
    """Turn raw scraped values into clean ones. Keeps raw values side by side."""
    record = dict(raw)
    price_text = (raw.get("price_text") or "").strip()
    match = re.search(r"([\d,]+\.\d{2})", price_text)
    if not match:
        raise ValueError(f"cannot read a price from {price_text!r}")
    record["price_gbp"] = float(match.group(1).replace(",", ""))
    record["title"] = (raw.get("title") or "").strip()
    record["product_url"] = (raw.get("product_url") or "").strip()
    return record


BOOKS_PATH = OUTPUT_DIR / "books.json"
ERRORS_PATH = OUTPUT_DIR / "errors.json"


def stage4(raw_records: list[dict]) -> list[dict]:
    good: list[dict] = []
    errors: list[dict] = []

    for raw in raw_records:
        try:
            normalized = normalize(raw)
        except ValueError as exc:
            errors.append({"product_url": raw.get("product_url"), "reason": str(exc)})
            continue
        try:
            record = BookRecord(**normalized)
        except ValidationError as exc:
            reason = "; ".join(
                f"{'.'.join(str(loc) for loc in err['loc'])}: {err['msg']}"
                for err in exc.errors()
            )
            errors.append({"product_url": raw.get("product_url"), "reason": reason})
            continue
        good.append(record.model_dump())

    # Idempotent store: the canonical product_url is the record's identity,
    # so a rerun overwrites the same 60 records instead of appending.
    by_url = {r["product_url"]: r for r in good}
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    BOOKS_PATH.write_text(
        json.dumps(list(by_url.values()), indent=2, ensure_ascii=False), encoding="utf-8"
    )
    ERRORS_PATH.write_text(json.dumps(errors, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"valid_records={len(by_url)} invalid_records={len(errors)} stored=output/books.json")
    return list(by_url.values()), errors


REPORT_PATH = OUTPUT_DIR / "run-report.json"

FAKE_BOOK_URL = (
    "https://books.toscrape.com/catalogue/this-book-does-not-exist_99999/index.html"
)


def stage5(valid_count: int, invalid_count: int) -> dict:
    """Write the honest end-of-run report."""
    report = {
        "started_at": _iso(stats.started_at),
        "duration_seconds": stats.duration_seconds(),
        "pages_fetched": stats.pages_fetched,
        "cache_hits": stats.cache_hits,
        "valid_records": valid_count,
        "invalid_records": invalid_count,
        "failed_pages": len(stats.failed_urls),
        "failed_urls": stats.failed_urls,
    }
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"run report written: failed_pages={report['failed_pages']} "
          f"duration={report['duration_seconds']}s -> output/run-report.json")
    return report


def main() -> None:
    import sys

    demo_failure = "--demo-failure" in sys.argv

    stage1()
    book_list: list[dict] | None = None
    if demo_failure:
        book_list = discover_book_urls() + [
            {"product_url": FAKE_BOOK_URL, "source_page": "deliberately-broken"}
        ]
        print(f"demo: one deliberately broken URL added -> {FAKE_BOOK_URL}")

    raw_records = stage3(book_list)
    valid, errors = stage4(raw_records)
    stage5(len(valid), len(errors))


if __name__ == "__main__":
    main()
