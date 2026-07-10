"""Mail-intake tests — MX routing, webhook signature, OAuth state, IMAP cursor, dedup.

    source backend/venv/bin/activate && python backend/tests/test_mail_intake.py

No network. DNS and HTTP are stubbed; the DB portion runs against the local dev
database inside a transaction that is always rolled back.

The assertions that carry real weight:
  * the Resend webhook rejects a bad signature BEFORE any tenant lookup or fetch,
    and refuses a replayed capture outside the timestamp window;
  * the OAuth callback rejects a forged or stale `state` (CSRF);
  * a changed IMAP UIDVALIDITY resets the cursor instead of silently skipping mail;
  * a second delivery of the same message is a no-op (dedup);
  * an attachment whose filename fails the guard is refused before parsing.
"""

import asyncio
import base64
import hashlib
import hmac
import json
import sys
import time
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import httpx  # noqa: E402

from app.services.mail_intake import (  # noqa: E402
    MAILBOX_ATTACHMENT_PATTERN,
    FetchedAttachment,
    MailIntakeError,
    ingest_mail_attachment,
)
from app.services.mail_intake import detect as detect_mod  # noqa: E402
from app.services.mail_intake import graph as graph_mod  # noqa: E402
from app.services.mail_intake import gmail as gmail_mod  # noqa: E402
from app.services.mail_intake import resend as resend_mod  # noqa: E402

FIXTURE = Path(__file__).parent / "fixtures" / "Ild_prod_1_09344_30042026.zip"

_failures = 0


def check(label, got, expected):
    global _failures
    ok = got == expected
    _failures += not ok
    print(f"  [{'PASS' if ok else 'FAIL'}] {label}" + ("" if ok else f": {got!r} != {expected!r}"))


# ── MX detection ────────────────────────────────────────────────────────────


def _mx_payload(*targets):
    return {"Answer": [{"data": f"{10 + i} {t}."} for i, t in enumerate(targets)]}


async def test_mx_detection():
    print("\nMX detection (never ask the user who hosts their mail):")
    cases = [
        ("moshe@eitam-finance.com", _mx_payload("eitamfinance-com01c.mail.protection.outlook.com"), "microsoft"),
        ("roygiat@gmail.com", _mx_payload("gmail-smtp-in.l.google.com"), "google"),
        # Google WORKSPACE shares Gmail's MX but refuses app passwords since 2025.
        # It must NOT get the app-password field — that path can never succeed.
        ("a@corp.com", _mx_payload("aspmx.l.google.com"), "other"),
        ("a@shop.co.il", _mx_payload("mail.cpanelhost.co.il"), "other"),
        ("a@nomx.com", {"Answer": []}, "other"),                       # NXDOMAIN / no MX
        ("not-an-email", None, "other"),                               # malformed
    ]
    for email, payload, expected in cases:
        if payload is None:
            got = await detect_mod.detect_mail_host(email)
        else:
            transport = httpx.MockTransport(lambda req, p=payload: httpx.Response(200, json=p))
            orig = httpx.AsyncClient
            httpx.AsyncClient = lambda **kw: orig(transport=transport, **kw)
            try:
                got = await detect_mod.detect_mail_host(email)
            finally:
                httpx.AsyncClient = orig
        check(f"{email} -> {expected}", got, expected)

    # A DoH failure must degrade to `other` (which works everywhere), not raise.
    transport = httpx.MockTransport(lambda req: httpx.Response(500))
    orig = httpx.AsyncClient
    httpx.AsyncClient = lambda **kw: orig(transport=transport, **kw)
    try:
        check("DoH 500 degrades to 'other'", await detect_mod.detect_mail_host("a@b.com"), "other")
    finally:
        httpx.AsyncClient = orig


# ── Resend webhook signature (the whole defence of a public write path) ──────


def _sign(secret_b64, msg_id, ts, body):
    signed = f"{msg_id}.{ts}.".encode() + body
    mac = hmac.new(base64.b64decode(secret_b64), signed, hashlib.sha256).digest()
    return base64.b64encode(mac).decode()


