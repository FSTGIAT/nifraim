import asyncio
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
from app.models.commission_rate import CommissionRate
from app.models.volume_commission_rate import VolumeCommissionRate
from app.models.production_summary import ProductionSummary
from app.services.comparison_service import compute_comparison, _normalize_id

logger = logging.getLogger(__name__)


SYSTEM_PROMPT = """You are a specialized insurance reconciliation analyst assistant for the Nifraim platform.
המשתמש שמדבר איתך הוא סוכן הביטוח בעל התיק. כל הנתונים למטה שייכים לו ולתיק הלקוחות שלו.
כשהוא שואל "שלי" הוא מתכוון לנתונים שלו כסוכן — סה"כ הפרמיה, הלקוחות, העמלות וכו'.
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
- You may have access to multi-month production history. You can identify trends, growth/decline patterns, and notable changes over time.
- The personal file (קובץ אישי) may include sign dates (תאריך חתימה) for each client. Use the "גיוסים לפי חודש" block to answer questions like "כמה גייסתי במרץ/אפריל" — count per month and by company. If a client in the personal file has a sign date after the active production file's month, they won't appear in production yet — that's expected, not an error.

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

    # Top 10 clients by premium
    top_premium_q = await db.execute(
        select(
            ClientRecord.id_number,
            func.min(ClientRecord.first_name).label("first_name"),
            func.min(ClientRecord.last_name).label("last_name"),
            func.coalesce(func.sum(ClientRecord.total_premium), 0).label("total_prem"),
        )
        .where(ClientRecord.upload_id == uid, ClientRecord.id_number.isnot(None))
        .group_by(ClientRecord.id_number)
        .order_by(desc(func.coalesce(func.sum(ClientRecord.total_premium), 0)))
        .limit(10)
    )
    top_premium = [
        f"{r.first_name or ''} {r.last_name or ''}".strip() + f"({float(r.total_prem):,.0f}₪)"
        for r in top_premium_q.all() if float(r.total_prem) > 0
    ]

    # Top 10 clients by accumulation
    top_accum_q = await db.execute(
        select(
            ClientRecord.id_number,
            func.min(ClientRecord.first_name).label("first_name"),
            func.min(ClientRecord.last_name).label("last_name"),
            func.coalesce(func.sum(ClientRecord.accumulation), 0).label("total_accum"),
        )
        .where(ClientRecord.upload_id == uid, ClientRecord.id_number.isnot(None))
        .group_by(ClientRecord.id_number)
        .order_by(desc(func.coalesce(func.sum(ClientRecord.accumulation), 0)))
        .limit(10)
    )
    top_accum = [
        f"{r.first_name or ''} {r.last_name or ''}".strip() + f"({float(r.total_accum):,.0f}₪)"
        for r in top_accum_q.all() if float(r.total_accum) > 0
    ]

    parts = [
        "=== קובץ פרודוקציה ===",
        f"שם קובץ: {prod_upload.filename}",
        f"סה\"כ רשומות (מוצרים): {t.cnt}",
        f"לקוחות ייחודיים: {t.unique_clients}",
        f"סה\"כ פרמיה: {float(t.total_premium):,.0f}₪",
        f"סה\"כ צבירה: {float(t.total_accumulation):,.0f}₪",
    ]
    # Company breakdown with unique client counts
    company_enriched_q = await db.execute(
        select(
            ClientRecord.receiving_company,
            func.count().label("count"),
            func.count(func.distinct(ClientRecord.id_number)).label("unique_clients"),
            func.coalesce(func.sum(ClientRecord.total_premium), 0).label("premium"),
            func.coalesce(func.sum(ClientRecord.accumulation), 0).label("accumulation"),
        )
        .where(ClientRecord.upload_id == uid, ClientRecord.receiving_company.isnot(None))
        .group_by(ClientRecord.receiving_company)
        .order_by(desc(func.coalesce(func.sum(ClientRecord.accumulation), 0)))
    )
    companies_enriched = [
        f"{r[0]}({r[2]} לקוחות, {r[1]} מוצרים, פרמיה: {float(r[3]):,.0f}₪, צבירה: {float(r[4]):,.0f}₪)"
        for r in company_enriched_q.all() if r[0] and r[0] not in ("nan", "None")
    ]
    if companies_enriched:
        parts.append(f"חברות: {', '.join(companies_enriched)}")
    if products:
        parts.append(f"סוגי מוצרים: {', '.join(products)}")
    if top_premium:
        parts.append(f"לקוחות מובילים (פרמיה): {', '.join(top_premium)}")
    if top_accum:
        parts.append(f"לקוחות מובילים (צבירה): {', '.join(top_accum)}")

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

        # Per-company commission breakdown (matched + only_commission)
        comm_by_company = {}
        for c in commission_customers:
            for p in c.get("product_matches", {}).get("matched", []):
                co = p.get("company") or "לא ידוע"
                comm_by_company.setdefault(co, {"count": 0, "commission": 0})
                comm_by_company[co]["count"] += 1
                comm_by_company[co]["commission"] += p.get("commission") or 0
            for p in c.get("product_matches", {}).get("unmatched_commission", []):
                co = p.get("company") or "לא ידוע"
                comm_by_company.setdefault(co, {"count": 0, "commission": 0})
                comm_by_company[co]["count"] += 1
                comm_by_company[co]["commission"] += p.get("commission") or 0

        # Per-company unpaid breakdown
        unpaid_by_company = {}
        for c in unpaid:
            for p in c.get("production_products", []):
                co = p.get("company") or p.get("company_full") or "לא ידוע"
                unpaid_by_company.setdefault(co, {"customers": [], "premium": 0})
                name = f"{c.get('first_name', '')} {c.get('last_name', '')}".strip() or c.get('id_number', '')
                if name not in [n for n, _ in unpaid_by_company[co]["customers"]]:
                    unpaid_by_company[co]["customers"].append((name, float(p.get("premium") or 0)))
                unpaid_by_company[co]["premium"] += float(p.get("premium") or 0)

        part = [
            f"\n--- השוואת נפרעים: {source} ({cat_label}) ---",
            f"קובץ נפרעים: {comm_upload.filename}",
            f"סה\"כ לקוחות בהשוואה: {dashboard_total}",
            f"נמצא בשניהם (משולם): {len(matched)} ({_pct(len(matched), dashboard_total)}%)",
            f"לא שולם (בפרודוקציה אבל לא בנפרעים — חייבים לסוכן): {len(unpaid)} ({_pct(len(unpaid), dashboard_total)}%)",
            f"רק בנפרעים (בנפרעים אבל לא בפרודוקציה — לא חייבים לסוכן): {len(only_comm)} ({_pct(len(only_comm), dashboard_total)}%)",
            f"הערה חשובה: כש'חייבים לי' = לקוחות 'לא שולם' בלבד. 'רק בנפרעים' הם לקוחות שהחברה משלמת עליהם עמלה אבל לא מופיעים בפרודוקציה.",
            f"סה\"כ עמלה שהתקבלה: {total_commission:,.0f}₪",
            f"סה\"כ יתרה: {total_balance:,.0f}₪",
        ]

        # Commission by company
        if comm_by_company:
            co_lines = ", ".join(
                f"{co}({v['count']} מוצרים, עמלה: {v['commission']:,.0f}₪)"
                for co, v in sorted(comm_by_company.items(), key=lambda x: x[1]["commission"], reverse=True)
            )
            part.append(f"עמלות שהתקבלו לפי חברה: {co_lines}")

        if unpaid:
            part.append(f"סה\"כ חיוב לא משולם (חייבים לסוכן): {unpaid_charge:,.0f}₪")
            # Unpaid by company with names and amounts
            if unpaid_by_company:
                for co, data in sorted(unpaid_by_company.items(), key=lambda x: x[1]["premium"], reverse=True):
                    names_with_amounts = ", ".join(
                        f"{name}({premium:,.0f}₪)" for name, premium in data["customers"][:5]
                    )
                    part.append(f"לא משולמים מ{co} ({len(data['customers'])} לקוחות, פרמיה: {data['premium']:,.0f}₪): {names_with_amounts}")
            else:
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
    found_clients = []
    not_found = []
    total_premium_found = 0.0
    total_recruit_amount = 0.0
    company_stats = {}
    # Monthly breakdown by sign_date (YYYY-MM -> {total, by_company})
    monthly_stats = {}

    HEBREW_MONTHS = {
        1: "ינואר", 2: "פברואר", 3: "מרץ", 4: "אפריל", 5: "מאי", 6: "יוני",
        7: "יולי", 8: "אוגוסט", 9: "ספטמבר", 10: "אוקטובר", 11: "נובמבר", 12: "דצמבר",
    }

    for norm_id, recruit in recruits_by_id.items():
        prod_recs = prod_by_id.get(norm_id, [])
        comp = recruit.company or "לא ידוע"
        if comp not in company_stats:
            company_stats[comp] = {"found": 0, "not_found": 0, "premium": 0.0}

        recruit_amount = float(recruit.amount or 0)
        total_recruit_amount += recruit_amount

        if prod_recs:
            found_count += 1
            premium = sum(float(r.total_premium or 0) for r in prod_recs)
            total_premium_found += premium
            company_stats[comp]["found"] += 1
            company_stats[comp]["premium"] += premium
            found_clients.append(recruit)
        else:
            not_found.append(recruit)
            company_stats[comp]["not_found"] += 1

        # Monthly bucket by sign_date
        if recruit.sign_date:
            ym = recruit.sign_date.strftime("%Y-%m")
            bucket = monthly_stats.setdefault(ym, {"total": 0, "by_company": {}})
            bucket["total"] += 1
            bucket["by_company"][comp] = bucket["by_company"].get(comp, 0) + 1

    total = len(recruits_by_id)
    not_found_count = total - found_count
    with_sign_date = sum(1 for r in recruits_by_id.values() if r.sign_date)
    without_sign_date = total - with_sign_date

    parts = [
        "\n--- קובץ אישי (My File) ---",
        f"סה\"כ לקוחות בקובץ אישי: {total}",
        f"סה\"כ סכום בקובץ אישי: {total_recruit_amount:,.0f}₪",
        f"נמצאו בפרודוקציה: {found_count} ({_pct(found_count, total)}%)",
        f"לא נמצאו בפרודוקציה: {not_found_count} ({_pct(not_found_count, total)}%)",
        f"סה\"כ פרמיה של לקוחות שנמצאו: {total_premium_found:,.0f}₪",
        f"לקוחות עם תאריך חתימה/הצטרפות: {with_sign_date} מתוך {total}",
    ]
    if without_sign_date:
        parts.append(
            f"⚠ {without_sign_date} לקוחות בקובץ האישי חסר להם תאריך חתימה — "
            "לא ייכללו בספירות החודשיות למטה. ייתכן שיש לעדכן את הקובץ או להעלות אותו שוב."
        )

    # Monthly breakdown with Hebrew month names — helps AI answer "how many in March?"
    if monthly_stats:
        parts.append("\nגיוסים לפי חודש (לפי תאריך חתימה):")
        for ym in sorted(monthly_stats.keys(), reverse=True):
            year, month_num = ym.split("-")
            month_name = HEBREW_MONTHS.get(int(month_num), month_num)
            bucket = monthly_stats[ym]
            by_co = ", ".join(
                f"{co}: {n}"
                for co, n in sorted(bucket["by_company"].items(), key=lambda x: x[1], reverse=True)
            )
            parts.append(f"  {month_name} {year} ({ym}): {bucket['total']} לקוחות — {by_co}")

    if company_stats:
        co_lines = ", ".join(
            f"{co}(נמצאו {v['found']}, לא נמצאו {v['not_found']}, פרמיה: {v['premium']:,.0f}₪)"
            for co, v in sorted(company_stats.items(), key=lambda x: x[1]["found"] + x[1]["not_found"], reverse=True)[:8]
        )
        parts.append(f"פירוט לפי חברה: {co_lines}")

    # Detail clients — sorted by sign_date desc so recent recruits come first,
    # which matters when the global context cap truncates the tail.
    def _format_recruit(r, include_status=False):
        name = f"{r.first_name} {r.last_name}".strip() or r.id_number
        amt = float(r.amount or 0)
        product = r.product or ""
        sign = r.sign_date.strftime("%Y-%m-%d") if r.sign_date else "—"
        detail = f"  {name} (ת.ז: {r.id_number}, חברה: {r.company or '—'}, תאריך חתימה: {sign}"
        if product:
            detail += f", מוצר: {product}"
        if amt > 0:
            detail += f", סכום: {amt:,.0f}₪"
        if include_status and r.customer_status:
            detail += f", סטטוס: {r.customer_status}"
        detail += ")"
        return detail

    def _sort_key(r):
        # Most recent sign_date first; rows without sign_date go last.
        return (r.sign_date is None, -(r.sign_date.toordinal() if r.sign_date else 0))

    if not_found:
        parts.append(f"\nלקוחות שלא נמצאו בפרודוקציה ({len(not_found)}) — ייתכן שגויסו אחרי תאריך קובץ הפרודוקציה:")
        for r in sorted(not_found, key=_sort_key):
            parts.append(_format_recruit(r, include_status=True))

    if found_clients:
        parts.append(f"\nלקוחות שנמצאו בפרודוקציה ({len(found_clients)}):")
        for r in sorted(found_clients, key=_sort_key):
            parts.append(_format_recruit(r))

    return "\n".join(parts)


async def _get_commission_rates_context(db: AsyncSession, user_id: uuid.UUID) -> str | None:
    """Get commission rates and volume rates as context."""
    # Nifraim commission rates
    rates_result = await db.execute(
        select(CommissionRate).where(CommissionRate.user_id == user_id)
    )
    rates = rates_result.scalars().all()

    # Volume commission rates
    vol_rates_result = await db.execute(
        select(VolumeCommissionRate).where(VolumeCommissionRate.user_id == user_id)
    )
    vol_rates = vol_rates_result.scalars().all()

    if not rates and not vol_rates:
        return None

    parts = ["\n--- שיעורי עמלה ---"]
    if rates:
        parts.append("עמלות נפרעים:")
        for r in rates:
            freq = f", תדירות: {r.payment_frequency}" if r.payment_frequency else ""
            parts.append(f"  {r.company_name}: {float(r.rate) * 100:.2f}%{freq}")

    if vol_rates:
        parts.append("עמלות היקפים:")
        for r in vol_rates:
            nifraim = f"נפרעים: {float(r.nifraim_rate) * 100:.2f}%" if r.nifraim_rate else ""
            volume = f"היקפים: {float(r.volume_rate_per_million):,.0f}₪/מיליון" if r.volume_rate_per_million else ""
            freq = f", תדירות: {r.payment_frequency}" if r.payment_frequency else ""
            rate_parts = [p for p in [nifraim, volume] if p]
            parts.append(f"  {r.company_name}: {', '.join(rate_parts)}{freq}")

    return "\n".join(parts)


def _pct(part: int, total: int) -> str:
    if total == 0:
        return "0"
    return f"{part * 100 / total:.0f}"


STOP_WORDS = {'האם', 'מה', 'כמה', 'של', 'את', 'לי', 'על', 'יש', 'אם', 'או',
              'הוא', 'היא', 'זה', 'זו', 'לא', 'כן', 'איפה', 'למה', 'מי', 'איך',
              'שלי', 'שלו', 'שלה', 'לו', 'לה',
              'גם', 'עם', 'בין', 'כל', 'אני', 'הם', 'הן', 'אנחנו', 'אתה', 'את'}


async def _search_customers(db: AsyncSession, user_id: uuid.UUID, prod_upload_id, question: str) -> str | None:
    """Search for specific customers mentioned in the question, in both production and commission files."""
    import re

    # Extract potential ID numbers (5+ digits)
    id_patterns = re.findall(r'\d{5,}', question)

    # Extract Hebrew name words (filter stop words)
    words = re.findall(r'[\u0590-\u05FF]+', question)
    name_words = [w for w in words if w not in STOP_WORDS and len(w) > 1]

    if not id_patterns and not name_words:
        return None

    # Get all upload IDs to search (production + commission)
    upload_ids_to_search = [(prod_upload_id, "פרודוקציה")]

    comm_uploads_result = await db.execute(
        select(FileUpload)
        .where(
            FileUpload.user_id == user_id,
            FileUpload.file_category == "commission",
        )
        .order_by(desc(FileUpload.uploaded_at))
    )
    seen_filenames = set()
    for u in comm_uploads_result.scalars().all():
        if u.filename not in seen_filenames:
            seen_filenames.add(u.filename)
            label = f"נפרעים ({u.company_source or u.filename})"
            upload_ids_to_search.append((u.id, label))
        if len(seen_filenames) >= 5:
            break

    all_lines = ["\n--- תוצאות חיפוש לקוחות ---"]

    for upload_id, source_label in upload_ids_to_search:
        results = []

        # Search by ID number
        for id_pat in id_patterns:
            q = await db.execute(
                select(ClientRecord).where(
                    ClientRecord.upload_id == upload_id,
                    ClientRecord.id_number.like(f"%{id_pat}%"),
                ).limit(10)
            )
            results.extend(q.scalars().all())

        # Search by name
        for word in name_words[:3]:
            q = await db.execute(
                select(ClientRecord).where(
                    ClientRecord.upload_id == upload_id,
                    (ClientRecord.first_name.ilike(f"%{word}%")) |
                    (ClientRecord.last_name.ilike(f"%{word}%")),
                ).limit(10)
            )
            results.extend(q.scalars().all())

        if not results:
            continue

        # Deduplicate by id
        seen = set()
        unique = []
        for r in results:
            if r.id not in seen:
                seen.add(r.id)
                unique.append(r)

        all_lines.append(f"\n[{source_label}]")
        for r in unique[:10]:
            name = f"{r.first_name or ''} {r.last_name or ''}".strip()
            premium = float(r.total_premium or 0)
            accum = float(r.accumulation or 0)
            commission = float(r.commission_before_fee or 0) if hasattr(r, 'commission_before_fee') and r.commission_before_fee else 0
            line = (
                f"שם: {name}, ת.ז: {r.id_number}, חברה: {r.receiving_company or '—'}, "
                f"מוצר: {r.product_type or r.product or '—'}, "
                f"סטטוס: {r.product_status or '—'}, "
                f"פרמיה: {premium:,.0f}₪, צבירה: {accum:,.0f}₪"
            )
            if commission > 0:
                line += f", עמלה: {commission:,.0f}₪"
            all_lines.append(line)

    if len(all_lines) <= 1:
        return None

    return "\n".join(all_lines)


async def _get_historical_context(db: AsyncSession, user_id: uuid.UUID) -> str | None:
    """Get multi-month production history from pre-computed summaries."""
    result = await db.execute(
        select(ProductionSummary)
        .where(ProductionSummary.user_id == user_id)
        .order_by(desc(ProductionSummary.upload_date))
        .limit(12)
    )
    summaries = result.scalars().all()
    if not summaries:
        return None

    parts = ["=== היסטוריית פרודוקציה ==="]
    parts.append("חודש | לקוחות | פרמיה | צבירה | שינוי פרמיה")
    parts.append("---|---|---|---|---")

    for s in summaries:
        premium_change = ""
        if s.changes_json:
            pct = s.changes_json.get("premium_diff_pct", 0)
            if pct > 0:
                premium_change = f"+{pct}%"
            elif pct < 0:
                premium_change = f"{pct}%"

        parts.append(
            f"{s.period_label} | {s.unique_clients:,} | "
            f"{float(s.total_premium):,.0f}₪ | {float(s.total_accumulation):,.0f}₪ | "
            f"{premium_change or '—'}"
        )

    # Add notable changes for the most recent month
    latest = summaries[0]
    if latest.changes_json:
        ch = latest.changes_json
        changes_parts = []
        if ch.get("new_clients", 0) > 0:
            changes_parts.append(f"+{ch['new_clients']} לקוחות חדשים")
        if ch.get("removed_clients", 0) > 0:
            changes_parts.append(f"-{ch['removed_clients']} עזבו")
        if ch.get("premium_diff", 0) != 0:
            diff = ch["premium_diff"]
            sign = "+" if diff > 0 else ""
            changes_parts.append(f"פרמיה {sign}{diff:,.0f}₪")
        if changes_parts:
            parts.append(f"\nשינויים בולטים ({latest.period_label}): {', '.join(changes_parts)}")

    return "\n".join(parts)


async def _get_customer_history(
    db: AsyncSession, user_id: uuid.UUID, question: str
) -> str | None:
    """Get per-customer historical data across production uploads when a specific customer is mentioned."""
    import re

    # Extract ID number from question
    id_match = re.search(r'\d{5,}', question)
    if not id_match:
        return None

    search_id = id_match.group(0).lstrip('0') or '0'

    # Query this customer across all production uploads
    result = await db.execute(
        select(
            FileUpload.filename,
            FileUpload.uploaded_at,
            func.min(ClientRecord.first_name).label("first_name"),
            func.min(ClientRecord.last_name).label("last_name"),
            func.coalesce(func.sum(ClientRecord.total_premium), 0).label("premium"),
            func.coalesce(func.sum(ClientRecord.accumulation), 0).label("accumulation"),
            func.count().label("products"),
        )
        .join(FileUpload, ClientRecord.upload_id == FileUpload.id)
        .where(
            ClientRecord.id_number == search_id,
            FileUpload.user_id == user_id,
            FileUpload.file_category == "production",
        )
        .group_by(FileUpload.id, FileUpload.filename, FileUpload.uploaded_at)
        .order_by(desc(FileUpload.uploaded_at))
        .limit(12)
    )
    rows = result.all()
    if not rows:
        return None

    name = f"{rows[0].first_name or ''} {rows[0].last_name or ''}".strip()
    parts = [f"=== היסטוריית לקוח: {name} (ת.ז {search_id}) ==="]
    parts.append("תקופה | פרמיה | צבירה | מוצרים")
    parts.append("---|---|---|---")

    for r in rows:
        period = r.uploaded_at.strftime("%Y-%m")
        parts.append(
            f"{period} | {float(r.premium):,.0f}₪ | {float(r.accumulation):,.0f}₪ | {r.products}"
        )

    return "\n".join(parts)


def _detect_question_topics(question: str) -> set[str]:
    """Detect which data sources are relevant to the user's question."""
    q = question.lower()
    topics = set()

    # Always include production (base context)
    topics.add("production")

    # Commission / comparison keywords
    if any(w in q for w in ["נפרעים", "עמלה", "עמלות", "משולם", "לא שולם", "commission", "השוואה", "השוואת"]):
        topics.add("comparison")

    # My file / recruits keywords
    if any(w in q for w in ["קובץ אישי", "מגויס", "מגויסים", "גיוס", "תיק אישי", "ניהול תיק", "מעקב"]):
        topics.add("myfile")

    # Commission rates keywords
    if any(w in q for w in ["שיעור", "שיעורי", "אחוז", "rates", "תעריף", "היקפים"]):
        topics.add("rates")

    # History / trends keywords
    if any(w in q for w in ["מגמה", "מגמות", "היסטוריה", "שינוי", "שינויים", "חודש קודם",
                             "חודשים", "לאורך זמן", "השוואה בין חודשים", "גדל", "ירד",
                             "עלה", "ירידה", "עלייה", "צמיחה", "trend", "history"]):
        topics.add("history")

    # Customer search — if question has names or IDs
    import re
    if re.search(r'\d{5,}', question) or len([w for w in re.findall(r'[\u0590-\u05FF]+', question) if w not in STOP_WORDS and len(w) > 1]) > 0:
        topics.add("search")

    # If no specific topic detected, include everything
    if topics == {"production"}:
        topics = {"production", "comparison", "myfile", "rates", "history"}

    return topics


