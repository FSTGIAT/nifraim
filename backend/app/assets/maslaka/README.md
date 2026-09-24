# מסלקה form assets

## `shiyuch_form_blank.pdf` — MISSING, must be supplied

The **blank** `טופס בקשה – שיוך לבית תוכנה או בית סוכן`, as published by Swiftness
(helpdesk@swiftness.co.il). Drop it here under exactly that name.

**Do not substitute a completed copy.** The file first supplied (2026-09-24) turned out to be
kiko's *signed* form — it extracts as `משה היב כהן` / `Nifraim.com` / `24/09/2026` — and serving
it as a template would hand one agent another agent's name and signature. It was removed.

## How the form is built

The form body is a **scanned image**, sliced into 14 (page 1) / 23 (page 2) JPEG fragments;
none of its Hebrew labels are extractable text. So a blank cannot be reconstructed by stripping
the filled values, and the form cannot be filled via AcroForm fields — it has **zero**.

Pre-filling is therefore a coordinate overlay: draw onto the blank with reportlab, merge with
pypdf. Coordinates live in one place (`services/maslaka/association.py: FIELD_POSITIONS`) and
**must be calibrated against the real blank** — the values there are placeholders until then.

Page size of the supplied copy: 595.32 × 841.92 pt (A4). Hebrew needs an embedded font with
Hebrew glyphs plus RTL shaping; digits and `Nifraim.com` are plain.