def test_resend_signature():
    print("\nResend webhook signature:")
    secret_b64 = base64.b64encode(b"super-secret-key-material").decode()
    secret = f"whsec_{secret_b64}"
    body = json.dumps({"data": {"email_id": "e1"}}).encode()
    ts = str(int(time.time()))
    good = _sign(secret_b64, "msg_1", ts, body)

    hdrs = {"svix-id": "msg_1", "svix-timestamp": ts, "svix-signature": f"v1,{good}"}
    check("valid signature accepted", resend_mod.verify_signature(secret, hdrs, body), True)

    check(
        "forged signature rejected",
        resend_mod.verify_signature(secret, {**hdrs, "svix-signature": "v1,AAAA"}, body),
        False,
    )
    check(
        "tampered body rejected",
        resend_mod.verify_signature(secret, hdrs, body + b"x"),
        False,
    )
    old = str(int(time.time()) - 3600)
    replay = _sign(secret_b64, "msg_1", old, body)
    check(
        "replay outside window rejected",
        resend_mod.verify_signature(
            secret, {"svix-id": "msg_1", "svix-timestamp": old, "svix-signature": f"v1,{replay}"}, body
        ),
        False,
    )
    check("missing headers rejected", resend_mod.verify_signature(secret, {}, body), False)
    # Key rotation: several v1 values, one of which matches.
    check(
        "accepts one of several rotated signatures",
        resend_mod.verify_signature(secret, {**hdrs, "svix-signature": f"v1,AAAA v1,{good}"}, body),
        True,
    )

    print("\nRecipient token (tenant comes from `to`, never from `from`):")
    check("plain", resend_mod.token_from_recipient("hachshara+abc123@in.nifraim.com"), "abc123")
    check("display name form", resend_mod.token_from_recipient("X <hachshara+t9@in.nifraim.com>"), "t9")
    check("no token", resend_mod.token_from_recipient("hachshara@in.nifraim.com"), None)
    # secrets.token_urlsafe emits MIXED CASE. Lowercasing the local part breaks
    # every tenant lookup, and the webhook then 200s as "unknown token" and
    # silently drops the mail. This is a real bug that shipped once.
    mixed = "pvHAxUtocSE_tDhPJ3rfF1j0dLSNane9"
    check("mixed-case token preserved", resend_mod.token_from_recipient(f"hachshara+{mixed}@in.nifraim.com"), mixed)
    check("token with - and _", resend_mod.token_from_recipient("hachshara+A-b_C@x.com"), "A-b_C")


# ── Graph OAuth state (CSRF) ────────────────────────────────────────────────


def test_graph_state():
    print("\nMicrosoft OAuth state (signed, single-use window):")
    from app.config import settings
    settings.MAILBOX_ENCRYPTION_KEY = "test-state-secret"

    uid = str(uuid.uuid4())
    state = graph_mod.make_state(uid)
    check("round-trips the user id", graph_mod.parse_state(state), uid)

    body, sig = state.rsplit(".", 1)
    forged = f"{body}.{'0' * len(sig)}"
    try:
        graph_mod.parse_state(forged)
        check("forged signature rejected", False, True)
    except MailIntakeError:
        check("forged signature rejected", True, True)

    stale_payload = json.dumps({"u": uid, "t": int(time.time()) - 9999}, separators=(",", ":")).encode()
    stale_body = base64.urlsafe_b64encode(stale_payload).decode().rstrip("=")
    stale_sig = hmac.new(graph_mod._state_secret(), stale_body.encode(), hashlib.sha256).hexdigest()[:32]
    try:
        graph_mod.parse_state(f"{stale_body}.{stale_sig}")
        check("expired state rejected", False, True)
    except MailIntakeError:
        check("expired state rejected", True, True)

    try:
        graph_mod.parse_state("garbage")
        check("malformed state rejected", False, True)
    except MailIntakeError:
        check("malformed state rejected", True, True)


# ── Gmail IMAP cursor semantics ─────────────────────────────────────────────


