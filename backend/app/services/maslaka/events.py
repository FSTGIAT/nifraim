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
    │   ├─ KOD-SVIVAT-AVODA                1 = TEST, 2 = PRODUCTION (per the XSD)
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

import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import datetime
from zoneinfo import ZoneInfo

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


# "דוחות פרודוקציה מיצרן ספציפי" — each needs the יצרן in NetuneiMutzar.
# (2500, the cancel, names the subscription by MISPAR-MISLAKA-LEBITUL instead.)
PRODUCTION_REPORT_CODES = frozenset({"2000", "2100"})

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


def _mark_nils(elem: ET.Element, exempt: set[int] | None = None) -> None:
    """Flag every empty LEAF as `xsi:nil="true"`, after the tree is complete.

    Done as a pass rather than at creation: a container is created before its
    children exist, so deciding at creation time would mark `KoteretKovetz` nil
    and then hang children off it — a contradiction no schema accepts.
    """
    exempt = exempt or set()
    for child in elem:
        _mark_nils(child, exempt)
    if id(elem) in exempt:
        # minOccurs=1 but NOT nillable, with all children optional: the element
        # must be PRESENT and EMPTY. Marking it nil makes the file invalid.
        return
    if len(elem) == 0 and not (elem.text or "").strip():
        elem.set("xsi:nil", "true")


