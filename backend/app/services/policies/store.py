"""The one place policies are written and read — API, Nifra Agent tools and the data map all use
customer_picture(), so a number the agent quotes is the number the contacts card shows."""
from __future__ import annotations

import hashlib
import logging
from collections import OrderedDict
from datetime import datetime

from sqlalchemy import select

from app.models.harb_request import HarbRequest
from app.models.insurance_policy import InsurancePolicy
from app.models.policy_document import PolicyDocument
from app.services.policies.markdown import (
    group_policies, is_active, monthly, period_text, policy_detail_md, portfolio_md, short_company,
)

logger = logging.getLogger(__name__)


def norm_id(v) -> str:
    return "".join(c for c in str(v or "") if c.isdigit()).lstrip("0")


def sha(b: bytes | str) -> str:
    return hashlib.sha256(b if isinstance(b, bytes) else b.encode("utf-8")).hexdigest()


FIELDS = ("domain", "main_branch", "sub_branch", "product_type", "company", "period_start", "period_end",
          "renewing", "premium", "premium_type", "policy_number", "plan_class")


def _pkey(r: dict) -> tuple:
    """One POLICY: company + policy number (a coverage line without a number stands alone)."""
    return (short_company(r.get("company")), r.get("policy_number") or f"_{r.get('sub_branch')}")


def _ckey(r: dict) -> tuple:
    """One COVERAGE line inside a policy."""
    return _pkey(r) + (r.get("sub_branch") or "", r.get("product_type") or "")


def diff_snapshots(old: list[dict], new: list[dict]) -> dict:
    """What changed between two fetches of one customer: policies added/removed, premium and
    period changes per coverage. Pure — numbers are copied from the two files, never computed
    beyond the difference itself."""
    def pol(rows):
        out: dict = {}
        for r in rows:
            p = out.setdefault(_pkey(r), {"company": short_company(r.get("company")), "policy_number": r.get("policy_number"),
                                          "branch": r.get("main_branch"), "sub_branches": []})
            if r.get("sub_branch") and r["sub_branch"] not in p["sub_branches"]:
                p["sub_branches"].append(r["sub_branch"])
        return out
    po, pn = pol(old), pol(new)
    # A policy can list the SAME coverage twice (Harel 860786920: two "ייעוץ ובדיקות" lines at 1 and 19;
    # Menora 350760062: two "תרופות"). Match per coverage key as multisets: identical lines cancel
    # out first, only what's left is paired — else the 19 meets the 1 and reports a fake change.
    def sig(r):
        return (round(float(r["premium"]), 2) if r.get("premium") is not None else None, r.get("period_end"), bool(r.get("renewing")))
    from collections import defaultdict
    og, ng = defaultdict(list), defaultdict(list)
    for r in old:
        og[_ckey(r)].append(r)
    for r in new:
        ng[_ckey(r)].append(r)
    pairs = []
    for k, ns in ng.items():
        os_ = list(og.get(k, []))
        left = []
        for r in ns:
            hit = next((o for o in os_ if sig(o) == sig(r)), None)
            if hit is not None:
                os_.remove(hit)
            else:
                left.append(r)
        pairs += list(zip(sorted(os_, key=lambda x: (x.get("premium") or 0)), sorted(left, key=lambda x: (x.get("premium") or 0))))
    premium, period = [], []
    for o, r in pairs:
        a, b = o.get("premium"), r.get("premium")
        if a is not None and b is not None and abs(float(a) - float(b)) >= 0.5:
            premium.append({"company": short_company(r.get("company")), "policy_number": r.get("policy_number"),
                            "coverage": r.get("product_type"), "sub_branch": r.get("sub_branch"),
                            "old": float(a), "new": float(b), "premium_type": r.get("premium_type")})
        if (o.get("period_end"), bool(o.get("renewing"))) != (r.get("period_end"), bool(r.get("renewing"))):
            period.append({"company": short_company(r.get("company")), "policy_number": r.get("policy_number"),
                           "sub_branch": r.get("sub_branch"), "old": period_text(o), "new": period_text(r)})
    added = [v for k, v in pn.items() if k not in po]
    removed = [v for k, v in po.items() if k not in pn]
    parts = []
    if added:
        parts.append(f"{len(added)} פוליסות חדשות")
    if removed:
        parts.append(f"{len(removed)} פוליסות שלא מופיעות יותר")
    if premium:
        parts.append(f"{len(premium)} שינויי פרמיה")
    if period:
        parts.append(f"{len(period)} שינויי תקופה")
    return {"new_policies": added, "removed_policies": removed, "premium_changes": premium[:40],
            "period_changes": period[:40], "summary_he": " · ".join(parts) or "אין שינויים מאז השליפה הקודמת"}