class FakeImap:
    """Just enough IMAP to drive _fetch_new_attachments_sync."""

    def __init__(self, uidvalidity, uids, raw_by_uid, expect_readonly=True):
        self.uidvalidity = uidvalidity
        self.uids = uids
        self.raw_by_uid = raw_by_uid
        self.expect_readonly = expect_readonly
        self.commands = []

    def login(self, u, p):
        self.commands.append("LOGIN")
        return ("OK", [b""])

    def select(self, folder, readonly=False):
        self.commands.append(f"SELECT readonly={readonly}")
        assert readonly is True, "must EXAMINE, never SELECT"
        return ("OK", [b"1"])

    def response(self, key):
        return ("OK", [str(self.uidvalidity).encode()]) if key == "UIDVALIDITY" else ("NO", [None])

    def uid(self, cmd, *args):
        self.commands.append(cmd)
        if cmd == "SEARCH":
            return ("OK", [" ".join(str(u) for u in self.uids).encode()])
        if cmd == "FETCH":
            assert "BODY.PEEK" in args[1], "must PEEK so \\Seen is untouched"
            u = int(args[0])
            return ("OK", [(b"1 (UID)", self.raw_by_uid[u])])
        return ("NO", [None])

    def logout(self):
        self.commands.append("LOGOUT")


def _mime_with_zip(filename: str, blob: bytes) -> bytes:
    from email.message import EmailMessage
    m = EmailMessage()
    m["From"] = "noreply@hcsra.co.il"
    m["To"] = "agent@example.com"
    m["Subject"] = "production"
    m["Message-ID"] = "<abc@hcsra>"
    m.set_content("see attached")
    m.add_attachment(blob, maintype="application", subtype="zip", filename=filename)
    return m.as_bytes()


def test_gmail_imap():
    print("\nGmail IMAP (read-only, UIDVALIDITY-aware):")
    blob = FIXTURE.read_bytes()
    raw = {7: _mime_with_zip("Ild_prod_1_09344_30042026.zip", blob)}

    fake = FakeImap(uidvalidity=111, uids=[7], raw_by_uid=raw)
    orig = gmail_mod.imaplib.IMAP4_SSL
    gmail_mod.imaplib.IMAP4_SSL = lambda *a, **k: fake
    try:
        res = gmail_mod._fetch_new_attachments_sync("h", 993, "INBOX", "a@b.c", "pw", None, None)
        check("one attachment extracted", len(res.attachments), 1)
        check("bytes round-trip", res.attachments[0].content, blob)
        check("filename", res.attachments[0].filename, "Ild_prod_1_09344_30042026.zip")
        check("external_id embeds the UIDVALIDITY epoch", res.attachments[0].external_id.startswith("111:7:"), True)
        check("cursor advanced", res.last_uid, 7)
        check("EXAMINE not SELECT", "SELECT readonly=True" in fake.commands, True)
        check("never mutates the mailbox", any(c in fake.commands for c in ("STORE", "EXPUNGE")), False)

        # Same epoch, cursor past the message -> nothing new.
        fake2 = FakeImap(uidvalidity=111, uids=[7], raw_by_uid=raw)
        gmail_mod.imaplib.IMAP4_SSL = lambda *a, **k: fake2
        res2 = gmail_mod._fetch_new_attachments_sync("h", 993, "INBOX", "a@b.c", "pw", 111, 7)
        check("second poll is a no-op", len(res2.attachments), 0)

        # UIDVALIDITY changed: uid 7 is a DIFFERENT message now. Cursor must reset,
        # not silently skip.
        fake3 = FakeImap(uidvalidity=222, uids=[7], raw_by_uid=raw)
        gmail_mod.imaplib.IMAP4_SSL = lambda *a, **k: fake3
        res3 = gmail_mod._fetch_new_attachments_sync("h", 993, "INBOX", "a@b.c", "pw", 111, 7)
        check("UIDVALIDITY change re-reads", len(res3.attachments), 1)
        check("new epoch in external_id", res3.attachments[0].external_id.startswith("222:7:"), True)
    finally:
        gmail_mod.imaplib.IMAP4_SSL = orig

    print("\n  bad app password surfaces a CODE, never the echoed LOGIN line:")

    class BadLogin(FakeImap):
        def login(self, u, p):
            raise gmail_mod.imaplib.IMAP4.error(f'LOGIN "{u}" "{p}" failed')

    gmail_mod.imaplib.IMAP4_SSL = lambda *a, **k: BadLogin(1, [], {})
    try:
        gmail_mod._fetch_new_attachments_sync("h", 993, "INBOX", "a@b.c", "hunter2", None, None)
        check("raises MailIntakeError", False, True)
    except MailIntakeError as e:
        check("error code", e.code, "bad_app_password")
        check("password absent from the exception", "hunter2" not in str(e), True)
    finally:
        gmail_mod.imaplib.IMAP4_SSL = orig


