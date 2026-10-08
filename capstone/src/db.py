import psycopg
from psycopg.rows import dict_row

from .config import BASE_DIR, DATABASE_URL


def get_conn():
    return psycopg.connect(DATABASE_URL, row_factory=dict_row)


def init_db():
    schema_sql = (BASE_DIR / "sql" / "init.sql").read_text(encoding="utf-8")
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(schema_sql)


def db_healthy() -> bool:
    try:
        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1")
                cur.fetchone()
        return True
    except Exception:
        return False
