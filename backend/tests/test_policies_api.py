"""/api/policies + /office-agent/act kind=harb — privacy and edge cases, in-process (httpx ASGI).

    source backend/venv/bin/activate && python backend/tests/test_policies_api.py

Local dev DB: user A = test@test.com (has policies), user B = cycle-ui@test.com. One tiny blank PDF
is converted by Claude (it must end `failed`, never stuck `processing`). Cleans up what it creates.
"""
import asyncio
import io
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import httpx  # noqa: E402
from sqlalchemy import select  # noqa: E402

from app.database import async_session  # noqa: E402
from app.main import app  # noqa: E402
from app.models import PolicyDocument, User  # noqa: E402
from app.services.auth_service import create_access_token  # noqa: E402

FAILS: list[str] = []


def check(cond, msg):
    print(("  ok   " if cond else "  FAIL ") + msg)
    if not cond:
        FAILS.append(msg)


def blank_pdf() -> bytes:
    from pypdf import PdfWriter
    w = PdfWriter()
    w.add_blank_page(width=200, height=200)
    b = io.BytesIO()
    w.write(b)
    return b.getvalue()


async def main():
    async with async_session() as db:
        a = (await db.execute(select(User).where(User.email == "test@test.com"))).scalar_one()
        b = (await db.execute(select(User).where(User.email == "cycle-ui@test.com"))).scalar_one_or_none()
        a_doc = (await db.execute(select(PolicyDocument).where(PolicyDocument.user_id == a.id, PolicyDocument.status == "ready")
                                  .order_by((PolicyDocument.source == "pdf").desc()).limit(1))).scalar_one_or_none()
    if not b or not a_doc:
        print("skip — needs user B and one ready policy document for user A (run test_harb_e2e_mock / upload first)")
        return
    HA = {"Authorization": f"Bearer {create_access_token(str(a.id))}"}
    HB = {"Authorization": f"Bearer {create_access_token(str(b.id))}"}
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://t", timeout=60) as c:
        print("privacy — user B never reaches user A's policies")
        for method, url in (("GET", f"/api/policies/documents/{a_doc.id}"), ("GET", f"/api/policies/documents/{a_doc.id}/file"),
                            ("DELETE", f"/api/policies/documents/{a_doc.id}")):
            r = await c.request(method, url, headers=HB)
            check(r.status_code == 404, f"B {method} {url.split('/api/policies')[1][:22]}… → 404 (got {r.status_code})")
        r = await c.get(f"/api/policies/customers/{a_doc.customer_id_number}", headers=HB)
        check(r.status_code == 200 and not r.json()["policies"] and not r.json()["documents"], "B's view of A's customer is empty")
        r = await c.get("/api/policies/customers", headers=HB)
        ids = {x["id_number"] for x in r.json()["customers"]}
        check(a_doc.customer_id_number not in ids, "A's customer is not in B's list")
        r = await c.get("/api/policies/customers")
        check(r.status_code in (401, 403), f"no token → refused (got {r.status_code})")

        print("uploads")
        r = await c.post("/api/policies/upload", headers=HA, files={"file": ("x.txt", b"hello world", "text/plain")})
        check(r.status_code == 400, "a non-PDF is refused")
        r = await c.post("/api/policies/upload", headers=HA, files={"file": ("e.pdf", b"", "application/pdf")})
        check(r.status_code == 400, "an empty file is refused")
        r = await c.post("/api/policies/upload", headers=HA, files={"file": ("big.pdf", b"%PDF-" + b"0" * (25 * 1024 * 1024), "application/pdf")})
        check(r.status_code == 400, "over 25MB is refused")
        if a_doc.file_path and Path(a_doc.file_path).exists():
            r = await c.post("/api/policies/upload", headers=HA, files={"file": ("again.pdf", Path(a_doc.file_path).read_bytes(), "application/pdf")})
            check(r.json().get("duplicate") and r.json()["id"] == str(a_doc.id), "the same PDF twice → the existing document, not a copy")
        r = await c.post("/api/policies/upload", headers=HA, data={"id_number": "0099999998"},
                         files={"file": ("blank.pdf", blank_pdf(), "application/pdf")})
        new_id = r.json()["id"]
        check(r.status_code == 200 and r.json()["status"] == "processing", "a PDF is accepted and converts in the background")
        st = "processing"
        for _ in range(90):
            await asyncio.sleep(2)
            st = (await c.get(f"/api/policies/documents/{new_id}", headers=HA)).json()["status"]
            if st != "processing":
                break
        doc = (await c.get(f"/api/policies/documents/{new_id}", headers=HA)).json()
        check(st == "failed" and "אינו פוליסת" in (doc.get("error") or ""),
              f"a blank PDF ends failed ('not a policy'), never ready or stuck (got {st}: {doc.get('error')})")
        check(doc["customer_id_number"] == "99999998", "the agent's ID is stored zero-stripped")
        r = await c.get(f"/api/policies/documents/{new_id}/file", headers=HA)
        check(r.status_code == 200 and r.content[:5] == b"%PDF-", "the original PDF is served back to its owner")
        r = await c.delete(f"/api/policies/documents/{new_id}", headers=HA)
        check(r.status_code == 200 and (await c.get(f"/api/policies/documents/{new_id}", headers=HA)).status_code == 404,
              "delete removes it")

        print("act kind=harb — input validation")
        for data, why in (({"customer_id_number": "12", "birth_date": "22/05/1986", "issue_date": "01/01/2004"}, "short ID"),
                          ({"customer_id_number": "32489387", "birth_date": "31/02/1986", "issue_date": "01/01/2004"}, "impossible date"),
                          ({"customer_id_number": "32489387", "birth_date": "22/05/1986", "issue_date": "01/01/2999"}, "future date")):
            r = await c.post("/api/office-agent/act", headers=HA, json={"kind": "harb", "data": data})
            check(r.status_code == 400, f"{why} → 400 (got {r.status_code})")
        r = await c.post("/api/office-agent/act", headers=HB, json={"kind": "harb", "data": {
            "customer_id_number": "32489387", "birth_date": "22/05/1986", "issue_date": "01/01/2004"}})
        check(r.status_code == 409 and "פרטי כניסה" in r.json().get("detail", ""), "B without a הר הביטוח credential → 409 with the Hebrew reason")
    print(f"\n{'ALL PASSED' if not FAILS else f'{len(FAILS)} FAILED'}")
    sys.exit(1 if FAILS else 0)


if __name__ == "__main__":
    asyncio.run(main())