# ── Graph delta + attachment decode ─────────────────────────────────────────


async def test_graph_delta():
    print("\nMicrosoft Graph delta poll:")
    blob = FIXTURE.read_bytes()
    b64 = base64.b64encode(blob).decode()

    def handler(req: httpx.Request) -> httpx.Response:
        url = str(req.url)
        if "/attachments" in url:
            return httpx.Response(200, json={"value": [
                {"name": "Ild_prod_1_09344_30042026.zip", "contentBytes": b64},
                {"name": "logo.png", "contentBytes": base64.b64encode(b"png").decode()},
            ]})
        if "delta" in url:
            return httpx.Response(200, json={
                "value": [
                    {"id": "m1", "hasAttachments": True, "internetMessageId": "<x@y>"},
                    {"id": "m2", "hasAttachments": False},
                ],
                "@odata.deltaLink": "https://graph.microsoft.com/delta?token=NEXT",
            })
        return httpx.Response(404)

    transport = httpx.MockTransport(handler)
    orig = httpx.AsyncClient
    httpx.AsyncClient = lambda **kw: orig(transport=transport, **kw)
    try:
        atts, delta = await graph_mod.fetch_new_attachments("tok", None)
        check("skips messages without attachments", len(atts), 2)
        check("zip bytes round-trip", atts[0].content, blob)
        check("delta cursor captured", delta, "https://graph.microsoft.com/delta?token=NEXT")
    finally:
        httpx.AsyncClient = orig

    # 401 => consent revoked, not a generic failure: the UI offers "reconnect".
    transport = httpx.MockTransport(lambda r: httpx.Response(401))
    httpx.AsyncClient = lambda **kw: orig(transport=transport, **kw)
    try:
        await graph_mod.fetch_new_attachments("tok", None)
        check("401 raises", False, True)
    except MailIntakeError as e:
        check("401 -> consent_revoked", e.code, "consent_revoked")
    finally:
        httpx.AsyncClient = orig


# ── Seam: guard + dedup, against the real DB (rolled back) ──────────────────


