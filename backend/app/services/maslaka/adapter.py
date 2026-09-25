"""XML adapter — THE ONLY XSD-DEPENDENT MODULE.

When the Swiftness schemas land, every `# TODO(XSD):` in this file gets
filled in. Everything else in `services/maslaka/` (transport, orchestration,
audit, persistence, scheduler) is finished and does not depend on knowing
the real XSD layout — until the inquiry/holdings XPaths are known we use
the stub layout that matches `backend/tests/fixtures/maslaka/*.xml`.

Stdlib `xml.etree.ElementTree` (consistent with `services/mimshak/parse_dat.py`)
— no lxml. Keep it that way unless we hit a real XPath/perf wall.
"""

from __future__ import annotations

import logging
import uuid
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Iterable

from app.config import settings

logger = logging.getLogger(__name__)


class MaslakaIdentityNotConfigured(RuntimeError):
    """Raised when an outbound request is built without MASLAKA_AGENT_NUMBER /
    MASLAKA_AGENT_ID. Fail loudly here rather than ship an unidentified — or
    worse, a placeholder-stamped — request into the clearinghouse vault."""


# ─── Dataclasses returned from the parse functions ─────────────────────────
@dataclass
class HoldingItem:
    """One product row, ready to map to the PensionHolding ORM model.

    Field names match `PensionHolding` columns so the orchestrator can
    splat the dict straight into the model: `PensionHolding(**item.to_dict())`.
    """
    customer_id_number: str
    provider_code: str | None = None
    receiving_company: str | None = None
    product: str | None = None
    product_type: str | None = None
    fund_policy_number: str | None = None
    track: str | None = None
    accumulation: float | None = None
    total_premium: float | None = None
    management_fee_deposit: float | None = None
    management_fee_balance: float | None = None
    expected_pension: float | None = None
    insurance_coverage: str | None = None  # JSON-encoded list of {coverage_name, sum_assured, premium, ...}
    status_date: date | None = None

    def to_dict(self) -> dict:
        return {k: v for k, v in self.__dict__.items()}


@dataclass
class FeedbackResult:
    """Outcome of a Feedback v009 message — ack or defect.

    `acked_filename` (`SHEM-HAKOVETZ`) is the REAL correlation key: the מסלקה
    echoes the name of the file it is answering. There is no `RequestReference`
    on the wire — that was our stub's invention. `request_reference` is kept
    only so the old fixtures still parse.

    `mislaka_number` (`MISPAR-MISLAKA`) is the GUID the מסלקה gave the request;
    the insurers' data files carry it, so it is how an answer finds its request.

    `sug_mashov` is 1 = משוב א' (technical receipt) or 2 = משוב ב' (content).
    A משוב א' ack means "the file is well-formed and accepted", NOT "here is
    your data" — the data arrives later as משוב ב' or a holdings file.
    """
    request_reference: str
    is_ack: bool
    providers_expected: int | None = None
    error_code: str | None = None
    error_detail: str | None = None
    acked_filename: str | None = None
    mislaka_number: str | None = None
    sug_mashov: str | None = None
    # משוב ב' — the INSURER's content answer: MaaneMiYazran/MAANE-BERAMAT-RESHUMA
    # (e.g. 1032 "לא ניתן לספק דוח פרודוקציה עבור המפיץ הפונה") + its PERUT text.
    maane_code: str | None = None
    maane_detail: str | None = None
    extras: dict[str, str] = field(default_factory=dict)


