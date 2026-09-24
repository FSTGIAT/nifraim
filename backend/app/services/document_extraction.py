"""Extract structured data (summary + commission rates) from an insurance
agreement PDF using Claude's native PDF document input.

Uses Anthropic tool_use to force a strict JSON output schema — the model
emits a `tool_use` block whose `input` is already a parsed dict, so we avoid
the fragile "ask for JSON in text and parse it" loop which broke on long
Hebrew content overrunning the token budget.

Also runs pdfplumber locally first to grab the PDF text layer. We pass that
text alongside the document block so Claude doesn't have to OCR every page —
deterministic for any PDF with an embedded text layer (most modern Hebrew
agreements).
"""
import asyncio
import base64
import io
import logging
import re
import time

import anthropic
import pdfplumber

from app.config import settings


logger = logging.getLogger(__name__)


# Below this length, we treat the text layer as essentially absent (likely a
# scanned PDF) and let Claude rely purely on vision.
_MIN_TEXT_LAYER_CHARS = 200
# Cap how much we forward as a text block to keep the call fast.
_MAX_TEXT_LAYER_CHARS = 60000

# Rate rows whose product / scope / notes match these markers are NOT ongoing
# נפרעים commissions — they are one-time scope/היקף grants or Clawback/refund
# percentages. They must never land in commission_rates (they corrupt the
# expected-commission math and the reconciliation Tier-3 max()). Belt-and-
# suspenders on top of the prompt, which already tells the model to keep these
# out of rates[]. See plan section B.
_NON_COMMISSION_RE = re.compile(
    r"היקף|מתפוק|יעדים|מענק\s*גיוס|לכל\s*מיליון|clawback|החזר|קנס|עזב",
    re.IGNORECASE,
)


# OCR settings for scanned PDFs (no embedded text layer). Hebrew via
# tesseract-ocr-heb; pdf2image rasterization needs poppler-utils. Both are
# installed in the Docker image; the imports are guarded so local dev without
# them still runs (it just skips OCR).
_OCR_MAX_PAGES = 30
_OCR_DPI = 200


def _ocr_pdf(file_bytes: bytes) -> str:
    """Rasterize a scanned PDF and OCR it in Hebrew. Returns '' on any failure
    or when the OCR deps aren't installed. Re-enables the literal-value
    anti-hallucination guard for scanned agreements (Harel/Meitav/Mor/Phoenix
    gemel were all textlen=0 → guard was disabled)."""
    try:
        import pytesseract
        from pdf2image import convert_from_bytes
    except ImportError as e:
        logger.warning("OCR deps unavailable (%s) — skipping OCR fallback", e)
        return ""
    try:
        images = convert_from_bytes(
            file_bytes, dpi=_OCR_DPI, fmt="png", last_page=_OCR_MAX_PAGES
        )
    except Exception as e:
        logger.warning("pdf2image rasterization failed: %s", e)
        return ""
    out: list[str] = []
    for i, img in enumerate(images, start=1):
        try:
            page_text = pytesseract.image_to_string(img, lang="heb").strip()
        except Exception as e:
            logger.debug("tesseract page %d failed: %s", i, e)
            page_text = ""
        if page_text:
            out.append(f"--- עמוד {i} (OCR) ---\n{page_text}")
    return "\n\n".join(out).strip()


def extract_text_layer_with_source(
    file_bytes: bytes, timing: dict | None = None,
) -> tuple[str, str]:
    """Pull the text layer from a PDF and say WHERE it came from.

    Returns `(text, source)` with source in {"layer", "ocr", "none"}.

    The source is not cosmetic. `_value_appears_in_text` — the guard that drops
    fabricated rates — returns True unconditionally when the text is empty, so
    on a scanned agreement with no OCR it silently switches itself off. The
    caller has to know that happened in order to say so; see `extract_pdf`.

    Each page is separated with a marker so Claude can cite page numbers.
    When `timing` is given, it receives `pages`, `t_layer` and `t_ocr` (secs).
    """
    text = ""
    source = "none"
    pages = 0
    t0 = time.monotonic()
    try:
        out: list[str] = []
        with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
            pages = len(pdf.pages)
            for i, page in enumerate(pdf.pages, start=1):
                try:
                    page_text = page.extract_text() or ""
                except Exception as e:  # pdfplumber occasionally chokes on a single page
                    logger.debug(f"pdfplumber page {i} failed: {e}")
                    page_text = ""
                page_text = page_text.strip()
                if page_text:
                    out.append(f"--- עמוד {i} ---\n{page_text}")
        text = "\n\n".join(out).strip()
        if text:
            source = "layer"
    except Exception as e:
        logger.warning(f"pdfplumber extraction failed: {e}")
        text = ""
    t_layer = time.monotonic() - t0
    t_ocr = 0.0

    # Scanned / image-only PDF (little or no embedded text) → Hebrew OCR. Only
    # when the embedded layer is essentially absent, so text-native PDFs stay
    # fast (no rasterization).
    if len(text) < _MIN_TEXT_LAYER_CHARS:
        logger.info(
            "Embedded text layer %d chars (< %d) — running Hebrew OCR fallback",
            len(text), _MIN_TEXT_LAYER_CHARS,
        )
        t1 = time.monotonic()
        ocr = _ocr_pdf(file_bytes)
        t_ocr = time.monotonic() - t1
        if len(ocr) > len(text):
            text = ocr
            source = "ocr"

    if not text:
        source = "none"
    if len(text) > _MAX_TEXT_LAYER_CHARS:
        text = text[:_MAX_TEXT_LAYER_CHARS] + "\n\n[... text layer truncated ...]"
    if timing is not None:
        timing.update(pages=pages, t_layer=round(t_layer, 1), t_ocr=round(t_ocr, 1))
    return text, source


