import time

from . import db

SUMMARY_TTL_SECONDS = 60
_cache: dict = {}


def invalidate_all():
    _cache.clear()
    print("cache invalidated (new check cycle)", flush=True)


def compute_summary(watch_id: int, user_id: str) -> dict | None:
    with db.get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT w.id, w.label, w.url,
                       COUNT(c.id)                          AS total_checks,
                       COUNT(c.id) FILTER (WHERE c.ok)      AS ok_checks,
                       COUNT(c.id) FILTER (WHERE c.changed) AS changes,
                       MAX(c.checked_at)                    AS last_checked_at
                FROM watches w
                LEFT JOIN checks c ON c.watch_id = w.id
                WHERE w.id = %s AND w.user_id = %s
                GROUP BY w.id
                """,
                (watch_id, user_id),
            )
            row = cur.fetchone()
    if row is None:
        return None
    summary = dict(row)
    total = summary["total_checks"]
    summary["uptime_pct"] = round(summary["ok_checks"] * 100.0 / total, 1) if total else None
    return summary


def get_or_compute(watch_id: int, user_id: str) -> tuple[dict | None, str]:
    key = f"{user_id}:{watch_id}"
    now = time.monotonic()
    entry = _cache.get(key)
    if entry is not None and entry["expires"] > now:
        print(f"cache HIT  {key}", flush=True)
        return entry["value"], "HIT"
    value = compute_summary(watch_id, user_id)
    if value is not None:
        _cache[key] = {"value": value, "expires": now + SUMMARY_TTL_SECONDS}
        print(f"cache MISS {key}", flush=True)
    return value, "MISS"
