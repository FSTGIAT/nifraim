"""ממשק אירועים v007 — the OUTBOUND request builder.

Every request an agent sends the מסלקה rides this one interface: information
requests, POA grant/revoke, production-report subscriptions. The action is a code
inside the envelope (`KOD-EIRUA`), not a different message type.

The structure below is NOT inferred from an XSD — it is read off Swiftness's own
published sample `001000347464265EVENTS000007202412011241080003.DAT`, a real
agent→מסלקה 9101 request, and mirrors it element for element. That matters: the
previous `adapter.build_events_request` invented an `<EventsRequest>` root that
appears in no standard, and would have been rejected before anyone read it.

    Mimshak
    ├─ KoteretKovetz                       file header
    │   ├─ SUG-MIMSHAK = 6                 6 = ממשק אירועים
    │   ├─ MISPAR-GIRSAT-XML = 007
    │   ├─ TAARICH-BITZUA                  YYYYMMDDHHMMSS
    │   ├─ KOD-SVIVAT-AVODA                1 in the real production sample
    │   ├─ NetuneiGoremSholech             us
    │   └─ NetuneiGoremNimaan              the מסלקה (ח.פ 514813450)
    ├─ GufHamimshak
    │   └─ YeshutGoremPoneLemislaka
    │       └─ YeshutLakoachMeidaBsisi     the saver
    │           └─ Eirua/KodEirua/KOD-EIRUA   ← the action
    └─ ReshumatSgira                       closing counts

Nothing here sends anything; `orchestration.submit_inquiry` owns transport.
"""

from __future__ import annotations

import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import datetime

from app.config import settings

# The מסלקה's own ח.פ. — it is the נמען on everything we send.
MASLAKA_ENTITY_ID = "514813450"

SUG_MIMSHAK_EVENTS = "6"
EVENTS_VERSION = "007"


@dataclass(frozen=True)
class ActionCode:
    code: str
    label: str
    note: str
    needs_customer: bool = True


# נספח י"א. Only the codes an AGENT may send — employer-side codes (9300-9303,
# 9401-9403) need an employer authorisation form and a different direction, so
# they are listed separately where relevant.
ACTION_CODES: dict[str, ActionCode] = {
    "9100": ActionCode(
        "9100", "בקשת מידע מכל הגופים — טרום ייעוץ",
        "חד־פעמי, לפגישת הייעוץ הראשונה. התשובה חוזרת כקבצי CONSLT, אחד לכל משפחת מוצר.",
    ),
    "9101": ActionCode(
        "9101", "בקשת מידע מגוף ספציפי — טרום ייעוץ",
        "כמו 9100 אבל מיצרן אחד.",
    ),
    "9102": ActionCode(
        "9102", "איתור קרנות פנסיה לא מפקידות",
        "\"פישינג פנסיה\" — איתור כספים אבודים.",
    ),
    "9200": ActionCode(
        "9200", "בקשת מידע חד־פעמית — אחזקות",
        "לקשר קיים, לא לפגישה ראשונה. התשובה חוזרת כ-HOLDNG.",
    ),
    "9201": ActionCode(
        "9201", "בקשת מידע מתמשכת — אחזקות",
        "זה המנגנון לרענון תקופתי של לקוח, לא 9100 החד־פעמי.",
    ),
    "1700": ActionCode(
        "1700", "מתן ייפוי כוח לבעל רישיון",
        "תנאי מוקדם לכל בקשת מידע. המסמך החתום נשלח כקובץ מצורף _001.",
    ),
    "1900": ActionCode(
        "1900", "ביטול ייפוי כוח — כל המוצרים בגוף",
        "ביוזמת הסוכן.",
    ),
    "2000": ActionCode(
        "2000", "בקשת דוח פרודוקציה — חד־פעמי",
        "מיצרן מסוים. לא לפי לקוח — לפי יצרן.", needs_customer=False,
    ),
    "2100": ActionCode(
        "2100", "בקשת דוח פרודוקציה — מתמשך חודשי",
        "המנוי שממלא את הפרודוקציה החסרה של מור/מיטב/ילין/אנליסט. לפי יצרן, לא לפי לקוח.",
        needs_customer=False,
    ),
    "2500": ActionCode(
        "2500", "ביטול בקשה מתמשכת", "מבטל מנוי 2100/2101.", needs_customer=False,
    ),
}


