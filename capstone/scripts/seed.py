"""Idempotent demo seed: demo account + sandbox watches via the local API.

Usage (server must be running first):
    py -3 capstone/scripts/seed.py
"""

import os
import sys
from pathlib import Path

import requests

CAPSTONE_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(CAPSTONE_DIR))

from src.config import APP_PORT  # noqa: E402

BASE = f"http://127.0.0.1:{APP_PORT}"
DEMO_EMAIL = os.environ.get("DEMO_EMAIL", "demo@pagepulse.dev")
DEMO_PASSWORD = os.environ.get("DEMO_PASSWORD", "demo-password-123")

WATCHES = [
    ("https://books.toscrape.com/", "Sandbox homepage"),
    ("https://books.toscrape.com/catalogue/page-1.html", "Catalogue page 1"),
    ("https://books.toscrape.com/catalogue/page-2.html", "Catalogue page 2"),
    ("https://quotes.toscrape.com/", "Quotes of the day"),
    ("https://books.toscrape.com/this-page-is-missing", "Known broken page (demo of failures)"),
]


def main() -> None:
    try:
        requests.get(f"{BASE}/health", timeout=5)
    except requests.RequestException:
        raise SystemExit("Server is not running - start it first (see README demo path)")

    try:
        login = requests.post(
            f"{BASE}/auth/login",
            json={"email": DEMO_EMAIL, "password": DEMO_PASSWORD},
            timeout=15,
        )
        if login.status_code != 200:
            requests.post(
                f"{BASE}/auth/signup",
                json={"email": DEMO_EMAIL, "password": DEMO_PASSWORD},
                timeout=15,
            )
            login = requests.post(
                f"{BASE}/auth/login",
                json={"email": DEMO_EMAIL, "password": DEMO_PASSWORD},
                timeout=15,
            )
        if login.status_code != 200:
            raise SystemExit(
                "login failed - the demo account already exists with a different "
                "password; set DEMO_PASSWORD to that password or delete the user "
                "in the Supabase dashboard and rerun"
            )
        token = login.json()["access_token"]
    except requests.RequestException as exc:
        raise SystemExit(f"cannot reach the API: {exc}")

    headers = {"Authorization": f"Bearer {token}"}
    created = reused = 0
    for url, label in WATCHES:
        resp = requests.post(
            f"{BASE}/watches",
            json={"url": url, "label": label},
            headers=headers,
            timeout=15,
        )
        if resp.status_code == 201:
            created += 1
        elif resp.status_code == 400:
            reused += 1
        else:
            raise SystemExit(f"seed failed for {url}: {resp.status_code} {resp.text}")

    watches = requests.get(f"{BASE}/watches", headers=headers, timeout=15).json()
    print("seed complete")
    print(f"  demo login : {DEMO_EMAIL}")
    print(f"  password   : {DEMO_PASSWORD}")
    print(f"  watches    : {len(watches)} total ({created} new, {reused} already present)")
    print("  next       : POST /jobs/run-now, then GET /watches/1/summary, then POST /reports/weekly")


if __name__ == "__main__":
    main()