# ─── Inbound classifier ────────────────────────────────────────────────────
def classify_inbound(xml_bytes: bytes) -> str:
    """Return 'holdings' | 'feedback' | 'unknown' for an inbound XML.

    Used by the poll loop to route each `/inbox` file to the right parser
    without us having to encode interface info in the filename.
    """
    try:
        root = ET.fromstring(xml_bytes)
    except ET.ParseError as e:
        logger.warning("maslaka.adapter.classify_inbound: parse error: %s", e)
        return "unknown"

    # `SUG-MIMSHAK` inside the envelope is authoritative. Every real מסלקה file
    # has root <Mimshak> — routing on the root tag (our stub looked for
    # <Feedback>/<Holdings>, names we invented) classified all 12 of the first
    # real FEDBKA acks as "unknown" on 2026-09-24 and left them in the inbox.
    from app.services.maslaka.xsd import sug_mimshak

    sm = sug_mimshak(xml_bytes)
    if sm == "20":
        return "feedback"
    if sm in ("1", "2", "3"):        # the four holdings / טרום-ייעוץ families
        return "holdings"

    # Legacy stub fixtures (tests/fixtures/maslaka/*.xml) predate the real
    # schema; keep them parsing so the fixture suite still means something.
    tag = _local_tag(root.tag).lower()
    if tag == "feedback":
        return "feedback"
    if tag == "holdings":
        return "holdings"
    return "unknown"


# ─── Outbound builder ──────────────────────────────────────────────────────
def build_events_request(
    customer_id_number: str,
    *,
    request_reference: str | None = None,
) -> tuple[bytes, str]:
    """Build an Events v007 בקשת מידע (information-request) XML.

    Returns `(xml_bytes, request_reference)` — the reference is also embedded
    inside the XML so feedback/holdings responses can be matched back.

    TODO(XSD): rebuild the tree to match Events v007 exactly:
      - Root element + namespace declarations
      - Required identity nodes: agent number, agent ID, sender code, message GUID
      - Customer ID node (with the leading-zero convention the schema expects)
      - Request-type code for "בקשת מידע" (likely "01" or similar)
      - Timestamp node, version node
    The stub below is what the LocalVaultTransport mock writes today — kept
    minimal so the test fixtures echo it back believably.
    """
    if request_reference is None:
        request_reference = uuid.uuid4().hex

    # Our identity is what the clearinghouse authorises the request against.
    # Unset, the tree below used to emit a literal "TODO(XSD)" — and did, into
    # a real outbox file. A regulator's vault is the wrong place to discover
    # that the deployment was never configured, so refuse to build the request.
    if not settings.MASLAKA_AGENT_NUMBER or not settings.MASLAKA_AGENT_ID:
        raise MaslakaIdentityNotConfigured(
            "MASLAKA_AGENT_NUMBER and MASLAKA_AGENT_ID must be set before an "
            "inquiry can be built — refusing to send an unidentified request."
        )

    customer_id_normalized = (customer_id_number or "").lstrip("0") or "0"

    root = ET.Element("EventsRequest", attrib={"version": "v007"})
    ET.SubElement(root, "RequestReference").text = request_reference
    ET.SubElement(root, "Timestamp").text = datetime.utcnow().isoformat()
    ET.SubElement(root, "AgentNumber").text = settings.MASLAKA_AGENT_NUMBER
    ET.SubElement(root, "AgentId").text = settings.MASLAKA_AGENT_ID
    ET.SubElement(root, "CustomerIdNumber").text = customer_id_normalized
    ET.SubElement(root, "RequestType").text = "INFO"  # TODO(XSD): real code

    xml_bytes = ET.tostring(root, encoding="utf-8", xml_declaration=True)
    return xml_bytes, request_reference


# ─── Inbound parsers ───────────────────────────────────────────────────────
# feedback_009.xsd KOD-SHGIHA: 15 = valid file received, 5 = receipt of an
# error notice. Every other file-level code is a rejection.
FILE_LEVEL_OK_CODES = frozenset({"5", "15"})