XSI_NS = "http://www.w3.org/2001/XMLSchema-instance"


def _sub(parent: ET.Element, tag: str, text: str | None = None) -> ET.Element:
    """Add a child. An absent value is `xsi:nil="true"`, NOT an empty tag.

    The real agent-sent sample declares `xmlns:xsi` on <Mimshak> and marks every
    one of its 39 absent values `xsi:nil="true"` — it contains zero `<TAG></TAG>`
    pairs. A schema that validates nillable elements treats the two differently,
    and this is the class of mistake the מסלקה rejects before returning any
    content-level feedback.
    """
    el = ET.SubElement(parent, tag)
    if text is not None and str(text) != "":
        el.text = str(text)
    return el


def _mark_nils(elem: ET.Element) -> None:
    """Flag every empty LEAF as `xsi:nil="true"`, after the tree is complete.

    Done as a pass rather than at creation: a container is created before its
    children exist, so deciding at creation time would mark `KoteretKovetz` nil
    and then hang children off it — a contradiction no schema accepts.
    """
    for child in elem:
        _mark_nils(child)
    if len(elem) == 0 and not (elem.text or "").strip():
        elem.set("xsi:nil", "true")


class MaslakaIdentityNotConfigured(RuntimeError):
    """Raised when building a request without MASLAKA_AGENT_NUMBER / _ID.

    A regulator's vault is the wrong place to discover the deployment was never
    configured, so refuse rather than ship a placeholder.
    """


@dataclass
class EventsRequest:
    xml: bytes
    action_code: str
    customer_id: str | None
    record_reference: str


