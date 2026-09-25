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

    # BAKASHA-MITMASHECHET is 1 = חד"פ / 2 = מתמשכת, and per the field spec it is
    # mandatory ONLY for 9100/1 (and 9300/2). It used to carry "1" on the ONGOING
    # codes — the opposite meaning — and nil on 9100 where it is required.
    ongoing = build_events_request(action_code="9201", customer_id_number="043417252",
                                   allow_placeholder_identity=True).xml.decode()
    check("9100 marks BAKASHA-MITMASHECHET 1 (one-off)", text_of(x, "BAKASHA-MITMASHECHET") == "1")
    check("9201 leaves it nil (not relevant)", text_of(ongoing, "BAKASHA-MITMASHECHET") == "")

    # MISPAR-MEZAHE-RESHUMA follows the spec layout: file no (34) + customer
    # (16, zero-padded) + employee (16 zeros) + event (4) + numerator (4).
    _ref = text_of(x, "MISPAR-MEZAHE-RESHUMA") or ""
    check("record reference is 74 chars", len(_ref) == 74, str(len(_ref)))
    check("record reference starts with MISPAR-HAKOVETZ",
          _ref[:34] == text_of(x, "MISPAR-HAKOVETZ"), _ref[:34])
    check("record reference carries the customer, zero-padded to 16",
          _ref[34:50] == "0000000043417252", _ref[34:50])
    check("record reference carries the event code", _ref[66:70] == "9100", _ref[66:70])

    # Production reports are per MANUFACTURER, and their subject is the AGENT
    # (SUG-LAKOACH 3 = מפיץ, field spec) — not a saver.
    check("2100 needs no customer", ACTION_CODES["2100"].needs_customer is False)
    try:
        build_events_request(action_code="2000", allow_placeholder_identity=True,
                             acting_agent_id="040336281", acting_agent_name="משה כהן")
        check("2000 refuses to build with no יצרן", False, "it built anyway")
    except ValueError as e:
        check("2000 refuses to build with no יצרן", "yatzran_id" in str(e))
    try:
        build_events_request(action_code="2000", yatzran_id="514956465",
                             allow_placeholder_identity=True)
        check("2000 refuses to build with no acting agent", False, "it built anyway")
    except ValueError as e:
        check("2000 refuses to build with no acting agent", "MISPAR-MEZAHE-LAKOACH" in str(e))
    prod = build_events_request(action_code="2000", yatzran_id="514956465",
                                acting_agent_id="40336281", acting_agent_name="משה כהן",
                                allow_placeholder_identity=True).xml.decode()
    check("2000: SUG-LAKOACH is 3 (מפיץ)", text_of(prod, "SUG-LAKOACH") == "3")
    check("2000: the subject is the agent, zero-padded to 9",
          text_of(prod, "MISPAR-MEZAHE-LAKOACH") == "040336281")
    check("2000: SHEM-MAASIK carries the מפיץ name", text_of(prod, "SHEM-MAASIK") == "משה כהן")
    check("2000: KOD-MEZAHE-YATZRAN names the body",
          text_of(prod, "KOD-MEZAHE-YATZRAN") == "514956465")
    check("acting agent rides in YeshutGoremPoneLemislaka",
          text_of(prod, "SUG-PONE") == "3" and text_of(prod, "MISPAR-MEZAHE-PONE") == "040336281")
    check("9100 carries no Mutzar block", "<Mutzar>" not in x)

    # Environment: this decides whether real traffic hits the live vault.
    # **1 = TEST, 2 = PRODUCTION**, per the XSD's own <xsd:documentation>.
    # These two only prove the explicit argument is honoured — both labels used
    # to state the mapping BACKWARDS, which is how the inverted default below
    # went unnoticed for twelve days.
    check("explicit 2 → KOD-SVIVAT-AVODA 2 (PRODUCTION)",
          text_of(x, "KOD-SVIVAT-AVODA") == "2")
    prd = build_events_request(action_code="9100", customer_id_number="043417252",
                               environment_code="1", allow_placeholder_identity=True).xml.decode()
    check("explicit 1 → KOD-SVIVAT-AVODA 1 (TEST)",
          text_of(prd, "KOD-SVIVAT-AVODA") == "1")

    # THE regression guard that was missing. Every production caller passes
    # `environment_code`, so the builder's own fallback was never exercised —
    # and it still held the pre-2026-09-10 INVERTED mapping, emitting `2`
    # (PRODUCTION) for the test vault. It must agree with `environment()`, and
    # with the filename suffix that is derived from the same call.
    from app.config import settings as _s
    from app.services.maslaka.events import environment
    _saved_env = _s.MASLAKA_TEST_ENVIRONMENT
    try:
        for _test_env, _want_code, _want_suffix in ((True, "1", "TST"), (False, "2", "DAT")):
            _s.MASLAKA_TEST_ENVIRONMENT = _test_env
            _d = build_events_request(action_code="9100", customer_id_number="043417252",
                                      allow_placeholder_identity=True).xml.decode()
            _label = "TST" if _test_env else "PRD"
            check(f"default (no environment_code) on {_label} → {_want_code}",
                  text_of(_d, "KOD-SVIVAT-AVODA") == _want_code,
                  str(text_of(_d, "KOD-SVIVAT-AVODA")))
            check(f"default on {_label} agrees with environment() and the .{_want_suffix} suffix",
                  environment() == (_want_code, _want_suffix)
                  and text_of(_d, "KOD-SVIVAT-AVODA") == environment()[0],
                  str(environment()))
    finally:
        _s.MASLAKA_TEST_ENVIRONMENT = _saved_env

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
    # ── The filename clock ────────────────────────────────────────────────
    # `build_filename` defaulted to `datetime.now()` — the HOST clock. The dev
    # box runs IDT so it looked perfect here, while the UTC Gateway named two
    # real files 174253/174254 on 2026-09-22 with 204253 inside them. These
    # assertions are deliberately host-INDEPENDENT: comparing against utcnow()
    # catches the regression on a UTC box and an Israeli one alike.
    from datetime import datetime as _dt, timedelta as _td
    from app.services.maslaka.filenames import maslaka_now as _fn_now
    from app.services.maslaka.events import maslaka_now as _ev_now

    _off = (_fn_now() - _dt.utcnow()).total_seconds() / 3600
    check("filename clock is Israel local, not UTC (offset 2h or 3h)",
          1.9 < _off < 3.1, f"offset {_off:.2f}h")
    check("filenames and events agree on the clock",
          abs((_fn_now() - _ev_now()).total_seconds()) < 2)

    _stamp = _dt(2026, 9, 22, 20, 42, 53)
    _nm = build_filename(direction="001", sender_id="558638623", service="EVENTS",
                         version="007", sequence=1, file_type="TST", when=_stamp)
    check("an explicit `when` lands verbatim in the name",
          "20260922204253" in _nm, _nm)

    # The real invariant: the NAME and TAARICH-BITZUA must be the same instant.
    _r = build_events_request(action_code="9100", customer_id_number="043417252",
                              when=_stamp, sequence=1, allow_placeholder_identity=True)
    check("name timestamp == TAARICH-BITZUA in the payload",
          text_of(_r.xml.decode(), "TAARICH-BITZUA") == "20260922204253",
          str(text_of(_r.xml.decode(), "TAARICH-BITZUA")))

    check("filename parses", parsed is not None, name)
    check("sender zero-padded to 12 in the filename",
          parsed and parsed.sender_id == "000043417252", parsed.sender_id if parsed else "")
    check("TST suffix marks the test environment", parsed and parsed.is_test)

    print("\n" + ("ALL PASS" if not FAILURES else f"{len(FAILURES)} FAILURE(S): " + "; ".join(FAILURES)))
    sys.exit(1 if FAILURES else 0)


if __name__ == "__main__":
    main()
