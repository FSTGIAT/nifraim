"""The מסלקה's monthly answers become the agent's production book.

A 2000/2100 answer is stored as `pension_holdings` (one row per product, stamped
with its תאריך נכונות). Until 2026-10-10 nothing turned them into production: the
Production tab kept showing the last uploaded file (July) while September sat in
the holdings table.

`rebuild_production_book` writes a NEW merged production upload for the newest
holdings month. It starts from the base book (the newest production upload that
is not itself built from the מסלקה) and replaces only the products the מסלקה
actually reported:

  * A base row is replaced ONLY when the same customer + policy + company appears
    in the new month. Answers are partial by body and by product family: kiko's
    Phoenix answer held its gemel/השתלמות but not its pension funds (32 active
    rows, ₪6.2M), and Altshuler's held its pension but not its gemel (231 rows,
    ₪17.2M). Replacing "the whole company" would have dropped them.
  * The company is part of the key because pension rows carry the member's ID as
    the policy, so customer + policy alone matches across insurers.
  * A replaced row keeps everything the base row knew (names, phone, employer,
    product name) and takes the new month's values, and only the values the
    מסלקה actually sent. Migdal's answer has a balance on 5 of 54 rows; a
    missing one must not become ₪0.
  * Every row says which month it is: `processing_date` holds its as-of date
    (the holding's status_date, or the base book's month for a carried row).
    The comparison uses it so a July row is never judged against September
    נפרעים, or the other way round.

The base upload stays in the database, now inactive, so the comparison can still
judge July production against July נפרעים until September's arrive (the 21st).
"""
from __future__ import annotations

import logging
import uuid
from collections import defaultdict
from datetime import date, datetime

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.pension_holding import PensionHolding
from app.models.pension_inquiry import PensionInquiry
from app.models.record import ClientRecord
from app.models.upload import FileUpload
from app.utils.company_norm import company_stem

logger = logging.getLogger(__name__)

PRODUCTION_CODES = ("events_v007:2000", "events_v007:2100")
MASLAKA_BOOK_FORMAT = "maslaka_production"
MERGED_SOURCE = "מאוחד"

_HE_MONTHS = ["ינואר", "פברואר", "מרץ", "אפריל", "מאי", "יוני", "יולי", "אוגוסט",
              "ספטמבר", "אוקטובר", "נובמבר", "דצמבר"]

# The מסלקה's account status → the production file's vocabulary.
_STATUS = {"פעיל": "פעיל", "מוקפא": "לא פעיל"}

# Columns a September holding refreshes on the base row, when it carries a value.
_VALUE_FIELDS = (("accumulation", "accumulation"), ("total_premium", "total_premium"))


def _cid(v) -> str:
    return str(v or "").strip().lstrip("0")


def _pol(v) -> str:
    v = str(v or "").strip()
    if v.endswith(".0"):
        v = v[:-2]
    return v.lstrip("0") or v


def _month(d: date) -> date:
    return date(d.year, d.month, 1)


def product_family(product_type: str | None, product: str | None) -> str:
    """The product family a row belongs to, in the agent's words: פנסיה ·
    גמל והשתלמות · ביטוח. A מסלקה answer arrives per body and family (Phoenix's
    September held its gemel/השתלמות, not its pension or insurance)."""
    from app.services.comparison_service import is_pension_record
    if is_pension_record(product, product_type):
        return "פנסיה"
    text = f"{product_type or ''} {product or ''}"
    if "גמל" in text or "השתלמות" in text:
        return "גמל והשתלמות"
    return "ביטוח"


def row_month(rec_processing_date: str | None, upload_period: date | None) -> str | None:
    """'YYYY-MM' a production row is FOR: its own as-of date, else its file's month."""
    s = (rec_processing_date or "").strip()
    if len(s) >= 7 and s[4] == "-" and s[:4].isdigit() and s[5:7].isdigit():
        return s[:7]
    return upload_period.strftime("%Y-%m") if upload_period else None


def book_filename(month: date) -> str:
    return f"פרודוקציה מסלקה {_HE_MONTHS[month.month - 1]} {str(month.year)[2:]}.xlsx"


async def _base_book(db: AsyncSession, user_id: uuid.UUID) -> FileUpload | None:
    """The newest real production book: the newest production upload that was not
    built from the מסלקה. Picked by upload time, active or not, because a
    rebuild deactivates it."""
    current = (await db.execute(
        select(FileUpload).where(
            FileUpload.user_id == user_id,
            FileUpload.is_production == True,  # noqa: E712
        ).order_by(FileUpload.uploaded_at.desc())
    )).scalars().all()
    for u in current:
        if u.format_type != MASLAKA_BOOK_FORMAT:
            return u
    # The active book is a מסלקה book: its base is the newest real one before it.
    return (await db.execute(
        select(FileUpload).where(
            FileUpload.user_id == user_id,
            FileUpload.file_category == "production",
            FileUpload.format_type != MASLAKA_BOOK_FORMAT,
            FileUpload.record_count > 0,
        ).order_by(FileUpload.uploaded_at.desc()).limit(1)
    )).scalars().first()


