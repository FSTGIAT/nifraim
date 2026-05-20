"""Generate per-product yield-track recommendations from the active production
file against the latest mygemel.net data.

V2 (2026-05-19) — smarter classification:
  1. Risk class detection from product + track fields ("מניות"/"stocks" vs
     bonds/general). Default is "general" — only flip to "stocks" on strong
     evidence.
  2. Same-risk match by default — a קונסרבטיבי user is not blindly pushed
     into all-equity. Cross-risk recommendations are still emitted but
     tagged `move_type='aggressive'` so the UI can label them clearly.
  3. Pick a SPECIFIC top fund from fund_track_funds (rank=1 by 3Y within the
     recommended track) rather than recommending the track average — gives
     the agent a concrete destination to discuss with the customer.
"""
from __future__ import annotations

import logging
import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.fund_track import FundTrack
from app.models.fund_track_fund import FundTrackFund
from app.models.record import ClientRecord
from app.models.upload import FileUpload
from app.models.yield_recommendation import YieldRecommendation

logger = logging.getLogger(__name__)

MIN_ANNUAL_DIFF = 0.5  # pp/year (blended 3Y+5Y) — below this we don't recommend a move


# product_type/product keyword → fund_tracks.category.
# Order matters: "גמל להשקעה" must beat "גמל" alone.
_CATEGORY_KEYWORDS: list[tuple[str, str]] = [
    ("גמל להשקעה", "gemel_lehashkaa"),
    ("השקעה", "gemel_lehashkaa"),
    ("השתלמות", "keren_hishtalmut"),
    ("פוליס", "polisot_hisachon"),
    ("חיסכון פרט", "polisot_hisachon"),
    ("חיסכון", "polisot_hisachon"),
    ("גמל", "kupot_gemel"),
]

_CATEGORY_LABELS_HE: dict[str, str] = {
    "kupot_gemel": "קופת גמל",
    "keren_hishtalmut": "קרן השתלמות",
    "polisot_hisachon": "פוליסת חיסכון",
    "gemel_lehashkaa": "גמל להשקעה",
}

# Risk-class signals. Anything matching pushes the user to "stocks" risk —
# else we default to "general". Conservative on purpose: we'd rather under-
# recommend stocks moves than push a low-risk customer into all-equity.
_STOCKS_HINTS = ["מניות", "stocks", "אקסטרה", "פסיב", "מחקה מדד", "מחקה", "אסיא", "אקסל"]


def _classify_category(product_type: str | None, product_name: str | None) -> str | None:
    haystack = f"{product_type or ''} {product_name or ''}".lower()
    if not haystack.strip():
        return None
    for kw, cat in _CATEGORY_KEYWORDS:
        if kw.lower() in haystack:
            return cat
    return None


def _detect_risk(track: str | None, product_name: str | None, product_type: str | None) -> tuple[str, bool]:
    """Return (risk_class, explicit). risk_class ∈ {'stocks', 'general'}.
    `explicit` is True only when the `track` column clearly says so."""
    track_lc = (track or '').lower()
    if track_lc and any(h in track_lc for h in _STOCKS_HINTS):
        return ('stocks', True)
    needle = f"{product_name or ''} {product_type or ''}".lower()
    if any(h in needle for h in _STOCKS_HINTS):
        return ('stocks', False)
    return ('general', bool(track_lc))


def _pick_current_track(
    category: str,
    risk: str,
    tracks_by_cat: dict[str, list[FundTrack]],
) -> FundTrack | None:
    """Best representative track for the user's CURRENT position. We don't
    have a per-policy yield in production data, so we use the equivalent
    mygemel.net track as a yield baseline.

    - risk='stocks' → the category's stocks track
    - risk='general' → the category's klali (or under50 for kupot_gemel)
    """
    candidates = tracks_by_cat.get(category, [])
    if not candidates:
        return None
    if risk == 'stocks':
        for t in candidates:
            if t.maslul == 'stocks':
                return t
        return None
    # general
    for t in candidates:
        if t.maslul == 'klali':
            return t
    # kupot_gemel has no klali — use under50 as a representative baseline
    for t in candidates:
        if t.maslul == 'under50':
            return t
    # last resort
    non_stocks = [t for t in candidates if t.maslul != 'stocks']
    return non_stocks[0] if non_stocks else candidates[0]


