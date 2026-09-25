"""Validate every request we build against Swiftness's OFFICIAL XSD.

    source backend/venv/bin/activate && python backend/tests/test_maslaka_xsd_validation.py

This test exists because reverse-engineering the wire format from sample files
silently missed three things that made all four of our first live sends invalid,
and produced total silence from the מסלקה rather than a defect report:

  * KOD-SVIVAT-AVODA is 1 = TEST, 2 = PRODUCTION. We had it INVERTED and sent
    `2` (production) into the test vault four times. Every one of the 12 vendor
    samples is a `.DAT` production file carrying `2`, which is consistent with
    both readings — the samples could never have caught this. The XSD's own
    <xsd:documentation> says it outright.
  * MISPAR-TELEPHONE-KAVI-ISH-KESHER-SHOLECH is minOccurs=1 and NOT nillable
    with pattern [0-9]+ — we were emitting xsi:nil.
  * KodEirua does not end at RIANUN-FISHING. Five more nillable fields follow,
    plus YipuiKoach and mismachim, which are mandatory-and-not-nillable but
    whose children are all optional — so they must be present and EMPTY.

Schemas are vendored from
https://www.swiftness.co.il/agents/קבצים-עדכניים-לעבודה-מול-המסלקה/
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

XSD_DIR = Path(__file__).parent / "fixtures" / "maslaka" / "xsd"
SAMPLES = Path(__file__).parent / "fixtures" / "maslaka" / "swiftness_samples"
FAILURES: list[str] = []


def check(label: str, ok: bool, detail: str = "") -> None:
    print(f"  {'PASS' if ok else 'FAIL'} — {label}" + (f"  [{detail}]" if detail else ""))
    if not ok:
        FAILURES.append(label)


def main() -> None:
    from lxml import etree
    from app.services.maslaka.events import (
        ACTION_CODES, build_events_request, build_file_number, environment, maslaka_now,
    )

    schema = etree.XMLSchema(etree.parse(str(XSD_DIR / "events_007.xsd")))

    print("\nEvery action code must build a schema-valid request:")
    now = maslaka_now()
    for code, action in sorted(ACTION_CODES.items()):
        # 2000/2100/2500: the subject is the acting agent (SUG-LAKOACH 3), and
        # 2000/2100 also name ONE יצרן (Mutzar/NetuneiMutzar).
        req = build_events_request(
            action_code=code,
            customer_id_number="043417252" if action.needs_customer else None,
            customer_first_name="רועי", customer_last_name="גיאת",
            sequence=1, when=now, environment_code=environment()[0],
            file_number=build_file_number(sender_id="558638623", sequence=1, when=now),
            allow_placeholder_identity=True,
            acting_agent_id="040336281", acting_agent_name="משה כהן",
            yatzran_id="514956465" if code in ("2000", "2100") else None,
        )
        doc = etree.fromstring(req.xml)
        ok = schema.validate(doc)
        detail = "" if ok else schema.error_log[0].message[:90]
        check(f"{code} ({action.label}) validates", ok, detail)

    print("\nProduction requests with an as-of date (TAARICH-NECHONUT-MEIDA) and monthly 2100:")
    for code, info_date in (("2000", "20260831"), ("2100", None), ("2100", "20260831")):
        req = build_events_request(
            action_code=code, sequence=1, when=now, environment_code=environment()[0],
            file_number=build_file_number(sender_id="558638623", sequence=1, when=now),
            allow_placeholder_identity=True, acting_agent_id="040336281",
            acting_agent_name="משה כהן", yatzran_id="514956465", information_date=info_date,
        )
        ok = schema.validate(etree.fromstring(req.xml))
        check(f"{code} information_date={info_date} validates", ok,
              "" if ok else schema.error_log[0].message[:90])
        if info_date:
            check(f"{code} carries TAARICH-NECHONUT-MEIDA",
                  f"<TAARICH-NECHONUT-MEIDA>{info_date}</TAARICH-NECHONUT-MEIDA>".encode() in req.xml)
    try:
        build_events_request(action_code="2000", yatzran_id="514956465", acting_agent_id="040336281",
                             allow_placeholder_identity=True, information_date="20260231")
        check("an impossible date (31.02) is refused", False, "it built anyway")
    except ValueError:
        check("an impossible date (31.02) is refused", True)

    print("\nMISPAR-HAKOVETZ is xsd:length 34 EXACTLY — including the default:")
    import re
    bare = build_events_request(
        action_code="9100", customer_id_number="043417252",
        sequence=1, when=now, allow_placeholder_identity=True,
    )  # deliberately NO file_number: the fallback must be valid on its own
    fn = re.search(r"<MISPAR-HAKOVETZ>([^<]*)</MISPAR-HAKOVETZ>", bare.xml.decode()).group(1)
    check("default file number is 34 chars", len(fn) == 34, f"{len(fn)}: {fn}")
    check("a request built with no file_number still validates",
          schema.validate(etree.fromstring(bare.xml)),
          "" if schema.validate(etree.fromstring(bare.xml)) else schema.error_log[0].message[:80])

    print("\nThe environment mapping is 1=TEST / 2=PRODUCTION, per the XSD:")
    root = etree.parse(str(XSD_DIR / "events_007.xsd")).getroot()
    XS = "{http://www.w3.org/2001/XMLSchema}"
    doc_text = ""
    for el in root.iter(f"{XS}element"):
        if el.get("name") == "KOD-SVIVAT-AVODA":
            d = el.find(f".//{XS}documentation")
            doc_text = " ".join((d.text or "").split())
            break
    check("XSD documents 1 = TEST", "1 = TEST" in doc_text, doc_text[:60])
    check("XSD documents 2 = PRODUCTION", "2 = PRODUCTION" in doc_text, doc_text[:60])
    check("environment() returns 1 for the test vault", environment() == ("1", "TST"),
          str(environment()))

    print("\nEvery vendored schema compiles, and each sample matches exactly ONE:")
    # NOT XSD_DIR — importing it here would shadow the module-level constant
    # for the whole function, including the lines above this one.
    from app.services.maslaka.xsd import sug_mimshak, SCHEMA_BY_SUG_MIMSHAK
    schemas = {}
    for x in sorted(XSD_DIR.glob("*.xsd")):
        try:
            schemas[x.stem] = etree.XMLSchema(etree.parse(str(x)))
        except Exception as e:                              # noqa: BLE001
            check(f"{x.stem} compiles", False, str(e)[:60])
    check("all 18 interface schemas compile", len(schemas) == 18, f"{len(schemas)}")

    for f in sorted(SAMPLES.iterdir()):
        doc = etree.parse(str(f))
        hits = [n for n, sc in schemas.items() if sc.validate(doc)]
        # Exactly one is the real assertion: if a file validated against two
        # schemas the routing would be a coin flip.
        check(f"{f.name[:34]} matches exactly one schema", len(hits) == 1,
              ", ".join(hits) or "none")

    print("\nSUG-MIMSHAK inside the envelope routes without a filename:")
    for f in sorted(SAMPLES.glob("*FEDBK*"))[:1] + sorted(SAMPLES.glob("*CONSLT*"))[:1]:
        raw = f.read_bytes()
        sm = sug_mimshak(raw)
        check(f"{f.name[:30]} declares SUG-MIMSHAK", sm is not None, str(sm))
    check("feedback routes by envelope alone",
          SCHEMA_BY_SUG_MIMSHAK.get("20") == "feedback_009.xsd")
    check("events routes by envelope alone",
          SCHEMA_BY_SUG_MIMSHAK.get("6") == "events_007.xsd")

    print("\nThe vendor's own files validate against their published schemas:")
    fb = etree.XMLSchema(etree.parse(str(XSD_DIR / "feedback_009.xsd")))
    for f in sorted(SAMPLES.glob("*FEDBK*")):
        doc = etree.parse(str(f))
        ok = fb.validate(doc)
        check(f"{f.name[:40]} validates", ok,
              "" if ok else fb.error_log[0].message[:70])

    print()
    if FAILURES:
        print(f"{len(FAILURES)} FAILURE(S): " + "; ".join(FAILURES))
        sys.exit(1)
    print("ALL PASS")


if __name__ == "__main__":
    main()