async def _latest_holdings(db: AsyncSession, user_id: uuid.UUID) -> tuple[date | None, list[PensionHolding]]:
    """The newest production month's holdings, exact duplicates removed (a 2000
    and a 2100 can report the same product)."""
    rows = (await db.execute(
        select(PensionHolding)
        .join(PensionInquiry, PensionInquiry.id == PensionHolding.inquiry_id)
        .where(PensionHolding.user_id == user_id,
               PensionInquiry.interface_code.in_(PRODUCTION_CODES),
               PensionHolding.status_date.is_not(None))
    )).scalars().all()
    if not rows:
        return None, []
    newest = max(_month(h.status_date) for h in rows)
    seen, out = set(), []
    for h in rows:
        if _month(h.status_date) != newest:
            continue
        key = (_cid(h.customer_id_number), _pol(h.fund_policy_number), company_stem(h.receiving_company),
               h.product, h.account_status, str(h.accumulation), str(h.total_premium))
        if key in seen:
            continue
        seen.add(key)
        out.append(h)
    return newest, out


def _copy(rec: ClientRecord) -> dict:
    return {c.key: getattr(rec, c.key) for c in ClientRecord.__table__.columns
            if c.key not in ("id", "upload_id", "created_at")}


def _apply_holding(d: dict, h: PensionHolding) -> dict:
    for src, dst in _VALUE_FIELDS:
        v = getattr(h, src)
        if v is not None:
            d[dst] = v
            if dst == "accumulation":
                d["accumulation_source"] = "maslaka"
    if h.account_status:
        d["product_status"] = _STATUS.get(h.account_status, h.account_status)
    if h.track and not d.get("product"):
        d["product"] = h.track
    d["processing_date"] = h.status_date.isoformat()
    return d


async def _names_for(db: AsyncSession, user_id: uuid.UUID, holdings: list[PensionHolding],
                     known: dict[str, ClientRecord]) -> dict[str, tuple[str | None, str | None]]:
    """Names for customers the base book doesn't have (kiko 2026-10-10: two new
    September customers showed as bare IDs). First any other file of the agent
    (נפרעים, older production), then the מסלקה's own answer — it carries
    SHEM-PRATI / SHEM-MISHPACHA — decrypted where the key lives (the Gateway)."""
    want = {_cid(h.customer_id_number) for h in holdings} - set(known) - {""}
    out: dict[str, tuple] = {}
    if not want:
        return out
    for cid, first, last in (await db.execute(
        select(ClientRecord.id_number, ClientRecord.first_name, ClientRecord.last_name).where(
            ClientRecord.user_id == user_id,
            func.ltrim(ClientRecord.id_number, "0").in_(want),
            (ClientRecord.first_name.is_not(None)) | (ClientRecord.last_name.is_not(None)))
    )).all():
        out.setdefault(_cid(cid), (first, last))
    missing = want - set(out)
    if not missing:
        return out
    from app.utils.crypto import is_key_configured
    if not is_key_configured("MASLAKA_ENCRYPTION_KEY"):
        return out
    from xml.etree import ElementTree as ET
    from sqlalchemy import text
    from app.utils.crypto import decrypt_bytes
    payload_ids = {h.raw_payload_id for h in holdings
                   if h.raw_payload_id and _cid(h.customer_id_number) in missing}
    for pid in payload_ids:
        try:
            row = (await db.execute(text("select ciphertext from pension_raw_payloads where id = :i"),
                                    {"i": pid})).first()
            if not row or not row[0]:
                continue
            ct = row[0] if isinstance(row[0], (bytes, bytearray)) else row[0].encode()
            root = ET.fromstring(decrypt_bytes(bytes(ct), key_env="MASLAKA_ENCRYPTION_KEY"))
            for el in root.iter():
                kids = {c.tag: (c.text or "").strip() for c in el}
                if not (kids.get("SHEM-PRATI") or kids.get("SHEM-MISHPACHA")):
                    continue
                for k, v in kids.items():
                    if ("ZIHUY" in k or "MEZAHE" in k) and _cid(v) in missing:
                        out.setdefault(_cid(v), (kids.get("SHEM-PRATI"), kids.get("SHEM-MISHPACHA")))
        except Exception:
            logger.warning("production_book: could not read names from payload %s", pid, exc_info=True)
    return out


