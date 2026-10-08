"""הר הביטוח portfolio Excel → coverage rows.

The site's "כל הביטוחים" export (sheet "תיק ביטוחי"):
  row 1   "התיק הביטוחי, הופק מאתר 'הר הביטוח' של משרד האוצר, בתאריך" … 'dd/mm/yyyy'
  row 2   ענף ראשי | ענף (משני) | סוג מוצר | חברה | תקופת ביטוח | פרמיה בש"ח | סוג פרמיה | מספר פוליסה | סיווג תכנית
  then    section rows "תחום - כללי" / "תחום - בריאות ותאונות אישיות" / "תחום - חיים ואבדן כושר עבודה"
          and one row per COVERAGE (a car policy is 5–7 rows sharing one מספר פוליסה).
  period  "01/08/2019 - 31/07/2020" or "מתחדש".
Rows below the table (an agent's own notes in a hand-edited copy) are ignored. Columns are found
by header name, never by position.
"""
from __future__ import annotations

import io
import re
from datetime import date, datetime

COLS = {
    "ענף ראשי": "main_branch",
    "ענף (משני)": "sub_branch",
    "סוג מוצר": "product_type",
    "חברה": "company",
    "תקופת ביטוח": "period",
    'פרמיה בש"ח': "premium",
    "סוג פרמיה": "premium_type",
    "מספר פוליסה": "policy_number",
    "סיווג תכנית": "plan_class",
}
_DATE = re.compile(r"(\d{1,2})[/.](\d{1,2})[/.](\d{2,4})")


def _norm(s) -> str:
    return re.sub(r"\s+", " ", str(s or "").replace("״", '"').replace("”", '"')).strip()


def parse_date(v) -> date | None:
    if v is None or v == "":
        return None
    if isinstance(v, datetime):
        return v.date()
    if isinstance(v, date):
        return v
    m = _DATE.search(str(v))
    if not m:
        return None
    d, mth, y = (int(x) for x in m.groups())
    if y < 100:
        y += 2000 if y < 50 else 1900
    try:
        return date(y, mth, d)
    except ValueError:
        return None


def _period(v) -> tuple[date | None, date | None, bool]:
    s = _norm(v)
    if not s:
        return None, None, False
    if "מתחדש" in s:
        return None, None, True
    dates = [parse_date(m.group(0)) for m in _DATE.finditer(s)]
    return (dates[0] if dates else None), (dates[1] if len(dates) > 1 else None), False


def _policy_no(v) -> str | None:
    if v is None or v == "":
        return None
    if isinstance(v, float) and v.is_integer():
        v = int(v)
    s = str(v).strip()
    return s[:-2] if s.endswith(".0") else s or None


def _premium(v) -> float | None:
    if v is None or v == "":
        return None
    if isinstance(v, (int, float)):
        return float(v)
    s = re.sub(r"[^\d.\-]", "", str(v))
    try:
        return float(s) if s else None
    except ValueError:
        return None


def parse_harb_xlsx(data: bytes) -> dict:
    """→ {"produced_at": date|None, "rows": [dict], "notes": [str]}. Raises ValueError when the
    file is not a הר הביטוח portfolio (no header row)."""
    import openpyxl

    wb = openpyxl.load_workbook(io.BytesIO(data), read_only=True, data_only=True)
    ws = wb.worksheets[0]
    # The live export declares a wrong sheet <dimension> (A1:K5 on a 38-row sheet, 2026-10-07);
    # read_only mode trusts it and silently stops after 5 rows → 0 policies. Ignore it.
    ws.reset_dimensions()
    grid = [list(r) for r in ws.iter_rows(values_only=True)]
    wb.close()

    produced_at = None
    header_i, colmap = None, {}
    for i, r in enumerate(grid[:15]):
        cells = [_norm(c) for c in r]
        if produced_at is None and any("הר הביטוח" in c or "הופק" in c for c in cells):
            produced_at = next((d for d in (parse_date(c) for c in r if c not in (None, "")) if d), None)
        if "ענף ראשי" in cells:
            header_i = i
            colmap = {j: COLS[c] for j, c in enumerate(cells) if c in COLS}
            break
    if header_i is None or "company" not in colmap.values():
        raise ValueError("not a הר הביטוח portfolio: header row 'ענף ראשי' not found")

    rows, notes, domain = [], [], None
    ended = False
    for r in grid[header_i + 1:]:
        vals = {f: r[j] if j < len(r) else None for j, f in colmap.items()}
        filled = [c for c in r if c not in (None, "")]
        if not filled:
            continue
        # the "תחום - …" section marker sits in column A of the sample export and in column B
        # (under ענף ראשי, column A empty) of the live one — accept it as the first filled cell
        first = _norm(filled[0])
        if first.startswith("תחום"):
            domain = first.split("-", 1)[-1].strip() if "-" in first else first
            continue
        if ended or not (_norm(vals.get("main_branch")) and _norm(vals.get("company"))):
            # below the table: free text (a hand-edited copy's notes). Kept as notes, never as policies.
            ended = True
            txt = " ".join(_norm(c) for c in filled if not isinstance(c, (int, float)))
            if txt:
                notes.append(txt)
            continue
        start, end, renewing = _period(vals.get("period"))
        rows.append({
            "domain": domain,
            "main_branch": _norm(vals.get("main_branch"))[:120] or None,
            "sub_branch": _norm(vals.get("sub_branch"))[:160] or None,
            "product_type": _norm(vals.get("product_type"))[:160] or None,
            "company": _norm(vals.get("company"))[:160] or None,
            "period_start": start, "period_end": end, "renewing": renewing,
            "premium": _premium(vals.get("premium")),
            "premium_type": _norm(vals.get("premium_type"))[:300] or None,
            "policy_number": _policy_no(vals.get("policy_number")),
            "plan_class": _norm(vals.get("plan_class"))[:40] or None,
        })
    return {"produced_at": produced_at, "rows": rows, "notes": notes}