def changes_md(ch: dict, prev_at) -> str:
    when = prev_at.strftime("%d/%m/%Y") if prev_at else "הקודמת"
    out = [f"## שינויים מאז השליפה הקודמת ({when})", f"- {ch['summary_he']}"]
    for p in ch["new_policies"][:15]:
        out.append(f"- חדשה: {p['branch'] or ''} — {' + '.join(p['sub_branches'])} · {p['company']}"
                   + (f" · פוליסה {p['policy_number']}" if p.get("policy_number") else ""))
    for p in ch["removed_policies"][:15]:
        out.append(f"- לא מופיעה יותר: {p['branch'] or ''} — {' + '.join(p['sub_branches'])} · {p['company']}"
                   + (f" · פוליסה {p['policy_number']}" if p.get("policy_number") else ""))
    for c in ch["premium_changes"][:15]:
        out.append(f"- פרמיה: {c['company']} {c.get('policy_number') or ''} · {c.get('coverage') or ''} {c.get('sub_branch') or ''}"
                   f" · ₪{c['old']:,.2f} → ₪{c['new']:,.2f} {c.get('premium_type') or ''}".rstrip())
    for c in ch["period_changes"][:15]:
        out.append(f"- תקופה: {c['company']} {c.get('policy_number') or ''} · {c.get('sub_branch') or ''} · {c['old']} → {c['new']}")
    return "\n".join(out) + "\n"


async def replace_harb_snapshot(db, req: HarbRequest, parsed: dict, details: list[dict] | None = None) -> int:
    """Make this fetch the customer's CURRENT הר הביטוח picture. The previous fetch is kept but
    superseded (is_current=False) — the history behind "what changed" — and the differences are
    stored on the request and written into the portfolio Markdown (so the AI can answer them).
    Uploaded PDFs are never touched. The caller commits."""
    from sqlalchemy import text, update
    uid, idn = req.user_id, req.customer_id_number
    old_rows = (await db.execute(select(InsurancePolicy).where(
        InsurancePolicy.user_id == uid, InsurancePolicy.customer_id_number == idn,
        InsurancePolicy.source == "harb", InsurancePolicy.is_current.is_(True)))).scalars().all()
    prev_req = (await db.execute(select(HarbRequest).where(
        HarbRequest.user_id == uid, HarbRequest.customer_id_number == idn, HarbRequest.status == "done",
        HarbRequest.id != req.id).order_by(HarbRequest.completed_at.desc().nullslast()).limit(1))).scalar_one_or_none()
    old = [{f: getattr(r, f) for f in FIELDS} for r in old_rows]
    rows = parsed.get("rows") or []
    req.changes = diff_snapshots(old, rows) if old else None

    await db.execute(update(InsurancePolicy).where(
        InsurancePolicy.user_id == uid, InsurancePolicy.customer_id_number == idn,
        InsurancePolicy.source == "harb", InsurancePolicy.is_current.is_(True)).values(is_current=False))
    superseded = (await db.execute(select(PolicyDocument.id).where(
        PolicyDocument.user_id == uid, PolicyDocument.customer_id_number == idn,
        PolicyDocument.source.in_(("harb_portfolio", "harb_policy")), PolicyDocument.is_current.is_(True)))).scalars().all()
    if superseded:
        await db.execute(update(PolicyDocument).where(PolicyDocument.id.in_(superseded)).values(is_current=False))
        # their passages leave search (the documents stay readable as history)
        if (await db.execute(text("SELECT to_regclass('public.doc_chunks') IS NOT NULL"))).scalar():
            await db.execute(text("DELETE FROM doc_chunks WHERE document_id = ANY(:ids)"), {"ids": list(superseded)})

    for r in rows:
        db.add(InsurancePolicy(user_id=uid, customer_id_number=idn, harb_request_id=req.id, source="harb",
                               produced_at=parsed.get("produced_at"), is_current=True, **r))
    md = portfolio_md(idn, req.customer_name, rows, parsed.get("produced_at"), parsed.get("notes"))
    if req.changes:
        prev_at = getattr(prev_req, "completed_at", None) or (old_rows[0].created_at if old_rows else None)
        md = md.replace("\n## ", "\n" + changes_md(req.changes, prev_at) + "\n## ", 1) if "\n## " in md else md + changes_md(req.changes, prev_at)
    stamp = datetime.utcnow().isoformat()
    db.add(PolicyDocument(user_id=uid, customer_id_number=idn, customer_name=req.customer_name, source="harb_portfolio",
                          title=f"תיק ביטוחי מהר הביטוח — {req.customer_name or idn}", markdown=md,
                          sha256=sha(f"harb|{idn}|{stamp}|{md}"), harb_request_id=req.id, status="ready", is_current=True))
    for i, d in enumerate(details or []):
        dtext = (d.get("text") or "").strip()
        if not dtext:
            continue
        title = d.get("title") or f"פוליסה {d.get('policy_number') or i + 1}"
        dmd = policy_detail_md(idn, req.customer_name, title, dtext, d.get("company"), d.get("policy_number"))
        db.add(PolicyDocument(user_id=uid, customer_id_number=idn, source="harb_policy", title=title[:300],
                              company=(d.get("company") or None), policy_number=(d.get("policy_number") or None),
                              markdown=dmd, sha256=sha(f"harbp|{idn}|{stamp}|{i}|{dmd}"),
                              harb_request_id=req.id, status="ready", is_current=True))
    return len(rows)


