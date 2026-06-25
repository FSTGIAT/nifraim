"""Template-filter OTP e2e test (emulator).

Proves the company-SMS-template filter end-to-end on the Android emulator, and
that the OTP is actually sent + consumed by the real runner. Mirrors
`test_full_otp_automation.py` but exercises the data-driven `OtpFilter`:

  ALLOW    — a Migdal-shaped OTP matches a company ALLOW template -> forwarded ->
             the run reaches `success` (this is the "see you send the OTP" check).
  FAIL-OPEN — a code-bearing SMS matching NO template is still forwarded.
  BLOCK    — a personal code SMS matching a BLOCK template is dropped on device
             (never reaches otp_inbox).

Chain (ALLOW case):
    run_automation -> login -> awaiting_otp -> [emulator SMS -> SmsReceiver ->
    OtpFilter(allow) -> WorkManager -> HTTPS POST -> phone_forward webhook ->
    otp_inbox] -> _wait_for_otp consumes -> submit_otp -> download -> success

Prereqs (identical to test_full_otp_automation.py — see
.claude/skills/android-sms-test/skill.md):
  - backend up on :8000
  - cloudflared https tunnel up; the emulator app's webhook_url points to it
  - emulator container `nifraim-emu` booted, the REBUILT APK installed + launched
    (so it has fetched these templates), RECEIVE_SMS granted

Run:
  source /home/roygi/test/backend/venv/bin/activate
  python3 /home/roygi/test/backend/tests/test_template_filter_otp.py
"""

import asyncio
import subprocess
import sys
import uuid
from datetime import datetime

sys.path.insert(0, "/home/roygi/test/backend")

import openpyxl
from sqlalchemy import delete, select

from app.database import async_session
from app.models.user import User
from app.models.portal_credential import PortalCredential
from app.models.portal_run import PortalRun
from app.models.otp_inbox import OtpInbox
from app.models.sms_otp_template import SmsOtpTemplate
from app.services.portal_automation.base import BasePortalAutomation
from app.services.portal_automation.companies import REGISTRY
from app.services.portal_automation import runner
from app.utils.crypto import encrypt

TEST_USER_EMAIL = "test@test.com"
EMU_CONTAINER = "nifraim-emu"

OTP_CODE = "246810"               # the code the ALLOW case must consume
FAILOPEN_CODE = "553311"          # unique, matches no template
BLOCK_CODE = "778899"             # personal, matches the BLOCK template

SMS_FROM = "+972521234567"
SMS_ALLOW = f"מגדל קוד אימות {OTP_CODE}"
SMS_FAILOPEN = f"Reservation {FAILOPEN_CODE} confirmed - thank you"
SMS_BLOCK = f"בנק לאומי קוד כניסה {BLOCK_CODE}"


class TestProductionPortal(BasePortalAutomation):
    """No-network portal used only to drive the runner's OTP + ingest path."""

    portal_kind = "test_production"
    company_label = "בדיקה"
    requires_otp = True
    received_otp: str | None = None

    async def login(self, page, username, password):
        await page.goto("about:blank")

    async def submit_otp(self, page, otp):
        TestProductionPortal.received_otp = otp

    async def download_reports(self, page, download_dir, *, username=None):
        download_dir.mkdir(parents=True, exist_ok=True)
        path = download_dir / "בדיקה פרודוקציה מרץ 26.xlsx"
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.append([
            "מספר ת.ז", "שם פרטי לקוח", "שם משפחה לקוח", "יצרן", "סוג מוצר",
            "מס' חשבון/פוליסה", 'סה"כ פרמיה', "צבירה", "סטטוס מוצר", "תאריך הצטרפות",
        ])
        ws.append(["123456782", "ישראל", "ישראלי", "מגדל", "גמל", "POL-001", 1200, 50000, "פעיל", "2024-01-15"])
        wb.save(path)
        return [path]


def _send_emulator_sms(body: str):
    subprocess.run(
        ["docker", "exec", EMU_CONTAINER, "adb", "emu", "sms", "send", SMS_FROM, body],
        check=True,
    )


def _relaunch_app_to_refresh_templates():
    """Launch MainActivity so the app re-fetches the templates we just set."""
    subprocess.run(
        ["docker", "exec", EMU_CONTAINER, "adb", "shell", "am", "start",
         "-n", "com.nifraim.smsforwarder/.MainActivity"],
        check=True,
    )


async def _setup_templates(db):
    """Wipe + install a known template set: Migdal ALLOW + bank BLOCK."""
    await db.execute(delete(SmsOtpTemplate))
    db.add(SmsOtpTemplate(company_name="מגדל", portal_kind="migdal",
                          pattern=r"מגדל.*\d{4,8}", is_block=False, active=True))
    db.add(SmsOtpTemplate(company_name="בנק", pattern=r"בנק.*\d{4,8}",
                          is_block=True, active=True))
    await db.commit()


