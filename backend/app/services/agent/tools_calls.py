"""Calls (שיחות) — the agent records a conversation when asked, and reads summaries back.

Recording happens in the AGENT'S BROWSER (microphone → calls store → /api/calls →
ivrit.ai transcript → Claude summary; see api/calls.py). So these tools don't record on
the server: they hand the open app an instruction (`proposal` kind record_call /
stop_call) that the chat surfaces execute at once — the agent's own request is the
consent, and nothing leaves the app. When the summary is ready the app posts it back
into the conversation (frontend utils/agentCalls.js).
"""
from __future__ import annotations

from sqlalchemy import select

from app.models.call_recording import CALL_TERMINAL, CallRecording
from app.services.agent.registry import tool


def call_brief(c: CallRecording) -> dict:
    ins = c.insights or {}
    return {
        "id": str(c.id), "status": c.status, "title": c.title,
        "when": c.created_at.strftime("%d/%m %H:%M") if c.created_at else None,
        "minutes": round((c.duration_s or 0) / 60, 1) if c.duration_s else None,
        "tldr": ins.get("tldr"), "summary": c.summary,
        "action_items": ins.get("action_items"), "follow_up": ins.get("follow_up"),
        "customer_needs": ins.get("customer_needs"), "sentiment": ins.get("sentiment"),
    }


@tool("start_call_recording", "התחלת הקלטה של שיחה עם לקוח (מהמיקרופון בדפדפן של הסוכן). כשהשיחה תסתיים והסוכן יעצור — היא מתומללת ומסוכמת, והסיכום יגיע לכאן אוטומטית.",
      {"about": {"type": "string", "description": "עם מי / על מה השיחה, אם נאמר"}},
      category="calls", status_he="מתחיל להקליט")
async def start_call_recording(ctx, about: str = ""):
    ctx.proposals.append({"kind": "record_call", "about": (about or "")[:120]})
    return "ההקלטה מתחילה עכשיו בדפדפן. כתוב משפט אחד: שאתה מקליט, ושיגידו 'עצור' (או ילחצו עצור) בסוף — והסיכום יגיע לכאן."


@tool("stop_call_recording", "עצירת ההקלטה שרצה ושליחתה לתמלול וסיכום. הסיכום יגיע לכאן כשיהיה מוכן (בדרך כלל דקות).",
      category="calls", status_he="עוצר את ההקלטה")
async def stop_call_recording(ctx):
    ctx.proposals.append({"kind": "stop_call"})
    return "ההקלטה נעצרת ונשלחת לסיכום. כתוב משפט אחד שהסיכום יגיע לכאן כשיהיה מוכן."


@tool("get_call_summaries", "סיכומי שיחות שהוקלטו: which=last לשיחה האחרונה, או חיפוש לפי מילה בכותרת/בסיכום (שם לקוח, נושא). מחזיר כותרת, שורת סיכום, משימות והצעד הבא.",
      {"which": {"type": "string", "description": "last, או מילה לחיפוש"}, "n": {"type": "integer"}},
      category="calls", status_he="קורא את סיכומי השיחות")
async def get_call_summaries(ctx, which: str = "last", n: int = 3):
    rows = (await ctx.db.execute(select(CallRecording).where(CallRecording.user_id == ctx.user.id)
                                 .order_by(CallRecording.created_at.desc()).limit(100))).scalars().all()
    if not rows:
        return {"calls": [], "note": "עוד לא הוקלטו שיחות. אפשר לבקש ממני 'תקליט את השיחה'."}
    q = (which or "last").strip()
    if q and q != "last":
        rows = [c for c in rows if q in (c.title or "") or q in (c.summary or "") or q in (c.transcript_text or "")]
    pending = [c for c in rows if c.status not in CALL_TERMINAL]
    done = [c for c in rows if c.status == "done" and (c.summary or c.title)]
    out = {"calls": [call_brief(c) for c in done[: max(1, min(int(n or 3), 10))]]}
    if pending:
        out["in_progress"] = len(pending)
        out["note"] = f"{len(pending)} שיחות עדיין בעיבוד — הסיכום יגיע לכאן כשיהיה מוכן."
    if not done and not pending:
        out["note"] = f"לא נמצאה שיחה שמתאימה ל«{q}»."
    return out
