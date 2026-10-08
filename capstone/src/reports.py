from datetime import datetime
from pathlib import Path

from fpdf import FPDF

from . import db
from .config import BASE_DIR

REPORTS_DIR = BASE_DIR / "output" / "reports"


def _latin1(text, limit: int | None = None) -> str:
    value = str(text)
    if limit and len(value) > limit:
        value = value[: limit - 3] + "..."
    return value.encode("latin-1", "replace").decode("latin-1")


def _week_rows(user_id: str) -> list[dict]:
    with db.get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT w.label, w.url,
                       COUNT(c.id) FILTER (WHERE c.checked_at > now() - interval '7 days')              AS checks_week,
                       COUNT(c.id) FILTER (WHERE c.checked_at > now() - interval '7 days' AND c.ok)      AS ok_week,
                       COUNT(c.id) FILTER (WHERE c.checked_at > now() - interval '7 days' AND NOT c.ok)  AS failed_week,
                       COUNT(c.id) FILTER (WHERE c.changed)                                              AS changes,
                       MAX(c.checked_at)                                                                 AS last_checked_at
                FROM watches w
                LEFT JOIN checks c ON c.watch_id = w.id
                WHERE w.user_id = %s
                GROUP BY w.id
                ORDER BY w.id
                """,
                (user_id,),
            )
            return [dict(row) for row in cur.fetchall()]


def build_weekly_report(user_id: str, email: str) -> dict:
    rows = _week_rows(user_id)
    totals = {
        "watches": len(rows),
        "checks_week": sum(r["checks_week"] for r in rows),
        "failed_week": sum(r["failed_week"] for r in rows),
        "changes": sum(r["changes"] for r in rows),
    }

    pdf = FPDF()
    pdf.set_title("PagePulse Weekly Report")
    pdf.set_author("PagePulse")
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 16)
    pdf.cell(0, 10, _latin1("PagePulse - Weekly Report"), new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 9)
    pdf.cell(0, 6, _latin1(f"Generated {datetime.now():%Y-%m-%d %H:%M}  |  {email}"),
             new_x="LMARGIN", new_y="NEXT")
    pdf.ln(3)

    pdf.set_font("Helvetica", "B", 10)
    pdf.cell(0, 6,
             _latin1(f"Watches: {totals['watches']}   Checks (7d): {totals['checks_week']}   "
                     f"Failures (7d): {totals['failed_week']}   Changes: {totals['changes']}"),
             new_x="LMARGIN", new_y="NEXT")
    pdf.ln(4)

    if not rows:
        pdf.set_font("Helvetica", "", 11)
        pdf.cell(0, 8, "No watches yet - add one to start the history.",
                 new_x="LMARGIN", new_y="NEXT")
    else:
        widths = (32, 58, 22, 26, 24, 28)
        headers = ("Label", "URL", "Checks", "Uptime %", "Changes", "Last check")
        pdf.set_font("Helvetica", "B", 9)
        for width, header in zip(widths, headers):
            pdf.cell(width, 7, _latin1(header), border=1)
        pdf.ln()
        pdf.set_font("Helvetica", "", 8)
        for row in rows:
            week = row["checks_week"]
            uptime = f"{row['ok_week'] * 100.0 / week:.1f}" if week else "-"
            last = row["last_checked_at"].strftime("%Y-%m-%d") if row["last_checked_at"] else "-"
            cells = (
                _latin1(row["label"], 30),
                _latin1(row["url"], 56),
                str(week),
                uptime,
                str(row["changes"]),
                last,
            )
            for width, value in zip(widths, cells):
                pdf.cell(width, 6, value, border=1)
            pdf.ln()

    pdf.ln(6)
    pdf.set_font("Helvetica", "I", 8)
    pdf.cell(0, 5, "PagePulse checks your pages politely and reports only what changed.",
             new_x="LMARGIN", new_y="NEXT")

    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    filename = f"pagepulse-weekly-{datetime.now():%Y%m%d-%H%M%S-%f}.pdf"
    pdf.output(dest="F", name=str(REPORTS_DIR / filename))
    return {
        "filename": filename,
        "path": str(REPORTS_DIR / filename),
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "totals": totals,
    }