def parse_feedback(xml_bytes: bytes) -> FeedbackResult:
    """Parse a Feedback v009 message.

    TODO(XSD): replace XPaths with real Feedback v009 element paths:
      - Echoed request reference
      - Status/result code (ack vs defect)
      - Error code + description on defect
      - providers_expected count
    """
    root = ET.fromstring(xml_bytes)

    # ── The real wire format (feedback_009.xsd + 43 live FEDBKA files) ───────
    #   SHEM-HAKOVETZ  echoes the filename being answered  ← the correlation key
    #   SUG-MASHOV     1 = משוב א' (technical) · 2 = משוב ב' (content)
    #   RAMAT-MASHOV   1 = file level · 2 = record level
    # File-level verdict: MashovBeramatKovetz/KOD-SHGIHA + one or more
    #   PerutShgihaBeramatKovetz/PERUT-SHGIHA-BERAMAT-KOVETZ.
    # Record-level: KOD-SHGIHA-BERAMAT-RESHUMA (+ PERUT-SHGIHA-BERAMAT-RESHUMA).
    #
    # There is NO `KOD-SHGIHA-BERAMAT-KOVETZ` and NO `TEUR-SHGIHA` in the schema.
    # Reading those names made every rejection (KOD-SHGIHA=3, "מבנה XML לא
    # חוקי") look like a clean ack — 43 of 43 files, 09-10 → 09-25 — while
    # nothing could ever come back. Read the tags the XSD actually defines.
    acked_filename = _text_of(root, "SHEM-HAKOVETZ") or None
    sug_mashov = _text_of(root, "SUG-MASHOV") or None

    err_file = None
    file_details: list[str] = []
    for e in root.iter():
        if _local_tag(e.tag) == "MashovBeramatKovetz":
            code = (_text_of(e, "KOD-SHGIHA") or "").strip()
            # 15 = "אישור קבלת קובץ תקין", 5 = "אישור על קבלת הודעת שגיאה" —
            # the two file-level codes that are receipts, not defects.
            if code and code not in FILE_LEVEL_OK_CODES:
                err_file = code
            file_details += [
                (d.text or "").strip() for d in e.iter()
                if _local_tag(d.tag) == "PERUT-SHGIHA-BERAMAT-KOVETZ" and (d.text or "").strip()
            ]
    err_rec = (_text_of(root, "KOD-SHGIHA-BERAMAT-RESHUMA") or "").strip()
    error_code = err_file or err_rec or None
    rec_detail = (
        _text_of(root, "PERUT-SHGIHA-BERAMAT-RESHUMA") or _text_of(root, "PERUT-SHGIHA") or ""
    ).strip()
    error_detail = " | ".join(dict.fromkeys(file_details + ([rec_detail] if rec_detail else []))) or None

    providers_raw = _text_of(root, "KAMUT-RESHUMOT-TKINOT")
    providers_expected = int(providers_raw) if (providers_raw or "").strip().isdigit() else None

    if acked_filename is None:
        # Legacy stub fixture — keep the old reading so those tests still pass.
        request_reference = _text_of(root, "RequestReference") or ""
        status = (_text_of(root, "Status") or "").upper()
        is_ack = status in {"ACK", "OK", "ACCEPTED"}
        error_code = _text_of(root, "ErrorCode")
        error_detail = _text_of(root, "ErrorDetail")
        providers_raw = _text_of(root, "ProvidersExpected")
        providers_expected = int(providers_raw) if (providers_raw or "").isdigit() else None
    else:
        request_reference = ""
        is_ack = error_code is None

    return FeedbackResult(
        mislaka_number=(_text_of(root, "MISPAR-MISLAKA") or "").strip().upper() or None,
        request_reference=request_reference,
        is_ack=is_ack,
        providers_expected=providers_expected,
        error_code=error_code if not is_ack else None,
        error_detail=error_detail if not is_ack else None,
        acked_filename=acked_filename,
        sug_mashov=sug_mashov,
        maane_code=(_text_of(root, "MAANE-BERAMAT-RESHUMA") or "").strip() or None,
        maane_detail=rec_detail or None if acked_filename is not None else None,
    )