async def customer_picture(db, user_id, id_number: str) -> dict:
    """Everything known about a customer's policies: הר הביטוח coverages grouped per policy,
    totals, and every policy document (הר הביטוח + uploaded PDFs)."""
    idn = norm_id(id_number)
    rows = (await db.execute(select(InsurancePolicy).where(
        InsurancePolicy.user_id == user_id, InsurancePolicy.customer_id_number == idn, InsurancePolicy.is_current.is_(True))
        .order_by(InsurancePolicy.created_at))).scalars().all()
    all_docs = (await db.execute(select(PolicyDocument).where(
        PolicyDocument.user_id == user_id, PolicyDocument.customer_id_number == idn)
        .order_by(PolicyDocument.created_at.desc()))).scalars().all()
    reqs = (await db.execute(select(HarbRequest).where(
        HarbRequest.user_id == user_id, HarbRequest.customer_id_number == idn)
        .order_by(HarbRequest.created_at.desc()).limit(50))).scalars().all()
    return build_picture(idn, rows, [d for d in all_docs if d.is_current], reqs[0] if reqs else None,
                         history=_history(reqs, all_docs), changes=_done_changes(reqs))


def _history(reqs, docs) -> list[dict]:
    """Every finished fetch of the customer, newest first, with its portfolio document (readable
    even after it was superseded) and what it changed."""
    port = {d.harb_request_id: d for d in docs if d.source == "harb_portfolio"}
    out = []
    for q in reqs:
        if q.status != "done":
            continue
        d = port.get(q.id)
        out.append({"request_id": str(q.id), "fetched_at": q.completed_at or q.created_at, "coverages": q.policies_count,
                    "changes": (q.changes or {}).get("summary_he") if q.changes else None,
                    "document_id": str(d.id) if d else None, "current": bool(d and d.is_current)})
    return out


async def all_pictures(db, user_id, limit: int = 400) -> dict[str, dict]:
    """{id_number: picture} for every customer with policies — three queries, for the data map."""
    rows = (await db.execute(select(InsurancePolicy).where(InsurancePolicy.user_id == user_id, InsurancePolicy.is_current.is_(True))
                             .order_by(InsurancePolicy.created_at).limit(20000))).scalars().all()
    all_docs = (await db.execute(select(PolicyDocument).where(PolicyDocument.user_id == user_id,
                                                              PolicyDocument.customer_id_number.isnot(None))
                                 .order_by(PolicyDocument.created_at.desc()).limit(5000))).scalars().all()
    docs = [d for d in all_docs if d.is_current]
    reqs = (await db.execute(select(HarbRequest).where(HarbRequest.user_id == user_id)
                             .order_by(HarbRequest.created_at.desc()).limit(2000))).scalars().all()
    by_rows, by_docs, by_all_docs, by_reqs = {}, {}, {}, {}
    for r in rows:
        by_rows.setdefault(r.customer_id_number, []).append(r)
    for d in docs:
        by_docs.setdefault(d.customer_id_number, []).append(d)
    for d in all_docs:
        by_all_docs.setdefault(d.customer_id_number, []).append(d)
    for q in reqs:
        by_reqs.setdefault(q.customer_id_number, []).append(q)
    ids = list(dict.fromkeys([*by_docs, *by_rows]))[:limit]
    return {i: build_picture(i, by_rows.get(i, []), by_docs.get(i, []), (by_reqs.get(i) or [None])[0],
                             history=_history(by_reqs.get(i, []), by_all_docs.get(i, [])),
                             changes=_done_changes(by_reqs.get(i, []))) for i in ids}


