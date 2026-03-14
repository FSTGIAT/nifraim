import json
import logging
import uuid
from typing import AsyncGenerator

import anthropic
from sqlalchemy import select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.upload import FileUpload
from app.models.record import ClientRecord
from app.models.paying_company import PayingCompany
from app.models.recruit import Recruit
from app.services.comparison_service import compute_comparison, _normalize_id

logger = logging.getLogger(__name__)


SYSTEM_PROMPT = """You are a specialized insurance reconciliation analyst assistant for the Nifraim platform.
You have access ONLY to the user's data shown below. You MUST:
- Answer ONLY questions about this data. Refuse anything else politely.
- Always respond in Hebrew.
- Be concise and professional.
- Use numbers and specific data points from the context.
- If asked about something not in the data, say you don't have that information.
- When presenting lists, comparisons, or financial data — ALWAYS use markdown tables with | columns |.
- Format currency values with ₪ symbol and comma separators (e.g. ₪1,234).
- Use **bold** for important numbers and key insights.
- Keep tables concise — max 10 rows, summarize the rest.

=== נתוני המשתמש ===
{context}
==="""


def _record_to_dict(r):
    return {c.key: getattr(r, c.key) for c in r.__table__.columns if c.key not in ("id", "user_id", "upload_id")}


async def _get_production_context(db: AsyncSession, user_id: uuid.UUID) -> tuple[str | None, FileUpload | None]:
    """Get production file analytics as context string."""
    # Find active production upload
    result = await db.execute(
        select(FileUpload).where(
            FileUpload.user_id == user_id,
            FileUpload.is_production == True,
        )
    )
    prod_upload = result.scalar_one_or_none()
    if not prod_upload:
        return None, None

    uid = prod_upload.id

    # Totals
    totals = await db.execute(
        select(
            func.count().label("cnt"),
            func.count(func.distinct(ClientRecord.id_number)).label("unique_clients"),
            func.coalesce(func.sum(ClientRecord.total_premium), 0).label("total_premium"),
            func.coalesce(func.sum(ClientRecord.accumulation), 0).label("total_accumulation"),
        ).where(ClientRecord.upload_id == uid)
    )
    t = totals.one()

    # Company breakdown
    company_q = await db.execute(
        select(
            ClientRecord.receiving_company,
            func.count().label("count"),
            func.coalesce(func.sum(ClientRecord.total_premium), 0).label("premium"),
            func.coalesce(func.sum(ClientRecord.accumulation), 0).label("accumulation"),
        )
        .where(ClientRecord.upload_id == uid, ClientRecord.receiving_company.isnot(None))
        .group_by(ClientRecord.receiving_company)
        .order_by(desc(func.coalesce(func.sum(ClientRecord.accumulation), 0)))
    )
    companies = [
        f"{r[0]}({r[1]} מוצרים, פרמיה: {float(r[2]):,.0f}₪, צבירה: {float(r[3]):,.0f}₪)"
        for r in company_q.all() if r[0] and r[0] not in ("nan", "None")
    ]

    # Product type breakdown
    product_q = await db.execute(
        select(
            ClientRecord.product_type,
            func.count().label("count"),
            func.coalesce(func.sum(ClientRecord.total_premium), 0).label("premium"),
        )
        .where(ClientRecord.upload_id == uid, ClientRecord.product_type.isnot(None))
        .group_by(ClientRecord.product_type)
        .order_by(desc(func.count()))
    )
    products = [
        f"{r[0]}({r[1]} מוצרים, פרמיה: {float(r[2]):,.0f}₪)"
        for r in product_q.all() if r[0] and r[0] not in ("nan", "None")
    ]

    parts = [
        "=== קובץ פרודוקציה ===",
        f"שם קובץ: {prod_upload.filename}",
        f"סה\"כ רשומות (מוצרים): {t.cnt}",
        f"לקוחות ייחודיים: {t.unique_clients}",
        f"סה\"כ פרמיה: {float(t.total_premium):,.0f}₪",
        f"סה\"כ צבירה: {float(t.total_accumulation):,.0f}₪",
    ]
    if companies:
        parts.append(f"חברות: {', '.join(companies)}")
    if products:
        parts.append(f"סוגי מוצרים: {', '.join(products)}")

    return "\n".join(parts), prod_upload