def _pick_aggressive(
    category: str,
    tracks_by_cat: dict[str, list[FundTrack]],
) -> FundTrack | None:
    """The stocks track in the category — used for aggressive upgrade
    suggestions for general-risk users when the stocks gap is large."""
    for t in tracks_by_cat.get(category, []):
        if t.maslul == 'stocks':
            return t
    return None


def _annualized(y3, y5, y1=None) -> float | None:
    """Annualized return blending the 3Y and 5Y cumulative figures.

    mygemel.net publishes cumulative returns; dividing by the horizon gives a
    comparable per-year number. We average the 3Y and 5Y annualized values so a
    fund that merely spiked over the last 3 years doesn't outrank a steady
    long-term performer — the agent is making a multi-year placement, so the 5Y
    track record matters. Falls back to 3Y alone, then 1Y, then None."""
    parts = []
    if y3 is not None:
        parts.append(float(y3) / 3.0)
    if y5 is not None:
        parts.append(float(y5) / 5.0)
    if parts:
        return sum(parts) / len(parts)
    if y1 is not None:
        return float(y1)
    return None


def _fund_score(f: FundTrackFund) -> float:
    s = _annualized(f.y3_return, f.y5_return, f.y1_return)
    return s if s is not None else float('-inf')


def _top_fund(track_id: str, funds_by_track: dict[str, list[FundTrackFund]]) -> FundTrackFund | None:
    """Top individual fund in a track by blended 3Y+5Y annualized return."""
    funds = funds_by_track.get(track_id, [])
    if not funds:
        return None
    scored = [f for f in funds if _annualized(f.y3_return, f.y5_return, f.y1_return) is not None]
    if scored:
        scored.sort(key=lambda f: -_fund_score(f))
        return scored[0]
    return sorted(funds, key=lambda f: f.rank or 999)[0]


def _confidence(category_found: bool, risk_explicit: bool, move_is_same_risk: bool) -> str:
    """High when classification was unambiguous AND move stays in same risk
    class. Medium when one signal is soft. Low when crossing risk classes."""
    if category_found and risk_explicit and move_is_same_risk:
        return "high"
    if not move_is_same_risk:
        return "low"
    if category_found:
        return "medium"
    return "low"


