"""Admin operations dashboard — one row per agent across everything that runs
on its own: the monthly cycle (did this month's download run on their
worker?), the worker itself, Nifraim Mail Agent, the מסלקה (pension
clearinghouse) link and its downloads, and the agreement requests.

Grouped queries only (one per area), so it stays cheap with many agents.
Read-only; admin-gated by the router (api/admin.py).
"""
from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.agreement_request import AgreementRequest
from app.models.mail_item import MailItem
from app.models.mail_watch_sender import MailWatchSender
from app.models.mailbox_config import MailboxConfig
from app.models.maslaka_agent_link import MaslakaAgentLink
from app.models.pension_holding import PensionHolding
from app.models.pension_inquiry import PensionInquiry
from app.models.portal_credential import PortalCredential
from app.models.portal_run_batch import PortalRunBatch
from app.models.user import User
from app.models.worker_heartbeat import WorkerHeartbeat
from app.services import cycle_service as cs

WORKER_LIVE_WINDOW_S = 90


def _iso(d):
    return d.isoformat() if d else None


async def operations_overview(db: AsyncSession) -> dict:
    now_aware = datetime.now(timezone.utc)
    now = now_aware.replace(tzinfo=None)
    ly, lm = cs.latest_cycle(now_aware)
    current_period = cs.cycle_period(ly, lm)
    prelaunch = (ly, lm) < cs.launch_cycle()
    ny, nm = cs.next_cycle(now_aware)
    since_30 = now - timedelta(days=30)

    users = (await db.execute(select(User).order_by(User.created_at.desc()))).scalars().all()

    hb = {h.user_id: h for h in (await db.execute(select(WorkerHeartbeat))).scalars().all()}
    creds = dict((await db.execute(
        select(PortalCredential.user_id, func.count(PortalCredential.id))
        .where(PortalCredential.is_active.is_(True)).group_by(PortalCredential.user_id)
    )).all())

    # this cycle's batch per user + the most recent batch of any kind
    cyc = {b.user_id: b for b in (await db.execute(
        select(PortalRunBatch).where(PortalRunBatch.trigger == "cycle", PortalRunBatch.cycle_period == current_period)
    )).scalars().all()}
    last_batch = {b.user_id: b for b in (await db.execute(
        select(PortalRunBatch)
        .distinct(PortalRunBatch.user_id)
        .order_by(PortalRunBatch.user_id, PortalRunBatch.started_at.desc())
    )).scalars().all()}

    mb = {m.user_id: m for m in (await db.execute(select(MailboxConfig))).scalars().all()}
    watched = dict((await db.execute(
        select(MailWatchSender.user_id, func.count(MailWatchSender.id)).group_by(MailWatchSender.user_id)
    )).all())
    mail_30 = defaultdict(lambda: {"received": 0, "sent": 0})
    for uid, st, n in (await db.execute(
        select(MailItem.user_id, MailItem.status, func.count(MailItem.id))
        .where(MailItem.received_at >= since_30).group_by(MailItem.user_id, MailItem.status)
    )).all():
        mail_30[uid]["received"] += n
        if st == "SENT":
            mail_30[uid]["sent"] += n

    links = {l.user_id: l for l in (await db.execute(select(MaslakaAgentLink))).scalars().all()}
    inq = defaultdict(dict)
    for uid, st, n in (await db.execute(
        select(PensionInquiry.user_id, PensionInquiry.status, func.count(PensionInquiry.id))
        .group_by(PensionInquiry.user_id, PensionInquiry.status)
    )).all():
        inq[uid][st] = n
    inq_last = dict((await db.execute(
        select(PensionInquiry.user_id, func.max(PensionInquiry.submitted_at)).group_by(PensionInquiry.user_id)
    )).all())
    holdings = {uid: (n, c, last) for uid, n, c, last in (await db.execute(
        select(PensionHolding.user_id, func.count(PensionHolding.id),
               func.count(func.distinct(PensionHolding.customer_id_number)), func.max(PensionHolding.created_at))
        .group_by(PensionHolding.user_id)
    )).all()}

    agr = defaultdict(dict)
    for uid, st, n in (await db.execute(
        select(AgreementRequest.user_id, AgreementRequest.status, func.count(AgreementRequest.id))
        .group_by(AgreementRequest.user_id, AgreementRequest.status)
    )).all():
        agr[uid][st] = n

    rows = []
    for u in users:
        h = hb.get(u.id)
        online = bool(h and (now - h.last_seen).total_seconds() <= WORKER_LIVE_WINDOW_S)
        first = cs.first_cycle_for(u.created_at or now)
        b = cyc.get(u.id)
        lb = last_batch.get(u.id)
        if (ly, lm) < first:
            cycle_state = "locked"          # new agent: before their first 21st
        elif prelaunch:
            cycle_state = "prelaunch"
        elif b is None:
            cycle_state = "not_queued" if creds.get(u.id) else "no_portals"
        elif b.status == "pending":
            cycle_state = "waiting_worker" if not online else "queued"
        else:
            cycle_state = b.status  # running | success | partial | failed
        m = mb.get(u.id)
        l = links.get(u.id)
        hd = holdings.get(u.id)
        rows.append({
            "id": str(u.id), "email": u.email, "full_name": u.full_name, "company_name": u.company_name,
            "is_active": u.is_active, "is_admin": u.is_admin, "created_at": _iso(u.created_at),
            "worker": {
                "online": online, "last_seen": _iso(h.last_seen) if h else None,
                "hostname": h.hostname if h else None, "current_job": h.current_job if h else None,
                "portals": creds.get(u.id, 0),
            },
            "cycle": {
                "state": cycle_state,
                "first_cycle": f"{first[0]}-{first[1]:02d}",
                "batch_status": b.status if b else None,
                "queued_at": _iso(b.started_at) if b else None,
                "finished_at": _iso(b.finished_at) if b else None,
                "succeeded": b.succeeded if b else None, "failed": b.failed if b else None,
                "last_batch_status": lb.status if lb else None,
                "last_batch_at": _iso(lb.started_at) if lb else None,
                "last_batch_trigger": getattr(lb, "trigger", None) if lb else None,
            },
            "mail_agent": {
                "connected": bool(m and m.is_active), "address": m.email_address if m else None,
                "host": m.mail_host if m else None,
                "can_send": bool(m and m.is_active and m.mail_host == "google" and m.encrypted_password),
                "last_status": m.last_status if m else None, "last_error": m.last_error if m else None,
                "last_polled_at": _iso(m.last_polled_at) if m else None,
                "watched_senders": watched.get(u.id, 0),
                "mails_30d": mail_30[u.id]["received"] if u.id in mail_30 else 0,
                "sent_30d": mail_30[u.id]["sent"] if u.id in mail_30 else 0,
            },
            "maslaka": {
                "association": l.status if l else "not_started",
                "submitted_at": _iso(l.submitted_at) if l else None,
                "approved_at": _iso(l.approved_at) if l else None,
                "auto_production": bool(l and l.auto_production),
                # first automatic מסלקה production (the 27th rule, cycle_service)
                "expected_first_production": _iso(cs.maslaka_first_auto(l.submitted_at or l.approved_at))
                    if l and l.status in ("submitted", "approved") else None,
                "inquiries": inq.get(u.id, {}),
                "last_inquiry_at": _iso(inq_last.get(u.id)),
                "holdings": hd[0] if hd else 0, "customers": hd[1] if hd else 0,
                "last_holding_at": _iso(hd[2]) if hd else None,
            },
            "agreements": agr.get(u.id, {}),
        })

    def count(pred):
        return sum(1 for r in rows if pred(r))

    return {
        "now": now_aware.isoformat(),
        "cycle": {
            "current_period": current_period.isoformat(),
            "current_period_label": cs.month_label(current_period),
            "prelaunch": prelaunch,
            "launch": "-".join(str(x).zfill(2) for x in cs.launch_cycle()),
            "next_cycle_at": cs.cycle_moment(ny, nm).isoformat(),
        },
        "summary": {
            "agents": len(rows),
            "workers_online": count(lambda r: r["worker"]["online"]),
            "cycle_success": count(lambda r: r["cycle"]["state"] in ("success", "partial")),
            "cycle_waiting": count(lambda r: r["cycle"]["state"] in ("waiting_worker", "queued", "running")),
            "cycle_failed": count(lambda r: r["cycle"]["state"] == "failed"),
            "mail_agent": count(lambda r: r["mail_agent"]["connected"]),
            "maslaka_approved": count(lambda r: r["maslaka"]["association"] == "approved"),
            "maslaka_customers": sum(r["maslaka"]["customers"] for r in rows),
        },
        "agents": rows,
    }
