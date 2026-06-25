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


def is_mimshak_dat(dat_bytes: bytes) -> bool:
    """True iff the bytes are a bare Mimshak DAT (the standardised Israeli
    "מבנה אחיד" holdings XML envelope), independent of any companion .MBT files.

    The Phoenix SFE כספת vault serves a lone .DAT (no ZIP, no MBT); Migdal's
    Safes vault wraps the same XML alongside .MBT lookups inside a ZIP. Sniff
    the head for the `<Mimshak>` root / `SUG-MIMSHAK` tag rather than parsing
    the whole document."""
    head = dat_bytes[:4096].decode("utf-8", errors="ignore")
    return "<Mimshak" in head or "SUG-MIMSHAK" in head


def parse_mimshak_dat(dat_bytes: bytes, filename: str) -> dict:
    """Parse a bare Mimshak holdings .DAT (no companion .MBT). Returns the
    parse_excel() result dict so upload_ingest can use it identically to an
    xlsx upload result.

    Same build→parse path as `parse_mimshak_zip`, but for a single .DAT written
    alone into a temp folder. The xlsx writer's per-MBT augmentation steps are
    each guarded by `if <path>.exists()`, so a folder with no .MBT degrades
    gracefully — the holdings come straight from the DAT itself; the .MBT files
    only enrich (customer email/DOB, extra policies)."""
    if not is_mimshak_dat(dat_bytes):
        raise ValueError("Not a Mimshak DAT — expected an XML holdings envelope (<Mimshak>)")

    from .to_production_xlsx import run as _build_xlsx
    from app.services.parser_service import parse_excel

    with tempfile.TemporaryDirectory(prefix="mimshak_dat_") as tmp_str:
        tmp = Path(tmp_str)
        # Keep the .DAT extension so the writer's find_dat() picks it up.
        dat_name = filename if filename.lower().endswith(".dat") else "holdings.DAT"
        (tmp / Path(dat_name).name).write_bytes(dat_bytes)

        xlsx_path = tmp / "mimshak_production.xlsx"
        _build_xlsx(tmp, xlsx_path, verbose=False)

        if not xlsx_path.exists():
            raise RuntimeError("Mimshak xlsx writer produced no output")

        xlsx_bytes = xlsx_path.read_bytes()
        result = parse_excel(xlsx_bytes, xlsx_path.name)

        logger.info(
            "mimshak: parsed %d records from bare DAT %s (size=%d bytes, fmt=%s, company=%s)",
            len(result.get("records", [])),
            filename,
            len(dat_bytes),
            result.get("format"),
            result.get("company_source"),
        )
        return result


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

        # Some insurer zips wrap everything in one or more sub-folders.
        # Migdal Safes vault, for example, wraps as
        # `<AGENT>_FROMMIGDAL_NN/Root/LIFE/{*.DAT,*.MBT}` — two levels of
        # wrappers above the data. Walk down until we hit the directory
        # that actually contains both a .DAT and a .MBT file.
        def _find_data_folder(root: Path) -> Path:
            for d in [root, *(p for p in root.rglob("*") if p.is_dir())]:
                names = [p.name.lower() for p in d.iterdir() if p.is_file()]
                if any(n.endswith(".dat") for n in names) and any(
                    n.endswith(".mbt") for n in names
                ):
                    return d
            # Fallback: original one-level flatten behaviour.
            contents = list(root.iterdir())
            if len(contents) == 1 and contents[0].is_dir():
                return contents[0]
            return root

        folder = _find_data_folder(tmp)

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


def merge_mimshak_zips_to_xlsx(
    zips: list[bytes],
    out_xlsx_path: Path,
) -> dict:
    """Build ONE consolidated production xlsx from multiple Mimshak ZIPs.

    Each ZIP is parsed via the existing single-bundle pipeline (extract →
    find data folder → run xlsx_writer); then pandas concatenates the
    per-sheet rows across all bundles into the final output xlsx.

    The downstream caller passes this xlsx to `parse_excel()` exactly like
    a manual upload, so every schema mapping / sanitisation rule applies.

    Returns metadata dict: {sources: n, out: str, insurer: str | None}.
    Raises ValueError if no valid Mimshak bundles are found.
    """
    import pandas as pd
    from .to_production_xlsx import run as _build_xlsx

    if not zips:
        raise ValueError("merge_mimshak_zips_to_xlsx: empty input list")

    # Re-use the same nested-folder walker as parse_mimshak_zip's flatten
    # logic so Safes ZIPs (AGENT_FROMMIGDAL_NN/Root/<subfolder>/) resolve
    # to the actual data directory regardless of wrapping depth.
    def _find_data_folder(root: Path) -> Path:
        for d in [root, *(p for p in root.rglob("*") if p.is_dir())]:
            names = [p.name.lower() for p in d.iterdir() if p.is_file()]
            if any(n.endswith(".dat") for n in names) and any(
                n.endswith(".mbt") for n in names
            ):
                return d
        contents = list(root.iterdir())
        if len(contents) == 1 and contents[0].is_dir():
            return contents[0]
        return root

    with tempfile.TemporaryDirectory(prefix="mimshak_merge_") as tmp_str:
        tmp = Path(tmp_str)
        per_bundle_xlsx: list[Path] = []

        for i, zip_bytes in enumerate(zips):
            if not is_mimshak_zip(zip_bytes):
                logger.warning("merge: bundle %d is not Mimshak (skipping)", i)
                continue
            sub = tmp / f"bundle_{i}"
            sub.mkdir()
            with zipfile.ZipFile(io.BytesIO(zip_bytes)) as z:
                z.extractall(sub)
            data_folder = _find_data_folder(sub)
            bundle_out = tmp / f"bundle_{i}.xlsx"
            _build_xlsx(data_folder, bundle_out, verbose=False)
            per_bundle_xlsx.append(bundle_out)

        if not per_bundle_xlsx:
            raise ValueError(
                "merge_mimshak_zips_to_xlsx: no valid Mimshak bundles in input"
            )

        # Concatenate per-sheet across all bundles. The xlsx_writer always
        # emits the same 6 sheets (some may be empty in a given bundle —
        # PENSION bundles fill מוצרי חיסכון / מסלולי השקעה while LIFE bundles
        # fill מוצרי ביטוח / כיסויים).
        sheet_names = pd.ExcelFile(per_bundle_xlsx[0]).sheet_names
        with pd.ExcelWriter(out_xlsx_path, engine="openpyxl") as writer:
            for sheet in sheet_names:
                frames = []
                for p in per_bundle_xlsx:
                    try:
                        df = pd.read_excel(p, sheet_name=sheet)
                    except Exception:
                        df = pd.DataFrame()
                    if not df.empty:
                        frames.append(df)
                if frames:
                    merged = pd.concat(frames, ignore_index=True)
                else:
                    # Preserve empty sheet (headers only) so the downstream
                    # parser still recognises the workbook structure.
                    merged = pd.read_excel(per_bundle_xlsx[0], sheet_name=sheet)
                merged.to_excel(writer, sheet_name=sheet, index=False)

        logger.info(
            "mimshak: merged %d bundle(s) into %s",
            len(per_bundle_xlsx), out_xlsx_path,
        )
        return {"sources": len(per_bundle_xlsx), "out": str(out_xlsx_path)}


__all__ = [
    "parse_mimshak_zip",
    "is_mimshak_zip",
    "parse_mimshak_dat",
    "is_mimshak_dat",
    "merge_mimshak_zips_to_xlsx",
]