MAX_CONTEXT_CHARS = 30000  # ~7.5K tokens — big enough for full recruits + comparison context


async def build_user_context(db: AsyncSession, user_id, question: str = "") -> str | None:
    prod_context, prod_upload = await _get_production_context(db, user_id)
    if not prod_context:
        return None

    topics = _detect_question_topics(question) if question else {"production", "comparison", "myfile", "rates", "history"}

    context_parts = [prod_context]

    # Historical production trends
    if "history" in topics:
        hist_context = await _get_historical_context(db, user_id)
        if hist_context:
            context_parts.append(hist_context)

        # Per-customer history if a specific ID is mentioned
        if question:
            cust_hist = await _get_customer_history(db, user_id, question)
            if cust_hist:
                context_parts.append(cust_hist)

    if prod_upload:
        if "comparison" in topics:
            comp_context = await _get_comparison_context(db, user_id, prod_upload)
            if comp_context:
                context_parts.append(comp_context)

        if "myfile" in topics:
            myfile_context = await _get_myfile_context(db, user_id, prod_upload)
            if myfile_context:
                context_parts.append(myfile_context)

        # Search for specific customers if question contains names/IDs
        if question and "search" in topics:
            search_context = await _search_customers(db, user_id, prod_upload.id, question)
            if search_context:
                context_parts.append(search_context)

    # Commission rates (independent of production upload)
    if "rates" in topics:
        rates_context = await _get_commission_rates_context(db, user_id)
        if rates_context:
            context_parts.append(rates_context)

    full_context = "\n\n".join(context_parts)

    # Truncate if too long to avoid API overload
    if len(full_context) > MAX_CONTEXT_CHARS:
        full_context = full_context[:MAX_CONTEXT_CHARS] + "\n\n[... נתונים נוספים קוצצו למניעת עומס ...]"

    return full_context


