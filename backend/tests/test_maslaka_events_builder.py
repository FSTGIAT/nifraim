"""ממשק אירועים v007 outbound builder.

    source backend/venv/bin/activate && python backend/tests/test_maslaka_events_builder.py

The structure under test is not inferred — it mirrors Swiftness's published
`001000347464265EVENTS000007202412011241080003.DAT`, a real agent→מסלקה 9101.

The assertion that matters most: a ת"ז keeps its LEADING ZERO. Israeli IDs are
nine digits including leading zeros, `043417252` is a real one, and the sample
this builder was modelled on happened to be `381788223` — so a `.lstrip("0")`
looked correct and would have sent an 8-digit identifier for roughly a tenth of
savers, silently, only in live traffic.
"""

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

FAILURES: list[str] = []


def check(label: str, ok: bool, detail: str = "") -> None:
    print(f"  {'PASS' if ok else 'FAIL'} — {label}" + (f"  [{detail}]" if detail else ""))
    if not ok:
        FAILURES.append(label)


def text_of(xml: str, tag: str) -> str | None:
    """Text of a tag, or "" when the builder marked it xsi:nil.

    Absent values serialise as `<TAG xsi:nil="true" />`, so a naive
    `<TAG>(.*?)</TAG>` finds nothing and cannot tell "empty" from "missing".
    """
    m = re.search(rf"<{tag}>(.*?)</{tag}>", xml)
    if m:
        return m.group(1)
    if re.search(rf'<{tag}\s+xsi:nil="true"\s*/>', xml):
        return ""
    return None