async def _get_comparison_context(db: AsyncSession, user_id: uuid.UUID, prod_upload: FileUpload) -> str | None:
    """Recompute comparison from latest commission uploads and format as context.

    Matches the dashboard logic exactly:
    - Deduplicate commission uploads by filename (use latest)
    - "נמצא בשניהם" = matched customers
    - "לא שולם" = only_production customers with accumulation > 0 (for gemel)
    - "רק בנפרעים" = only_commission customers
    - Total shown = matched + unpaid + only_commission (excludes only_prod with no accumulation)
    """
    # Find commission uploads, deduplicate by filename (keep latest)
    comm_uploads_result = await db.execute(
        select(FileUpload)
        .where(
            FileUpload.user_id == user_id,
            FileUpload.file_category == "commission",
        )
        .order_by(desc(FileUpload.uploaded_at))
    )
    all_comm_uploads = comm_uploads_result.scalars().all()
    if not all_comm_uploads:
        return None

    # Deduplicate: keep only latest upload per filename
    seen_filenames = set()
    comm_uploads = []
    for u in all_comm_uploads:
        if u.filename not in seen_filenames:
            seen_filenames.add(u.filename)
            comm_uploads.append(u)
    comm_uploads = comm_uploads[:5]  # max 5 unique files

    # Load production records
    prod_result = await db.execute(
        select(ClientRecord).where(
            ClientRecord.upload_id == prod_upload.id,
            ClientRecord.user_id == user_id,
        )
    )
    prod_records = prod_result.scalars().all()
    if not prod_records:
        return None

    prod_dicts = [_record_to_dict(r) for r in prod_records]

    # Load paying companies
    paying_result = await db.execute(
        select(PayingCompany).where(PayingCompany.user_id == user_id)
    )
    paying_names = [p.company_name for p in paying_result.scalars().all()]

    comparison_parts = []
    for comm_upload in comm_uploads:
        comm_result = await db.execute(
            select(ClientRecord).where(
                ClientRecord.upload_id == comm_upload.id,
                ClientRecord.user_id == user_id,
            )
        )
        comm_records = comm_result.scalars().all()
        if not comm_records:
            continue

        comm_dicts = [_record_to_dict(r) for r in comm_records]
        comparison = compute_comparison(prod_dicts, comm_dicts, paying_names)

        cat = comparison.get("commission_category", "")
        cat_label = comparison.get("commission_category_label", "")
        source = comm_upload.company_source or comm_upload.filename
        is_gemel = cat == "gemel_hishtalmut"

        # Commission company sources for filtering only_production (matches frontend relevantCustomers)
        comm_company = comm_upload.company_source or ""

        def _matches_commission_company(product_company):
            if not product_company or not comm_company:
                return False
            return comm_company.lower() in product_company.lower() or product_company.lower() in comm_company.lower()

        # Classify customers exactly like the dashboard
        matched = [c for c in comparison["customers"] if c["match_status"] == "matched"]
        only_comm = [c for c in comparison["customers"] if c["match_status"] == "only_commission"]

        # Filter only_production to relevant commission company (like frontend relevantCustomers)
        relevant_only_prod = []
        for c in comparison["customers"]:
            if c["match_status"] != "only_production":
                continue
            relevant_products = [
                p for p in c.get("production_products", [])
                if _matches_commission_company(p.get("company")) or _matches_commission_company(p.get("company_full"))
            ]
            if relevant_products:
                c_copy = dict(c)
                c_copy["production_products"] = relevant_products
                relevant_only_prod.append(c_copy)

        # "לא שולם" = relevant only_production, filtered by accumulation for gemel
        if is_gemel:
            unpaid = [c for c in relevant_only_prod
                      if any((p.get("accumulation") or 0) > 0 for p in c.get("production_products", []))]
        else:
            unpaid = relevant_only_prod

        # Dashboard total = matched + unpaid + only_commission
        dashboard_total = len(matched) + len(unpaid) + len(only_comm)
        commission_customers = matched + only_comm

        # Commission totals (from matched + only_commission customers)
        total_commission = sum(c.get("total_commission") or 0 for c in commission_customers)

        # Total balance from all commission products (matched + unmatched)
        total_balance = 0
        for c in commission_customers:
            for p in c.get("product_matches", {}).get("matched", []):
                total_balance += p.get("balance") or 0
            for p in c.get("product_matches", {}).get("unmatched_commission", []):
                total_balance += p.get("balance") or 0

        # Unpaid charge estimate: sum premium or accumulation of unpaid customers' relevant products
        unpaid_charge = 0
        for c in unpaid:
            for p in c.get("production_products", []):
                unpaid_charge += (p.get("premium") or 0) or (p.get("accumulation") or 0)

        part = [
            f"\n--- השוואת נפרעים: {source} ({cat_label}) ---",
            f"קובץ נפרעים: {comm_upload.filename}",
            f"סה\"כ לקוחות בהשוואה: {dashboard_total}",
            f"נמצא בשניהם: {len(matched)} ({_pct(len(matched), dashboard_total)}%)",
            f"לא שולם: {len(unpaid)} ({_pct(len(unpaid), dashboard_total)}%)",
            f"רק בנפרעים: {len(only_comm)} ({_pct(len(only_comm), dashboard_total)}%)",
            f"לקוחות בנפרעים: {len(commission_customers)}",
            f"סה\"כ עמלה: {total_commission:,.0f}₪",
            f"סה\"כ יתרה: {total_balance:,.0f}₪",
        ]

        if unpaid:
            part.append(f"סה\"כ חיוב לא משולם: {unpaid_charge:,.0f}₪")
            unpaid_names = [
                f"{c.get('first_name', '')} {c.get('last_name', '')}".strip() or c.get('id_number', '')
                for c in unpaid[:10]
            ]
            part.append(f"לקוחות לא משולמים: {', '.join(unpaid_names)}")

        comparison_parts.append("\n".join(part))

    if not comparison_parts:
        return None

    return "\n".join(comparison_parts)