def build_events_request(
    *,
    action_code: str,
    customer_id_number: str | None = None,
    customer_first_name: str = "",
    customer_last_name: str = "",
    file_number: str | None = None,
    sequence: int = 1,
    when: datetime | None = None,
    environment_code: str | None = None,
    allow_placeholder_identity: bool = False,
) -> EventsRequest:
    """Build one ממשק אירועים v007 request.

    `allow_placeholder_identity` exists only for the preview console: it lets the
    UI render exactly what we WOULD send before Swiftness has issued our agent
    number. It must never be set on a path that transports.
    """
    action = ACTION_CODES.get(action_code)
    if action is None:
        raise ValueError(f"unknown action code {action_code!r}")

    agent_id = settings.MASLAKA_AGENT_ID
    agent_name = settings.MASLAKA_AGENT_NUMBER
    if not (agent_id and agent_name):
        if not allow_placeholder_identity:
            raise MaslakaIdentityNotConfigured(
                "MASLAKA_AGENT_NUMBER and MASLAKA_AGENT_ID must be set before a "
                "request can be built — refusing to send an unidentified request."
            )
        agent_id = agent_id or "<ת.ז. הסוכן>"
        agent_name = agent_name or "<שם הסוכן>"

    if action.needs_customer and not customer_id_number:
        raise ValueError(f"action {action_code} requires a customer id")

    now = when or datetime.now()
    # KOD-SVIVAT-AVODA: the real production sample from an agent carries "1".
    # Still worth confirming with Swiftness — sending production traffic into the
    # test environment is silent, and this is the field that decides it.
    env = environment_code or ("1" if not settings.MASLAKA_TEST_ENVIRONMENT else "2")

    root = ET.Element("Mimshak", {"xmlns:xsi": XSI_NS})

    header = _sub(root, "KoteretKovetz")
    _sub(header, "SUG-MIMSHAK", SUG_MIMSHAK_EVENTS)
    _sub(header, "MISPAR-GIRSAT-XML", EVENTS_VERSION)
    _sub(header, "TAARICH-BITZUA", now.strftime("%Y%m%d%H%M%S"))
    _sub(header, "KOD-SVIVAT-AVODA", env)
    _sub(header, "MISPAR-HAKOVETZ", file_number or now.strftime("%Y%m%d%H%M%S%f"))
    _sub(header, "MISPAR-SIDURI", str(int(sequence)).zfill(4))

    sender = _sub(header, "NetuneiGoremSholech")
    _sub(sender, "KOD-SHOLECH", "3")            # 3 = בעל רישיון
    # Must match the KIND of MISPAR-ZIHUI-SHOLECH below: 1 = ח.פ, 3 = ת"ז.
    # Nifraim is registered on the vault form under ח.פ, so "1".
    _sub(sender, "SUG-MEZAHE-SHOLECH", settings.MASLAKA_SENDER_ID_TYPE or "1")
    _sub(sender, "MISPAR-ZIHUI-SHOLECH", agent_id)
    _sub(sender, "SHEM-GOREM-SHOLECH", agent_name)
    _sub(sender, "SHEM-PRATI-ISH-KESHER-SHOLECH", settings.MASLAKA_CONTACT_FIRST_NAME)
    _sub(sender, "SHEM-MISHPACHA-ISH-KESHER-SHOLECH", settings.MASLAKA_CONTACT_LAST_NAME)
    _sub(sender, "MISPAR-TELEPHONE-KAVI-ISH-KESHER-SHOLECH", settings.MASLAKA_CONTACT_PHONE)
    _sub(sender, "E-MAIL-ISH-KESHER-SHOLECH", settings.MASLAKA_CONTACT_EMAIL)
    _sub(sender, "MISPAR-CELLULARI-ISH-KESHER-SHOLECH", settings.MASLAKA_CONTACT_MOBILE)
    _sub(sender, "MISPAR-ZIHUI-ETZEL-YATZRAN-NIMAAN")

    nimaan = _sub(header, "NetuneiGoremNimaan")
    _sub(nimaan, "KOD-NIMAAN", "2")             # 2 = המסלקה
    _sub(nimaan, "SUG-MEZAHE-NIMAAN", "1")      # 1 = ח.פ.
    _sub(nimaan, "MISPAR-ZIHUI-NIMAAN", MASLAKA_ENTITY_ID)
    _sub(nimaan, "MISPAR-ZIHUI-ETZEL-YATZRAN-NIMAAN", MASLAKA_ENTITY_ID)

    body = _sub(root, "GufHamimshak")
    pone = _sub(body, "YeshutGoremPoneLemislaka")
    for tag in (
        "SUG-PONE", "SUG-KOD-MEZAHE-PONE", "MISPAR-MEZAHE-PONE", "SHEM-GOREM-PONE",
        "MISPAR-MEZAHE-METAFEL", "SHEM-PRATI-PONE-LEMISLAKA",
        "SHEM-MISHPACHA-PONE-LEMISLAKA", "MISPAR-TELEPHONE-KAVI-PONE-LEMISLAKA",
        "E-MAIL-PONE-LEMISLAKA", "MISPAR-CELLULARI", "MISPAR-ZIHUI-PNIMI-ETZEL-YATZRAN",
    ):
        _sub(pone, tag)

    customer = _sub(pone, "YeshutLakoachMeidaBsisi")
    _sub(customer, "SUG-LAKOACH", "1")
    _sub(customer, "SUG-MEZAHE-LAKOACH", "3")   # 3 = ת.ז.
    # NINE digits, zero-PADDED — not stripped. An Israeli ת"ז is nine digits
    # including any leading zero, and `043417252` is a real one. Stripping would
    # send an 8-digit identifier for every saver whose ת"ז starts with 0 — about
    # a tenth of them — and the sample this builder was modelled on happened to
    # carry `381788223`, so the bug would not have shown until live traffic.
    # The 12-digit padding is a separate thing, and belongs to the FILENAME.
    _digits = "".join(ch for ch in (customer_id_number or "") if ch.isdigit())
    _sub(customer, "MISPAR-MEZAHE-LAKOACH", _digits.zfill(9) if _digits else "")
    _sub(customer, "SHEM-PRATI-LAKOACH", customer_first_name)
    _sub(customer, "SHEM-MISHPACHA-LAKOACH", customer_last_name)
    for tag in ("SHEM-MAASIK", "KOD-MEZAHE-MAASIK-ETZEL-YATZRAN", "KOD-MEDINA", "TAARICH-LEIDA"):
        _sub(customer, tag)

    eirua = _sub(customer, "Eirua")
    kod = _sub(eirua, "KodEirua")
    _sub(kod, "KOD-EIRUA", action.code)
    # MISPAR-MEZAHE-RESHUMA is FIXED-WIDTH 74. Every one of the 13 real EVENTS
    # samples is exactly 74 characters; an 18-char value would have come back a
    # defect. The first 14 are the timestamp in all of them — the remaining 60
    # differ per file and their internal composition is not documented in
    # anything we hold, so we fill deterministically: sender, action, sequence,
    # then zero padding. Length and uniqueness are right; the internal layout is
    # an assumption to re-check against the Events XSD when it arrives.
    record_ref = (
        now.strftime("%Y%m%d%H%M%S")                       # 14
        + "".join(ch for ch in str(agent_id) if ch.isdigit()).zfill(12)   # 12
        + action.code.zfill(4)                             # 4
        + str(int(sequence)).zfill(4)                      # 4
    ).ljust(74, "0")[:74]
    _sub(kod, "MISPAR-MEZAHE-RESHUMA", record_ref)
    # Left empty on an opening request: MISPAR-MISLAKA is the GUID the מסלקה
    # ASSIGNS, and it comes back to us on the FEDBKB. It is the correlation key
    # for the eventual answer — we never invent it.
    _sub(kod, "MISPAR-MISLAKA")
    _sub(kod, "MISPAR-MISLAKA-LPNIIYA-CHOZORET")
    _sub(kod, "OFEN-HAAVARAT-MEIDA-MIMISLLAKA-LELAKOACH", "1")
    for tag in (
        "TAARICH-NECHONUT-MEIDA", "MAANE-ACHZAKOT", "DOCH-BEINAIM",
        "MISPAR-MISLAKA-LEBITUL",
    ):
        _sub(kod, tag)
    # An ongoing request (9201, 2100) is flagged here rather than by a different code.
    ongoing = action.code in ("9201", "2100", "2101")
    _sub(kod, "BAKASHA-MITMASHECHET", "1" if ongoing else "")
    _sub(kod, "TADIRUT-BAKASHA", "1" if ongoing else "")
    for tag in ("HAZHARAT-MAASIK-H-P-KASUR", "ISUR-OVED-PIZUIM"):
        _sub(kod, tag)
    _sub(kod, "RIANUN-FISHING", "1" if action.code == "9102" else "2")

    closing = _sub(root, "ReshumatSgira")
    _sub(closing, "MISPAR-YESHUYUT-LAKOACH-BAKOVETZ", "1" if action.needs_customer else "0")
    _sub(closing, "MISPAR-BAKASHOT", "1")

    # The real file is indented two spaces; match it so a byte-level diff against
    # the vendor sample stays readable.
    _mark_nils(root)
    ET.indent(root, space="  ")
    xml = (b'<?xml version="1.0" encoding="utf-8"?>\n'
           + ET.tostring(root, encoding="utf-8"))
    return EventsRequest(
        xml=xml,
        action_code=action.code,
        customer_id=customer_id_number,
        record_reference=record_ref,
    )


