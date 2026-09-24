# מסלקה form assets

## `shiyuch_form_blank.pdf` — right variant, but a FILLED copy (placeholder)

Currently vendored (2026-09-24, commit `85790d8`): the **2-page `טופס בקשה – שיוך לבית תוכנה או
בית סוכן`**, the variant with the לבית תוכנה / לבית סוכן choice. This is the correct form for
Nifraim (a **בית תוכנה**), and `FIELD_POSITIONS` is calibrated against it.

⚠️ **It is not blank.** It is an agent's filled copy, so the blank-template guard refuses it
unless `MASLAKA_ALLOW_FILLED_TEMPLATE=true`. That flag is set on production because kiko is the
only agent, and he downloads his own form. **A second agent would get kiko's details underneath
their own overlay.** Before anyone else signs up, either unset the flag or vendor the genuine blank
from `helpdesk@swiftness.co.il`. That blank is not on the public forms page.

History: the 1-page `בקשת שיוך לבית סוכן`
(<https://www.swiftness.co.il/agents/טפסים-ונהלי-עבודה/>) was vendored briefly and replaced
because it is the wrong entity type.

## Why there is a guard

The file first supplied as "clean" (2026-09-24) was an agent's **signed** copy — it extracts as
`משה היב כהן / Nifraim.com / 24/09/2026`. Serving that as the template hands every agent another
agent's name and signature, and this repo deploys the working tree, so a local placeholder ships
to production.

`association._assert_template_is_blank` refuses any template containing `Nifraim.com` or
`558638623`: those are OUR side of the form, written in by the agent, so they cannot appear on a
blank. (An earlier version flagged *any* extractable text, on the assumption the blank is a pure
scan — wrong: this text-based variant's own labels extract as ~600 characters and would have been
rejected.) `MASLAKA_ALLOW_FILLED_TEMPLATE=true` overrides it for local calibration only.

## Pre-filling

No AcroForm fields on either variant, so it is a coordinate overlay: reportlab canvas → merged
with pypdf. Positions live in `services/maslaka/association.py: FIELD_POSITIONS`, with
`BOX_PITCH` for the digit-box rows — the מסלקה prints identity numbers as a row of empty squares,
and a plain `drawString` bunches the digits at the left, outside the grid.

**Calibrate by rendering and looking at it**, not by extracting text. Text extraction confirmed
the first attempt's coordinates as "correct" while both numbers were visibly sitting below and
left of their boxes:

```python
import pypdfium2 as pdfium
pdfium.PdfDocument("out.pdf")[0].render(scale=1.4).to_pil().save("out.png")
```

Hebrew needs an embedded font (Heebo, from the frontend) and `_shape_hebrew`, which reverses the
string because reportlab has no bidi engine — so it must never touch anything containing digits.

Page size of both variants: 595.32 × 841.92 pt (A4).