async def _count_inbox_with(db, user_id, marker: str, since: datetime) -> int:
    res = await db.execute(
        select(OtpInbox).where(
            OtpInbox.user_id == user_id,
            OtpInbox.received_at >= since,
            OtpInbox.body.contains(marker),
        )
    )
    return len(res.scalars().all())


async def _wait_for_inbox(db, user_id, marker, since, timeout=15) -> bool:
    for _ in range(timeout):
        await asyncio.sleep(1)
        async with async_session() as d2:
            if await _count_inbox_with(d2, user_id, marker, since):
                return True
    return False


async def _get_user_id(db):
    res = await db.execute(select(User).where(User.email == TEST_USER_EMAIL))
    return res.scalar_one().id


async def _ensure_credential(db, user_id):
    res = await db.execute(
        select(PortalCredential).where(
            PortalCredential.user_id == user_id,
            PortalCredential.portal_kind == "test_production",
        )
    )
    cred = res.scalar_one_or_none()
    if cred is None:
        cred = PortalCredential(
            user_id=user_id, portal_kind="test_production", username="test",
            encrypted_password=encrypt("x"), otp_method="phone_forward",
            is_active=True, schedule_kind="manual",
        )
        db.add(cred)
        await db.commit()
        await db.refresh(cred)
    return cred


async def case_allow(user_id, cred) -> bool:
    """ALLOW: Migdal SMS -> forwarded -> run completes to success."""
    print("\n--- CASE ALLOW (full run) ---")
    async with async_session() as db:
        run = PortalRun(user_id=user_id, credential_id=cred.id, kind="download",
                        status="pending", started_at=datetime.utcnow())
        db.add(run)
        await db.commit()
        await db.refresh(run)
        run_id = run.id

    task = asyncio.create_task(runner.run_automation(run_id))
    sms_sent = False
    last = None
    for _ in range(120):
        await asyncio.sleep(1)
        async with async_session() as db:
            r = (await db.execute(select(PortalRun).where(PortalRun.id == run_id))).scalar_one()
            status = r.status
        if status != last:
            print(f"[allow] status -> {status}")
            last = status
        if status == "awaiting_otp" and not sms_sent:
            print(f"[allow] injecting Migdal OTP {OTP_CODE}")
            _send_emulator_sms(SMS_ALLOW)
            sms_sent = True
        if status in ("success", "failed", "timeout"):
            break
    await task

    async with async_session() as db:
        r = (await db.execute(select(PortalRun).where(PortalRun.id == run_id))).scalar_one()
    ok = (r.status == "success" and r.upload_id is not None
          and TestProductionPortal.received_otp == OTP_CODE)
    print(f"[allow] status={r.status} upload_id={r.upload_id} consumed={TestProductionPortal.received_otp} -> {'PASS' if ok else 'FAIL'}")
    return ok


async def case_failopen(user_id) -> bool:
    print("\n--- CASE FAIL-OPEN (no template match, has code) ---")
    since = datetime.utcnow()
    _send_emulator_sms(SMS_FAILOPEN)
    forwarded = await _wait_for_inbox(None, user_id, FAILOPEN_CODE, since)
    ok = forwarded  # must be forwarded
    print(f"[failopen] forwarded={forwarded} -> {'PASS' if ok else 'FAIL'}")
    return ok


async def case_block(user_id) -> bool:
    print("\n--- CASE BLOCK (personal code SMS, matches block template) ---")
    since = datetime.utcnow()
    _send_emulator_sms(SMS_BLOCK)
    forwarded = await _wait_for_inbox(None, user_id, BLOCK_CODE, since, timeout=12)
    ok = not forwarded  # must be dropped
    print(f"[block] forwarded={forwarded} (expected False) -> {'PASS' if ok else 'FAIL'}")
    return ok


async def main():
    REGISTRY["test_production"] = TestProductionPortal

    async with async_session() as db:
        user_id = await _get_user_id(db)
        cred = await _ensure_credential(db, user_id)
        await _setup_templates(db)

    print("[setup] templates installed (Migdal allow + bank block).")
    print("[setup] relaunching emulator app to refresh templates...")
    _relaunch_app_to_refresh_templates()
    await asyncio.sleep(8)  # let the expedited TemplateFetchWorker run

    results = {
        "ALLOW": await case_allow(user_id, cred),
        "FAIL-OPEN": await case_failopen(user_id),
        "BLOCK": await case_block(user_id),
    }

    print("\n=== RESULTS ===")
    for k, v in results.items():
        print(f"  {k:10s}: {'PASS ✅' if v else 'FAIL ❌'}")
    ok = all(results.values())
    print("\nTEMPLATE-FILTER E2E:", "PASS ✅" if ok else "FAIL ❌")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    asyncio.run(main())
