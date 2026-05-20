"""Yield-track recommendation endpoints.

POST /api/yield-recommendations/generate     — recompute + persist
GET  /api/yield-recommendations              — list current recommendations
GET  /api/yield-recommendations/export.xlsx  — same data as a single-sheet xlsx
"""
from __future__ import annotations

import io
import logging

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_paid_user as get_current_user
from app.database import get_db
from app.models.user import User
from app.models.yield_recommendation import YieldRecommendation
from app.services.yield_recommender_service import generate_recommendations

logger = logging.getLogger(__name__)
router = APIRouter()


def _serialize(r: YieldRecommendation) -> dict:
    def _num(v):
        return float(v) if v is not None else None
    return {
        "id": str(r.id),
        "id_number": r.id_number,
        "client_name": r.client_name,
        "fund_policy_number": r.fund_policy_number,
        "product_type": r.product_type,
        "current_company": r.current_company,
        "current_track": r.current_track,
        "current_yield_1y": _num(r.current_yield_1y),
        "current_yield_3y": _num(r.current_yield_3y),
        "current_yield_5y": _num(r.current_yield_5y),
        "recommended_track_id": r.recommended_track_id,
        "recommended_track_name": r.recommended_track_name,
        "recommended_fund_name": r.recommended_fund_name,
        "recommended_yield_1y": _num(r.recommended_yield_1y),
        "recommended_yield_3y": _num(r.recommended_yield_3y),
        "recommended_yield_5y": _num(r.recommended_yield_5y),
        "accumulation": float(r.accumulation),
        "potential_annual_gain": float(r.potential_annual_gain),
        "reasoning": r.reasoning,
        "confidence": r.confidence,
        "risk_class": r.risk_class,
        "move_type": r.move_type,
        "generated_at": r.generated_at.isoformat() if r.generated_at else None,
    }


@router.post("/generate")
async def generate(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Recompute recommendations for the user's active production file."""
    try:
        count = await generate_recommendations(db, user.id)
    except Exception as e:
        logger.exception("yield_recommendations: generate failed")
        raise HTTPException(status_code=500, detail=f"כשל ביצירת המלצות: {e}")
    return {"count": count}


@router.get("")
async def list_recommendations(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Persisted recommendations, ranked by potential annual gain (desc)."""
    q = await db.execute(
        select(YieldRecommendation)
        .where(YieldRecommendation.user_id == user.id)
        .order_by(desc(YieldRecommendation.potential_annual_gain))
    )
    rows = list(q.scalars().all())
    total_gain = sum(float(r.potential_annual_gain) for r in rows)
    return {
        "count": len(rows),
        "total_potential_annual_gain": round(total_gain, 2),
        "generated_at": rows[0].generated_at.isoformat() if rows else None,
        "items": [_serialize(r) for r in rows],
    }


@router.get("/export.xlsx")
async def export_xlsx(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Single-sheet Excel export of the persisted recommendations.

    Mirrors the styling pattern from debts.py: orange header fill, white bold
    font, RTL sheet view, auto-widthed columns. Numbers formatted as ₪.
    """
    import openpyxl
    from openpyxl.styles import Alignment, Font, PatternFill

    q = await db.execute(
        select(YieldRecommendation)
        .where(YieldRecommendation.user_id == user.id)
        .order_by(desc(YieldRecommendation.potential_annual_gain))
    )
    rows = list(q.scalars().all())

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "המלצות ניוד"
    ws.sheet_view.rightToLeft = True

    headers = [
        "#", "לקוח", "ת.ז", "מוצר", "חברה נוכחית", "מסלול נוכחי",
        "תשואה 1Y נוכחי", "תשואה 3Y נוכחי", "תשואה 5Y נוכחי",
        "מסלול מומלץ", "קרן ספציפית",
        "תשואה 1Y מומלץ", "תשואה 3Y מומלץ", "תשואה 5Y מומלץ",
        "צבירה", "פוטנציאל שנתי", "סוג מהלך", "סיכון", "ביטחון", "נימוק",
    ]
    ws.append(headers)

    header_fill = PatternFill(start_color="F57C00", end_color="F57C00", fill_type="solid")
    header_font = Font(bold=True, color="FFFFFF", size=11)
    for cell in ws[1]:
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = Alignment(horizontal="right", vertical="center")

    confidence_he = {"high": "גבוה", "medium": "בינוני", "low": "נמוך"}
    move_he = {"same": "באותה רמת סיכון", "aggressive": "אגרסיבי יותר"}
    risk_he = {"stocks": "מניות", "general": "כללי"}

    for i, r in enumerate(rows, start=1):
        ws.append([
            i,
            r.client_name or "—",
            r.id_number or "—",
            r.product_type or "—",
            r.current_company or "—",
            r.current_track or "—",
            float(r.current_yield_1y) if r.current_yield_1y is not None else None,
            float(r.current_yield_3y) if r.current_yield_3y is not None else None,
            float(r.current_yield_5y) if r.current_yield_5y is not None else None,
            r.recommended_track_name,
            r.recommended_fund_name or "—",
            float(r.recommended_yield_1y) if r.recommended_yield_1y is not None else None,
            float(r.recommended_yield_3y) if r.recommended_yield_3y is not None else None,
            float(r.recommended_yield_5y) if r.recommended_yield_5y is not None else None,
            float(r.accumulation),
            float(r.potential_annual_gain),
            move_he.get(r.move_type, r.move_type),
            risk_he.get(r.risk_class, r.risk_class),
            confidence_he.get(r.confidence, r.confidence),
            r.reasoning or "",
        ])

    # Number formats — yields as percentage points, accumulation/gain as ₪
    pct_cols = ("G", "H", "I", "L", "M", "N")
    money_cols = ("O", "P")
    for col in pct_cols:
        for cell in ws[col][1:]:
            cell.number_format = '0.00"%"'
    for col in money_cols:
        for cell in ws[col][1:]:
            cell.number_format = '#,##0'

    for col in ws.columns:
        max_len = max(len(str(cell.value or "")) for cell in col)
        ws.column_dimensions[col[0].column_letter].width = min(max_len + 2, 36)

    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    return StreamingResponse(
        buf,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=yield_recommendations.xlsx"},
    )