async def _get_myfile_context(db: AsyncSession, user_id: uuid.UUID, prod_upload: FileUpload) -> str | None:
    """Get My File (recruits) comparison context against production."""
    # Load recruits
    recruits_result = await db.execute(
        select(Recruit).where(Recruit.user_id == user_id).order_by(Recruit.created_at.desc())
    )
    recruits = recruits_result.scalars().all()
    if not recruits:
        return None

    # Group recruits by normalized id (keep first per client)
    recruits_by_id = {}
    for r in recruits:
        key = _normalize_id(r.id_number)
        if key not in recruits_by_id:
            recruits_by_id[key] = r

    # Load production records grouped by normalized id
    prod_result = await db.execute(
        select(ClientRecord).where(
            ClientRecord.upload_id == prod_upload.id,
            ClientRecord.user_id == user_id,
        )
    )
    prod_records = prod_result.scalars().all()
    prod_by_id = {}
    for r in prod_records:
        if r.id_number:
            prod_by_id.setdefault(_normalize_id(r.id_number), []).append(r)

    found_count = 0
    not_found = []
    total_premium_found = 0.0
    company_stats = {}

    for norm_id, recruit in recruits_by_id.items():
        prod_recs = prod_by_id.get(norm_id, [])
        comp = recruit.company or "לא ידוע"
        if comp not in company_stats:
            company_stats[comp] = {"found": 0, "not_found": 0, "premium": 0.0}

        if prod_recs:
            found_count += 1
            premium = sum(float(r.total_premium or 0) for r in prod_recs)
            total_premium_found += premium
            company_stats[comp]["found"] += 1
            company_stats[comp]["premium"] += premium
        else:
            not_found.append(recruit)
            company_stats[comp]["not_found"] += 1

    total = len(recruits_by_id)
    not_found_count = total - found_count

    parts = [
        "\n--- My File (קובץ אישי) ---",
        f"סה\"כ לקוחות: {total}",
        f"נמצאו בפרודוקציה: {found_count} ({_pct(found_count, total)}%)",
        f"לא נמצאו: {not_found_count} ({_pct(not_found_count, total)}%)",
        f"סה\"כ פרמיה של לקוחות שנמצאו: {total_premium_found:,.0f}₪",
    ]

    if company_stats:
        co_lines = ", ".join(
            f"{co}(נמצאו {v['found']}, לא נמצאו {v['not_found']}, פרמיה: {v['premium']:,.0f}₪)"
            for co, v in sorted(company_stats.items(), key=lambda x: x[1]["found"] + x[1]["not_found"], reverse=True)[:8]
        )
        parts.append(f"פירוט לפי חברה: {co_lines}")

    if not_found[:10]:
        names = [
            f"{r.first_name} {r.last_name}".strip() or r.id_number
            for r in not_found[:10]
        ]
        parts.append(f"לקוחות שלא נמצאו: {', '.join(names)}")

    return "\n".join(parts)


