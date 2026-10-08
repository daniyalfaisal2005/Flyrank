import time

from . import db, summaries
from .fetcher import FETCH_DELAY_SECONDS, fetch_page


def _previous_hash(conn, watch_id: int):
    with conn.cursor() as cur:
        cur.execute(
            "SELECT content_hash FROM checks WHERE watch_id = %s AND ok ORDER BY id DESC LIMIT 1",
            (watch_id,),
        )
        row = cur.fetchone()
    return row["content_hash"] if row else None


def run_check_cycle() -> dict:
    with db.get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT id, url FROM watches WHERE active ORDER BY id")
            watches = cur.fetchall()

        checked = ok_count = failed = changed_count = 0
        started = time.perf_counter()

        for index, watch in enumerate(watches):
            if index > 0:
                time.sleep(FETCH_DELAY_SECONDS)

            result = fetch_page(watch["url"])
            prev_hash = _previous_hash(conn, watch["id"])
            changed = bool(
                result["content_hash"] and prev_hash and prev_hash != result["content_hash"]
            )

            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO checks
                        (watch_id, status_code, ok, changed, content_hash, response_ms, error)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        watch["id"],
                        result["status_code"],
                        result["ok"],
                        changed,
                        result["content_hash"],
                        result["response_ms"],
                        result["error"],
                    ),
                )

            checked += 1
            if result["ok"]:
                ok_count += 1
            else:
                failed += 1
            if changed:
                changed_count += 1

        duration_ms = int((time.perf_counter() - started) * 1000)
    summaries.invalidate_all()

    summary = {
        "checked": checked,
        "ok": ok_count,
        "failed": failed,
        "changed": changed_count,
        "duration_ms": duration_ms,
    }
    print(f"check cycle: {summary}", flush=True)
    return summary
