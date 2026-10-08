import hashlib
import time

import requests
from bs4 import BeautifulSoup

USER_AGENT = "PagePulse/1.0 (page watcher; polite checker for a capstone project)"
REQUEST_TIMEOUT = 10
FETCH_DELAY_SECONDS = 0.5


def _content_hash(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    text = " ".join(soup.get_text(separator=" ").split())
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def fetch_page(url: str) -> dict:
    started = time.perf_counter()
    try:
        resp = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=REQUEST_TIMEOUT)
        elapsed_ms = int((time.perf_counter() - started) * 1000)
        status_code = resp.status_code
        if status_code < 400:
            # W5 lesson: decode via content, pages may omit a charset header
            html = resp.content.decode("utf-8", errors="replace")
            return {
                "ok": True,
                "status_code": status_code,
                "content_hash": _content_hash(html),
                "response_ms": elapsed_ms,
                "error": None,
            }
        return {
            "ok": False,
            "status_code": status_code,
            "content_hash": None,
            "response_ms": elapsed_ms,
            "error": f"HTTP {status_code}",
        }
    except requests.RequestException as exc:
        elapsed_ms = int((time.perf_counter() - started) * 1000)
        return {
            "ok": False,
            "status_code": None,
            "content_hash": None,
            "response_ms": elapsed_ms,
            "error": str(exc)[:500],
        }