def _pct(part: int, total: int) -> str:
    if total == 0:
        return "0"
    return f"{part * 100 / total:.0f}"


async def build_user_context(db: AsyncSession, user_id) -> str | None:
    prod_context, prod_upload = await _get_production_context(db, user_id)
    if not prod_context:
        return None

    context_parts = [prod_context]

    if prod_upload:
        comp_context = await _get_comparison_context(db, user_id, prod_upload)
        if comp_context:
            context_parts.append(comp_context)

        myfile_context = await _get_myfile_context(db, user_id, prod_upload)
        if myfile_context:
            context_parts.append(myfile_context)

    return "\n\n".join(context_parts)


async def stream_chat(
    db: AsyncSession, user_id, question: str, history: list[dict]
) -> AsyncGenerator[str, None]:
    context = await build_user_context(db, user_id)
    if context is None:
        yield f"data: {json.dumps({'text': 'אין נתונים במערכת. יש להעלות קבצים תחילה.'}, ensure_ascii=False)}\n\n"
        yield f"data: {json.dumps({'done': True})}\n\n"
        return

    system_prompt = SYSTEM_PROMPT.format(context=context)

    messages = []
    for msg in history[-10:]:
        messages.append({"role": msg["role"], "content": msg["content"]})
    messages.append({"role": "user", "content": question})

    if not settings.ANTHROPIC_API_KEY:
        yield f"data: {json.dumps({'text': 'שגיאה: מפתח API של Anthropic לא הוגדר. יש להגדיר ANTHROPIC_API_KEY.'}, ensure_ascii=False)}\n\n"
        yield f"data: {json.dumps({'done': True})}\n\n"
        return

    client = anthropic.AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)

    try:
        async with client.messages.stream(
            model="claude-sonnet-4-20250514",
            max_tokens=1024,
            system=system_prompt,
            messages=messages,
        ) as stream:
            async for text in stream.text_stream:
                yield f"data: {json.dumps({'text': text}, ensure_ascii=False)}\n\n"
    except anthropic.AuthenticationError:
        yield f"data: {json.dumps({'text': 'שגיאה: מפתח ה-API אינו תקין.'}, ensure_ascii=False)}\n\n"
    except Exception as e:
        logger.error(f"AI chat error: {type(e).__name__}: {e}")
        yield f"data: {json.dumps({'text': 'שגיאה: לא ניתן לעבד את הבקשה כרגע.'}, ensure_ascii=False)}\n\n"

    yield f"data: {json.dumps({'done': True})}\n\n"
