"""render_chart — the model points at rows a tool already returned (result_id);
the SERVER builds the chart, so the model never re-types numbers (that was
~1,100 output tokens per chart answer — docs/AI_VIZ.md §3)."""
from __future__ import annotations

from app.services.agent.registry import tool


LIMITS = {"bar": 10, "donut": 8, "trend": 24}


def build_table(kept: dict, title: str = "", insight: str = "") -> dict | None:
    """{type: table, columns, rows} — from a kept table, or the label/value rows."""
    t = kept.get("table")
    if t and t.get("rows"):
        cols, rows = list(t["columns"]), [list(r) for r in t["rows"]][:40]
    else:
        rows_ = [r for r in kept["rows"] if r.get("label") is not None][:40]
        if not rows_:
            return None
        cols = [kept.get("label") or "פריט", kept.get("value") or "ערך"]
        rows = [[r["label"], r.get("value")] for r in rows_]
    # a column with nothing in it is dropped (never a column of dashes)
    keep_idx = [i for i in range(len(cols)) if any(r[i] not in (None, "", 0) for r in rows if i < len(r))]
    out = {"type": "table", "title": title or kept.get("title") or "", "unit": kept.get("unit") or "",
           "columns": [cols[i] for i in keep_idx], "rows": [[r[i] if i < len(r) else None for i in keep_idx] for r in rows]}
    if insight:
        out["insight"] = insight
    return out


def build_viz(kept: dict, chart_type: str, title: str = "", insight: str = "") -> dict:
    """Same payload contract as the native registry (frontend/src/components/ai-charts)."""
    if chart_type == "matrix":
        m = kept.get("matrix")
        if not m or not m.get("rows"):
            return build_table(kept, title, insight)
        out = {"type": "matrix", "title": title or kept.get("title") or "", "unit": kept.get("unit") or "₪",
               "metric": kept.get("value") or "", "columns": m["columns"], "rows": m["rows"][:12]}
        if insight:
            out["insight"] = insight
        return out
    if chart_type == "table":
        return build_table(kept, title, insight)
    rows = [r for r in kept["rows"] if isinstance(r.get("value"), (int, float))]
    t = chart_type
    if t == "kpi":
        total = sum(r["value"] for r in rows)
        return {"type": "kpi", "title": title or kept["title"], "value": round(total, 2), "unit": kept["unit"],
                "subtitle": insight or kept["value"]}
    if t == "donut":
        rows = [r for r in rows if r["value"] > 0]
        rows.sort(key=lambda r: -r["value"])
        if len(rows) > LIMITS["donut"]:   # palette rule: fold the tail into "אחרות"
            rows = rows[:7] + [{"label": "אחרות", "value": sum(r["value"] for r in rows[7:])}]
    elif t == "bar":
        rows = sorted(rows, key=lambda r: -r["value"])[: LIMITS["bar"]]
    else:
        rows = rows[-LIMITS["trend"]:]
    data = [{"label": str(r.get("label")), "value": round(float(r["value"]), 2),
             **({"id": str(r["id_number"])} if r.get("id_number") else {})} for r in rows]
    out = {"type": t, "title": title or kept["title"], "unit": kept["unit"], "data": data}
    if insight:
        out["insight"] = insight
    if t in ("bar", "donut") and data:
        out["highlight_label"] = data[0]["label"]
    return out


@tool("render_chart", "הצגת גרף או טבלה לסוכן מתוך תוצאה של כלי קודם. העבר את result_id שהכלי החזיר — אל תעתיק מספרים. bar = השוואה בין פריטים, trend = לפי חודשים, donut = חלוקה (עד 8 פלחים), kpi = מספר אחד גדול, matrix = לקוחות × סוגי מוצרים (מי מחזיק מה — מ-products_matrix_result_id), table = טבלה רק כשביקשו במפורש «טבלה».",
      {"result_id": {"type": "string"}, "type": {"type": "string", "enum": ["bar", "trend", "donut", "kpi", "table", "matrix"]},
       "title": {"type": "string"}, "insight": {"type": "string", "description": "משפט אחד עם המספר שמסביר את הסיפור"}},
      ["result_id", "type"], category="viz", status_he="מכין גרף")
async def render_chart(ctx, result_id: str, type: str, title: str = "", insight: str = ""):  # noqa: A002 — schema field name
    kept = ctx.results.get(result_id)
    if not kept or not (kept["rows"] or kept.get("table") or kept.get("matrix")):
        return "אין נתונים לגרף הזה — המשך בלי גרף."
    if len(ctx.vizs) >= 3:
        return "כבר הוצגו 3 גרפים — מספיק."
    v = build_viz(kept, type, title, insight)
    if not v:
        return "אין נתונים להצגה — המשך בלי."
    ctx.vizs.append(v)
    return "הגרף מוצג לסוכן. אל תחזור על כל המספרים בטקסט — תן את התובנה במשפט-שניים."
