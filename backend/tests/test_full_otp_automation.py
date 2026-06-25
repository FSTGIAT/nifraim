"""Full-automation OTP test for ONE company's production flow.

Proves the *full* automation (no manual OTP entry): drives the REAL portal
runner with a synthetic `test_production` plugin, and injects the OTP through
the Android emulator (adb emu sms send -> app forwards -> webhook -> otp_inbox).
The runner's _wait_for_otp consumes it automatically and continues to download
+ parse a synthetic production file.

Contrast with the manual flow, where the run sits in `awaiting_otp` until a
human types the code into the modal.

Chain exercised:
    run_automation -> login -> awaiting_otp -> [emulator SMS -> SmsReceiver ->
    WorkManager -> HTTPS POST -> phone_forward webhook -> otp_inbox] ->
    _wait_for_otp consumes -> submit_otp -> download_reports (synthetic xlsx)
    -> ingest -> success

Prereqs (see .claude/skills/android-sms-test/skill.md):
  - backend up on :8000
  - cloudflared https tunnel up, and the emulator app's webhook_url points to it
  - emulator container `nifraim-emu` booted, app installed + launched (not in
    stopped state), RECEIVE_SMS granted

Run:
  source /home/roygi/test/backend/venv/bin/activate
  python3 /home/roygi/test/backend/tests/test_full_otp_automation.py
"""

import asyncio
import subprocess
import sys
import uuid
from datetime import datetime

sys.path.insert(0, "/home/roygi/test/backend")

import openpyxl
from sqlalchemy import select

from app.database import async_session
from app.models.user import User
from app.models.portal_credential import PortalCredential
from app.models.portal_run import PortalRun
from app.services.portal_automation.base import BasePortalAutomation
from app.services.portal_automation.companies import REGISTRY
from app.services.portal_automation import runner
from app.utils.crypto import encrypt

TEST_USER_EMAIL = "test@test.com"
EMU_CONTAINER = "nifraim-emu"
OTP_CODE = "246810"
SMS_FROM = "+972521234567"
SMS_BODY = f"Nifraim test production verification code {OTP_CODE}"


class TestProductionPortal(BasePortalAutomation):
    """A no-network portal used only for testing the runner's OTP + ingest path."""

    portal_kind = "test_production"
    company_label = "בדיקה"
    requires_otp = True
    received_otp: str | None = None

    async def login(self, page, username, password):
        await page.goto("about:blank")

    async def submit_otp(self, page, otp):
        # Record the OTP the runner fed us so the test can assert it was the
        # one injected via the emulator (not a stale / manual code).
        TestProductionPortal.received_otp = otp

    async def download_reports(self, page, download_dir, *, username=None):
        download_dir.mkdir(parents=True, exist_ok=True)
        path = download_dir / "בדיקה פרודוקציה מרץ 26.xlsx"
        wb = openpyxl.Workbook()
        ws = wb.active
        cols = [
            "מספר ת.ז", "שם פרטי לקוח", "שם משפחה לקוח", "יצרן", "סוג מוצר",
            "מס' חשבון/פוליסה", 'סה"כ פרמיה', "צבירה", "סטטוס מוצר", "תאריך הצטרפות",
        ]
        ws.append(cols)
        ws.append(["123456782", "ישראל", "ישראלי", "מגדל", "גמל", "POL-001", 1200, 50000, "פעיל", "2024-01-15"])
        ws.append(["987654321", "שרה", "כהן", "מגדל", "השתלמות", "POL-002", 800, 30000, "פעיל", "2023-06-01"])
        wb.save(path)
        return [path]


async def _get_test_user_id(db):
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
            user_id=user_id,
            portal_kind="test_production",
            username="test",
            encrypted_password=encrypt("x"),
            otp_method="phone_forward",
            is_active=True,
            schedule_kind="manual",
        )
        db.add(cred)
        await db.commit()
        await db.refresh(cred)
    return cred


def _send_emulator_sms():
    subprocess.run(
        ["docker", "exec", EMU_CONTAINER, "adb", "emu", "sms", "send", SMS_FROM, SMS_BODY],
        check=True,
    )


async def main():
    # Register the test plugin in THIS process's registry (run_automation runs
    # in-process as an asyncio task, so it sees this).
    REGISTRY["test_production"] = TestProductionPortal

    async with async_session() as db:
        user_id = await _get_test_user_id(db)
        cred = await _ensure_credential(db, user_id)
        run = PortalRun(
            user_id=user_id,
            credential_id=cred.id,
            kind="download",
            status="pending",
            started_at=datetime.utcnow(),
        )
        db.add(run)
        await db.commit()
        await db.refresh(run)
        run_id = run.id

    print(f"[test] PortalRun {run_id} created (status=pending)")
    print("[test] launching run_automation (real runner)...")
    task = asyncio.create_task(runner.run_automation(run_id))

    sms_sent = False
    last_status = None
    for _ in range(120):
        await asyncio.sleep(1)
        async with async_session() as db:
            r = (await db.execute(select(PortalRun).where(PortalRun.id == run_id))).scalar_one()
            status = r.status
        if status != last_status:
            print(f"[test] status -> {status}")
            last_status = status
        if status == "awaiting_otp" and not sms_sent:
            print(f"[test] >>> reached awaiting_otp; injecting OTP {OTP_CODE} via emulator SMS")
            _send_emulator_sms()
            sms_sent = True
        if status in ("success", "failed", "timeout"):
            break

    await task

    async with async_session() as db:
        r = (await db.execute(select(PortalRun).where(PortalRun.id == run_id))).scalar_one()
        print("\n=== RESULT ===")
        print("status:                ", r.status)
        print("stage:                 ", r.stage)
        print("downloaded_filename:   ", r.downloaded_filename)
        print("upload_id:             ", r.upload_id)
        print("error_message:         ", r.error_message)
        print("OTP consumed by runner:", TestProductionPortal.received_otp)

    ok = (
        r.status == "success"
        and r.upload_id is not None
        and TestProductionPortal.received_otp == OTP_CODE
        and not sms_sent_was_manual()
    )
    print("\nFULL-AUTOMATION E2E:", "PASS ✅" if ok else "FAIL ❌")
    sys.exit(0 if ok else 1)


def sms_sent_was_manual():
    # The OTP was injected by the emulator path (phone_forward), never typed by
    # a human. Always False here — present for self-documentation.
    return False


if __name__ == "__main__":
    asyncio.run(main())