async def generate_recommendations(db: AsyncSession, user_id: uuid.UUID) -> int:
    """Generate & persist recommendations for the user's active production file."""
    prod_q = await db.execute(
        select(FileUpload).where(
            FileUpload.user_id == user_id,
            FileUpload.is_production == True,  # noqa: E712
        )
    )
    prod_upload = prod_q.scalar_one_or_none()
    if not prod_upload:
        return 0

    tracks_q = await db.execute(select(FundTrack))
    tracks = list(tracks_q.scalars().all())
    if not tracks:
        return 0
    tracks_by_cat: dict[str, list[FundTrack]] = {}
    for t in tracks:
        tracks_by_cat.setdefault(t.category, []).append(t)

    funds_q = await db.execute(select(FundTrackFund))
    funds_by_track: dict[str, list[FundTrackFund]] = {}
    for f in funds_q.scalars().all():
        funds_by_track.setdefault(f.track_id, []).append(f)

    rec_q = await db.execute(
        select(
            ClientRecord.id_number,
            ClientRecord.first_name,
            ClientRecord.last_name,
            ClientRecord.fund_policy_number,
            ClientRecord.product_type,
            ClientRecord.product,
            ClientRecord.track,
            ClientRecord.receiving_company,
            ClientRecord.accumulation,
        ).where(
            ClientRecord.upload_id == prod_upload.id,
            ClientRecord.user_id == user_id,
        )
    )

    await db.execute(delete(YieldRecommendation).where(YieldRecommendation.user_id == user_id))

    now = datetime.utcnow()
    inserted = 0

    for (id_number, first_name, last_name, policy_number, product_type, product_name,
         track, company, accumulation) in rec_q.all():
        accum_val = float(accumulation or 0)
        if accum_val <= 0:
            continue
        category = _classify_category(product_type, product_name)
        if category is None:
            continue

        risk, risk_explicit = _detect_risk(track, product_name, product_type)
        current_track = _pick_current_track(category, risk, tracks_by_cat)
        if current_track is None:
            continue

        cur_annual = _annualized(current_track.y3_return, current_track.y5_return, current_track.y1_return)
        if cur_annual is None:
            continue

        client_name = " ".join(filter(None, [first_name, last_name])).strip() or None
        cat_label = _CATEGORY_LABELS_HE.get(category, "")

        def _add_rec(dest_track: FundTrack, dest_fund: FundTrackFund | None,
                     move_type: str, dest_risk: str) -> int:
            """Build & stage one recommendation. Returns 1 if added, 0 if it
            failed the gain threshold. Uses the blended 3Y+5Y annual return of
            the concrete destination fund (fallback: track average)."""
            rec_annual = None
            if dest_fund is not None:
                rec_annual = _annualized(dest_fund.y3_return, dest_fund.y5_return, dest_fund.y1_return)
            if rec_annual is None:
                rec_annual = _annualized(dest_track.y3_return, dest_track.y5_return, dest_track.y1_return)
            if rec_annual is None:
                return 0
            annual_diff = rec_annual - cur_annual
            if annual_diff < MIN_ANNUAL_DIFF:
                return 0
            potential_gain = round(accum_val * annual_diff / 100.0, 2)
            if potential_gain <= 0:
                return 0

            rec_fund_name = dest_fund.fund_name if dest_fund else None
            rec_y1 = dest_fund.y1_return if (dest_fund and dest_fund.y1_return is not None) else dest_track.y1_return
            rec_y3 = dest_fund.y3_return if (dest_fund and dest_fund.y3_return is not None) else dest_track.y3_return
            rec_y5 = dest_fund.y5_return if (dest_fund and dest_fund.y5_return is not None) else dest_track.y5_return

            move_phrase = (
                "החלפת קרן באותה רמת סיכון"
                if move_type == "same"
                else "מעבר למסלול אגרסיבי יותר (סיכון גבוה יותר)"
            )
            fund_phrase = f" — קרן מומלצת: {rec_fund_name}" if rec_fund_name else ""
            y5_phrase = f", 5ש {float(rec_y5):.1f}%" if rec_y5 is not None else ""
            reasoning = (
                f"{move_phrase}. {dest_track.label_he}{fund_phrase}. "
                f"תשואת יעד: 3ש {float(rec_y3):.1f}%{y5_phrase} "
                f"(≈ +{annual_diff:.1f}% בשנה ממוצעת על הצבירה ב-{cat_label}, משוקלל 3+5 שנים)."
            )

            db.add(YieldRecommendation(
                user_id=user_id,
                production_upload_id=prod_upload.id,
                id_number=id_number,
                client_name=client_name,
                fund_policy_number=policy_number,
                product_type=product_type,
                current_company=company,
                current_track=current_track.label_he,
                current_yield_1y=Decimal(str(current_track.y1_return)) if current_track.y1_return is not None else None,
                current_yield_3y=Decimal(str(current_track.y3_return)) if current_track.y3_return is not None else None,
                current_yield_5y=Decimal(str(current_track.y5_return)) if current_track.y5_return is not None else None,
                recommended_track_id=dest_track.id,
                recommended_track_name=dest_track.label_he,
                recommended_fund_name=rec_fund_name,
                recommended_yield_1y=Decimal(str(rec_y1)) if rec_y1 is not None else None,
                recommended_yield_3y=Decimal(str(rec_y3)) if rec_y3 is not None else None,
                recommended_yield_5y=Decimal(str(rec_y5)) if rec_y5 is not None else None,
                accumulation=Decimal(str(accum_val)),
                potential_annual_gain=Decimal(str(potential_gain)),
                reasoning=reasoning,
                confidence=_confidence(True, risk_explicit, move_type == "same"),
                risk_class=dest_risk,
                move_type=move_type,
                generated_at=now,
            ))
            return 1

        # Emit BOTH options so the agent can filter by move type and pick per
        # client's risk appetite — instead of the engine silently collapsing
        # everyone into one bucket (the "all aggressive / no same-risk" report).
        #
        # 1. Same-risk fund switch: stay in the current track/risk class but
        #    move to its best-performing fund. mygemel.net has only one general
        #    track per category, so this fund-level move is the ONLY way a
        #    same-risk recommendation can exist.
        same_top = _top_fund(current_track.id, funds_by_track)
        inserted += _add_rec(current_track, same_top, "same", risk)

        # 2. Aggressive upgrade (general → stocks). Only when not already stocks.
        if risk == 'general':
            agg_track = _pick_aggressive(category, tracks_by_cat)
            if agg_track and agg_track.id != current_track.id:
                agg_top = _top_fund(agg_track.id, funds_by_track)
                inserted += _add_rec(agg_track, agg_top, "aggressive", "stocks")

    await db.commit()
    return inserted