def extract_text_layer(file_bytes: bytes) -> str:
    """Back-compat wrapper — the text only. Prefer the `_with_source` variant."""
    return extract_text_layer_with_source(file_bytes)[0]


# The extraction runs as TWO concurrent calls over the same document — one
# writes the rates table, the other the summary/full_content. Measured on
# kiko's 15 agreements (2026-09-24): upload time tracked how much Hebrew the
# model WROTE (74s for a short summary, 238s for Menora's 10K-char
# full_content + 51 rates), so doing both halves in one tool call serialised
# them. The prompt is split along the same seam; each half is unchanged.
_PROMPT_INTRO = """אתה קורא מסמכים של חברות ביטוח (הסכמי עמלות, חוזרים, טבלאות אחוזים) ומחלץ מהם נתונים מובנים.

זוהי הקריאה היחידה שלך למסמך — לאחר מכן ה-AI יענה על שאלות המשתמש על המסמך אך ורק על בסיס הפלט שלך.
"""

_PROMPT_RATES = """
==========================================================================
חלק 1 — טבלת ה-rates (הכי חשוב — מוזרם ישירות ל-DB; שגיאות כאן משבשות חישובי עמלה):
==========================================================================

**מהו rate?** אך ורק **עמלת נפרעים שוטפת** — האחוז שהסוכן מקבל שוב ושוב (חודשי/שנתי)
על הפרמיה או על הצבירה של לקוח קיים. סימני זיהוי: "עמלת נפרעים", "עמלת ספר",
"שיעור תגמול", "עמלת טיפול", "עמלה מצבירה", "עמלה מפרמיה", "לאורך כל חיי הפוליסה".

**אסור להכניס ל-rates (אלה שייכים ל-full_content בלבד, לא לטבלה):**
- עמלת **היקף** / **תפוקה** / **יעדים** / "מענק גיוס" / "לכל מיליון" / "% מתפוקה" —
  עמלות חד-פעמיות על גיוס חדש, לא נפרעים. הכנסתן לטבלה משבשת את חישוב העמלות.
- **Clawback / החזר עמלה / החזר מענק / ניכוי ביטול / קנס** — אחוזי החזר, לא עמלה.
- כל שורה שאינה עמלה שוטפת שהסוכן מרוויח על לקוח קיים.

**חוקי חילוץ (אל תפר):**
1. **שלמות** — אם במסמך יש טבלת נפרעים, חובה להחזיר שורה אחת לכל מוצר/כיסוי בטבלה.
   אל תסתפק בסיכום הטבלה ב-full_content — כל שורת נפרעים חייבת להופיע גם ב-rates.
2. **אסור להמציא** — כל מספר ב-components חייב להופיע מילולית במסמך. עדיף שורה אחת
   נכונה מאשר שלוש מומצאות. אל תוסיף "תוספת" שלא כתובה, ואל תחשב סה״כ בעצמך
   (השאר total_rate_percent=null כשלא מודפס סה״כ).
3. **מוצר אחד לכל שורה** — אל תמזג שני סוגי מוצר לשם אחד. אם עמלה חלה רק על
   גמל/השתלמות, שדה product לא יכלול "פנסיה". פנסיה, גמל והשתלמות — שורות נפרדות.
4. **ספר + תוספת** — במוצרי ריסק/ביטוח שמוצגות להם גם "עמלת ספר" וגם
   "שיעור תגמול"/"תוספת" — החזר את שניהם כרכיבים נפרדים (kind=book ו-kind=reward).
   הנפרע הסופי הוא הסכום שלהם. אל תחזיר רק את התוספת בלי הספר.
5. **kind** לכל רכיב, מהסט הסגור: `book` (עמלת ספר), `reward` (שיעור תגמול/תוספת),
   `total` (סה״כ מודפס במסמך — לא חישוב שלך), `single` (מספר יחיד למוצר),
   `addition` (שורת תוספת נלווית — לא נשמרת כשורה עצמאית).
6. **טווח שנים** — אם למוצר יש עמודות שנים (1-5 / 6-15 / 16 ומעלה), החזר ערך לכל
   שנה כרכיב נפרד ורשום את הטווח ב-`scope` (למשל "שנה 1-5"). כך המערכת תוכל בהמשך
   להחיל את השיעור לפי גיל הפוליסה.
7. **דוגמה נכונה**: למוצר "השתלות וטיפולים מיוחדים" מוצגות עמלת ספר `15%`/`15%`/`5%`
   (שנים 1-5 / 6-15 / 16+) ושיעור תגמול `7.2%`/`7.2%` (6-15 / 16+) → החזר בדיוק 5
   רכיבים, kind=book/reward, scope לכל אחד, product="השתלות וטיפולים מיוחדים".
   אסור להמציא "תוספת" או "סה״כ" שלא מודפסים.
8. אם יש טווח אחוזים (למשל "0.4%–0.6%"), החזר את שני הקצוות כשתי רשומות עם הערה ב-`notes`.

**תוקף ההסכם** — על **כל** רשומת rate שים effective_from / effective_to (YYYY-MM-DD).
חפש ב"תוקף"/"מועדי תוקף" (למשל "01/01/2025 עד 31/12/2026"). זה קובע איזה הסכם חל
על איזו פוליסה (פוליסה משנת 2018 נשפטת לפי הסכם 2018). אם אין תאריכים — השאר ריק.
"""