def main() -> None:
    from app.services.maslaka.events import (
        ACTION_CODES, MASLAKA_ENTITY_ID, build_events_request,
        MaslakaIdentityNotConfigured,
    )
    from app.services.maslaka.filenames import build_filename, parse_filename

    print("Events v007 request builder")

    r = build_events_request(
        action_code="9100", customer_id_number="043417252",
        customer_first_name="ישראל", customer_last_name="ישראלי",
        environment_code="2", allow_placeholder_identity=True,
    )
    x = r.xml.decode("utf-8")

    check("root element is <Mimshak>, not the invented <EventsRequest>",
          x.count("<Mimshak") == 1 and "<EventsRequest" not in x)
    check("SUG-MIMSHAK = 6 (ממשק אירועים)", text_of(x, "SUG-MIMSHAK") == "6")
    check("version 007", text_of(x, "MISPAR-GIRSAT-XML") == "007")
    check("נמען is the מסלקה's ח.פ", text_of(x, "MISPAR-ZIHUI-NIMAAN") == MASLAKA_ENTITY_ID)
    check("action code lands in KOD-EIRUA", text_of(x, "KOD-EIRUA") == "9100")

    # THE one that matters.
    check("ת\"ז keeps its leading zero (9 digits)",
          text_of(x, "MISPAR-MEZAHE-LAKOACH") == "043417252",
          str(text_of(x, "MISPAR-MEZAHE-LAKOACH")))
    r2 = build_events_request(action_code="9100", customer_id_number="381788223",
                              allow_placeholder_identity=True)
    check("a ת\"ז without a leading zero is unchanged",
          text_of(r2.xml.decode(), "MISPAR-MEZAHE-LAKOACH") == "381788223")
    r3 = build_events_request(action_code="9100", customer_id_number="43417252",
                              allow_placeholder_identity=True)
    check("an 8-digit ת\"ז is padded back to 9",
          text_of(r3.xml.decode(), "MISPAR-MEZAHE-LAKOACH") == "043417252")

    # The vendor's own file declares xmlns:xsi and marks all 39 of its absent
    # values xsi:nil="true" — zero empty pairs. Match it.
    check("declares the xsi namespace on <Mimshak>",
          'xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"' in x)
    check("absent values are xsi:nil, not empty tags",
          'xsi:nil="true"' in x and not re.findall(r"<[A-Z][A-Za-z0-9-]*></[A-Z][A-Za-z0-9-]*>", x))
    check("containers are never marked nil",
          not re.findall(r"<(?:KoteretKovetz|NetuneiGoremSholech|GufHamimshak|Eirua|KodEirua)[^>]*xsi:nil", x))

    # MISPAR-MISLAKA is the מסלקה's GUID, returned on the FEDBKB. Never ours.
    check("MISPAR-MISLAKA is empty outbound", text_of(x, "MISPAR-MISLAKA") == "")

    # Ongoing vs one-off is a flag, not a separate code.
    ongoing = build_events_request(action_code="9201", customer_id_number="043417252",
                                   allow_placeholder_identity=True).xml.decode()
    check("9201 sets BAKASHA-MITMASHECHET", text_of(ongoing, "BAKASHA-MITMASHECHET") == "1")
    check("9100 does not", text_of(x, "BAKASHA-MITMASHECHET") == "")

    # Production-report subscriptions are per MANUFACTURER — no customer at all.
    check("2100 needs no customer", ACTION_CODES["2100"].needs_customer is False)
    # Corrected 2026-09-10 against the official XSD: "needs no customer" is about
    # the REQUEST's semantics (it is per-יצרן, not per-saver), but the schema
    # still makes MISPAR-MEZAHE-LAKOACH minOccurs=1 and NOT nillable. Building
    # without an identifier produced an invalid file, so the builder now refuses
    # instead of emitting one. Whose ID belongs there is open with Swiftness.
    try:
        build_events_request(action_code="2100", allow_placeholder_identity=True)
        check("2100 refuses to build with no identifier", False, "it built anyway")
    except ValueError as e:
        check("2100 refuses to build with no identifier", "MISPAR-MEZAHE-LAKOACH" in str(e))
    prod = build_events_request(action_code="2100", customer_id_number="558638623",
                                allow_placeholder_identity=True)
    check("2100 builds when given one", b"<KOD-EIRUA>2100</KOD-EIRUA>" in prod.xml)

    # Environment: this decides whether real traffic hits the live vault.
    check("TST → KOD-SVIVAT-AVODA 2", text_of(x, "KOD-SVIVAT-AVODA") == "2")
    prd = build_events_request(action_code="9100", customer_id_number="043417252",
                               environment_code="1", allow_placeholder_identity=True).xml.decode()
    check("PRD → KOD-SVIVAT-AVODA 1", text_of(prd, "KOD-SVIVAT-AVODA") == "1")

    # Identity refusal on any path that could transport.
    from app.config import settings
    saved = (settings.MASLAKA_AGENT_ID, settings.MASLAKA_AGENT_NUMBER)
    settings.MASLAKA_AGENT_ID, settings.MASLAKA_AGENT_NUMBER = "", ""
    try:
        build_events_request(action_code="9100", customer_id_number="043417252")
        raised = False
    except MaslakaIdentityNotConfigured:
        raised = True
    finally:
        settings.MASLAKA_AGENT_ID, settings.MASLAKA_AGENT_NUMBER = saved
    check("refuses to build without agent identity unless previewing", raised)

    # Filename: 12-digit zero-padding is the FILENAME's job, not the payload's.
    name = build_filename(direction="001", sender_id="043417252", service="EVENTS",
                          version="007", sequence=1, file_type="TST")
    parsed = parse_filename(name)
    check("filename parses", parsed is not None, name)
    check("sender zero-padded to 12 in the filename",
          parsed and parsed.sender_id == "000043417252", parsed.sender_id if parsed else "")
    check("TST suffix marks the test environment", parsed and parsed.is_test)

    print("\n" + ("ALL PASS" if not FAILURES else f"{len(FAILURES)} FAILURE(S): " + "; ".join(FAILURES)))
    sys.exit(1 if FAILURES else 0)


if __name__ == "__main__":
    main()