# ─── One source of truth for test-vs-production ─────────────────────────────
def environment() -> tuple[str, str]:
    """`(KOD-SVIVAT-AVODA, filename suffix)` — always derived together.

    These two must agree. On 2026-09-10 we sent the TST vault a file named
    `…0001.DAT` (ייצור) whose payload said `KOD-SVIVAT-AVODA=2` (בדיקות),
    because the filename suffix and the environment code were computed in two
    different places from two different expressions. Nothing rejected it and
    nothing answered it. Derive both here or not at all.
    """
    return ("2", "TST") if settings.MASLAKA_TEST_ENVIRONMENT else ("1", "DAT")


def build_file_number(*, sender_id: str, sequence: int, when: datetime) -> str:
    """`MISPAR-HAKOVETZ` in the shape Swiftness's own files use.

    Verified against all 12 vendor samples: `YYYYMMDDHHMMSS` + sender left-padded
    to 16 + the 4-digit daily sequence. NOTE this is house style, not a validated
    rule — three FEDBKB samples echo a *sender-chosen* value that does not derive
    from the filename at all, which proves the מסלקה accepts and answers a file
    whose MISPAR-HAKOVETZ disagrees with its name. Matching the shape is hygiene.
    """
    digits = "".join(ch for ch in str(sender_id) if ch.isdigit()) or "0"
    return f"{when.strftime('%Y%m%d%H%M%S')}{digits.zfill(16)}{str(int(sequence)).zfill(4)}"