# 9-digit Israeli landline: 0 + area code 2/3/4/8/9 + 7 digits (spec example
# 031234567; Swiftness's own header carries 037706000).
LANDLINE_RE = re.compile(r"0[23489][0-9]{7}")


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
    acting_agent_id: str | None = None,
    acting_agent_name: str | None = None,
    yatzran_id: str | None = None,
    information_date: str | None = None,
    consent_customer_signed: str | None = None,
    consent_agent_signed: str | None = None,
    sender_is_agent: bool = False,
    internal_agent_number: str | None = None,
    agent_id_type: str | None = None,
    agent_id_value: str | None = None,
) -> EventsRequest:
    """Build one ממשק אירועים v007 request.

    `allow_placeholder_identity` exists only for the preview console: it lets the
    UI render exactly what we WOULD send before Swiftness has issued our agent
    number. It must never be set on a path that transports.

    The SENDER is always Nifraim (the בית תוכנה, global settings). The agent the
    request is made FOR — `acting_agent_id` / `_name`, their ת"ז — rides in
    `YeshutGoremPoneLemislaka`. Without it the מסלקה sees a request from
    Nifraim on behalf of nobody, and cannot tie it to an agent it has linked.

    `yatzran_id` is the institutional body's ח.פ (`KOD-MEZAHE-YATZRAN`). A
    production report (2000/2100) is "מיצרן ספציפי" — one body per request —
    so it is mandatory there.
    """
    action = ACTION_CODES.get(action_code)
    if action is None:
        raise ValueError(f"unknown action code {action_code!r}")

    _agent_digits = "".join(ch for ch in (acting_agent_id or "") if ch.isdigit())
    _yatzran = "".join(ch for ch in (yatzran_id or "") if ch.isdigit())
    if action.code in PRODUCTION_REPORT_CODES and not _yatzran:
        raise ValueError(
            f"action {action.code} ({action.label}) is a production report from ONE "
            "specific יצרן — pass yatzran_id (the body's ח.פ). A request naming no "
            "יצרן is technically acked and can never return a report."
        )
    # TAARICH-NECHONUT-MEIDA (YYYYMMDD). The field spec allows it on production
    # requests but documents it only for 9300-series; sending 20260831 on a 2000
    # is a deliberate probe for "can a past month be requested" (2026-09-25).
    if information_date is not None:
        from datetime import datetime as _dt
        _dt.strptime(information_date, "%Y%m%d")        # raises on a bad date
    if _yatzran and len(_yatzran) > 9:
        raise ValueError(f"yatzran_id must be a ח.פ of up to 9 digits, got {yatzran_id!r}")

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

    # Production requests (2000-2500): the "customer" block describes the מפיץ
    # itself. Settled by the Events v007 FIELD SPEC (event_interface_v7-6-30.xlsx,
    # SUG-LAKOACH): "ערך 3 ישמש עבור פעולות 2000, 2001, 2100 … 2500", and
    # SHEM-MAASIK carries "במקרה של בקשות פרודוקציה את שם המפיץ". So the
    # identity here is the acting AGENT's — never Nifraim's ח.פ, never the
    # יצרן's. No agent → refuse: a production report for nobody is useless and
    # one for the wrong agent is someone else's book.
    distributor_request = not action.needs_customer
    # Production as the LICENSEE itself (see orchestration.submit_inquiry): the
    # agent is sender AND subject — rules 118 (sender = filename ID), 144
    # (subject = sender) and 128 (a ת"ז subject carries both names) together.
    agent_sender = bool(sender_is_agent and distributor_request and _agent_digits)
    # Identity override for the AGENT (sender = requester = subject in agent-sender
    # mode): e.g. type 12 "מספר בעל רישיון" instead of 3 ת"ז — the XSD allows it on
    # all three, and rule 144 needs type AND number equal, so they move together.
    _ag_type = (agent_id_type or "3").strip()
    _ag_val = ("".join(ch for ch in (agent_id_value or "") if ch.isalnum())
               or (_agent_digits.zfill(9) if _agent_digits else ""))
    _first, _, _last = (acting_agent_name or "").strip().partition(" ")
    if agent_sender and not (_first and _last.strip()):
        raise ValueError(f"agent-as-sender needs the agent's first AND last name "
                         f"(rule 128) — got {acting_agent_name!r}")
    if distributor_request:
        if not customer_id_number:
            customer_id_number = acting_agent_id
        if not customer_id_number:
            raise ValueError(
                f"action {action.code} ({action.label}) requires an identifier in "
                "MISPAR-MEZAHE-LAKOACH — for a production request that is the "
                "acting agent (מפיץ). Pass acting_agent_id."
            )
    if action.needs_customer and not customer_id_number:
        raise ValueError(f"action {action_code} requires a customer id")

    now = when or datetime.now()
    # KOD-SVIVAT-AVODA: **1 = TEST, 2 = PRODUCTION**, per the XSD's own
    # <xsd:documentation>. This fallback used to carry the INVERTED mapping —
    # the same inversion that made four live sends unanswerable on 2026-09-10.
    # It survived the fix because `environment()` was corrected and this third
    # copy was not, and every production caller passes `environment_code`
    # explicitly, so no test ever exercised it. Defer to the one helper instead
    # of restating the rule: a rule written down twice is a rule that goes wrong.
    env = environment_code or environment()[0]

    root = ET.Element("Mimshak", {"xmlns:xsi": XSI_NS})

    header = _sub(root, "KoteretKovetz")
    _sub(header, "SUG-MIMSHAK", SUG_MIMSHAK_EVENTS)
    _sub(header, "MISPAR-GIRSAT-XML", EVENTS_VERSION)
    _sub(header, "TAARICH-BITZUA", now.strftime("%Y%m%d%H%M%S"))
    _sub(header, "KOD-SVIVAT-AVODA", env)
    # xsd:length is 34 EXACTLY — not maxLength. The old fallback
    # (`%Y%m%d%H%M%S%f`) is 20 chars and made every request built without an
    # explicit file_number schema-invalid. Default to the real shape instead:
    # a bad default is worse than a missing argument, because it looks fine.
    _sender_for_file_no = _agent_digits if agent_sender else ("".join(
        ch for ch in str(settings.MASLAKA_AGENT_ID or "") if ch.isdigit()
    ) or "0")
    file_number = file_number or build_file_number(
        sender_id=_sender_for_file_no, sequence=sequence, when=now,
    )
    _sub(header, "MISPAR-HAKOVETZ", file_number)
    _sub(header, "MISPAR-SIDURI", str(int(sequence)).zfill(4))

    sender = _sub(header, "NetuneiGoremSholech")
    _sub(sender, "KOD-SHOLECH", "3")            # 3 = בעל רישיון
    # Must match the KIND of MISPAR-ZIHUI-SHOLECH below: 1 = ח.פ, 3 = ת"ז.
    # Nifraim is registered on the vault form under ח.פ, so "1".
    # The sender is ALWAYS the vault owner (Nifraim). Rule 118 — "מספר זיהוי גורם
    # שולח לא זהה למספר זהוי בשם הקובץ/למספר זיהוי הלקוח שטען את הקובץ" —
    # rejected seq 0034, which put the acting agent's ת"ז here.
    # With agent_sender the file is named for the agent too, which rule 118 accepts.
    if agent_sender:
        _sub(sender, "SUG-MEZAHE-SHOLECH", _ag_type)  # 3 = ת"ז (default), 12 = licence
        _sub(sender, "MISPAR-ZIHUI-SHOLECH", _ag_val)
        _sub(sender, "SHEM-GOREM-SHOLECH", acting_agent_name.strip())
    else:
        _sub(sender, "SUG-MEZAHE-SHOLECH", settings.MASLAKA_SENDER_ID_TYPE or "1")
        _sub(sender, "MISPAR-ZIHUI-SHOLECH", agent_id)
        _sub(sender, "SHEM-GOREM-SHOLECH", agent_name)
    _sub(sender, "SHEM-PRATI-ISH-KESHER-SHOLECH", settings.MASLAKA_CONTACT_FIRST_NAME)
    _sub(sender, "SHEM-MISHPACHA-ISH-KESHER-SHOLECH", settings.MASLAKA_CONTACT_LAST_NAME)
    # MISPAR-TELEPHONE-KAVI-ISH-KESHER-SHOLECH and E-MAIL are NOT nillable. The
    # Gateway's .env lacked them, so 43 of 43 files (09-10 → 09-25) went out nil
    # and came back KOD-SHGIHA=3 — while the dev box, whose .env has them, passed.
    # The landline must be a real LANDLINE: the XSD only says [0-9]+, but the
    # מסלקה's validation rule 116 rejects a mobile in it ("בפורמט לא תקין",
    # measured 2026-09-25 with 0508882597). Field spec example: 031234567 — a
    # 9-digit 0X number. So no mobile fallback: refuse rather than send a file
    # we know they reject.
    _landline = "".join(ch for ch in (settings.MASLAKA_CONTACT_PHONE or "") if ch.isdigit())
    if not LANDLINE_RE.fullmatch(_landline) or not (settings.MASLAKA_CONTACT_EMAIL or "").strip():
        if not allow_placeholder_identity:
            raise MaslakaIdentityNotConfigured(
                "MASLAKA_CONTACT_PHONE must be a real 9-digit landline (e.g. 031234567 — a "
                "mobile fails the מסלקה's rule 116) and MASLAKA_CONTACT_EMAIL must be set on "
                f"the host that builds the file (got phone={_landline!r})."
            )
    _sub(sender, "MISPAR-TELEPHONE-KAVI-ISH-KESHER-SHOLECH", _landline)
    _sub(sender, "E-MAIL-ISH-KESHER-SHOLECH", settings.MASLAKA_CONTACT_EMAIL)
    _sub(sender, "MISPAR-CELLULARI-ISH-KESHER-SHOLECH", settings.MASLAKA_CONTACT_MOBILE)
    # "מספר סוכן פנימי בגוף מוסדי — רלוונטי במקרים בהם האירוע מועבר על ידי בעל
    # רישיון לגוף מוסדי שלו יש הסכם עמו" (field spec, marked for production).
    # Without it Phoenix answered 1032 "לא קיים הסכם עמלות" for the agent's ת"ז.
    _internal = "".join(ch for ch in (internal_agent_number or "") if ch.isalnum()) or None
    _sub(sender, "MISPAR-ZIHUI-ETZEL-YATZRAN-NIMAAN", _internal)

    nimaan = _sub(header, "NetuneiGoremNimaan")
    _sub(nimaan, "KOD-NIMAAN", "2")             # 2 = המסלקה
    _sub(nimaan, "SUG-MEZAHE-NIMAAN", "1")      # 1 = ח.פ.
    _sub(nimaan, "MISPAR-ZIHUI-NIMAAN", MASLAKA_ENTITY_ID)
    _sub(nimaan, "MISPAR-ZIHUI-ETZEL-YATZRAN-NIMAAN", MASLAKA_ENTITY_ID)

    body = _sub(root, "GufHamimshak")
    pone = _sub(body, "YeshutGoremPoneLemislaka")
    # The acting agent. SUG-PONE 3 = מפיץ, SUG-KOD-MEZAHE-PONE 3 = ת.ז. Nil when
    # no agent is given (the preview console), which is what every send before
    # 2026-09-25 carried.
    _sub(pone, "SUG-PONE", "3" if _agent_digits else None)
    _sub(pone, "SUG-KOD-MEZAHE-PONE", (_ag_type if agent_sender else "3") if _agent_digits else None)
    _sub(pone, "MISPAR-MEZAHE-PONE", (_ag_val if agent_sender else _agent_digits.zfill(9)) if _agent_digits else None)
    _sub(pone, "SHEM-GOREM-PONE", (acting_agent_name or "").strip() or None)
    for tag in (
        "MISPAR-MEZAHE-METAFEL", "SHEM-PRATI-PONE-LEMISLAKA",
        "SHEM-MISHPACHA-PONE-LEMISLAKA", "MISPAR-TELEPHONE-KAVI-PONE-LEMISLAKA",
        "E-MAIL-PONE-LEMISLAKA", "MISPAR-CELLULARI",
    ):
        _sub(pone, tag)
    _sub(pone, "MISPAR-ZIHUI-PNIMI-ETZEL-YATZRAN", _internal)

    customer = _sub(pone, "YeshutLakoachMeidaBsisi")
    # 1 = עמית/מבוטח; 3 = מפיץ, the spec's value for every production request.
    _sub(customer, "SUG-LAKOACH", "3" if distributor_request else "1")
    # Rule 144 — "בבקשת פרודוקציה סוג מזהה לקוח ומספר מזהה לקוח צריך להיות זהה
    # לסוג מזהה שולח ומספר מזהה שולח" (seq 0033) — and rule 118 pins the sender
    # to the vault owner (seq 0034). So a production request's subject is
    # Nifraim's own ח.פ; the agent whose book it is rides in
    # YeshutGoremPoneLemislaka above. A ח.פ subject needs no personal names
    # (rule 128 applies only to a ת"ז subject).
    _sub(customer, "SUG-MEZAHE-LAKOACH",
         (settings.MASLAKA_SENDER_ID_TYPE or "1") if (distributor_request and not agent_sender)
         else (_ag_type if agent_sender else "3"))
    # NINE digits, zero-PADDED — not stripped. An Israeli ת"ז is nine digits
    # including any leading zero, and `043417252` is a real one. Stripping would
    # send an 8-digit identifier for every saver whose ת"ז starts with 0 — about
    # a tenth of them — and the sample this builder was modelled on happened to
    # carry `381788223`, so the bug would not have shown until live traffic.
    # The 12-digit padding is a separate thing, and belongs to the FILENAME.
    if distributor_request:
        customer_id_number = _agent_digits if agent_sender else "".join(
            ch for ch in str(agent_id) if ch.isdigit())
    _digits = "".join(ch for ch in (customer_id_number or "") if ch.isdigit())
    _sub(customer, "MISPAR-MEZAHE-LAKOACH",
         _ag_val if agent_sender else (_digits.zfill(9) if _digits else ""))
    if agent_sender:
        _sub(customer, "SHEM-PRATI-LAKOACH", _first[:20])
        _sub(customer, "SHEM-MISHPACHA-LAKOACH", _last.strip()[:30])
    else:
        _sub(customer, "SHEM-PRATI-LAKOACH", None if distributor_request else customer_first_name)
        _sub(customer, "SHEM-MISHPACHA-LAKOACH", None if distributor_request else customer_last_name)
    # SHEM-MAASIK is mandatory for SUG-LAKOACH 3: "את שם המפיץ".
    _sub(customer, "SHEM-MAASIK",
         ((acting_agent_name or "").strip() or None) if distributor_request else None)
    for tag in ("KOD-MEZAHE-MAASIK-ETZEL-YATZRAN", "KOD-MEDINA", "TAARICH-LEIDA"):
        _sub(customer, tag)

    eirua = _sub(customer, "Eirua")
    kod = _sub(eirua, "KodEirua")
    _sub(kod, "KOD-EIRUA", action.code)
    # MISPAR-MEZAHE-RESHUMA is 74 chars, and its layout IS documented — in the
    # Events v007 field spec (event_interface_v7-6-30.xlsx), not the XSD:
    #   מספר הקובץ (34) · מס' מזהה לקוח, 16 עם אפסים מובילים ·
    #   מס' מזהה עובד, 16 (אפסים — only 9301/3 on an employer's behalf) ·
    #   קוד אירוע (4) · נומרטור (4)
    # Until 2026-09-25 we filled it with timestamp+sender+padding — right length,
    # wrong content — and the technical ack (FEDBKA) did not object. Follow the
    # spec anyway: this is the key a content answer is correlated on.
    record_ref = (
        str(file_number)[:34].ljust(34, "0")
        + "".join(ch for ch in (customer_id_number or "") if ch.isdigit()).zfill(16)[-16:]
        + "0" * 16
        + action.code.zfill(4)
        + str(int(sequence)).zfill(4)[-4:]
    )
    _sub(kod, "MISPAR-MEZAHE-RESHUMA", record_ref)
    # Left empty on an opening request: MISPAR-MISLAKA is the GUID the מסלקה
    # ASSIGNS, and it comes back to us on the FEDBKB. It is the correlation key
    # for the eventual answer — we never invent it.
    _sub(kod, "MISPAR-MISLAKA")
    _sub(kod, "MISPAR-MISLAKA-LPNIIYA-CHOZORET")
    _sub(kod, "OFEN-HAAVARAT-MEIDA-MIMISLLAKA-LELAKOACH", "1")
    _sub(kod, "TAARICH-NECHONUT-MEIDA", information_date)
    for tag in ("MAANE-ACHZAKOT", "DOCH-BEINAIM", "MISPAR-MISLAKA-LEBITUL"):
        _sub(kod, tag)
    # BAKASHA-MITMASHECHET: **1 = חד"פ, 2 = מתמשכת**, and per the field spec it
    # is "שדה חובה בבקשות 9100/1, 9300/2. השדה אינו רלוונטי בבקשות אחרות" — and a
    # מפיץ may NOT file an ongoing 9100/1. This used to send "1" for the ONGOING
    # codes (9201/2100), i.e. the opposite meaning, and nil for 9100 where it is
    # mandatory. Frequency is carried by the code itself for 2100/2200/…, so
    # TADIRUT-BAKASHA (only for ongoing 9100/1 / 9300/2) stays nil.
    _sub(kod, "BAKASHA-MITMASHECHET", "1" if action.code in ("9100", "9101") else None)
    _sub(kod, "TADIRUT-BAKASHA")
    for tag in ("HAZHARAT-MAASIK-H-P-KASUR", "ISUR-OVED-PIZUIM"):
        _sub(kod, tag)
    _sub(kod, "RIANUN-FISHING", "1" if action.code == "9102" else "2")
    # The XSD sequence does not end at RIANUN-FISHING. These five are all
    # minOccurs=1 (nillable) and the file is INVALID without them — omitting
    # them is what made our first four live sends fail validation.
    for tag in (
        "KOD-ZIHUI-OVED-BAMISLAKA", "ZIHUI-HOSHECH-BAMISLAKA",
        "NITAN-LEYADEA-BAAL-RISHAYON", "ASMACHTA-MISLAKA", "RESERVA-MISLAKA",
    ):
        _sub(kod, tag)
    # YipuiKoach and mismachim are minOccurs=1 and NOT nillable, but every child
    # is minOccurs=0 — so an EMPTY container is valid and a missing one is not.
    # They must be excluded from _mark_nils for exactly that reason.
    yipui = _sub(kod, "YipuiKoach")
    _nil_exempt = (yipui, _sub(kod, "mismachim"))
    # 9100/9101 are "טרום ייעוץ (נספח א' לחוזר ייפוי כח)": the field spec makes
    # BakashatMefitzLeinianYipuiKoach mandatory for them, and BOTH signature
    # dates mandatory "גם אם לא צורף מסמך". SUG-BAKASHAT 1 = one-off נספח א';
    # with 1, SUG-/MISPAR-RISHAYON must NOT be sent. We attach nothing
    # (TZURAF 2, MISMACH-ZIHUI 2, ATAR-MEUVTACH 2). The dates are a declaration
    # to a regulator — they come from the signed form, never from "today".
    if action.code in ("9100", "9101") and not allow_placeholder_identity:
        for _lbl, _d in (("consent_customer_signed", consent_customer_signed),
                         ("consent_agent_signed", consent_agent_signed)):
            if not _d:
                raise ValueError(
                    f"action {action.code} needs the נספח א' signature dates "
                    f"({_lbl}, YYYYMMDD) from the signed form")
            datetime.strptime(_d, "%Y%m%d")
    if action.code in ("9100", "9101") and consent_customer_signed and consent_agent_signed:
        bm = _sub(yipui, "BakashatMefitzLeinianYipuiKoach")
        _sub(bm, "TZURAF-MISMACH-YIPUI-KOACH", "2")
        _sub(bm, "KOD-ZIHUI-YIPUI-KOACH-BEMISLAKA")
        _sub(bm, "MISMACH-ZIHUI", "2")
        _sub(bm, "SUG-BAKASHAT-MEFITZ-LEEINIAN-YIPUI-KOACH", "1")
        _sub(bm, "KAYAM-MUTZAR-MUCHRAG")
        _sub(bm, "TAARICH-CHTIMA-LAKOACH", consent_customer_signed)
        _sub(bm, "TAARICH-CHTIMA-BAAL-RISHAION", consent_agent_signed)
        for tag in ("TOKEF-YIPUI-KOACH", "MOED-PKIHA", "HARSHAA-LEMASHKANTA"):
            _sub(bm, tag)
        _sub(bm, "ATAR-MEUVTACH", "2")
        for tag in ("ERETZ", "SHEM-YISHUV", "SEMEL-YESHUV", "SHEM-RECHOV", "MISPAR-BAIT",
                    "MISPAR-KNISA", "MISPAR-DIRA", "MIKUD", "TA-DOAR", "NISPACH-D",
                    "BITUL-ARSHAA", "SUG-RISHAYON", "MISPAR-RISHAYON",
                    "MISPAR-SOHEN-PNIMI-ETZEL-MOSDI"):
            _sub(bm, tag)

    # Mutzar/NetuneiMutzar names the יצרן. The field spec: "בבלוק זה יוגדר קוד
    # מזהה של היצרן" — NOT sent for 9100/9102 (all bodies) or 2500 (cancel).
    # For a production report KOD-MEZAHE-YATZRAN is its only field; the XSD
    # still wants SUG-MUTZAR-PENSIONI present (nillable).
    if _yatzran:
        netunei = _sub(_sub(kod, "Mutzar"), "NetuneiMutzar")
        _sub(netunei, "KOD-MEZAHE-YATZRAN", _yatzran.zfill(9))
        _sub(netunei, "SUG-MUTZAR-PENSIONI")

    closing = _sub(root, "ReshumatSgira")
    # One YeshutLakoachMeidaBsisi block per file, whether it describes a saver
    # or (for production requests) the מפיץ.
    _sub(closing, "MISPAR-YESHUYUT-LAKOACH-BAKOVETZ", "1")
    _sub(closing, "MISPAR-BAKASHOT", "1")

    # The real file is indented two spaces; match it so a byte-level diff against
    # the vendor sample stays readable.
    _mark_nils(root, exempt=set(id(e) for e in _nil_exempt))
    ET.indent(root, space="  ")
    xml = (b'<?xml version="1.0" encoding="utf-8"?>\n'
           + ET.tostring(root, encoding="utf-8"))
    return EventsRequest(
        xml=xml,
        action_code=action.code,
        customer_id=customer_id_number,
        record_reference=record_ref,
    )