_PROMPT_CONTENT = """
==========================================================================
חלק 2 — full_content (סיכום מובנה בעברית Markdown, עד ~2500 מילים):
==========================================================================
כלול (אם קיים במסמך; אם נושא לא קיים — דלג):
1. פרטי הצדדים (חברות, סוכן, תאריכים, מועדי תוקף).
2. **טבלאות שיעורי עמלה** לפי קטגוריות (חיים/ריסק, בריאות, פנסיה/גמל, רכוש/כללי).
3. **עמלות היקף / תפוקה / יעדים** — שיעורים חד-פעמיים על גיוס (כאן בלבד, לא ב-rates).
4. **תנאי החזר עמלה / Clawback / ניכויי ביטולים** — חובה! כמעט בכל הסכם יש סעיף כזה.
   חפש: 'ביטול','החזר','ניכוי','פדיון','משיכה','ניוד','מחיקת תפוקה','Clawback'.
   כלול את כל טבלת אחוזי ההחזר לפי משך זמן ואת הטריגרים (כאן בלבד, לא ב-rates).
5. **תנאים מיוחדים** — בלעדיות, מינימום תפוקה, יעדים, סנקציות.
6. **חידוש / הארכה / סיום**.
7. **חתימות ותאריכים**.

`companies`: שמות חברות עיקריות בלבד. `summary`: 2–3 משפטים בעברית.
"""

RATES_SYSTEM_PROMPT = (
    _PROMPT_INTRO + _PROMPT_RATES
    + "\nבקריאה זו החזר את שורות ה-rates, את doc_type ואת companies (שמות חברות "
    "עיקריות בלבד), ו-summary של משפט אחד. אל תכתוב סיכום מלא.\n"
)
CONTENT_SYSTEM_PROMPT = (
    _PROMPT_INTRO
    + "\nבקריאה זו כתוב את full_content / summary / companies / doc_type בלבד — "
    "טבלת ה-rates המובנית נשלפת בקריאה נפרדת, אך full_content עדיין חייב לתאר את "
    "טבלאות העמלה כפי שמפורט למטה.\n"
    + _PROMPT_CONTENT
)


EXTRACT_TOOL = {
    "name": "save_extracted_document",
    "description": "שמירת התוכן המובנה שחולץ ממסמך ביטוח לשימוש עתידי של ה-AI.",
    "input_schema": {
        "type": "object",
        "required": ["doc_type", "companies", "summary", "full_content", "rates"],
        "properties": {
            "doc_type": {
                "type": "string",
                "enum": ["commission_agreement", "rate_sheet", "policy_terms", "other"],
            },
            "companies": {
                "type": "array",
                "items": {"type": "string"},
            },
            "summary": {"type": "string"},
            "full_content": {
                "type": "string",
                "description": "תוכן מקיף ומובנה בעברית ב-Markdown (~2500 מילים מקסימום).",
            },
            "rates": {
                "type": "array",
                "items": {
                    "type": "object",
                    "required": ["company", "components"],
                    "properties": {
                        "company": {"type": "string"},
                        "product": {"type": ["string", "null"]},
                        "components": {
                            "type": "array",
                            "description": (
                                "ONE row PER ongoing נפרעים rate cell PRINTED in the "
                                "document. Each component is a single number "
                                "(kind+rate_percent) that appears literally in the doc. "
                                "NEVER add fabricated rows. NEVER put one-time "
                                "scope/היקף/תפוקה/יעדים/מענק-גיוס rates or "
                                "Clawback/החזר/refund percentages here — those belong "
                                "in full_content only."
                            ),
                            "items": {
                                "type": "object",
                                "required": ["kind", "rate_percent"],
                                "properties": {
                                    "kind": {
                                        "type": "string",
                                        "enum": ["book", "reward", "addition", "total", "single"],
                                    },
                                    "rate_percent": {"type": "number"},
                                    "scope": {
                                        "type": ["string", "null"],
                                        "description": (
                                            "Policy-year band this rate applies to, "
                                            "e.g. 'שנה 1-5' / 'שנה 6-15' / 'שנה 16+'. "
                                            "Fill it whenever the table has year columns."
                                        ),
                                    },
                                },
                            },
                        },
                        "total_rate_percent": {
                            "type": ["number", "null"],
                            "description": (
                                "ONLY when the document LITERALLY PRINTS a "
                                "סה״כ value. Never the result of arithmetic you "
                                "performed yourself. Leave null when not printed."
                            ),
                        },
                        "rate_percent": {
                            "type": ["number", "null"],
                            "description": (
                                "DEPRECATED — kept for legacy callers. Prefer "
                                "components[]. If you have only one number for "
                                "the row, also expose it via components[0]."
                            ),
                        },
                        "frequency": {"type": ["string", "null"]},
                        "notes": {"type": ["string", "null"]},
                        "effective_from": {
                            "type": ["string", "null"],
                            "description": "Agreement validity start, YYYY-MM-DD. Same value across all rates from one agreement.",
                        },
                        "effective_to": {
                            "type": ["string", "null"],
                            "description": "Agreement validity end, YYYY-MM-DD.",
                        },
                    },
                },
            },
        },
    },
}