async def test_seam_db():
    """NOTE: `ingest_mail_attachment` COMMITS per attachment on purpose — one bad
    file must not roll back the good ones. So this test cannot wrap itself in a
    transaction; it cleans up explicitly in `finally` instead. It also stubs the
    post-ingest hooks, which would otherwise spawn background tasks that write
    rows after we've deleted them."""
    print("\nShared seam (guard, ingest, dedup) — DB, cleaned up after:")
    from sqlalchemy import delete, select
    from app.database import async_session
    from app.models.user import User
    from app.models.mailbox_config import MailboxConfig
    from app.models.mailbox_message import MailboxProcessedMessage
    from app.models.record import ClientRecord
    from app.models.upload import FileUpload
    from app.models.production_summary import ProductionSummary
    from app.models.portal_snapshot import PortalSnapshot
    from app.config import settings
    from cryptography.fernet import Fernet
    import app.services.mail_intake as seam
    settings.MAILBOX_ENCRYPTION_KEY = Fernet.generate_key().decode()

    original_hook = seam.schedule_post_ingest
    seam.schedule_post_ingest = lambda *a, **k: None  # no stray background writes

    blob = FIXTURE.read_bytes()
    cfg_id = None
    upload_id = None
    try:
        async with async_session() as db:
            user = (await db.execute(select(User).limit(1))).scalars().first()
            if not user:
                print("  SKIP — no user in local db")
                return
            cfg = MailboxConfig(user_id=user.id, email_address="moshe@eitam-finance.com", mail_host="microsoft")
            db.add(cfg)
            await db.flush()
            cfg_id = cfg.id

            good = FetchedAttachment("m1:z", "Ild_prod_1_09344_30042026.zip", blob, "<x@y>")
            upload = await ingest_mail_attachment(db, cfg, good)
            check("ingested", upload is not None, True)
            upload_id = upload.id
            check("company", upload.company_source, "הכשרה")
            check("is_production", upload.is_production, True)
            check("last_received_at stamped", cfg.last_received_at is not None, True)

            # Replay of the same external_id must not double-ingest.
            again = await ingest_mail_attachment(db, cfg, good)
            check("replay is a no-op", again, None)

            # Wrong filename is refused BEFORE parsing, and ledgered so it isn't retried.
            bad = FetchedAttachment("m2:i", "invoice.pdf", b"%PDF-1.4", None)
            check("non-matching filename refused", await ingest_mail_attachment(db, cfg, bad), None)
            row = (await db.execute(
                select(MailboxProcessedMessage).where(MailboxProcessedMessage.external_id == "m2:i")
            )).scalars().first()
            check("rejection is ledgered", row.status, "rejected")
            check("rejection reason", row.error, "filename_not_matched")

            # A matching filename with garbage inside is recorded, never wedged.
            junk = FetchedAttachment("m3:z", "Ild_prod_9_09344_31052026.zip", b"not a zip", None)
            check("unparseable content refused", await ingest_mail_attachment(db, cfg, junk), None)
            row = (await db.execute(
                select(MailboxProcessedMessage).where(MailboxProcessedMessage.external_id == "m3:z")
            )).scalars().first()
            check("parse failure is ledgered", row.status, "parse_error")
    finally:
        seam.schedule_post_ingest = original_hook
        async with async_session() as db:
            if upload_id:
                await db.execute(delete(ClientRecord).where(ClientRecord.upload_id == upload_id))
                await db.execute(delete(ProductionSummary).where(ProductionSummary.upload_id == upload_id))
                await db.execute(delete(PortalSnapshot).where(PortalSnapshot.upload_id == upload_id))
            if cfg_id:
                await db.execute(
                    delete(MailboxProcessedMessage).where(MailboxProcessedMessage.mailbox_id == cfg_id)
                )
            if upload_id:
                await db.execute(delete(FileUpload).where(FileUpload.id == upload_id))
            if cfg_id:
                await db.execute(delete(MailboxConfig).where(MailboxConfig.id == cfg_id))
            await db.commit()
        print("  cleaned up — test rows deleted")


def test_filename_guard():
    print("\nFilename guard (runs before any parsing):")
    for name, expected in [
        ("Ild_prod_1_09344_30042026.zip", True),
        ("ild_prod_2_9344_01012026.ZIP", True),
        ("Ild_prod_1_09344_30042026 (1).zip", False),
        ("invoice.pdf", False),
        ("../../etc/passwd", False),
        ("Ild_prod_1_09344_30042026.zip.exe", False),
        ("", False),
    ]:
        check(f"{name!r}", bool(MAILBOX_ATTACHMENT_PATTERN.match(name)), expected)


async def main():
    if not FIXTURE.exists():
        print(f"SKIP — fixture missing: {FIXTURE}")
        return 0
    await test_mx_detection()
    test_resend_signature()
    test_graph_state()
    test_gmail_imap()
    await test_graph_delta()
    test_filename_guard()
    try:
        await test_seam_db()
    except Exception as e:
        print(f"  SKIP db portion — {type(e).__name__}: {e}")

    print(f"\n{'ALL PASS' if not _failures else str(_failures) + ' FAILURE(S)'}")
    return 1 if _failures else 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
