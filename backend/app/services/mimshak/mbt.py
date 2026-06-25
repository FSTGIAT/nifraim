"""MBT lookup file decoders.

MBT files are small companion tables shipped alongside a Mimshak DAT:
  AGENTS.MBT    — newline list of agent codes (plain ASCII)
  COMPANY.MBT   — insurer metadata (often empty whitespace)
  PERSON.MBT    — customer master: email, DOB, gender, marital status, city, agent
  LIFE.MBT      — per-policy life summary (~133 pipe-delimited columns)
  LIFEHLTH.MBT  — life+health bundle (~30 cols)
  COVRLIFE.MBT  — per-coverage/rider rows (~23 cols)

File encodings vary. Many are written in VISUAL Hebrew order (character bytes
stored in display order, not logical order). We preserve both forms: the raw
string as stored, plus a best-effort logical-order string.
"""

from __future__ import annotations

import io
from pathlib import Path


# ── Encoding helpers ─────────────────────────────────────────────────────

_ENCODINGS = ("utf-8", "cp1255", "iso-8859-8")


def _read_text(path: Path) -> str:
    """Read a file trying a few encodings — Hebrew files in this format
    are either UTF-8 or Windows-1255."""
    raw = path.read_bytes()
    for enc in _ENCODINGS:
        try:
            return raw.decode(enc)
        except UnicodeDecodeError:
            continue
    # Last-resort: latin-1 never fails
    return raw.decode("latin-1", errors="replace")


def _maybe_reverse_hebrew(s: str) -> str:
    """Some MBT fields are in visual order — if a string consists entirely of
    Hebrew letters and ASCII, reverse just the Hebrew runs.

    This is a best-effort heuristic. We keep the original alongside in parsers."""
    if not s:
        return s
    # If no Hebrew characters, leave as-is.
    if not any("\u0590" <= c <= "\u05FF" for c in s):
        return s
    # Reverse runs of Hebrew+space; leave ASCII untouched.
    out = []
    buf = []
    for c in s:
        if "\u0590" <= c <= "\u05FF" or c == " ":
            buf.append(c)
        else:
            if buf:
                out.append("".join(reversed(buf)))
                buf = []
            out.append(c)
    if buf:
        out.append("".join(reversed(buf)))
    return "".join(out).strip()


def _split_pipe(line: str) -> list[str]:
    return [cell.strip() for cell in line.rstrip("\n").split("|")]


# ── AGENTS.MBT ───────────────────────────────────────────────────────────

def parse_agents(path: Path) -> set[str]:
    return {
        line.strip()
        for line in _read_text(path).splitlines()
        if line.strip()
    }


# ── COMPANY.MBT ──────────────────────────────────────────────────────────

def parse_company(path: Path) -> dict:
    text = _read_text(path).strip()
    # In the samples this file is often all-whitespace. Return whatever is there.
    return {"raw": text}


# ── PERSON.MBT ───────────────────────────────────────────────────────────
# Pipe-delimited. Column positions (0-indexed) — inferred from the sample and
# field meaning. Columns we care about are a minority of ~46; the rest stay raw.
# 0  full_id (with prefix, e.g. 01051695229)
# 2  short_id (9-digit national ID)
# 4  role description   (visual Hebrew)
# 5  email
# 17 age
# 18 address (city + street, visual Hebrew)
# 19 city (visual Hebrew)
# 26 last_name (visual Hebrew)
# 27 first_name (visual Hebrew)
# 28 dob (DDMMYYYY)
# 31 marital_status_code
# 33 gender_code (1=M, 2=F)
# 43 agent_category
# 44 agent_code
# 45 reference_number

