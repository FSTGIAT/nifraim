"""Deterministic safety net for the AI chat's chart contract.

The model is asked to append `<<VIZ:{...}>>` after any ranked / numeric answer
(see SYSTEM_PROMPT in ai_service.py). It sometimes answers with markdown tables
and forgets the marker — the user asked "הראה לי גרפים" and got no graph.

When that happens, `vizzes_from_answer()` rebuilds bar charts from the tables
the model already wrote. It invents nothing: every label and value is lifted
from the visible answer text, which ai_answer_validator has already checked
against the source context.
"""
from __future__ import annotations

import re

# Words that mean the user explicitly asked for a picture, not a list.
_CHART_WORDS = ("גרף", "גרפים", "תרשים", "דיאגרמ", "ויזואל", "גרפי", "chart", "graph")

_NUM_RE = re.compile(r"^[-+−]?\s*[₪$]?\s*[-+−]?\d[\d,]*(?:\.\d+)?\s*[%₪]?$")
_RANK_HEADERS = ("דירוג", "#", "מס'", "מס", "rank")
_MAX_BARS = 10
_MAX_TREND = 24
_MAX_VIZZES = 3

_HE_MONTHS = ("ינואר", "פברואר", "מרץ", "אפריל", "מאי", "יוני", "יולי",
              "אוגוסט", "ספטמבר", "אוקטובר", "נובמבר", "דצמבר")
_PERIOD_RE = re.compile(r"^(?:\d{1,2}[/.-]\d{2,4}|\d{4}[/.-]\d{1,2}|(?:19|20)\d{2}|Q[1-4].*|רבעון.*)$")


def _is_period(label: str) -> bool:
    lab = label.strip()
    return bool(_PERIOD_RE.match(lab)) or any(lab.startswith(m) for m in _HE_MONTHS)


def asks_for_chart(question: str) -> bool:
    q = (question or "").lower()
    return any(w in q for w in _CHART_WORDS)


def _cells(line: str) -> list[str]:
    s = line.strip()
    if s.startswith("|"):
        s = s[1:]
    if s.endswith("|"):
        s = s[:-1]
    return [c.strip().strip("*").strip() for c in s.split("|")]


def _is_separator(cells: list[str]) -> bool:
    return all(re.fullmatch(r":?-{2,}:?", c or "") for c in cells if c) and any(cells)


def _to_number(cell: str) -> float | None:
    c = cell.replace("−", "-").strip()
    if not _NUM_RE.match(c):
        return None
    try:
        return float(re.sub(r"[^\d.\-]", "", c))
    except ValueError:
        return None


def _unit(cells: list[str]) -> str:
    joined = " ".join(cells)
    if "₪" in joined:
        return "₪"
    if "%" in joined:
        return "%"
    return ""


def _tables(text: str) -> list[tuple[str, list[str], list[list[str]]]]:
    """Return (heading, header_cells, body_rows) for each pipe table.

    The heading is the nearest markdown `#` line (or bold line) above the
    table — it becomes the chart title."""
    lines = text.splitlines()
    out = []
    heading = ""
    i = 0
    while i < len(lines):
        raw = lines[i].strip()
        if raw.startswith("#"):
            heading = raw.lstrip("#").strip().rstrip(":")
        elif raw.startswith("**") and raw.endswith(("**", "**:")) and "|" not in raw:
            heading = raw.strip("*: ").strip()
        if "|" in raw and i + 1 < len(lines) and _is_separator(_cells(lines[i + 1])):
            header = _cells(raw)
            rows = []
            j = i + 2
            while j < len(lines) and "|" in lines[j]:
                rows.append(_cells(lines[j]))
                j += 1
            out.append((heading, header, rows))
            i = j
            continue
        i += 1
    return out


def _table_to_bar(heading: str, header: list[str], rows: list[list[str]]) -> dict | None:
    rows = [r for r in rows if len(r) == len(header)]
    if len(rows) < 2:
        return None
    ncol = len(header)

    numeric_cols = [
        c for c in range(ncol)
        if all(_to_number(r[c]) is not None for r in rows)
    ]
    # The rank column (1..N, or headed דירוג/#) is numeric but not a value.
    def _is_rank(c: int) -> bool:
        if header[c].strip().lower() in _RANK_HEADERS:
            return True
        vals = [_to_number(r[c]) for r in rows]
        return vals == [float(k) for k in range(1, len(rows) + 1)]

    value_cols = [c for c in numeric_cols if not _is_rank(c)]
    if not value_cols:
        return None
    # Prefer a money / percent column; otherwise the right-most numeric one.
    value_col = next(
        (c for c in value_cols if any(u in "".join(r[c] for r in rows) for u in "₪%")),
        value_cols[-1],
    )
    label_col = next((c for c in range(ncol) if c not in numeric_cols), None)
    if label_col is None:
        return None

    # Periods as labels = change over time → a trend, in the table's own order.
    is_trend = sum(_is_period(r[label_col]) for r in rows) >= max(2, len(rows) * 0.7)
    data = []
    for r in rows[:_MAX_TREND if is_trend else _MAX_BARS]:
        label = r[label_col]
        if not label:
            continue
        data.append({"label": label, "value": _to_number(r[value_col])})
    if len(data) < 2:
        return None

    unit = _unit([r[value_col] for r in rows])
    title = heading or (f"{header[value_col]} לפי {header[label_col]}")
    viz = {
        "type": "trend" if is_trend else "bar",
        "title": title[:80],
        "unit": unit,
        "data": data,
        "source": "table-fallback",
    }
    if not is_trend:
        viz["highlight_label"] = data[0]["label"]
    return viz


def vizzes_from_answer(question: str, answer: str) -> list[dict]:
    """Bar (or trend, for period labels) vizzes rebuilt from the answer's markdown tables.

    Fires when the user explicitly asked for a chart (any table ≥2 rows), or
    when the answer carries a ranked table of ≥5 rows — the same threshold the
    system prompt's FINAL CHECKLIST sets for a mandatory viz."""
    wants_chart = asks_for_chart(question)
    vizzes = []
    for heading, header, rows in _tables(answer or ""):
        if not wants_chart and len(rows) < 5:
            continue
        viz = _table_to_bar(heading, header, rows)
        if viz:
            vizzes.append(viz)
        if len(vizzes) >= _MAX_VIZZES:
            break
    return vizzes