async def stream_chat(
    db: AsyncSession,
    user_id,
    question: str,
    history: list[dict],
    view_context: str | None = None,
) -> AsyncGenerator[str, None]:
    context = await build_user_context(db, user_id, question=question)
    if context is None:
        yield f"data: {json.dumps({'text': 'אין נתונים במערכת. יש להעלות קבצים תחילה.'}, ensure_ascii=False)}\n\n"
        yield f"data: {json.dumps({'done': True})}\n\n"
        return

    system_prompt = SYSTEM_PROMPT.format(context=context)
    if view_context:
        system_prompt += (
            f"\n\n=== המסך הנוכחי של המשתמש ===\n"
            f"{view_context}\n\n"
            "הנחיה חשובה: הבלוק למעלה הוא מקור האמת ל\"מה שהמשתמש רואה עכשיו\". "
            "אל תגיד שאין לך נתונים השוואתיים או היסטוריים — הבלוק הזה כולל בדיוק את ההשוואה בין שני קבצי הפרודוקציה שהמשתמש צופה בה, "
            "לרבות לקוחות שהשתנו, חדשים, הוסרו, לקוחות שעברו חברה (אותו ת.ז מופיע גם בהוסרו וגם בחדשים עם חברה שונה), "
            "ושינויי פרמיה/צבירה/עמלה לפי חברה. השתמש בנתונים האלו ישירות כדי לענות על כל שאלה הקשורה להשוואה, "
            "למעברי חברה, לעליות/ירידות לפי חברה או לקוח — ואל תמציא שאין לך את הנתון."
        )

    messages = []
    for msg in history[-10:]:
        messages.append({"role": msg["role"], "content": msg["content"]})
    messages.append({"role": "user", "content": question})

    if not settings.ANTHROPIC_API_KEY:
        yield f"data: {json.dumps({'text': 'שגיאה: מפתח API של Anthropic לא הוגדר. יש להגדיר ANTHROPIC_API_KEY.'}, ensure_ascii=False)}\n\n"
        yield f"data: {json.dumps({'done': True})}\n\n"
        return

    client = anthropic.AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)

    # Try Sonnet twice (with backoff), then Haiku as fallback
    attempts = [
        ("claude-sonnet-4-20250514", 0),
        ("claude-sonnet-4-20250514", 2),
        ("claude-haiku-4-5-20251001", 1),
    ]
    last_error = None

    for model, delay in attempts:
        if delay:
            await asyncio.sleep(delay)
        try:
            async with client.messages.stream(
                model=model,
                max_tokens=2048,
                system=system_prompt,
                messages=messages,
            ) as stream:
                async for text in stream.text_stream:
                    yield f"data: {json.dumps({'text': text}, ensure_ascii=False)}\n\n"
            last_error = None
            break  # success
        except anthropic.AuthenticationError:
            yield f"data: {json.dumps({'text': 'שגיאה: מפתח ה-API אינו תקין.'}, ensure_ascii=False)}\n\n"
            last_error = None
            break
        except (anthropic.APIStatusError, anthropic.APIConnectionError) as e:
            last_error = e
            logger.warning(f"AI chat {model} failed: {type(e).__name__}: {e}")
            continue
        except Exception as e:
            last_error = e
            logger.error(f"AI chat error: {type(e).__name__}: {e}")
            break

    if last_error:
        logger.error(f"AI chat all attempts failed: {type(last_error).__name__}: {last_error}")
        yield f"data: {json.dumps({'text': 'שגיאה: לא ניתן לעבד את הבקשה כרגע. נסה שוב בעוד רגע.'}, ensure_ascii=False)}\n\n"

    yield f"data: {json.dumps({'done': True})}\n\n"