def parse_persons(path: Path) -> dict[str, dict]:
    by_id: dict[str, dict] = {}
    text = _read_text(path)
    for raw_line in text.splitlines():
        if not raw_line.strip():
            continue
        cells = _split_pipe(raw_line)
        if len(cells) < 45:
            continue
        short_id = cells[2].lstrip("0") or cells[2]

        def _cell(idx: int) -> str:
            return cells[idx] if idx < len(cells) else ""

        # Column positions in May 2026 Migdal samples (off-by-2 vs older comment
        # — Migdal removed two columns around col 18).
        # 0  full_id        4  role_he      5  email          7  phone
        # 15 address_he     16 city_he      24 last_name_he   25 first_name_he
        # 26 dob_raw        29 marital      31 gender_code    43 agent_category
        # 44 agent_code     45 reference_number
        row = {
            "full_id": _cell(0),
            "id_number": short_id,
            "role_he": _maybe_reverse_hebrew(_cell(4)),
            "role_raw": _cell(4),
            "email": _cell(5) or None,
            "mobile": _cell(7) or None,
            "address_he": _maybe_reverse_hebrew(_cell(15)),
            "city_he": _maybe_reverse_hebrew(_cell(16)),
            "age": _cell(17).strip() or None,
            "last_name_he": _maybe_reverse_hebrew(_cell(24)),
            "first_name_he": _maybe_reverse_hebrew(_cell(25)),
            "dob_raw": _cell(26).strip() or None,
            "marital_status_code": _cell(29).strip() or None,
            "gender_code": _cell(31).strip() or None,
            "agent_category": _cell(43).strip() or None,
            "agent_code": _cell(44).strip() or None,
            "reference_number": _cell(45).strip() or None if len(cells) > 45 else None,
        }
        by_id[short_id] = row
    return by_id


# ── COVRLIFE.MBT ─────────────────────────────────────────────────────────
# Pipe-delimited, ~23 columns per row. Multiple rows per policy.
# 0  rider_code
# 1  policy_ref_id
# 2  rider_sequence
# 3  rider_status (01=active)
# 4  rider_start (DDMMYYYY)
# 5  rider_end (DDMMYYYY)
# 6  benefit_code
# 7  benefit_amount
# (further columns: premium amounts, beneficiary name, agent codes)

def parse_covrlife(path: Path) -> dict[str, list[dict]]:
    by_policy: dict[str, list[dict]] = {}
    for raw_line in _read_text(path).splitlines():
        if not raw_line.strip():
            continue
        cells = _split_pipe(raw_line)
        if len(cells) < 8:
            continue
        policy_id = cells[1].lstrip("0") or cells[1]
        by_policy.setdefault(policy_id, []).append({
            "rider_code": cells[0],
            "policy_ref": cells[1],
            "rider_sequence": cells[2],
            "rider_status": cells[3],
            "rider_start": cells[4] or None,
            "rider_end": cells[5] or None,
            "benefit_code": cells[6],
            "benefit_amount": cells[7],
            "raw": cells,
        })
    return by_policy


# ── LIFE.MBT / LIFEHLTH.MBT ──────────────────────────────────────────────
# Policy summary. Schema has ~133 (LIFE) or ~30 (LIFEHLTH) columns.
# We treat them generically: index by policy_id and keep the raw cells.

def _parse_policy_summary(path: Path, policy_id_col: int = 9) -> dict[str, dict]:
    by_policy: dict[str, dict] = {}
    for raw_line in _read_text(path).splitlines():
        if not raw_line.strip():
            continue
        cells = _split_pipe(raw_line)
        if len(cells) <= policy_id_col:
            continue
        policy_id = cells[policy_id_col].lstrip("0") or cells[policy_id_col]
        by_policy[policy_id] = {
            "policy_id_raw": cells[policy_id_col],
            "insurer_code": cells[1] if len(cells) > 1 else "",
            "product_class": cells[2] if len(cells) > 2 else "",
            "cells": cells,
        }
    return by_policy


def parse_life(path: Path) -> dict[str, dict]:
    return _parse_policy_summary(path)


def parse_lifehlth(path: Path) -> dict[str, dict]:
    return _parse_policy_summary(path)


# ── Folder scanner ───────────────────────────────────────────────────────

def load_all(folder: Path) -> dict:
    """Load every MBT lookup we recognise, missing files → empty dict/set."""
    loaded = {
        "agents": set(),
        "company": {},
        "persons": {},
        "covrlife": {},
        "life": {},
        "lifehlth": {},
    }
    for mbt in folder.glob("*.MBT"):
        name = mbt.name.upper()
        try:
            if name == "AGENTS.MBT":
                loaded["agents"] = parse_agents(mbt)
            elif name == "COMPANY.MBT":
                loaded["company"] = parse_company(mbt)
            elif name == "PERSON.MBT":
                loaded["persons"] = parse_persons(mbt)
            elif name == "COVRLIFE.MBT":
                loaded["covrlife"] = parse_covrlife(mbt)
            elif name == "LIFE.MBT":
                loaded["life"] = parse_life(mbt)
            elif name == "LIFEHLTH.MBT":
                loaded["lifehlth"] = parse_lifehlth(mbt)
        except Exception as e:
            # Non-fatal: note in the returned dict so the report can show it
            loaded.setdefault("errors", []).append(f"{name}: {type(e).__name__}: {e}")
    return loaded
