"""Validate מסלקה files against Swiftness's OFFICIAL published schemas.

The wire format cannot be safely inferred from sample files. On 2026-09-10 four
live requests went unanswered because we had reverse-engineered them from the 13
real vendor samples, and every one of the four was schema-invalid. The clearest
case: `KOD-SVIVAT-AVODA` is **1 = TEST, 2 = PRODUCTION**, and we had it inverted.
All 12 samples are `.DAT` production files carrying `2` — perfectly consistent
with the wrong reading. Only the schema settles it.

Schemas are vendored under `tests/fixtures/maslaka/xsd/`, downloaded from
https://www.swiftness.co.il/agents/קבצים-עדכניים-לעבודה-מול-המסלקה/
Re-download when a circular bumps an interface version.

`lxml` is a hard dependency (requirements.txt) but validation degrades to
"unknown" rather than raising if it is missing, so a console page still renders.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

logger = logging.getLogger(__name__)

# tests/fixtures is the vendored location — these files ARE the spec, not test data.
XSD_DIR = Path(__file__).resolve().parents[3] / "tests" / "fixtures" / "maslaka" / "xsd"

# Service id (from the נספח ו' filename) → schema file.
SCHEMA_BY_SERVICE: dict[str, str] = {
    "EVENTS": "events_007.xsd",
    "FEDBKA": "feedback_009.xsd",
    "FEDBKB": "feedback_009.xsd",
    "WRNING": "feedback_009.xsd",
    # פיצויים — three schemas, split by the action-code pairs they carry.
    "EMPSV1": "pitzuim_9301_9303_005.xsd",
    "EMPSV2": "pitzuim_9300_9302_005.xsd",
    "EMPSV3": "pitzuim_9305_9306_005.xsd",
    # מעסיקים
    "EMPONG": "maasikim_shotef_006.xsd",
    "EMPNEG": "maasikim_shliliim_006.xsd",
    "EMPFED": "maasikim_mesakem_006.xsd",
    "EMPYRL": "maasikim_shnati_006.xsd",
    # Holdings/טרום-ייעוץ answers are split by product family, which the filename
    # carries in PPP — resolved by `schema_for()` below.
    "CONSLT": "",
    "HOLDNG": "",
    "HOLCON": "",
}

# `SUG-MIMSHAK` is declared INSIDE the file and is the authoritative interface
# id — a filename can be wrong or absent, the envelope cannot. Measured by
# reading the enumeration out of each vendored schema. Note two are ambiguous
# on their own: 1/2/3 covers all four holdings families and 17 covers all three
# פיצויים variants, so the filename still decides within those groups.
SCHEMA_BY_SUG_MIMSHAK: dict[str, str] = {
    "6": "events_007.xsd",
    "20": "feedback_009.xsd",
    "12": "maasikim_shotef_006.xsd",
    "13": "maasikim_shliliim_006.xsd",
    "14": "maasikim_mesakem_006.xsd",
    "18": "maasikim_mesakem_006.xsd",
    "16": "maasikim_shnati_006.xsd",
    "30": "niyud_haavaraamit_003.xsd",
    "31": "niyud_hizunminhali_003.xsd",
    "32": "niyud_nispachpigurim_003.xsd",
    "33": "niyud_nispasha_003.xsd",
    "35": "niyud_hizuncaspi_003.xsd",
}

SCHEMA_BY_PRODUCT_FAMILY: dict[str, str] = {
    "KGM": "kupotgemel.xsd",
    "PNN": "karnotpensiahadashot.xsd",
    "PNO": "karnotpensiavatikot.xsd",
    "ING": "hevrotbituah.xsd",
    "INP": "hevrotbituah.xsd",
    "INK": "hevrotbituah.xsd",
    "INM": "hevrotbituah.xsd",
}


@dataclass
class ValidationResult:
    """`ok` is None when we could not check (no schema, or lxml missing) — which
    is deliberately NOT the same as False. A console must not show a green tick
    for a file nobody validated."""
    ok: bool | None
    schema: str | None = None
    errors: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {"ok": self.ok, "schema": self.schema, "errors": self.errors}


def sug_mimshak(xml: bytes) -> str | None:
    """Read `SUG-MIMSHAK` out of the envelope. Cheap, namespace-agnostic, and
    does not require the file to have a legal name."""
    import re

    m = re.search(rb"<SUG-MIMSHAK>\s*([0-9]+)\s*</SUG-MIMSHAK>", xml)
    return m.group(1).decode() if m else None


def schema_for(
    *,
    service: str | None,
    product_family: str | None = None,
    xml: bytes | None = None,
) -> str | None:
    """Pick the schema file for a service id, using the product family where the
    service alone does not determine it (holdings answers are per-family).

    When `xml` is supplied and the filename does not resolve, fall back to the
    file's own `SUG-MIMSHAK`. That matters for anything the מסלקה sends whose
    name we do not recognise — an unrecognised name is exactly when you most
    want to know what the file actually is."""
    if not service:
        return _by_envelope(xml)
    name = SCHEMA_BY_SERVICE.get(service.upper())
    if name:
        return name
    if service.upper() in ("CONSLT", "HOLDNG", "HOLCON"):
        fam = SCHEMA_BY_PRODUCT_FAMILY.get((product_family or "").upper())
        if fam:
            return fam
    return _by_envelope(xml)


def _by_envelope(xml: bytes | None) -> str | None:
    if not xml:
        return None
    return SCHEMA_BY_SUG_MIMSHAK.get(sug_mimshak(xml) or "")


@lru_cache(maxsize=16)
def _load(schema_file: str):
    from lxml import etree

    path = XSD_DIR / schema_file
    if not path.exists():
        raise FileNotFoundError(f"schema not vendored: {path}")
    return etree.XMLSchema(etree.parse(str(path)))


def validate(xml: bytes, *, schema_file: str | None) -> ValidationResult:
    """Validate `xml`. Never raises — a validator that explodes is worse than one
    that reports it could not run."""
    if not schema_file:
        return ValidationResult(ok=None, errors=["אין סכימה מתאימה לסוג הקובץ הזה"])
    try:
        from lxml import etree
    except ImportError:
        return ValidationResult(ok=None, schema=schema_file, errors=["lxml לא מותקן"])
    try:
        schema = _load(schema_file)
    except Exception as e:
        logger.warning("maslaka.xsd: cannot load %s: %s", schema_file, e)
        return ValidationResult(ok=None, schema=schema_file, errors=[str(e)])
    try:
        doc = etree.fromstring(xml)
    except Exception as e:
        return ValidationResult(ok=False, schema=schema_file, errors=[f"XML לא תקין: {e}"])
    if schema.validate(doc):
        return ValidationResult(ok=True, schema=schema_file)
    return ValidationResult(
        ok=False,
        schema=schema_file,
        errors=[f"שורה {e.line}: {e.message}" for e in schema.error_log],
    )