# ─── The wire clock is Israel local time, ALWAYS ────────────────────────────
# Re-exported from `filenames`, NOT redefined. The payload stamp and the
# filename stamp must be the same instant, and the surest way to guarantee that
# is for there to be only one function. Two copies of this rule is how the
# 2026-09-22 filename bug happened (UTC name over an Israel-time payload), and
# three copies of the environment rule is how the 09-10 sends went out inverted.
from app.services.maslaka.filenames import ISRAEL_TZ, maslaka_now  # noqa: E402,F401


# ─── One source of truth for test-vs-production ─────────────────────────────
def environment() -> tuple[str, str]:
    """`(KOD-SVIVAT-AVODA, filename suffix)` — always derived together.

    **KOD-SVIVAT-AVODA is 1 = TEST, 2 = PRODUCTION.** This is the reverse of
    what this code assumed until 2026-09-10, and the inversion is why three
    live sends went unanswered: all three carried `2` (PRODUCTION) into the
    TEST vault. Two independent sources agree — Swiftness's published XSD says
    so in its own `<xsd:documentation>`, and all 12 vendor sample files are
    `.DAT` (ייצור) carrying `2`.

    The suffix and the code must also AGREE with each other, which is why they
    are returned together: a `.TST` name over a `2` payload is a test file with
    a production flag.
    """
    return ("1", "TST") if settings.MASLAKA_TEST_ENVIRONMENT else ("2", "DAT")


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