def parse_feedback_records(xml_bytes: bytes) -> list[FeedbackResult]:
    """Every record-level answer in a feedback file.

    feedback_009.xsd lets ONE file carry many answers: repeated
    YeshutGoremPoneLemislaka (one per answering body) × repeated
    MashovBeramatReshuma (one per request). Menora's 2026-09-25 FEDBKB carried
    four (two bodies × our 2000 + 2100) — reading only the first silently left
    three requests showing a false `acknowledged`. Each record is routed by its
    own MISPAR-MISLAKA. A file with no record blocks (file-level FEDBKA) yields
    the single file-level result."""
    root = ET.fromstring(xml_bytes)
    base = parse_feedback(xml_bytes)
    out: list[FeedbackResult] = []
    for rec in root.iter():
        if _local_tag(rec.tag) != "MashovBeramatReshuma":
            continue
        err = (_text_of(rec, "KOD-SHGIHA-BERAMAT-RESHUMA") or "").strip() or None
        status = (_text_of(rec, "STATUS-RESHUMA") or "").strip()
        details = [
            (d.text or "").strip() for d in rec.iter()
            if _local_tag(d.tag) == "PERUT-SHGIHA-BERAMAT-RESHUMA" and (d.text or "").strip()
        ]
        detail = " | ".join(dict.fromkeys(details)) or None
        is_ack = err is None and status != "2"
        out.append(FeedbackResult(
            mislaka_number=(_text_of(rec, "MISPAR-MISLAKA") or "").strip().upper() or None,
            request_reference="",
            is_ack=is_ack,
            providers_expected=base.providers_expected,
            error_code=None if is_ack else (err or "record_rejected"),
            error_detail=None if is_ack else detail,
            acked_filename=base.acked_filename,
            sug_mashov=base.sug_mashov,
            maane_code=(_text_of(rec, "MAANE-BERAMAT-RESHUMA") or "").strip() or None,
            maane_detail=detail,
        ))
    return out or [base]


def header_recipient_id(xml_bytes: bytes) -> str | None:
    """MISPAR-ZIHUI-NIMAAN from the file header (KoteretKovetz/NetuneiGoremNimaan)."""
    root = ET.fromstring(xml_bytes)
    for e in root.iter():
        if _local_tag(e.tag) == "NetuneiGoremNimaan":
            for c in e:
                if _local_tag(c.tag) == "MISPAR-ZIHUI-NIMAAN":
                    return (c.text or "").strip() or None
    return None


def holdings_index(xml_bytes: bytes) -> dict[str, dict]:
    """Per-customer routing keys from a REAL holdings / CONSLT (Mimshak) file.

    Measured on Swiftness's four CONSLT samples (ING/KGM/PNN/PNO):
      Mimshak/YeshutYatzran/Mutzarim/Mutzar/NetuneiMutzar/MISPAR-MISLAKA   ← request GUID
      Mimshak/YeshutYatzran/Mutzarim/Mutzar/NetuneiMutzar/KOD-MEZAHE-YATZRAN
      …/Mutzar/HeshbonotOPolisot/HeshbonOPolisa/NetuneiAmitOmevutach/MISPAR-ZIHUY ← customer
      …/Mutzar/HeshbonotOPolisot/HeshbonOPolisa/PerutMeyupeKoach/MISPAR-ZIHUY     ← authorised agent
    One file can answer SEVERAL requests (the KGM sample carries five GUIDs), so
    routing is per customer, never per file.

    Returns {customer_id (no leading zeros): {"guid", "agent_id", "yatzran"}}.
    """
    root = ET.fromstring(xml_bytes)
    out: dict[str, dict] = {}

    def first(elem: ET.Element, path: list[str]) -> str | None:
        cur = [elem]
        for name in path:
            cur = [c for e in cur for c in e if _local_tag(c.tag) == name]
            if not cur:
                return None
        return (cur[0].text or "").strip() or None

    for mutzar in (e for e in root.iter() if _local_tag(e.tag) == "Mutzar"):
        guid = (first(mutzar, ["NetuneiMutzar", "MISPAR-MISLAKA"]) or "").upper() or None
        yatzran = first(mutzar, ["NetuneiMutzar", "KOD-MEZAHE-YATZRAN"])
        for pol in (e for e in mutzar.iter() if _local_tag(e.tag) == "HeshbonOPolisa"):
            cust = first(pol, ["NetuneiAmitOmevutach", "MISPAR-ZIHUY"])
            if not cust:
                continue
            cust = cust.lstrip("0")
            if not cust:
                continue
            agent = (first(pol, ["PerutMeyupeKoach", "MISPAR-ZIHUY"]) or "").lstrip("0") or None
            out.setdefault(cust, {"guid": guid, "agent_id": agent, "yatzran": yatzran})
    return out