# Focused rates-only extraction — used as a fallback when the main pass returns
# an empty rates[] but the text layer clearly holds a rate table (the מנורה
# failure: the whole ~40-product table was captured into full_content while
# rates[] came back empty). Reuses the exact rates sub-schema from EXTRACT_TOOL.
RATES_ONLY_TOOL = {
    "name": "save_rates",
    "description": "שמירת שורות עמלת הנפרעים שחולצו מטבלת הסכם עמלות.",
    "input_schema": {
        "type": "object",
        "required": ["rates"],
        "properties": {"rates": EXTRACT_TOOL["input_schema"]["properties"]["rates"]},
    },
}

# The content half of the split extraction: everything EXTRACT_TOOL asks for
# except rates[], which the concurrent rates call (RATES_ONLY_TOOL) returns.
CONTENT_TOOL = {
    "name": "save_document_content",
    "description": EXTRACT_TOOL["description"],
    "input_schema": {
        "type": "object",
        "required": ["doc_type", "companies", "summary", "full_content"],
        "properties": {
            k: v for k, v in EXTRACT_TOOL["input_schema"]["properties"].items()
            if k != "rates"
        },
    },
}

# The rates call used by `extract_pdf`. Same rates schema, plus the few fields
# that place the document on the shelf even when it yields no rates
# (`/commission-rates/agreements` falls back to companies_mentioned) — so a
# rates-only upload doesn't need the slow content call at all.
RATES_DOC_TOOL = {
    "name": "save_rates",
    "description": RATES_ONLY_TOOL["description"],
    "input_schema": {
        "type": "object",
        "required": ["doc_type", "companies", "rates"],
        "properties": {
            "doc_type": EXTRACT_TOOL["input_schema"]["properties"]["doc_type"],
            "companies": EXTRACT_TOOL["input_schema"]["properties"]["companies"],
            "summary": {
                "type": "string",
                "description": "משפט אחד בעברית: איזה הסכם זה (חברה, סוג, תקופה).",
            },
            "rates": EXTRACT_TOOL["input_schema"]["properties"]["rates"],
        },
    },
}

RATES_ONLY_SYSTEM_PROMPT = """אתה מחלץ אך ורק את שורות **עמלת הנפרעים** מטבלת הסכם עמלות. אל תסכם — החזר שורות מובנות.

**מהו rate?** רק עמלת נפרעים שוטפת — האחוז שהסוכן מקבל שוב ושוב על הפרמיה או הצבירה
של לקוח קיים ("עמלת נפרעים", "עמלת ספר", "שיעור תגמול", "עמלת טיפול", "עמלה מצבירה",
"לאורך כל חיי הפוליסה").

**אסור להחזיר**: עמלת היקף/תפוקה/יעדים/מענק גיוס/"לכל מיליון"/"% מתפוקה" (חד-פעמי),
ו-Clawback/החזר/ניכוי ביטול/קנס (החזרים). אלה אינם נפרעים.

חוקים: (1) שורה אחת לכל מוצר/כיסוי בטבלה — שלמות מלאה. (2) כל מספר חייב להופיע
מילולית בטקסט; אל תמציא. (3) מוצר אחד לכל שורה — אל תמזג גמל+פנסיה. (4) כשמוצג גם
עמלת ספר וגם שיעור תגמול/תוספת — החזר את שניהם (kind=book ו-kind=reward), הנפרע הוא
הסכום. (5) עמודות שנים (1-5/6-15/16+) → רכיב לכל שנה עם הטווח ב-scope. (6) שים
effective_from/effective_to (YYYY-MM-DD) אם כתובים.
"""


