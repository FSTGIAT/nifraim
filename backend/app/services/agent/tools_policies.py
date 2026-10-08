"""Policies: the customer's insurance policies (הר הביטוח + uploaded policy PDFs, as Markdown) and a
PROPOSED הר הביטוח fetch — the agent's click is the consent the site asks for, and the local worker
(Israeli IP, hands-free OTP) does the fetch; nothing is fetched by the model."""
from __future__ import annotations

from app.services.agent.registry import tool

_FETCH_NOTE = ("אין עדיין פוליסות ללקוח. אפשר לשלוף מהר הביטוח (propose_harb_fetch) — צריך ת.ז, "
               "תאריך לידה ותאריך הנפקת ת.ז. או שהסוכן יעלה PDF של פוליסה בכרטיס הלקוח (אנשי קשר).")


STOP = {"בפוליסה", "בפוליסת", "פוליסה", "פוליסת", "ביטוח", "הביטוח", "הלקוח", "לקוח", "שלו", "שלה", "האם", "כמה", "איזה", "אילו"}


def _idn(v) -> str:
    return "".join(ch for ch in str(v or "") if ch.isdigit()).lstrip("0")


async def _name(ctx, idn: str) -> str:
    try:
        m = await ctx.map()
        c = next((x for x in m.customers if str(x.get("id_number")).lstrip("0") == idn), None) or m.extra.get(idn)
        return " ".join(x for x in ((c or {}).get("first_name"), (c or {}).get("last_name")) if x)
    except Exception:  # noqa: BLE001 — a name is cosmetic
        return ""


@tool("propose_harb_fetch",
      "הכנת שליפה של התיק הביטוחי של לקוח מהר הביטוח (משרד האוצר) — כל הפוליסות בכל החברות. "
      "נדרשים ת.ז, תאריך לידה ותאריך הנפקת ת.ז (כפי שהסוכן כתב). לא נשלף עד שהסוכן מאשר; אחרי האישור "
      "העובד המקומי מתחבר, קוד ה-SMS מגיע לבד, והתוצאה מגיעה לצ'אט. אם חסר תאריך — אל תמציא, שאל. "
      "לקוח שנשלף לאחרונה: הכלי מחזיר שאלה — שאל אותה; רק אחרי שהסוכן אישר ('כן'/'שוב') קרא שוב עם confirm_refetch=true.",
      {"id_number": {"type": "string"}, "birth_date": {"type": "string"},
       "issue_date": {"type": "string", "description": "תאריך הנפקת תעודת הזהות"},
       "customer_name": {"type": "string"},
       "confirm_refetch": {"type": "boolean", "description": "true רק אחרי שהסוכן אישר שליפה חוזרת של לקוח שכבר נשלף"}},
      ["id_number", "birth_date", "issue_date"], category="policies", status_he="מכין שליפה מהר הביטוח", action=True)
async def propose_harb_fetch(ctx, id_number: str, birth_date: str, issue_date: str, customer_name: str = "",
                             confirm_refetch: bool = False):
    from app.services.policies import harb_jobs
    idn = _idn(id_number)
    if not 5 <= len(idn) <= 9:
        return "ת.ז לא תקינה — בקש מהסוכן ת.ז מלאה. לא הוכנה שליפה."
    birth, issued = harb_jobs.parse_user_date(birth_date), harb_jobs.parse_user_date(issue_date)
    missing = [w for w, d in (("תאריך לידה", birth), ("תאריך הנפקת ת.ז", issued)) if d is None]
    if missing:
        return (f"חסר או לא תקין: {' ו'.join(missing)}. הר הביטוח דורש אותם — בקש אותם מהסוכן במשפט אחד "
                "(למשל 22/05/1986). אל תמציא ואל תכין שליפה.")
    if issued < birth:
        return "תאריך ההנפקה מוקדם מתאריך הלידה — בקש מהסוכן לבדוק את התאריכים. לא הוכנה שליפה."
    try:
        await harb_jobs.check_gates(ctx.db, ctx.user.id, idn)
    except harb_jobs.HarbGateError as e:
        return f"לא הוכנה שליפה: {e} הסבר לסוכן במשפט אחד."
    name = (customer_name or "").strip() or await _name(ctx, idn)
    if not confirm_refetch:
        from app.config import settings
        from datetime import datetime, timedelta
        last = await harb_jobs.last_fetch(ctx.db, ctx.user.id, idn)
        if last and (last.completed_at or last.created_at) >= datetime.utcnow() - timedelta(days=settings.HARB_REFETCH_ASK_DAYS):
            return "שאל את הסוכן: " + harb_jobs.refetch_question(last, name or last.customer_name)
    ctx.proposals.append({"kind": "harb", "customer_id_number": idn, "customer_name": name[:120],
                          "birth_date": birth.strftime("%d/%m/%Y"), "issue_date": issued.strftime("%d/%m/%Y")})
    return "השליפה הוכנה והוצגה לסוכן לאישור. כתוב משפט אחד: מה יישלף ושהתוצאה תגיע לכאן אחרי האישור."


