"""Action tools — they only PREPARE (§17: nothing is sent without the agent's click).
The proposal is approved through POST /api/office-agent/act."""
from __future__ import annotations

from app.services import agent_actions
from app.services.agent.registry import tool


def _prop(ctx, kind: str, args: dict) -> str:
    try:
        ctx.proposals.append(agent_actions.normalize(kind, args))
    except agent_actions.ActionError as e:
        if str(e) == "bad_email":
            return "כתובת המייל לא תקינה — אמור לסוכן איזו כתובת קיבלת ובקש את הנכונה. אל תכין בלי כתובת תקינה."
        return f"לא תקין ({e})."
    return "הוכן והוצג לסוכן לאישור. אל תכין שוב — כתוב משפט אחד."


@tool("propose_email", agent_actions.PROPOSE_EMAIL_TOOL["description"],
      agent_actions.PROPOSE_EMAIL_TOOL["input_schema"]["properties"], agent_actions.PROPOSE_EMAIL_TOOL["input_schema"]["required"],
      category="mail", status_he="מכין מייל", action=True)
async def propose_email(ctx, **args):
    return _prop(ctx, "email", args)


@tool("propose_meeting", agent_actions.PROPOSE_MEETING_TOOL["description"] + " אם יומן Google/Outlook מחובר — האירוע ייווצר ביומן אחרי האישור.",
      agent_actions.PROPOSE_MEETING_TOOL["input_schema"]["properties"], agent_actions.PROPOSE_MEETING_TOOL["input_schema"]["required"],
      category="calendar", status_he="מכין פגישה", action=True)
async def propose_meeting(ctx, **args):
    return _prop(ctx, "meeting", args)


@tool("propose_collection_reminder", "הכנת תזכורת לחברה על עמלות שלא שולמו (תיק גבייה פתוח). לא נשלח עד שהסוכן מאשר.",
      {"company": {"type": "string"}}, ["company"], category="commissions", status_he="מכין תזכורת גבייה", action=True)
async def propose_collection_reminder(ctx, company: str):
    m = await ctx.map()
    from app.services.agent.tools_data import _match_company
    case = next((c for k, c in m.cases.items() if _match_company(c.company_name, company) and c.status != "resolved"), None)
    if not case:
        return f"אין תיק גבייה פתוח ל{company}. אפשר להציע מייל רגיל לחברה (propose_email)."
    if not case.to_email:
        return (f"לתיק הגבייה של {case.company_name} אין מייל איש קשר, אז תזכורת לא תגיע לאף אחד. "
                "השתמש ב-propose_email עם כתובת שהסוכן נתן, או בקש ממנו את הכתובת.")
    ctx.proposals.append({"kind": "collection", "case_id": str(case.id), "company": case.company_name,
                          "case_status": case.status, "customers": case.customers_count,
                          "expected": round(float(case.expected_total or 0))})
    return "התזכורת הוכנה והוצגה לסוכן לאישור. כתוב משפט אחד."
