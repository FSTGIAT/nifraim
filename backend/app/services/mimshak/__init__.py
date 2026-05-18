"""Mimshak (Israeli insurance "מבנה אחיד") production-file parser.

Public API:
    parse_mimshak_zip(zip_bytes) -> dict
        Unzip a Migdal Mimshak bundle in memory (e.g. LIFE20260423131721.zip
        with *.DAT + *.MBT files), assemble a Mimshak-format xlsx in memory
        via the POC's xlsx_writer (full field decoding, status labels,
        per-coverage premium summing, insurer normalisation, etc.), then
        hand it to the existing `parse_excel()` so we reuse the same
        production parser as manually-uploaded xlsx files.

        Returns the parse_excel() result dict {format, company_source, records}.

    is_mimshak_zip(zip_bytes) -> bool
        Cheap detector — does the zip contain at least one .DAT and one .MBT?

The two-step "build xlsx → parse xlsx" path means ZIP uploads inherit every
schema mapping, column truncation rule, and downstream behaviour the manual
production-xlsx path already has. Zero divergence.
"""

from __future__ import annotations

import io
import logging
import tempfile
import zipfile
from pathlib import Path

logger = logging.getLogger(__name__)


def is_mimshak_zip(zip_bytes: bytes) -> bool:
    """True iff the zip contains at least one .DAT (XML envelope) and one .MBT
    (pipe-delimited lookup table) — the Migdal Mimshak signature."""
    try:
        with zipfile.ZipFile(io.BytesIO(zip_bytes)) as z:
            names = [n.lower() for n in z.namelist()]
            has_dat = any(n.endswith(".dat") for n in names)
            has_mbt = any(n.endswith(".mbt") for n in names)
            return has_dat and has_mbt
    except zipfile.BadZipFile:
        return False


def parse_mimshak_zip(zip_bytes: bytes) -> dict:
    """Parse a Migdal Mimshak ZIP. Returns the parse_excel() result dict so
    upload_ingest can use it identically to an xlsx upload result."""
    if not is_mimshak_zip(zip_bytes):
        raise ValueError("Not a Mimshak bundle — expected a ZIP containing .DAT + .MBT files")

    from .to_production_xlsx import run as _build_xlsx
    from app.services.parser_service import parse_excel

    with tempfile.TemporaryDirectory(prefix="mimshak_") as tmp_str:
        tmp = Path(tmp_str)
        with zipfile.ZipFile(io.BytesIO(zip_bytes)) as z:
            z.extractall(tmp)

        # Some insurer zips wrap everything in a single sub-folder — flatten.
        contents = list(tmp.iterdir())
        if len(contents) == 1 and contents[0].is_dir():
            folder = contents[0]
        else:
            folder = tmp

        # Build the production xlsx using the POC's full xlsx_writer (proper
        # field decoding, premium summing across coverages, status labels,
        # insurer normalisation).
        xlsx_path = tmp / "mimshak_production.xlsx"
        _build_xlsx(folder, xlsx_path, verbose=False)

        if not xlsx_path.exists():
            raise RuntimeError("Mimshak xlsx writer produced no output")

        # Re-parse via the existing production xlsx parser so we reuse every
        # schema mapping + downstream behaviour the manual upload path has.
        xlsx_bytes = xlsx_path.read_bytes()
        result = parse_excel(xlsx_bytes, xlsx_path.name)

        logger.info(
            "mimshak: parsed %d records from zip (size=%d bytes, fmt=%s, company=%s)",
            len(result.get("records", [])),
            len(zip_bytes),
            result.get("format"),
            result.get("company_source"),
        )
        return result


__all__ = ["parse_mimshak_zip", "is_mimshak_zip"]