@tool("customer_policies",
      "כל הפוליסות של לקוח לפי ת.ז: התיק הביטוחי מהר הביטוח (לפי תחום → פוליסה → כיסויים, תקופה, פרמיה, "
      "בתוקף/הסתיים) ורשימת מסמכי הפוליסה (כולל PDF שהועלו). ריק = עוד לא נשלף.",
      {"id_number": {"type": "string"}}, ["id_number"], category="policies", status_he="פותח את הפוליסות")
async def customer_policies(ctx, id_number: str):
    from app.services.policies.store import customer_picture
    pic = await customer_picture(ctx.db, ctx.user.id, _idn(id_number))
    if not pic["policies"] and not pic["documents"]:
        lr = pic.get("last_request")
        if lr and lr["status"] in ("pending", "running", "awaiting_otp", "downloading"):
            return {"id_number": pic["id_number"], "found": False, "note": "שליפה מהר הביטוח בדרך — התוצאה תגיע לצ'אט."}
        return {"id_number": pic["id_number"], "found": False, "note": _FETCH_NOTE,
                "last_request": lr}
    pols = pic["policies"]
    rid = None
    by_co: dict[str, float] = {}
    for p in pols:
        if p["active"] and p["monthly_premium"]:
            by_co[p["company_short"] or "—"] = by_co.get(p["company_short"] or "—", 0) + p["monthly_premium"]
    if len(by_co) >= 2:
        rid = ctx.keep([{"label": k, "value": round(v, 2)} for k, v in sorted(by_co.items(), key=lambda kv: -kv[1])],
                       label="חברה", value="פרמיה חודשית", title="פרמיה חודשית לפי חברה — הר הביטוח")
    # Active and ended apart, so the answer never has to work out which is which.
    def brief(p, full: bool):
        out = {k: p[k] for k in ("company_short", "policy_number", "branch", "sub_branches", "period", "plan_class")}
        if p["monthly_premium"]:
            out["monthly_premium"] = p["monthly_premium"]
        if full:
            out["coverages"] = p["coverages"][:8]
        return out
    active = [brief(p, True) for p in pols if p["active"]]
    ended = [brief(p, False) for p in pols if not p["active"]]
    return {"id_number": pic["id_number"], "found": True, "customer_name": pic["customer_name"],
            "fetched_at": pic["fetched_at"], "harb_produced_at": pic["produced_at"], "totals": pic["totals"],
            "active_policies": active, "ended_policies": ended[:30],
            "changes_since_previous_fetch": pic.get("changes"),
            "fetch_history": [{k: h[k] for k in ("fetched_at", "coverages", "changes")} for h in pic.get("history", [])[:10]],
            "documents": pic["documents"][:20], "result_id": rid,
            "note": ("בתוקף = active_policies בלבד; כל מספר פוליסה שאתה מזכיר חייב להופיע שם כפי שהוא. "
                     "פרמיה חודשית: שנתית חולקה ל-12; כיסוי בלי סוג פרמיה לא נספר. פרטי כיסוי מלאים: get_policy_document.")}


