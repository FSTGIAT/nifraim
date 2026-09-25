"""משוב א' (FEDBKA) verdicts, and the sender-contact guard that caused them.

    source backend/venv/bin/activate && python backend/tests/test_maslaka_feedback_parse.py

The case this guards against actually happened. From 09-10 to 09-25, all 43 FEDBKA
files the מסלקה returned were REJECTIONS (`MashovBeramatKovetz/KOD-SHGIHA=3`, "מבנה
XML לא חוקי": xsi:nil on non-nillable elements). The parser read
`KOD-SHGIHA-BERAMAT-KOVETZ` / `TEUR-SHGIHA`, and neither name exists in feedback_009.xsd,
so every rejection was stored as `acknowledged`. The two nils were the sender's
landline and e-mail. The Gateway `.env` had no MASLAKA_CONTACT_* values; the dev
`.env` had them, which is why every local test passed.
"""

import glob
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from lxml import etree  # noqa: E402

from app.config import settings  # noqa: E402
from app.services.maslaka.adapter import parse_feedback  # noqa: E402
from app.services.maslaka.events import MaslakaIdentityNotConfigured, build_events_request  # noqa: E402

FIX = Path(__file__).parent / "fixtures" / "maslaka"
FAILURES: list[str] = []


def check(label: str, ok: bool, detail: str = "") -> None:
    print(f"  {'PASS' if ok else 'FAIL'} — {label}" + (f"  [{detail}]" if detail else ""))
    if not ok:
        FAILURES.append(label)


print("live rejection (PROD, 2026-09-25)")
r = parse_feedback((FIX / "live_fedbka_rejected_nil_20260925.DAT").read_bytes())
check("is NOT an ack", r.is_ack is False)
check("file-level code 3", r.error_code == "3", str(r.error_code))
check("detail names the nillable violation", "nillable" in (r.error_detail or ""))
check("correlates to our filename",
      r.acked_filename == "001000558638623EVENTS000007202609250916410001.DAT")

print("vendor samples stay clean")
for f in sorted(glob.glob(str(FIX / "swiftness_samples" / "*FEDBK*"))):
    fb = parse_feedback(Path(f).read_bytes())
    check(Path(f).name[:40], fb.is_ack and fb.error_code is None)

print("builder refuses a file with nil sender contact")
_saved = {k: getattr(settings, k) for k in
          ("MASLAKA_CONTACT_PHONE", "MASLAKA_CONTACT_MOBILE", "MASLAKA_CONTACT_EMAIL",
           "MASLAKA_AGENT_ID", "MASLAKA_AGENT_NUMBER")}
kw = dict(action_code="2000", customer_id_number="040336281", yatzran_id="514956465",
          acting_agent_id="040336281", acting_agent_name="משה כהן", environment_code="2")
try:
    settings.MASLAKA_AGENT_ID, settings.MASLAKA_AGENT_NUMBER = "558638623", "Nifraim.com"
    for phone, mobile, email, label in [
        ("", "", "a@b.co", "no phone at all"),
        ("", "0501234567", "", "no e-mail"),
        ("", "0501234567", "a@b.co", "mobile only — rule 116 rejects a mobile as landline"),
        ("508882597", "0501234567", "a@b.co", "non-landline in PHONE (rule 116, seq 0032)"),
    ]:
        settings.MASLAKA_CONTACT_PHONE, settings.MASLAKA_CONTACT_MOBILE = phone, mobile
        settings.MASLAKA_CONTACT_EMAIL = email
        try:
            build_events_request(**kw)
            check(label, False, "built anyway")
        except MaslakaIdentityNotConfigured:
            check(label, True)

    settings.MASLAKA_CONTACT_PHONE, settings.MASLAKA_CONTACT_MOBILE = "031234567", "0501234567"
    settings.MASLAKA_CONTACT_EMAIL = "a@b.co"
    xml = build_events_request(**kw).xml
    # Rule 118 (seq 0034): the sender is the vault owner. Rule 144 (seq 0033): a
    # production request's subject equals its sender. The agent rides in PONE.
    _d = etree.fromstring(xml)
    _t = lambda tag: _d.find(".//" + tag).text  # noqa: E731
    check("2000 sender = vault owner (rule 118)",
          (_t("SUG-MEZAHE-SHOLECH"), _t("MISPAR-ZIHUI-SHOLECH")) == ("1", "558638623"))
    check("2000 subject = sender (rule 144)",
          (_t("SUG-MEZAHE-LAKOACH"), _t("MISPAR-MEZAHE-LAKOACH")) == ("1", "558638623"))
    check("2000 agent carried in PONE",
          (_t("SUG-PONE"), _t("SUG-KOD-MEZAHE-PONE"), _t("MISPAR-MEZAHE-PONE")) == ("3", "3", "040336281"))
    schema = etree.XMLSchema(etree.parse(str(FIX / "xsd" / "events_007.xsd")))
    ok = schema.validate(etree.fromstring(xml))
    check("with contact set, the 2000 is XSD-valid", ok, str(schema.error_log)[:200])
finally:
    for k, v in _saved.items():
        setattr(settings, k, v)

print()
if FAILURES:
    print(f"FAILED: {len(FAILURES)}")
    sys.exit(1)
print("all passed")
