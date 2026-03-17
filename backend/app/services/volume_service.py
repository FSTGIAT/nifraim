from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.record import ClientRecord
from app.models.recruit import Recruit
from app.models.upload import FileUpload
from app.models.volume_commission_rate import VolumeCommissionRate


async def compare_volume(db: AsyncSession, user_id, volume_data: dict) -> dict:
    """Compare volume report clients against production records and recruits."""
    volume_clients = volume_data.get("clients", [])

    # Build volume lookup by id_number
    volume_by_id = {}
    for c in volume_clients:
        idn = c.get("id_number")
        if not idn:
            continue
        idn = idn.lstrip('0') or '0'
        if idn not in volume_by_id:
            volume_by_id[idn] = {
                "id_number": idn,
                "name": c.get("full_name") or f"{c.get('first_name', '')} {c.get('last_name', '')}".strip(),
                "products": [],
                "total_deposit": 0.0,
                "total_production_after_cancel": 0.0,
            }
        volume_by_id[idn]["products"].append(c)
        volume_by_id[idn]["total_deposit"] += c.get("deposit_amount") or 0
        volume_by_id[idn]["total_production_after_cancel"] += c.get("production_after_cancel") or 0

    # Fetch production records
    prod_upload = await db.execute(
        select(FileUpload).where(
            FileUpload.user_id == user_id,
            FileUpload.is_production == True,
        )
    )
    prod_file = prod_upload.scalar_one_or_none()

    production_by_id = {}
    if prod_file:
        result = await db.execute(
            select(ClientRecord).where(
                ClientRecord.upload_id == prod_file.id,
                ClientRecord.user_id == user_id,
            )
        )
        for r in result.scalars().all():
            if not r.id_number:
                continue
            if r.id_number not in production_by_id:
                production_by_id[r.id_number] = {
                    "id_number": r.id_number,
                    "name": f"{r.first_name or ''} {r.last_name or ''}".strip(),
                    "company": r.receiving_company or "",
                    "premium": 0.0,
                    "accumulation": 0.0,
                    "products_count": 0,
                }
            p = production_by_id[r.id_number]
            p["premium"] += float(r.total_premium or 0)
            p["accumulation"] += float(r.accumulation or 0)
            p["products_count"] += 1

    # Fetch recruits
    recruits_result = await db.execute(
        select(Recruit).where(Recruit.user_id == user_id)
    )
    recruits_by_id = {}
    for r in recruits_result.scalars().all():
        if r.id_number:
            recruits_by_id[r.id_number] = {
                "id_number": r.id_number,
                "name": f"{r.first_name or ''} {r.last_name or ''}".strip(),
                "company": r.company or "",
            }

    volume_ids = set(volume_by_id.keys())
    production_ids = set(production_by_id.keys())
    recruit_ids = set(recruits_by_id.keys())

    matched_ids = volume_ids & production_ids
    in_production_only = production_ids - volume_ids
    in_volume_only = volume_ids - production_ids
    in_recruits_not_volume = recruit_ids - volume_ids

    matched = []
    for idn in sorted(matched_ids):
        v = volume_by_id[idn]
        p = production_by_id[idn]
        matched.append({
            "id_number": idn,
            "name": p["name"] or v["name"],
            "company": p["company"],
            "premium": round(p["premium"], 2),
            "accumulation": round(p["accumulation"], 2),
            "products_count": p["products_count"],
            "volume_deposit": round(v["total_deposit"], 2),
            "volume_production_after_cancel": round(v["total_production_after_cancel"], 2),
            "volume_products": len(v["products"]),
        })

    prod_only = []
    for idn in sorted(in_production_only):
        p = production_by_id[idn]
        prod_only.append({
            "id_number": idn,
            "name": p["name"],
            "company": p["company"],
            "premium": round(p["premium"], 2),
            "accumulation": round(p["accumulation"], 2),
            "products_count": p["products_count"],
        })

    vol_only = []
    for idn in sorted(in_volume_only):
        v = volume_by_id[idn]
        vol_only.append({
            "id_number": idn,
            "name": v["name"],
            "volume_deposit": round(v["total_deposit"], 2),
            "volume_production_after_cancel": round(v["total_production_after_cancel"], 2),
            "volume_products": len(v["products"]),
        })

    recruits_not_vol = []
    for idn in sorted(in_recruits_not_volume):
        r = recruits_by_id[idn]
        recruits_not_vol.append({
            "id_number": idn,
            "name": r["name"],
            "company": r["company"],
        })

    summary = {
        "matched_count": len(matched),
        "in_production_only_count": len(prod_only),
        "in_volume_only_count": len(vol_only),
        "in_recruits_not_volume_count": len(recruits_not_vol),
        "total_volume_clients": len(volume_by_id),
        "total_production_clients": len(production_by_id),
        "total_volume_deposits": round(sum(v["total_deposit"] for v in volume_by_id.values()), 2),
        "total_volume_production_after_cancel": round(
            sum(v["total_production_after_cancel"] for v in volume_by_id.values()), 2
        ),
    }

    return {
        "summary": summary,
        "matched": matched,
        "in_production_only": prod_only,
        "in_volume_only": vol_only,
        "in_recruits_not_volume": recruits_not_vol,
    }