def _value_appears_in_text(value: float, text: str) -> bool:
    """Return True when `value` appears literally in `text` as a percentage or
    plain number. Used to detect fabricated rate components (the test1-3 bug:
    AI invented `תוספת 10.4%` which never appears in the Phoenix PDF)."""
    if not text:
        return True  # No text layer — skip the check
    # Format both "10.4" and "10.40" and "10" variants
    candidates: set[str] = set()
    # 1-decimal
    candidates.add(f"{value:.1f}")
    # 2-decimal
    candidates.add(f"{value:.2f}")
    # Integer form when exact
    if abs(value - int(value)) < 1e-9:
        candidates.add(str(int(value)))
    # Hebrew/Israeli decimal sometimes uses comma
    candidates.update({c.replace(".", ",") for c in list(candidates)})
    for c in candidates:
        if c in text:
            return True
    return False


def _normalize_and_validate_rates(
    rates: list[dict], text_layer: str, dropped: list[dict] | None = None,
) -> list[dict]:
    """Normalise the model output and drop fabricated rate components.

    Pass a list as `dropped` to collect WHY each row was rejected. Every reject
    here used to be a `logger.warning` + `continue` with no user-visible
    surface at all, so an agent who saw "חולצו 12 שיעורי עמלה" had no way to
    learn that 30 more had been thrown away. The selection side has had
    `explain_expected_commission` for exactly this reason; this is its
    counterpart on the extraction side.

    Rules:
    - Legacy `rate_percent` (no components) is rewritten as a single
      `components=[{kind:"single", rate_percent: X}]` for downstream code.
    - Each component whose rate_percent does NOT appear literally in the
      text layer is dropped + logged (`viz_extraction.fabricated_rate`).
      Skipped when no text_layer (scanned PDF — we can't check).
    - `total_rate_percent` is nullified when it doesn't appear literally
      (prevents the AI from "summing" two components into a fake total).
    """
    normalized: list[dict] = []

    def _drop(reason: str, r: dict, **extra) -> None:
        if dropped is None:
            return
        dropped.append({
            "company": (r.get("company") or None),
            "product": (r.get("product") or None),
            "reason": reason,
            **extra,
        })

    for r in rates:
        if not isinstance(r, dict):
            continue

        # Guard: drop rows that are one-time scope/היקף grants or Clawback/refund
        # percentages, not ongoing נפרעים commissions. Identified by markers in
        # the product name or notes (e.g. "מענק גיוס חדש — עמלת היקף", "Clawback").
        row_marker_text = f"{r.get('product') or ''} {r.get('notes') or ''}"
        if _NON_COMMISSION_RE.search(row_marker_text):
            logger.warning(
                "viz_extraction.non_commission_rate_dropped company=%s product=%s "
                "(scope/היקף or clawback — not a נפרעים rate)",
                r.get("company"), r.get("product"),
            )
            _drop("non_commission_filter", r)
            continue

        components_raw = r.get("components")
        components: list[dict] = []
        if isinstance(components_raw, list):
            for c in components_raw:
                if not isinstance(c, dict):
                    continue
                kind = (c.get("kind") or "single").strip().lower()
                if kind not in {"book", "reward", "addition", "total", "single"}:
                    kind = "single"
                try:
                    rp = float(c.get("rate_percent"))
                except (TypeError, ValueError):
                    continue
                if rp <= 0 or rp > 100:
                    continue
                # Drop components whose scope marks them as scope/היקף/clawback
                # (the year-band scope like "שנה 1-5" never matches these markers).
                scope_raw = c.get("scope")
                if scope_raw and _NON_COMMISSION_RE.search(str(scope_raw)):
                    logger.warning(
                        "viz_extraction.non_commission_rate_dropped company=%s product=%s "
                        "scope=%s value=%s (scope/clawback component)",
                        r.get("company"), r.get("product"), scope_raw, rp,
                    )
                    _drop("non_commission_scope", r, percent=rp, scope=str(scope_raw))
                    continue
                if not _value_appears_in_text(rp, text_layer):
                    logger.warning(
                        "viz_extraction.fabricated_rate company=%s product=%s kind=%s value=%s "
                        "(not found literally in pdf text layer — dropped)",
                        r.get("company"), r.get("product"), kind, rp,
                    )
                    _drop("value_not_in_text", r, percent=rp, kind=kind)
                    continue
                comp = {"kind": kind, "rate_percent": rp}
                scope = c.get("scope")
                if scope:
                    comp["scope"] = str(scope).strip()
                components.append(comp)
        # Legacy fallback — model returned just rate_percent (older clients)
        if not components and r.get("rate_percent") is not None:
            try:
                rp = float(r.get("rate_percent"))
                if 0 < rp <= 100 and _value_appears_in_text(rp, text_layer):
                    components.append({"kind": "single", "rate_percent": rp})
            except (TypeError, ValueError):
                pass

        if not components:
            # Whole row was fabricated or unparseable — drop it.
            logger.warning(
                "viz_extraction.empty_rate_row dropped company=%s product=%s",
                r.get("company"), r.get("product"),
            )
            _drop("no_usable_component", r)
            continue

        # total_rate_percent: keep only if literally in text
        total = r.get("total_rate_percent")
        if total is not None:
            try:
                total_f = float(total)
                if not (0 < total_f <= 100 and _value_appears_in_text(total_f, text_layer)):
                    logger.warning(
                        "viz_extraction.fabricated_total company=%s product=%s value=%s "
                        "(not found literally — nullified)",
                        r.get("company"), r.get("product"), total_f,
                    )
                    total = None
                else:
                    total = total_f
            except (TypeError, ValueError):
                total = None

        # Choose a representative rate_percent for legacy DB inserts:
        # prefer total → single → book → reward (in that order).
        rep = total
        if rep is None:
            by_kind = {c["kind"]: c["rate_percent"] for c in components}
            for k in ("single", "total", "book", "reward"):
                if k in by_kind:
                    rep = by_kind[k]
                    break

        normalized.append({
            "company": r.get("company"),
            "product": r.get("product"),
            "components": components,
            "total_rate_percent": total,
            "rate_percent": rep,  # legacy field, for back-compat
            "frequency": r.get("frequency"),
            "notes": r.get("notes"),
            "effective_from": r.get("effective_from"),
            "effective_to": r.get("effective_to"),
        })
    return normalized


