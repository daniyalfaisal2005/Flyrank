from urllib.parse import urlsplit

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from .. import summaries
from ..db import get_conn
from ..deps import get_user_id

router = APIRouter(prefix="/watches", tags=["watches"])


class WatchIn(BaseModel):
    url: str = Field(min_length=1, max_length=2000)
    label: str = Field(min_length=1, max_length=200)


def _validate_url(url: str) -> str:
    url = url.strip()
    parts = urlsplit(url)
    if parts.scheme not in ("http", "https") or not parts.netloc:
        raise HTTPException(status_code=400, detail="url must be a valid http(s) URL")
    return url


@router.post("", status_code=201)
def create_watch(body: WatchIn, user_id: str = Depends(get_user_id)):
    url = _validate_url(body.url)
    label = body.label.strip()
    if not label:
        raise HTTPException(status_code=400, detail="label must not be empty")
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO watches (user_id, url, label)
                VALUES (%s, %s, %s)
                ON CONFLICT (user_id, url) DO NOTHING
                RETURNING id, url, label, active, created_at
                """,
                (user_id, url, label),
            )
            row = cur.fetchone()
    if row is None:
        raise HTTPException(status_code=400, detail="this url is already being watched")
    return dict(row)


@router.get("")
def list_watches(user_id: str = Depends(get_user_id)):
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, url, label, active, created_at
                FROM watches
                WHERE user_id = %s
                ORDER BY id
                """,
                (user_id,),
            )
            rows = cur.fetchall()
    return [dict(row) for row in rows]


@router.delete("/{watch_id}", status_code=204)
def delete_watch(watch_id: int, user_id: str = Depends(get_user_id)):
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "DELETE FROM watches WHERE id = %s AND user_id = %s RETURNING id",
                (watch_id, user_id),
            )
            row = cur.fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="watch not found")
    return None


@router.get("/{watch_id}/history")
def watch_history(
    watch_id: int,
    limit: int = Query(default=20, ge=1, le=100),
    user_id: str = Depends(get_user_id),
):
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT id FROM watches WHERE id = %s AND user_id = %s", (watch_id, user_id))
            if cur.fetchone() is None:
                raise HTTPException(status_code=404, detail="watch not found")
            cur.execute(
                """
                SELECT id, checked_at, status_code, ok, changed, content_hash, response_ms, error
                FROM checks
                WHERE watch_id = %s
                ORDER BY id DESC
                LIMIT %s
                """,
                (watch_id, limit),
            )
            rows = cur.fetchall()
    return [dict(row) for row in rows]


@router.get("/{watch_id}/summary")
def watch_summary(watch_id: int, user_id: str = Depends(get_user_id)):
    summary, cached = summaries.get_or_compute(watch_id, user_id)
    if summary is None:
        raise HTTPException(status_code=404, detail="watch not found")
    return {**summary, "cached": cached}