async def calculate_bonus(db: AsyncSession, user_id, volume_data: dict) -> dict:
    """Calculate volume commission bonus per company.

    Formula: bonus = (total_production_after_cancel / 1,000,000) × volume_rate_per_million

    Only includes companies from the volume report file.
    """
    volume_clients = volume_data.get("clients", [])

    # Group production_after_cancel by company from volume report
    # In real volume reports: פרוט מוצר (product_type) has company name, מוצר (product) has fund type
    # קופה (fund_type) is an account number — NOT a company name
    company_totals = {}  # company → {total_pac, client_ids}
    for c in volume_clients:
        company = c.get("product_type") or c.get("product") or "לא ידוע"
        pac = c.get("production_after_cancel") or 0
        idn = (c.get("id_number") or "").lstrip('0') or '0'
        if company not in company_totals:
            company_totals[company] = {"total_pac": 0.0, "client_ids": set()}
        company_totals[company]["total_pac"] += pac
        if idn:
            company_totals[company]["client_ids"].add(idn)

    # Fetch volume rates from DB
    result = await db.execute(
        select(VolumeCommissionRate).where(VolumeCommissionRate.user_id == user_id)
    )
    rates = result.scalars().all()
    rates_by_name = {}
    for r in rates:
        rates_by_name[r.company_name] = r

    # Also use agency_rates from the file itself as fallback (per-million rates)
    agency_rates = volume_data.get("agency_rates", {})

    def _find_rate(company_name):
        """Find matching rate: exact DB → substring DB → agency_rates from file → None."""
        # Exact match in DB
        if company_name in rates_by_name:
            r = rates_by_name[company_name]
            if r.volume_rate_per_million:
                return float(r.volume_rate_per_million), r.payment_frequency
        # Substring match in DB (full name contains or is contained)
        for rname, robj in rates_by_name.items():
            if rname in company_name or company_name in rname:
                if robj.volume_rate_per_million:
                    return float(robj.volume_rate_per_million), robj.payment_frequency
        # Fallback: use rate from the volume report file itself (agency rows)
        if company_name in agency_rates:
            return agency_rates[company_name], None
        # Try substring match on agency_rates too
        for aname, arate in agency_rates.items():
            if aname in company_name or company_name in aname:
                return arate, None
        return None, None

    companies = []
    grand_total = 0.0
    warnings = []

    for company, data in sorted(company_totals.items()):
        total_pac = data["total_pac"]
        client_count = len(data["client_ids"])

        rpm, frequency = _find_rate(company)

        if rpm:
            bonus = (total_pac / 1_000_000) * rpm
            grand_total += bonus
            companies.append({
                "company": company,
                "total_production_after_cancel": round(total_pac, 2),
                "rate_per_million": rpm,
                "calculated_bonus": round(bonus, 2),
                "payment_frequency": frequency,
                "client_count": client_count,
            })
        else:
            companies.append({
                "company": company,
                "total_production_after_cancel": round(total_pac, 2),
                "rate_per_million": None,
                "calculated_bonus": None,
                "payment_frequency": None,
                "client_count": client_count,
            })

    return {
        "companies": companies,
        "grand_total": round(grand_total, 2),
        "warnings": warnings,
    }