# A signed agreement often carries no rate table at all: it defers the numbers
# to a נספח (appendix) that is a physically separate sheet, and the scan the
# agent has is only the body. Measured on the live ילין לפידות agreement — 5
# scanned pages whose §4.1 reads "כמפורט בנספח א' להסכם זה", with no נספח א'
# attached. "0 rates" is then the CORRECT answer, and the only useful thing the
# app can do is name the missing document instead of showing a blank shelf.
_APPENDIX_RE = re.compile(
    r"נספח\s*(?:ה?תמורה|[א-ה]['׳]?)"
)
_APPENDIX_CONTEXT_RE = re.compile(r"תמורה|עמלה|עמלות|שיעור")


def _appendix_reference(*texts: str | None) -> str | None:
    """Return the appendix label an agreement defers its rates to, if any.

    Requires a compensation word near the mention, so a נספח about privacy or
    signatures doesn't get reported as the missing rate table.
    """
    for text in texts:
        if not text:
            continue
        for m in _APPENDIX_RE.finditer(text):
            window = text[max(0, m.start() - 120): m.end() + 120]
            if _APPENDIX_CONTEXT_RE.search(window):
                return m.group(0).strip()
    return None


def _looks_like_rate_table(text_layer: str) -> bool:
    """Heuristic: does the text layer clearly contain a rate table? Used to
    decide whether an empty rates[] is a real absence or an extraction miss."""
    return bool(text_layer) and text_layer.count("%") >= 15


async def _extract_rates_only(
    client: "anthropic.AsyncAnthropic", text_layer: str, filename: str
) -> list[dict]:
    """Second, focused pass: extract ONLY נפרעים rate rows from the text layer.

    Runs on the pdfplumber/OCR text alone (no PDF images → fast) with a tight
    rates-only schema. Returns the RAW rates list (caller normalizes)."""
    async with _CLAUDE_SLOTS:
        resp = await client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=16384,
            system=RATES_ONLY_SYSTEM_PROMPT,
            tools=[RATES_ONLY_TOOL],
            tool_choice={"type": "tool", "name": "save_rates"},
            messages=[{
                "role": "user",
                "content": [{
                    "type": "text",
                    "text": (
                        f"שם הקובץ: {filename}\n\n"
                        "טקסט מלא של ההסכם:\n\n"
                        f"{text_layer}\n\n"
                        "חלץ כל שורת עמלת נפרעים מהטבלאות שלמעלה."
                    ),
                }],
            }],
        )
    for block in resp.content:
        if getattr(block, "type", None) == "tool_use" and getattr(block, "name", "") == "save_rates":
            raw = getattr(block, "input", None)
            if isinstance(raw, dict):
                rates = raw.get("rates") or []
                return rates if isinstance(rates, list) else []
    return []


# Sonnet 4.6 reads complex Hebrew RTL agreements (scrambled pdfplumber text +
# PDF images) far more reliably than 4.0, which silently returned `rates=[]`
# on the Menora 2025 insurance agreement even though it set summary/doc_type.
# max_tokens 16384: full_content alone is ~2500 words (~6K tokens) and a long
# agreement's rates array can be as large again.
_MODEL_LADDER = (
    ("claude-sonnet-4-6", 0),
    ("claude-sonnet-4-6", 2),
    ("claude-haiku-4-5-20251001", 1),
)

