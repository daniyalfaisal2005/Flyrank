"""The polite scraper (W5 - A9). Entry point: py -3 scraper/src/main.py"""

from __future__ import annotations

import time
from pathlib import Path
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

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


def fetch(url: str, cache_name: str) -> tuple[str, bool]:
    """Fetch a URL politely, reading the local cache when possible.

    Returns (html, from_cache). Raises FetchError on failure.
    """
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cache_path = CACHE_DIR / cache_name

    if cache_path.exists():
        html = cache_path.read_text(encoding="utf-8")
        print(f"CACHE HIT  {cache_name}  size={len(html)}")
        return html, True

    try:
        resp = _session.get(url, timeout=TIMEOUT)
    except requests.RequestException as exc:
        raise FetchError(f"request failed: {exc}") from exc

    if resp.status_code != 200:
        raise FetchError(f"HTTP {resp.status_code} for {url}", status=resp.status_code)

    html = resp.text
    cache_path.write_text(html, encoding="utf-8")
    print(f"FETCH      {cache_name}  size={len(html)}  status=200")
    time.sleep(DELAY)
    return html, False


def stage1() -> None:
    url = f"{BASE_URL}/catalogue/page-1.html"
    html, from_cache = fetch(url, "catalogue-page-1.html")
    state = "cache" if from_cache else "network"
    print(f"stage1 ok  page saved ({len(html)} bytes, source={state})")


CATALOGUE_PAGES = 3


def discover_book_urls() -> list[str]:
    """Follow the catalogue's own 'next' links for the first 3 pages.

    Returns the unique book URLs in discovery order.
    """
    page_url = f"{BASE_URL}/catalogue/page-1.html"
    page_num = 0
    discovered: list[str] = []

    while page_url and page_num < CATALOGUE_PAGES:
        page_num += 1
        html, _ = fetch(page_url, f"catalogue-page-{page_num}.html")
        soup = BeautifulSoup(html, "html.parser")

        for a in soup.select("article.product_pod h3 a[href]"):
            discovered.append(urljoin(page_url, a["href"]))

        next_a = soup.select_one("li.next a[href]")
        if next_a and page_num < CATALOGUE_PAGES:
            page_url = urljoin(page_url, next_a["href"])
        else:
            page_url = None

    unique = list(dict.fromkeys(discovered))
    print(
        f"catalogue_pages={page_num} discovered={len(discovered)} unique_urls={len(unique)}"
    )
    return unique


def main() -> None:
    stage1()
    discover_book_urls()


if __name__ == "__main__":
    main()