def _new_row(h: PensionHolding, names: dict[str, ClientRecord], user_id: uuid.UUID,
             extra: dict[str, tuple] | None = None) -> dict:
    """A product the base book didn't have — built from the holding, with the
    customer's name/contact taken from any other row of theirs."""
    who = names.get(_cid(h.customer_id_number))
    first, last = (getattr(who, "first_name", None), getattr(who, "last_name", None)) if who else \
        (extra or {}).get(_cid(h.customer_id_number), (None, None))
    d = {
        "user_id": user_id,
        "id_number": _cid(h.customer_id_number),
        "first_name": first,
        "last_name": last,
        "client_phone": getattr(who, "client_phone", None),
        "client_email": getattr(who, "client_email", None),
        "receiving_company": h.receiving_company,
        "product": h.product or h.track,
        "product_type": h.product_type,
        "fund_policy_number": h.fund_policy_number,
        "reconciliation_status": "no_data",
    }
    return _apply_holding(d, h)


async def build_book_rows(db: AsyncSession, user_id: uuid.UUID) -> dict | None:
    """Compute the new book without writing. None when there is nothing newer
    than the base book."""
    month, holdings = await _latest_holdings(db, user_id)
    if month is None:
        return None
    base = await _base_book(db, user_id)
    base_month = base.period_month and _month(base.period_month) if base else None
    if base_month and base_month >= month:
        return None  # the agent's own book is already this month or newer

    # No book of their own yet (an agent whose production only ever came from
    # the מסלקה): the book is the holdings alone.
    base_rows = (await db.execute(
        select(ClientRecord).where(ClientRecord.upload_id == base.id)
    )).scalars().all() if base else []

    by_key: dict[tuple, list[ClientRecord]] = defaultdict(list)
    names: dict[str, ClientRecord] = {}
    for r in base_rows:
        by_key[(_cid(r.id_number), _pol(r.fund_policy_number), company_stem(r.receiving_company))].append(r)
        if r.first_name or r.last_name:
            names.setdefault(_cid(r.id_number), r)

    h_by_key: dict[tuple, list[PensionHolding]] = defaultdict(list)
    for h in holdings:
        h_by_key[(_cid(h.customer_id_number), _pol(h.fund_policy_number),
                  company_stem(h.receiving_company))].append(h)

    extra_names = await _names_for(db, user_id, holdings, names)
    rows: list[dict] = []
    replaced: set[uuid.UUID] = set()
    added = 0
    for key, hs in h_by_key.items():
        cands = list(by_key.get(key, []))
        left = list(hs)
        # Two accounts can share a policy on both sides — closest balance pairs.
        while cands and left:
            h, r = min(((h, r) for h in left for r in cands),
                       key=lambda hr: abs(float(hr[0].accumulation or 0) - float(hr[1].accumulation or 0)))
            rows.append(_apply_holding(_copy(r), h))
            replaced.add(r.id)
            left.remove(h)
            cands.remove(r)
        for h in left:
            rows.append(_new_row(h, names, user_id, extra_names))
            added += 1

    base_iso = base_month.isoformat() if base_month else None
    carried = 0
    for r in base_rows:
        if r.id in replaced:
            continue
        d = _copy(r)
        if row_month(d.get("processing_date"), None) is None and base_iso:
            d["processing_date"] = base_iso
        rows.append(d)
        carried += 1

    per_company: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    for d in rows:
        per_company[company_stem(d.get("receiving_company")) or "—"][
            row_month(d.get("processing_date"), base_month) or "—"] += 1

    return {
        "month": month, "base": base, "rows": rows,
        "replaced": len(replaced), "added": added, "carried": carried,
        "per_company": {k: dict(v) for k, v in per_company.items()},
    }