# Every upload makes two concurrent calls, and the shelf uploads several files
# at once — bound how many generations this process runs against Anthropic so a
# batch of 15 agreements queues here instead of tripping rate limits.
_CLAUDE_SLOTS = asyncio.Semaphore(6)


async def _forced_tool_call(
    client: "anthropic.AsyncAnthropic",
    *,
    label: str,
    system: str,
    tool: dict,
    blocks: list[dict],
    timing: dict,
) -> dict:
    """One forced tool call walked down `_MODEL_LADDER`. Returns the tool input
    dict and records model/attempt/secs/tokens/stop under `timing[label]` —
    without those numbers a slow upload can't be told apart from a retry storm."""
    last_error: Exception | None = None
    for attempt, (model, delay) in enumerate(_MODEL_LADDER, start=1):
        if delay:
            await asyncio.sleep(delay)
        async with _CLAUDE_SLOTS:
            t0 = time.monotonic()
            try:
                resp = await client.messages.create(
                    model=model,
                    max_tokens=16384,
                    system=system,
                    tools=[tool],
                    tool_choice={"type": "tool", "name": tool["name"]},
                    messages=[{"role": "user", "content": blocks}],
                )
            except anthropic.APIError as e:
                last_error = e
                logger.warning(
                    "doc_extraction.%s attempt=%d model=%s failed after %.1fs: %s",
                    label, attempt, model, time.monotonic() - t0, e,
                )
                continue
            secs = time.monotonic() - t0
        usage = getattr(resp, "usage", None)
        timing[label] = {
            "model": model,
            "attempt": attempt,
            "secs": round(secs, 1),
            "in_tok": getattr(usage, "input_tokens", None),
            "out_tok": getattr(usage, "output_tokens", None),
            "stop": getattr(resp, "stop_reason", None),
        }
        for block in resp.content:
            if getattr(block, "type", None) == "tool_use" and getattr(block, "name", "") == tool["name"]:
                raw = getattr(block, "input", None)
                if isinstance(raw, dict):
                    return raw
        last_error = ValueError(f"{model} did not return a {tool['name']} tool_use block")
        logger.warning("doc_extraction.%s attempt=%d: %s", label, attempt, last_error)
    raise ValueError(f"{label} extraction failed after all retries: {last_error}")


