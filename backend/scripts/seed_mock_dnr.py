"""Seed massive realistic mock data for the DNR agency demo.

Creates N synthetic Hebrew-named agents under the DNR agency, each with a
clone-with-variation of test@test.com's production records (so the agency
super-user dashboard fills with real-looking aggregated data) AND with a
*realistic* reconciliation distribution so that the "missing commission"
KPIs aren't all zero.

Usage:
    cd /home/roygi/test/backend
    /home/roygi/test/backend/venv/bin/python -m scripts.seed_mock_dnr --agents 30
"""
import argparse
import asyncio
import random
import sys
import uuid
from datetime import datetime, timedelta, date
from decimal import Decimal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import select, delete
from app.database import async_session
from app.models.user import User
from app.models.agency import Agency
from app.models.upload import FileUpload
from app.models.record import ClientRecord
from app.models.production_summary import ProductionSummary
from app.models.volume_bonus_payment import VolumeBonusPayment
from app.services.auth_service import hash_password


HEBREW_AGENTS = [
    ("אבי כהן", "avi.cohen"),
    ("שרה לוי", "sara.levi"),
    ("יוסי פרץ", "yossi.peretz"),
    ("רחל גולן", "rachel.golan"),
    ("דניאל שמש", "daniel.shemesh"),
    ("מירב אזולאי", "merav.azoulay"),
    ("איציק ברק", "itzik.barak"),
    ("נועה דוד", "noa.david"),
    ("רון אהרוני", "ron.aharoni"),
    ("טל מור", "tal.mor"),
    ("מיכל רביב", "michal.raviv"),
    ("עמית בן-דוד", "amit.bendavid"),
    ("ליאת סבן", "liat.saban"),
    ("גיא חדד", "guy.haddad"),
    ("עינת ביטון", "einat.biton"),
    ("יואב אדרי", "yoav.adri"),
    ("שירה לוין", "shira.levin"),
    ("בעז עמר", "boaz.amar"),
    ("הילה דהן", "hila.dahan"),
    ("עידן אברהם", "idan.abraham"),
    ("רותם פרץ", "rotem.peretz"),
    ("אסף נחום", "asaf.nachum"),
    ("דנה שלום", "dana.shalom"),
    ("ניר חזן", "nir.hazan"),
    ("מאיה בר", "maya.bar"),
    ("עופר דרור", "ofer.dror"),
    ("ענת מזרחי", "anat.mizrachi"),
    ("גלעד יעקב", "gilad.yaakov"),
    ("טליה עוזרי", "talia.uzeri"),
    ("שמעון פיש", "shimon.fish"),
    ("יעל לב", "yael.lev"),
    ("אלון פלד", "alon.peled"),
    ("אביגיל ויס", "avigail.weiss"),
    ("ערן שגב", "eran.segev"),
    ("הדס כהן-לוי", "hadas.cohenlevi"),
]

PAYING_COMPANIES = [
    "מגדל חברה לביטוח בע\"מ",
    "הפניקס חברה לביטוח בע\"מ",
    "כלל חברה לביטוח בע\"מ",
    "מנורה מבטחים פנסיה וגמל בע\"מ",
    "הראל חברה לביטוח בע\"מ",
    "מור גמל ופנסיה בע\"מ",
    "הכשרה חברה לביטוח בע\"מ",
    "אלטשולר שחם גמל ופנסיה בע\"מ",
    "מיטב גמל ופנסיה בע\"מ",
    "איילון חברה לביטוח בע\"מ",
]

# Realistic reconciliation distribution — produces real "missing money" data.
RECON_WEIGHTS = [
    ("paid_match",     0.30),
    ("paid_mismatch",  0.25),  # actual < expected → counts toward lost money
    ("unpaid",         0.22),  # 0 actual → fully lost
    ("no_data",        0.15),
    ("cancelled",      0.08),
]


def pick_recon():
    r = random.random()
    cum = 0
    for status, w in RECON_WEIGHTS:
        cum += w
        if r <= cum:
            return status
    return "no_data"