def parse_holdings(xml_bytes: bytes) -> tuple[str, list[HoldingItem]]:
    """Parse a Holdings v009 message → (request_reference, [HoldingItem]).

    TODO(XSD): replace XPaths with real Holdings v009 paths:
      - <Holdings><Customer><Product>... or per-provider envelope
      - per-product: provider_code, product_code, fund_policy_number, track,
        accumulation, total_premium, management_fee_deposit/balance,
        expected_pension, status_date, insurance_coverage block
      - unit scaling (some interfaces report deposits in agorot)
    """
    root = ET.fromstring(xml_bytes)

    request_reference = _text_of(root, "RequestReference") or ""
    items: list[HoldingItem] = []

    from app.services.maslaka.code_tables import label_for_provider, label_for_product_type

    # TODO(XSD): replace element name with the real product node.
    for prod in root.iter("Product"):
        provider_code = _text_of(prod, "ProviderCode")
        product_type_code = _text_of(prod, "ProductTypeCode")
        cust_id_raw = _text_of(prod, "CustomerIdNumber") or ""

        item = HoldingItem(
            customer_id_number=(cust_id_raw.lstrip("0") or "0"),
            provider_code=provider_code,
            receiving_company=label_for_provider(provider_code),
            product=_text_of(prod, "ProductName"),
            product_type=label_for_product_type(product_type_code) or product_type_code,
            fund_policy_number=_text_of(prod, "PolicyNumber"),
            track=_text_of(prod, "Track"),
            accumulation=_to_float(_text_of(prod, "Accumulation")),
            total_premium=_to_float(_text_of(prod, "TotalPremium")),
            management_fee_deposit=_to_float(_text_of(prod, "MgmtFeeDeposit")),
            management_fee_balance=_to_float(_text_of(prod, "MgmtFeeBalance")),
            expected_pension=_to_float(_text_of(prod, "ExpectedPension")),
            insurance_coverage=_text_of(prod, "InsuranceCoverage"),
            status_date=_to_date(_text_of(prod, "StatusDate")),
        )
        items.append(item)

    return request_reference, items


# ─── Internal helpers ──────────────────────────────────────────────────────
def _local_tag(tag: str) -> str:
    """Strip namespace from `{ns}name` → `name`."""
    return tag.rsplit("}", 1)[-1] if "}" in tag else tag


def _text_of(elem: ET.Element, name: str) -> str | None:
    """Return the text of the first descendant whose local tag == name."""
    for sub in elem.iter():
        if _local_tag(sub.tag) == name:
            return (sub.text or "").strip() or None
    return None


def _to_float(raw: str | None) -> float | None:
    if raw is None:
        return None
    try:
        return float(raw.replace(",", "").strip())
    except (ValueError, AttributeError):
        return None


def _to_date(raw: str | None) -> date | None:
    if not raw:
        return None
    # TODO(XSD): confirm Swiftness's actual date format. ISO 8601 is the
    # current guess; some Israeli interfaces use yyyymmdd or dd/mm/yyyy.
    for fmt in ("%Y-%m-%d", "%Y%m%d", "%d/%m/%Y"):
        try:
            return datetime.strptime(raw.strip(), fmt).date()
        except ValueError:
            continue
    return None
