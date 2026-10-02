"""render_chart — the model points at rows a tool already returned (result_id);
the SERVER builds the chart, so the model never re-types numbers (that was
~1,100 output tokens per chart answer — docs/AI_VIZ.md §3)."""
from __future__ import annotations

from app.services.agent.registry import tool


LIMITS = {"bar": 10, "donut": 8, "trend": 24}


def build_viz(kept: dict, chart_type: str, title: str = "", insight: str = "") -> dict:
    """Same payload contract as the native registry (frontend/src/components/ai-charts)."""
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


@tool("render_chart", "הצגת גרף מונפש לסוכן מתוך תוצאה של כלי קודם. העבר את result_id שהכלי החזיר — אל תעתיק מספרים. bar = השוואה בין פריטים, trend = לפי חודשים, donut = חלוקה (עד 8 פלחים), kpi = מספר אחד גדול.",
      {"result_id": {"type": "string"}, "type": {"type": "string", "enum": ["bar", "trend", "donut", "kpi"]},
       "title": {"type": "string"}, "insight": {"type": "string", "description": "משפט אחד עם המספר שמסביר את הסיפור"}},
      ["result_id", "type"], category="viz", status_he="מכין גרף")
async def render_chart(ctx, result_id: str, type: str, title: str = "", insight: str = ""):  # noqa: A002 — schema field name
    kept = ctx.results.get(result_id)
    if not kept or not kept["rows"]:
        return "אין נתונים לגרף הזה — המשך בלי גרף."
    if len(ctx.vizs) >= 3:
        return "כבר הוצגו 3 גרפים — מספיק."
    ctx.vizs.append(build_viz(kept, type, title, insight))
    return "הגרף מוצג לסוכן. אל תחזור על כל המספרים בטקסט — תן את התובנה במשפט-שניים."