async def reset_existing(db, dnr_id: uuid.UUID):
    """Wipe previous mock agents (any user under DNR whose email starts with mock_)."""
    rows = (await db.execute(
        select(User.id).where(
            User.agency_id == dnr_id,
            User.email.like("mock_%"),
        )
    )).all()
    ids = [r[0] for r in rows]
    if not ids:
        return 0
    # Cascade delete: records → uploads → summaries → bonuses → user
    await db.execute(delete(ClientRecord).where(ClientRecord.user_id.in_(ids)))
    await db.execute(delete(ProductionSummary).where(ProductionSummary.user_id.in_(ids)))
    await db.execute(delete(VolumeBonusPayment).where(VolumeBonusPayment.user_id.in_(ids)))
    await db.execute(delete(FileUpload).where(FileUpload.user_id.in_(ids)))
    await db.execute(delete(User).where(User.id.in_(ids)))
    await db.commit()
    return len(ids)


async def seed_one_agent(db, agency_id: uuid.UUID, name: str, slug: str, idx: int, source_records: list):
    """Create a synthetic agent + clone-with-variation a sample of source_records."""
    email = f"mock_{slug}@dnr.demo"
    user = User(
        email=email,
        full_name=name,
        hashed_password=hash_password("test123"),
        is_active=True,
        role="agent",
        agency_id=agency_id,
        company_name="ד.נ.ר",
    )
    db.add(user)
    await db.flush()

    # Per-agent bias: some agents are big producers, some small.
    size_factor = random.choices([0.4, 1.0, 1.8, 3.0], weights=[3, 5, 2, 1])[0]
    target_count = max(40, int(120 * size_factor))

    sample_n = min(target_count, len(source_records))
    sample = random.sample(source_records, sample_n)

    # One production upload per agent
    upload = FileUpload(
        user_id=user.id,
        filename=f"production_{slug}.xlsx",
        file_type="xlsx",
        company_source="agent",
        record_count=sample_n,
        format_type="production",
        is_production=True,
        file_category="production",
        uploaded_at=datetime.utcnow() - timedelta(days=random.randint(1, 60)),
    )
    db.add(upload)
    await db.flush()

    # Clone records with variation
    new_recs = []
    total_premium = Decimal("0")
    total_accum = Decimal("0")
    for r in sample:
        # Vary amounts ±30%
        prem_mult = Decimal(str(round(random.uniform(0.7, 1.3), 3)))
        accum_mult = Decimal(str(round(random.uniform(0.7, 1.3), 3)))
        recon = pick_recon()
        company = random.choice(PAYING_COMPANIES)

        # Compute expected/actual amounts based on reconciliation status
        base_expected = (r["total_premium"] or Decimal("0")) * Decimal("0.05")  # 5% commission
        base_expected = (base_expected * prem_mult).quantize(Decimal("0.01"))
        if recon == "paid_match":
            actual = base_expected
        elif recon == "paid_mismatch":
            actual = (base_expected * Decimal(str(round(random.uniform(0.45, 0.85), 2)))).quantize(Decimal("0.01"))
        elif recon == "unpaid":
            actual = Decimal("0")
        else:
            actual = None

        new_premium = ((r["total_premium"] or Decimal("0")) * prem_mult).quantize(Decimal("0.01"))
        new_accum = ((r["accumulation"] or Decimal("0")) * accum_mult).quantize(Decimal("0.01"))

        rec = ClientRecord(
            user_id=user.id,
            upload_id=upload.id,
            id_number=r["id_number"],
            first_name=r["first_name"],
            last_name=r["last_name"],
            product=r["product"],
            fund_policy_number=r["fund_policy_number"],
            receiving_company=company,
            product_type=r["product_type"],
            total_premium=new_premium,
            accumulation=new_accum,
            expected_amount=base_expected,
            actual_amount=actual,
            reconciliation_status=recon,
        )
        new_recs.append(rec)
        total_premium += new_premium
        total_accum += new_accum

    db.add_all(new_recs)

    # Production summaries for trend (3 months back)
    base_date = datetime(2026, 1, 15)
    months = ["2025-11", "2025-12", "2026-01"]
    monthly_factors = [0.85, 0.95, 1.0]  # gentle growth
    for i, period in enumerate(months):
        if random.random() > 0.35:  # not every agent uploads every month
            ps = ProductionSummary(
                user_id=user.id,
                upload_id=upload.id if i == 2 else uuid.uuid4(),  # fake upload_id for older months
                period_label=period,
                upload_date=base_date - timedelta(days=(2 - i) * 30 + random.randint(-5, 5)),
                total_records=sample_n,
                unique_clients=int(sample_n * 0.6),
                total_premium=total_premium * Decimal(str(monthly_factors[i])),
                total_accumulation=total_accum * Decimal(str(monthly_factors[i])),
                companies_json=[],
                product_types_json=[],
                top_clients_json=[],
            )
            # Older months can re-use the same upload_id only for the latest;
            # for older months we need a real FileUpload row to satisfy the FK.
            if i < 2:
                old_upload = FileUpload(
                    user_id=user.id,
                    filename=f"production_{slug}_{period}.xlsx",
                    file_type="xlsx",
                    company_source="agent",
                    record_count=sample_n,
                    format_type="production",
                    is_production=False,
                    file_category="production",
                    uploaded_at=ps.upload_date,
                )
                db.add(old_upload)
                await db.flush()
                ps.upload_id = old_upload.id
            db.add(ps)

    # Volume bonuses — half of agents have unpaid bonuses
    if random.random() > 0.5:
        for company in random.sample(PAYING_COMPANIES, k=random.randint(1, 3)):
            db.add(VolumeBonusPayment(
                user_id=user.id,
                company_name=company,
                year=2026,
                is_paid=random.random() > 0.6,
                paid_date=date(2026, random.randint(1, 4), random.randint(1, 28)) if random.random() > 0.5 else None,
            ))

    return user.id, sample_n


