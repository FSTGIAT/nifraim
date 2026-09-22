"""מסלקה file naming — נספח ו' of חוזר גופים מוסדיים 2026-9-3.

The clearinghouse identifies a file by its NAME before it ever parses the XML, so a
malformed name is rejected without any content-level feedback. Our stub used
`events_v007_<hex>.xml`, which is not a legal name in this grammar at all.

    AAABBBBBBBBBBBBCCCCCCPPPVVVDDDDDDDDDDDDDDEEEE.FFF

    AAA             3   direction
    BBBBBBBBBBBB    12  sender's ת.ז / ח.פ / passport, ZERO-LEFT-PADDED
    CCCCCC          6   service id (the interface)
    PPP             3   product family — "000" unless this is an אחזקות/טרום-ייעוץ file
    VVV             3   interface version
    DDDDDDDDDDDDDD  14  YYYYMMDDHHMMSS
    EEEE            4   per-sender sequence, RESET AT THE START OF EACH BUSINESS DAY
    FFF             3   DAT = production, TST = test

No blank characters, every field fully padded, alphabetics uppercase. Attachments hang
off the parent name with a 3-digit ordinal: `…EEEE_001.PDF`, one document per file.

Verified against Swiftness's published samples, e.g.
`101000514813450CONSLTPNN009202501090827016501.DAT` — מסלקה → licence holder, sender
514813450 (Swiftness's own ח.פ.), טרום ייעוץ, new pension funds, v009.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime
from zoneinfo import ZoneInfo

# The wire clock is ISRAEL LOCAL TIME. The Gateway VM runs UTC and the dev box
# runs IDT, so `datetime.now()` is right on one and three hours wrong on the
# other — and the dev box is the one the tests run on, which is why this hid.
# Measured live 2026-09-22: the Gateway named two files 174253/174254 while the
# clock in Israel read 204253. Same constant as `events.maslaka_now()`.
ISRAEL_TZ = ZoneInfo("Asia/Jerusalem")


def maslaka_now() -> datetime:
    """Wall-clock time in Israel, naive — the clock EVERY מסלקה timestamp uses.

    THE one definition: `events.maslaka_now` is an alias of this, not a copy.
    It lives in this module because `filenames` is pure formatting with no
    `settings` dependency, so `events` can import it but not the reverse.

    `TAARICH-BITZUA`, `MISPAR-HAKOVETZ` and the filename's 14-digit stamp are
    all read by an Israeli regulatory system as Israel local time. Neither
    `datetime.now()` nor `utcnow()` is safe: the Gateway runs UTC and the dev
    box runs IDT, so each is correct on exactly one of them — and the tests run
    on the dev box, which is why the filename bug survived a green suite.

    Not a per-user value: the מסלקה's clock is Israel's for every agent on
    every host, so it is a domain constant, not configuration.
    """
    return datetime.now(ISRAEL_TZ).replace(tzinfo=None)

# ── Direction (AAA) ─────────────────────────────────────────────────────────
DIRECTIONS: dict[str, str] = {
    "001": "בעל רישיון → מסלקה",
    "002": "לקוח → מסלקה",
    "003": "מעסיק → מסלקה",
    "004": "יצרן → מסלקה",
    "006": "לשכת שירות → מסלקה",
    "101": "מסלקה → בעל רישיון",
    "102": "מסלקה → לקוח",
    "103": "מסלקה → מעסיק",
    "104": "מסלקה → יצרן",
    "106": "מסלקה → לשכת שירות",
    "201": "יצרן → בעל רישיון (ישיר)",
    "202": "יצרן → מעסיק (ישיר)",
    "203": "יצרן → לקוח (ישיר)",
    "301": "בעל רישיון → מעסיק",
    "302": "מעסיק → בעל רישיון",
}

# ── Service id (CCCCCC) — the interface ─────────────────────────────────────
SERVICES: dict[str, str] = {
    "EVENTS": "ממשק אירועים",
    "FEDBKA": "היזון חוזר — שלב א' (משוב טכני)",
    "FEDBKB": "היזון חוזר — שלב ב' (משוב תוכן)",
    "HOLDNG": "ממשק אחזקות",
    "HOLCON": "אחזקות מתמשך ללקוח",
    "CONSLT": "ממשק טרום ייעוץ",
    "WRNING": "התראה על אי משלוח תשובה",
    "EMPONG": "מעסיקים — שוטף",
    "EMPNEG": "מעסיקים — שלילי",
    "EMPFED": "מעסיקים — היזון מסכם",
    "EMPYRL": "מעסיקים — היזון שנתי",
    "EMPSV1": "פיצויים (9301+9303)",
    "EMPSV2": "פיצויים (9300+9302)",
    "EMPSV3": "פיצויים (9305+9306)",
    "OPRONG": "דמי סליקה — שוטף",
    "OPRFED": "דמי סליקה — מסכם",
}

# ── Product family (PPP) ────────────────────────────────────────────────────
# NOTE: this is the FILENAME product family. It is NOT `SUG-MUTZAR` (the 1–10
# payload field). Two different tables; conflating them mislabels every row.
PRODUCT_FAMILIES: dict[str, str] = {
    "000": "לא רלוונטי",
    "KGM": "קופות גמל",
    "PNN": "קרנות פנסיה חדשות",
    "PNO": "קרנות פנסיה ותיקות",
    "INP": "פוליסות ביטוח פרט",
    "ING": "חברות ביטוח",
    "INK": "ביטוח קבוצתי",
    "INM": "ביטוח משכנתא",
}

# DAT/TST are the interface files themselves. Attachments (`…_001.PDF`) carry a
# document type instead — a signed ייפוי כוח rides in as PDF or JPG.
FILE_TYPES: dict[str, str] = {
    "DAT": "ייצור",
    "TST": "בדיקות",
    "PDF": "מסמך מצורף (PDF)",
    "JPG": "מסמך מצורף (JPG)",
}

# 45 fixed characters, then .FFF — plus the optional _NNN attachment ordinal.
_PATTERN = re.compile(
    r"^(?P<direction>\d{3})"
    r"(?P<sender>\d{12})"
    r"(?P<service>[A-Z0-9]{6})"
    r"(?P<product>[A-Z0-9]{3})"
    r"(?P<version>\d{3})"
    r"(?P<timestamp>\d{14})"
    r"(?P<sequence>\d{4})"
    r"(?:_(?P<attachment>\d{3}))?"
    r"\.(?P<filetype>[A-Za-z]{3})$"
)


@dataclass
class MaslakaFilename:
    direction: str
    sender_id: str
    service: str
    product_family: str
    version: str
    timestamp: str
    sequence: str
    file_type: str
    attachment: str | None = None

    # ── Human-readable, for the test console ────────────────────────────────
    @property
    def direction_label(self) -> str:
        return DIRECTIONS.get(self.direction, "לא ידוע")

    @property
    def service_label(self) -> str:
        return SERVICES.get(self.service, "לא ידוע")

    @property
    def product_label(self) -> str:
        return PRODUCT_FAMILIES.get(self.product_family, "לא ידוע")

    @property
    def file_type_label(self) -> str:
        return FILE_TYPES.get(self.file_type.upper(), "לא ידוע")

    @property
    def sent_at(self) -> datetime | None:
        try:
            return datetime.strptime(self.timestamp, "%Y%m%d%H%M%S")
        except ValueError:
            return None

    @property
    def is_test(self) -> bool:
        return self.file_type.upper() == "TST"

    def to_dict(self) -> dict:
        return {
            "direction": self.direction,
            "direction_label": self.direction_label,
            "sender_id": self.sender_id,
            "sender_id_stripped": self.sender_id.lstrip("0") or "0",
            "service": self.service,
            "service_label": self.service_label,
            "product_family": self.product_family,
            "product_label": self.product_label,
            "version": self.version,
            "timestamp": self.timestamp,
            "sent_at": self.sent_at.isoformat() if self.sent_at else None,
            "sequence": self.sequence,
            "file_type": self.file_type.upper(),
            "file_type_label": self.file_type_label,
            "is_test": self.is_test,
            "attachment": self.attachment,
        }


def parse_filename(name: str) -> MaslakaFilename | None:
    """Decode a מסלקה filename. None when it does not match the grammar —
    which for an inbound file means the מסלקה did not produce it."""
    m = _PATTERN.match(name.strip())
    if not m:
        return None
    g = m.groupdict()
    return MaslakaFilename(
        direction=g["direction"],
        sender_id=g["sender"],
        service=g["service"],
        product_family=g["product"],
        version=g["version"],
        timestamp=g["timestamp"],
        sequence=g["sequence"],
        file_type=g["filetype"],
        attachment=g["attachment"],
    )


def build_filename(
    *,
    direction: str,
    sender_id: str,
    service: str,
    version: str,
    sequence: int,
    product_family: str = "000",
    file_type: str = "DAT",
    when: datetime | None = None,
    attachment: int | None = None,
) -> str:
    """Compose a legal מסלקה filename.

    `sender_id` is zero-left-padded to 12 — the agent's ת.ז., NOT a separate
    "agent number". `sequence` resets each business day, so the caller owns it;
    this function only formats.
    """
    if len(service) != 6:
        raise ValueError(f"service id must be 6 chars, got {service!r}")
    if len(product_family) != 3:
        raise ValueError(f"product family must be 3 chars, got {product_family!r}")
    digits = "".join(ch for ch in str(sender_id) if ch.isdigit())
    if not digits:
        raise ValueError("sender_id has no digits")
    if len(digits) > 12:
        raise ValueError(f"sender_id longer than 12 digits: {digits!r}")
    # NEVER `datetime.now()` here: on the UTC Gateway that names the file three
    # hours before TAARICH-BITZUA inside it. Callers should still pass `when`
    # so the name and the payload share ONE timestamp, not two close ones.
    ts = (when or maslaka_now()).strftime("%Y%m%d%H%M%S")
    stem = (
        f"{str(direction).zfill(3)}"
        f"{digits.zfill(12)}"
        f"{service.upper()}"
        f"{product_family.upper()}"
        f"{str(version).zfill(3)}"
        f"{ts}"
        f"{str(int(sequence)).zfill(4)}"
    )
    if attachment is not None:
        stem = f"{stem}_{str(int(attachment)).zfill(3)}"
    return f"{stem}.{file_type.upper()}"
