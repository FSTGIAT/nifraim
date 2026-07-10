"""Watch a forwarded Hachshara mail land in the Production tab — no Resend account.

Exercises the REAL inbound path. Nothing is mocked inside the app: the backend
verifies a genuine Svix signature, resolves the tenant from the recipient token,
calls the Attachments API, downloads the zip, parses it, and ingests it.

The only substitution is *where* the Attachments API lives. This script stands up
a local stub that speaks Resend's shape, and the backend must be started with
`RESEND_API_BASE` pointing at it.

Run it:

    # terminal 1 — backend, pointed at the stub
    cd backend && source venv/bin/activate
    RESEND_API_BASE=http://127.0.0.1:8766 uvicorn app.main:app --port 8000

    # terminal 2
    cd backend && source venv/bin/activate
    python scripts/simulate_hachshara_mail.py

Then open the Production tab: 6 הכשרה clients, period 04/2026.
Add `--cleanup` to delete everything it created.
"""

import argparse
import base64
import hashlib
import hmac
import json
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.config import settings  # noqa: E402

API = "http://127.0.0.1:8000/api"
FIXTURE = Path(__file__).resolve().parents[1] / "tests" / "fixtures" / "Ild_prod_1_09344_30042026.zip"
STUB_PORT = 8766
EMAIL = "agent@some-small-host.co.il"   # not Microsoft, not Google -> forwarding path
# Any account, not a specific person's. Override with --email/--password.
DEFAULT_CREDS = {"email": "test@test.com", "password": "test123"}


class ResendStub(BaseHTTPRequestHandler):
    """Speaks the two calls the backend makes: list attachments, then download."""

    def do_GET(self):  # noqa: N802
        if self.path.endswith("/attachments"):
            payload = json.dumps({"data": [{
                "filename": FIXTURE.name,
                "content_type": "application/zip",
                "download_url": f"http://127.0.0.1:{STUB_PORT}/blob",
            }]}).encode()
            self._send(payload, "application/json")
        elif self.path == "/blob":
            self._send(FIXTURE.read_bytes(), "application/zip")
        else:
            self.send_error(404)

    def _send(self, body: bytes, ctype: str):
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *a):
        pass


def sign(secret: str, msg_id: str, ts: str, body: bytes) -> str:
    key = secret.split("_", 1)[1] if secret.startswith("whsec_") else secret
    mac = hmac.new(base64.b64decode(key), f"{msg_id}.{ts}.".encode() + body, hashlib.sha256)
    return base64.b64encode(mac.digest()).decode()


def login(creds: dict) -> dict:
    r = httpx.post(f"{API}/auth/login", json=creds, timeout=20)
    r.raise_for_status()
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--cleanup", action="store_true", help="remove the mailbox this script created")
    ap.add_argument("--email", default=DEFAULT_CREDS["email"], help="account to run against")
    ap.add_argument("--password", default=DEFAULT_CREDS["password"])
    ap.add_argument("--mailbox-email", default=EMAIL,
                    help="the agent's mail address to configure (forwarding path)")
    args = ap.parse_args()

    if not settings.RESEND_WEBHOOK_SECRET:
        print("RESEND_WEBHOOK_SECRET is unset — add it to .env"); return 2
    if "127.0.0.1" not in settings.RESEND_API_BASE:
        print(f"Backend must run with RESEND_API_BASE=http://127.0.0.1:{STUB_PORT}\n"
              f"(currently {settings.RESEND_API_BASE})"); return 2

    headers = login({"email": args.email, "password": args.password})

    if args.cleanup:
        httpx.delete(f"{API}/mailbox", headers=headers, timeout=20)
        print("mailbox deleted. Delete the upload from the Production tab if you want a clean slate.")
        return 0

    stub = HTTPServer(("127.0.0.1", STUB_PORT), ResendStub)
    threading.Thread(target=stub.serve_forever, daemon=True).start()

    print("1. Configure a forwarding mailbox (no credential is stored for this path)")
    r = httpx.put(f"{API}/mailbox", json={"email_address": args.mailbox_email, "mail_host": "other"},
                  headers=headers, timeout=20)
    r.raise_for_status()
    to_addr = r.json()["forward_address"]
    print(f"   forward address: {to_addr}")

    email_id = f"local_{int(time.time())}"
    body = json.dumps({
        "type": "email.received",
        "data": {
            "email_id": email_id,
            "from": "noreply@hcsra.co.il",
            "to": [to_addr],
            "subject": "קובץ פרודוקציה",
            "attachments": [{"filename": FIXTURE.name, "content_type": "application/zip"}],
        },
    }).encode()
    ts = str(int(time.time()))
    sig_headers = {
        "content-type": "application/json",
        "svix-id": email_id,
        "svix-timestamp": ts,
        "svix-signature": f"v1,{sign(settings.RESEND_WEBHOOK_SECRET, email_id, ts, body)}",
    }

    print("\n2. A tampered signature must be refused before anything else happens")
    bad = dict(sig_headers, **{"svix-signature": "v1,AAAAAAAA"})
    rb = httpx.post(f"{API}/mailbox/inbound/resend", content=body, headers=bad, timeout=30)
    print(f"   -> {rb.status_code} (expect 401)")

    print("\n3. The real, signed delivery")
    rg = httpx.post(f"{API}/mailbox/inbound/resend", content=body, headers=sig_headers, timeout=60)
    print(f"   -> {rg.status_code} {rg.text.strip()}")

    print("\n4. Replaying the identical message must be a no-op (dedup)")
    rr = httpx.post(f"{API}/mailbox/inbound/resend", content=body, headers=sig_headers, timeout=60)
    print(f"   -> {rr.status_code} (ingest suppressed by the ledger)")

    stub.shutdown()

    print("\n5. What the agent now sees")
    mb = httpx.get(f"{API}/mailbox", headers=headers, timeout=20).json()
    print(f"   status chip : last_received_at={mb['last_received_at']}  error={mb['last_error']}")
    prod = httpx.get(f"{API}/production/current", headers=headers, timeout=20).json()
    if prod:
        print(f"   production  : {prod.get('record_count')} records | "
              f"companies={prod.get('companies')} | period={prod.get('period_month')}")
    print("\nOpen the Production tab to see it. Re-run with --cleanup to undo.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