async def main(n_agents: int):
    random.seed(42)  # deterministic — same demo every time
    async with async_session() as db:
        agency = (await db.execute(select(Agency).where(Agency.slug == "dnr"))).scalar_one()
        print(f"agency: {agency.name} ({agency.id})")

        wiped = await reset_existing(db, agency.id)
        print(f"wiped {wiped} previous mock agents")

        # Read all of test@test.com's records once into memory (small enough)
        test = (await db.execute(select(User).where(User.email == "test@test.com"))).scalar_one()
        rec_rows = (await db.execute(
            select(
                ClientRecord.id_number,
                ClientRecord.first_name,
                ClientRecord.last_name,
                ClientRecord.product,
                ClientRecord.fund_policy_number,
                ClientRecord.product_type,
                ClientRecord.total_premium,
                ClientRecord.accumulation,
            ).where(ClientRecord.user_id == test.id, ClientRecord.id_number.isnot(None))
        )).all()
        source = [
            {
                "id_number": r[0],
                "first_name": r[1],
                "last_name": r[2],
                "product": r[3],
                "fund_policy_number": r[4],
                "product_type": r[5],
                "total_premium": r[6],
                "accumulation": r[7],
            }
            for r in rec_rows
        ]
        print(f"source records pool: {len(source)}")

        if not source:
            print("ERROR: test@test.com has no records — nothing to clone")
            sys.exit(2)

        agents = HEBREW_AGENTS[:n_agents]
        if len(agents) < n_agents:
            # pad by re-using names with suffix
            for i in range(len(agents), n_agents):
                base = HEBREW_AGENTS[i % len(HEBREW_AGENTS)]
                agents.append((f"{base[0]} #{i+1}", f"{base[1]}.{i+1}"))

        for idx, (name, slug) in enumerate(agents):
            uid, count = await seed_one_agent(db, agency.id, name, slug, idx, source)
            print(f"  [{idx+1:>2}/{n_agents}] {name:<20} → {count:>4} records")
            if idx % 5 == 4:
                await db.commit()

        await db.commit()
        print(f"\n✓ Seeded {n_agents} mock agents under DNR. Login as chashav@dnr.co.il / test123 to view.")


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--agents", type=int, default=30, help="Number of synthetic agents to create")
    args = p.parse_args()
    asyncio.run(main(args.agents))