async def rebuild_production_book(db: AsyncSession, user_id: uuid.UUID, *, commit: bool = True) -> dict | None:
    """Write the newest מסלקה month as the agent's active production book.

    Idempotent: a previous מסלקה book is replaced. Does NOT recompute the
    comparison — that only happens when נפרעים of the same month arrive, so the
    July "לא שולם" stays July vs July until the 21st."""
    from app.utils.sanitize import sanitize_record

    plan = await build_book_rows(db, user_id)
    if plan is None:
        return None
    month: date = plan["month"]

    # Drop earlier מסלקה books (this rebuild supersedes them).
    old = (await db.execute(
        select(FileUpload).where(FileUpload.user_id == user_id,
                                 FileUpload.format_type == MASLAKA_BOOK_FORMAT)
    )).scalars().all()
    for u in old:
        from sqlalchemy import delete
        await db.execute(delete(ClientRecord).where(ClientRecord.upload_id == u.id))
        await db.delete(u)
    await db.flush()

    up = FileUpload(
        user_id=user_id, filename=book_filename(month), file_type="xlsx",
        company_source=MERGED_SOURCE, record_count=len(plan["rows"]),
        format_type=MASLAKA_BOOK_FORMAT, is_production=True,
        file_category="production", period_month=month,
        uploaded_at=datetime.utcnow(),
    )
    db.add(up)
    await db.flush()
    for d in plan["rows"]:
        d = sanitize_record(dict(d))
        d["user_id"] = user_id
        db.add(ClientRecord(upload_id=up.id, **d))
    # One active book: the base (and any other production) steps aside.
    await db.execute(
        update(FileUpload)
        .where(FileUpload.user_id == user_id, FileUpload.is_production == True,  # noqa: E712
               FileUpload.id != up.id)
        .values(is_production=False)
    )
    await db.flush()
    # Read before commit: a session that expires on commit would lazy-load them.
    up_id = str(up.id)
    base_id = str(plan["base"].id) if plan["base"] else None
    if commit:
        await db.commit()
    logger.info("maslaka.production_book: user %s month %s — %d rows (%d replaced, %d new, %d carried)",
                user_id, month, len(plan["rows"]), plan["replaced"], plan["added"], plan["carried"])
    return {k: v for k, v in plan.items() if k not in ("rows", "base")} | {
        "upload_id": up_id, "base_upload_id": base_id, "rows": len(plan["rows"])}


async def book_months(db: AsyncSession, user_id: uuid.UUID) -> dict | None:
    """Per company, how many rows of the ACTIVE מסלקה book are of which month.

    `{"month": "2026-09", "companies": {"הפניקס": {"2026-09": 590, "2026-07": 117}, …}}`,
    or None when the active book is not a מסלקה book (rows carry no own month)."""
    book = (await db.execute(
        select(FileUpload).where(FileUpload.user_id == user_id,
                                 FileUpload.is_production == True,  # noqa: E712
                                 FileUpload.format_type == MASLAKA_BOOK_FORMAT)
        .order_by(FileUpload.uploaded_at.desc()).limit(1)
    )).scalars().first()
    if book is None:
        return None
    rows = (await db.execute(
        select(ClientRecord.receiving_company, ClientRecord.processing_date,
               ClientRecord.product_type, ClientRecord.product)
        .where(ClientRecord.upload_id == book.id)
    )).all()
    out: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    fam: dict[str, dict[str, dict[str, int]]] = defaultdict(lambda: defaultdict(lambda: defaultdict(int)))
    for rc, pd_, ptype, product in rows:
        stem, m = company_stem(rc) or "—", row_month(pd_, book.period_month) or "—"
        out[stem][m] += 1
        fam[stem][product_family(ptype, product)][m] += 1
    # When the מסלקה's answer for the book's month landed (not when the book
    # was rebuilt): the newest holding of that month.
    arrived = None
    if book.period_month:
        nxt = date(book.period_month.year + (book.period_month.month == 12),
                   book.period_month.month % 12 + 1, 1)
        arrived = (await db.execute(
            select(func.max(PensionHolding.created_at)).where(
                PensionHolding.user_id == user_id,
                PensionHolding.status_date >= book.period_month,
                PensionHolding.status_date < nxt)
        )).scalar()
    return {"month": book.period_month.strftime("%Y-%m") if book.period_month else None,
            "arrived_at": arrived.isoformat() + "Z" if arrived else None,
            "companies": {k: dict(v) for k, v in out.items()},
            # Per company, per family — "הפניקס: גמל והשתלמות ספטמבר, פנסיה
            # וביטוח עדיין יולי" instead of a bare "(חלקי)".
            "families": {k: {f: dict(m) for f, m in v.items()} for k, v in fam.items()}}


def newer_than(months: dict | None, nifraim_ym: str | None) -> dict | None:
    """The companies whose production is newer than the judged נפרעים month —
    "production arrived, no נפרעים for it yet"."""
    if not months or not nifraim_ym:
        return None
    newer = {}
    for co, by in months["companies"].items():
        n = sum(v for m, v in by.items() if m != "—" and m > nifraim_ym)
        if n:
            newer[co] = n
    if not newer:
        return None
    return {"month": max(m for by in months["companies"].values() for m in by if m != "—"),
            "arrived_at": months.get("arrived_at"),
            "companies": [{"company": k, "rows": v} for k, v in sorted(newer.items(), key=lambda kv: -kv[1])]}