@tool("search_policies",
      "חיפוש בתוך הפוליסות של הלקוחות (התיק מהר הביטוח + PDF שהועלו) לפי משמעות ומילים — למשל 'מי מבוטח בסיעוד בהראל', "
      "'תקופת אכשרה לתרופות', 'החרגות' או 'סכום ביטוח ריסק'. אפשר לצמצם לת.ז.",
      {"query": {"type": "string"}, "id_number": {"type": "string"}, "limit": {"type": "integer"}},
      ["query"], category="policies", status_he="מחפש בפוליסות")
async def search_policies(ctx, query: str, id_number: str = "", limit: int = 10):
    from app.services.policies import embeddings
    idn = _idn(id_number) or None
    k = max(1, min(int(limit or 10), 25))
    hits = await embeddings.search(ctx.db, ctx.user.id, query, k=k * 2, customer_id=idn)
    by = "meaning"
    words = await embeddings.search_words(ctx.db, ctx.user.id, query, k=k, customer_id=idn)
    if hits is None:
        hits, by = words, "words"
    else:   # hybrid: exact-word hits the meaning search didn't bring
        seen = {(h["document_id"], h["text"]) for h in hits}
        hits = hits + [w for w in words if (w["document_id"], w["text"]) not in seen]
    # A passage holding the question's own content words goes first — measured: "מי המוטב…" had all
    # passages from ONE policy and the per-document cap cut the one saying "המוטב הבלתי חוזר".
    import re as _re
    content = [w for w in _re.findall(r"[\w\u0590-\u05FF]{4,}", query) if w not in STOP]
    def has(w, h):
        hay = h["heading"] + " " + h["text"]
        return w in hay or (w[:1] in "הבלוכמש" and w[1:] in hay)
    # rare words decide: a customer's name is in nearly every passage of their policy, "המוטב" in one
    rarity = {w: 1 - sum(has(w, h) for h in hits) / max(len(hits), 1) for w in content}

    def wscore(h):
        return sum(rarity[w] for w in content if has(w, h))
    hits = sorted(hits, key=lambda h: -wscore(h))           # stable: meaning order inside each score
    cap = 6 if idn else 3                                    # one customer's question → go deeper in their policy
    out, per_doc = [], {}
    for h in hits:
        n = per_doc.get(h["document_id"], 0)
        if n >= cap:
            continue
        per_doc[h["document_id"]] = n + 1
        out.append({"document_id": str(h["document_id"]), "customer": h.get("customer_id_number"),
                    "title": h["title"], "company": h.get("company"), "policy_number": h.get("policy_number"),
                    "section": h["heading"], "text": h["text"][:600]})
        if len(out) >= k:
            break
    if not out:
        return {"passages": [], "note": "לא נמצא בפוליסות. " + (_FETCH_NOTE if idn else "")}
    return {"passages": out, "by": by,
            "note": ("ענה רק ממה שכתוב בקטעים; ציין חברה ומספר פוליסה. סכומים — העתק בדיוק כפי שכתוב (בלי לעגל) "
                     "ואל תוסיף 'לחודש'/'לשנה' אם המסמך לא אומר. לפרטים מלאים — get_policy_document.")}


@tool("get_policy_document",
      "מסמך פוליסה מלא (Markdown) לפי document_id — כיסויים, סכומים, הנחות, החרגות ותנאים. להשתמש כששאלה דורשת פירוט.",
      {"document_id": {"type": "string"}}, ["document_id"], category="policies", status_he="קורא את הפוליסה")
async def get_policy_document(ctx, document_id: str):
    import uuid
    from app.models.policy_document import PolicyDocument
    try:
        d = await ctx.db.get(PolicyDocument, uuid.UUID(str(document_id)))
    except ValueError:
        d = None
    if not d or d.user_id != ctx.user.id:
        return "המסמך לא נמצא."
    if d.status != "ready":
        return "המסמך עוד בעיבוד (פוליסה שהועלתה כרגע) — נסה שוב בעוד דקה." if d.status == "processing" else f"המסמך נכשל: {d.error}"
    return (f"# מסמך: {d.title} (לקוח {d.customer_id_number or '—'})\n"
            "(ענה מהמסמך בלבד. סכומים — העתק בדיוק, בלי לעגל, ובלי להוסיף תקופה שהמסמך לא מציין.)\n\n"
            + (d.markdown or "")[:11000])