async def extract_pdf(file_bytes: bytes, filename: str, rates_only: bool = False) -> dict:
    """Send a PDF to Claude and return parsed structured output.

    Two forced tool calls run concurrently over the same document — rates
    (RATES_DOC_TOOL) and content (CONTENT_TOOL) — so the upload waits for the
    longer of the two generations instead of their sum. Includes the
    pdfplumber/OCR text layer under `text_layer` (chat re-attaches it on
    doc-oriented questions).

    `rates_only` skips the content call. The agreement shelf only needs the
    rates, and the content call (5–9K tokens of Hebrew full_content) was the
    slowest part of every upload: measured 117–209s against 4–100s for rates
    on kiko's agreements (2026-09-24). Chat Q&A still works on such a document
    — it re-attaches the stored PDF itself.
    """
    if not settings.ANTHROPIC_API_KEY:
        raise RuntimeError("ANTHROPIC_API_KEY is not configured")

    t_start = time.monotonic()
    timing: dict = {}
    text_layer, text_source = await asyncio.to_thread(
        extract_text_layer_with_source, file_bytes, timing
    )
    has_text_layer = len(text_layer) >= _MIN_TEXT_LAYER_CHARS

    pdf_b64 = base64.standard_b64encode(file_bytes).decode("ascii")
    # Retries are owned by `_MODEL_LADDER`; SDK-level retries on top of it
    # would silently multiply one bad multi-minute generation. 600s: a full
    # 16K-token generation at the measured ~45–55 tok/s is 300–370s, so a
    # shorter timeout would cut off legitimate long agreements.
    client = anthropic.AsyncAnthropic(
        api_key=settings.ANTHROPIC_API_KEY, max_retries=0, timeout=600,
    )

    def _blocks(instruction: str) -> list[dict]:
        if has_text_layer:
            instruction += (
                "\n\n**מצורף שכבת הטקסט המלאה של ה-PDF (pdfplumber)**. "
                "השתמש בה כמקור אמת לשמות מוצרים, מספרים, ושמות סעיפים — "
                "ב-PDF המצורף יש גם תמונות עמוד אם תזדקק להן לפריסת טבלאות."
            )
        blocks: list[dict] = [{
            "type": "document",
            "source": {"type": "base64", "media_type": "application/pdf", "data": pdf_b64},
        }]
        if has_text_layer:
            blocks.append({
                "type": "text",
                "text": f"### שכבת טקסט מה-PDF (לקריאה דטרמיניסטית):\n\n{text_layer}",
            })
        blocks.append({"type": "text", "text": f"שם הקובץ: {filename}\n\n{instruction}"})
        return blocks

    t_claude = time.monotonic()
    rates_call = _forced_tool_call(
        client, label="rates", system=RATES_SYSTEM_PROMPT, tool=RATES_DOC_TOOL,
        blocks=_blocks(
            "קרא את המסמך וקרא ל-save_rates עם כל שורות עמלת הנפרעים שבו."
        ),
        timing=timing,
    )
    if rates_only:
        rates_input = await rates_call
        content_input = {}
    else:
        content_input, rates_input = await asyncio.gather(
            _forced_tool_call(
                client, label="content", system=CONTENT_SYSTEM_PROMPT, tool=CONTENT_TOOL,
                blocks=_blocks(
                    "קרא את המסמך וקרא ל-save_document_content עם כל השדות הנדרשים. "
                    "full_content צריך לכסות את כל הסעיפים החשובים, אבל תמציתית — עד ~2500 מילים."
                ),
                timing=timing,
            ),
            rates_call,
        )
    timing["t_claude"] = round(time.monotonic() - t_claude, 1)
    # The content call owns doc_type/companies/summary when it runs; the
    # rates call's copies fill in when it doesn't.
    doc_fields = {**rates_input, **{k: v for k, v in content_input.items() if v}}

    companies = doc_fields.get("companies") or []
    if not isinstance(companies, list):
        companies = []
    rates = rates_input.get("rates") or []
    if not isinstance(rates, list):
        rates = []

    dropped: list[dict] = []
    normalized = _normalize_and_validate_rates(
        rates, text_layer if has_text_layer else "", dropped
    )

    # Fallback: the rates call returned nothing usable but the text layer
    # clearly holds a rate table (the מנורה miss). One more focused pass over
    # the text alone to recover the table.
    if not normalized and has_text_layer and _looks_like_rate_table(text_layer):
        logger.warning(
            "viz_extraction.empty_rates_fallback file=%s — rates pass returned 0 "
            "rates but text layer has a rate table; running text-only rates pass",
            filename,
        )
        try:
            fb_rates = await _extract_rates_only(client, text_layer, filename)
            dropped = []
            rates = fb_rates
            normalized = _normalize_and_validate_rates(fb_rates, text_layer, dropped)
            logger.info(
                "viz_extraction.empty_rates_fallback file=%s recovered=%d rows",
                filename, len(normalized),
            )
        except (ValueError, anthropic.APIError) as e:
            logger.warning("viz_extraction.empty_rates_fallback failed file=%s: %s", filename, e)

    if not normalized and _looks_like_rate_table(text_layer):
        logger.warning(
            "viz_extraction.zero_rates_after_fallback file=%s — a rate table "
            "appears present but no נפרעים rows were extracted; needs review",
            filename,
        )

    full_content = (doc_fields.get("full_content") or "").strip() or None

    # Why the shelf is about to not move. Without this the UI has
    # nothing to say and stays silent (see `stores/chat.js`), which
    # reads to the agent as "the upload did nothing".
    appendix = _appendix_reference(text_layer, full_content)
    zero_reason = None
    if not normalized:
        if dropped:
            zero_reason = "all_rows_dropped"
        elif appendix:
            zero_reason = "appendix_missing"
        elif _looks_like_rate_table(text_layer):
            zero_reason = "rate_table_present_but_unparsed"
        elif text_source == "none":
            zero_reason = "no_readable_text"
        else:
            zero_reason = "no_rates_in_document"

    timing["total"] = round(time.monotonic() - t_start, 1)
    ct, rt = timing.get("content", {}), timing.get("rates", {})
    # WARNING, not INFO: app INFO lines never reach Railway's log stream.
    logger.warning(
        "doc_extraction.timing file=%s pages=%s src=%s t_layer=%s t_ocr=%s "
        "content=%ss/%s/att%s/in%s/out%s/%s rates=%ss/%s/att%s/in%s/out%s/%s "
        "t_claude=%s total=%s",
        filename, timing.get("pages"), text_source, timing.get("t_layer"), timing.get("t_ocr"),
        ct.get("secs"), ct.get("model"), ct.get("attempt"), ct.get("in_tok"), ct.get("out_tok"), ct.get("stop"),
        rt.get("secs"), rt.get("model"), rt.get("attempt"), rt.get("in_tok"), rt.get("out_tok"), rt.get("stop"),
        timing.get("t_claude"), timing["total"],
    )

    return {
        "doc_type": doc_fields.get("doc_type") or "other",
        "companies": [str(c).strip() for c in companies if c],
        "summary": (doc_fields.get("summary") or "").strip() or None,
        "full_content": full_content,
        "rates": normalized,
        "text_layer": text_layer or None,
        "text_source": text_source,
        "extraction": {
            "proposed": len(rates),
            "kept": len(normalized),
            "dropped": dropped,
            # False ⇒ `_value_appears_in_text` could not run, so nothing
            # here was checked against the document's own words.
            "verified": bool(has_text_layer),
            "text_source": text_source,
            "appendix_ref": appendix,
            "zero_reason": zero_reason,
            "mode": "rates_only" if rates_only else "full",
            "timing": timing,
        },
    }