def _span(items: list[dict]) -> str:
    """A policy's period across all its coverages: earliest start – latest end, or מתחדש."""
    if any(x.get("renewing") for x in items):
        return "מתחדש"
    starts = [x["period_start"] for x in items if x.get("period_start")]
    ends = [x["period_end"] for x in items if x.get("period_end")]
    return period_text({"period_start": min(starts) if starts else None, "period_end": max(ends) if ends else None})


def _done_changes(reqs) -> dict | None:
    """What the most recent FINISHED fetch changed (a newer one may still be in flight)."""
    q = next((q for q in reqs if q.status == "done"), None)
    return q.changes if q else None


def build_picture(idn: str, rows, docs, last, history: list | None = None, changes: dict | None = None) -> dict:
    dicts = [{c: getattr(r, c) for c in ("domain", "main_branch", "sub_branch", "product_type", "company",
                                         "period_start", "period_end", "renewing", "premium", "premium_type",
                                         "policy_number", "plan_class")} for r in rows]
    for d in dicts:
        d["premium"] = float(d["premium"]) if d["premium"] is not None else None
    policies = []
    for (dom, company, pno), items in group_policies(dicts).items():
        act = [x for x in items if is_active(x)]
        m = sum(v for v in (monthly(x) for x in act) if v)
        policies.append({
            "domain": dom, "company": company, "company_short": short_company(company),
            "policy_number": None if str(pno).startswith("_") else pno,
            "branch": items[0]["main_branch"],
            "sub_branches": list(OrderedDict.fromkeys(x["sub_branch"] for x in items if x["sub_branch"])),
            "period": _span(items), "active": bool(act), "plan_class": items[0]["plan_class"],
            "monthly_premium": round(m, 2) if m else None,
            "coverages": [{"product": x["product_type"], "sub_branch": x["sub_branch"], "period": period_text(x),
                           "premium": x["premium"], "premium_type": x["premium_type"]} for x in items],
        })
    active_m = sum(p["monthly_premium"] or 0 for p in policies if p["active"])
    return {
        "id_number": idn,
        "customer_name": getattr(last, "customer_name", None) or next((d.customer_name for d in docs if d.customer_name), None),
        "fetched_at": rows[0].created_at if rows else None,
        "produced_at": rows[0].produced_at if rows else None,
        "policies": policies,
        "totals": {"policies": len(policies), "coverages": len(rows),
                   "active_policies": sum(1 for p in policies if p["active"]),
                   "companies": sorted({p["company_short"] for p in policies if p["company_short"]}),
                   "monthly_premium_active": round(active_m, 2) if active_m else None},
        "documents": [{"id": str(d.id), "source": d.source, "title": d.title, "company": d.company,
                       "policy_number": d.policy_number, "status": d.status, "error": d.error,
                       "filename": d.filename, "created_at": d.created_at} for d in docs],
        "last_request": ({"id": str(last.id), "status": last.status, "error": last.error,
                          "created_at": last.created_at, "completed_at": last.completed_at} if last else None),
        # what the latest fetch changed vs the one before it (None = first fetch / no re-fetch yet)
        "changes": changes,
        "history": history or [],
    }


async def customers_with_policies(db, user_id) -> list[dict]:
    """[{id_number, name, policies, documents}] — for the data map's index line / search."""
    from sqlalchemy import func
    pol = dict((await db.execute(select(InsurancePolicy.customer_id_number, func.count(func.distinct(
        func.coalesce(InsurancePolicy.policy_number, InsurancePolicy.sub_branch))))
        .where(InsurancePolicy.user_id == user_id, InsurancePolicy.is_current.is_(True))
        .group_by(InsurancePolicy.customer_id_number))).all())
    docs = dict((await db.execute(select(PolicyDocument.customer_id_number, func.count())
                                  .where(PolicyDocument.user_id == user_id, PolicyDocument.customer_id_number.isnot(None))
                                  .group_by(PolicyDocument.customer_id_number))).all())
    names = dict((await db.execute(select(HarbRequest.customer_id_number, func.max(HarbRequest.customer_name))
                                   .where(HarbRequest.user_id == user_id).group_by(HarbRequest.customer_id_number))).all())
    return [{"id_number": i, "name": names.get(i), "policies": pol.get(i, 0), "documents": docs.get(i, 0)}
            for i in sorted(set(pol) | set(docs))]
