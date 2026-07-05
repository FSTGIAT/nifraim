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


def extract_text_layer(file_bytes: bytes) -> str:
    """Pull the text layer from a PDF: pdfplumber first, Hebrew OCR fallback for
    scanned PDFs.

    Each page is separated with a marker so Claude can cite page numbers.
    Returns an empty string only when both pdfplumber and OCR yield nothing.
    """
    text = ""
    try:
        out: list[str] = []
        with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
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
    except Exception as e:
        logger.warning(f"pdfplumber extraction failed: {e}")
        text = ""

    # Scanned / image-only PDF (little or no embedded text) → Hebrew OCR. Only
    # when the embedded layer is essentially absent, so text-native PDFs stay
    # fast (no rasterization).
    if len(text) < _MIN_TEXT_LAYER_CHARS:
        logger.info(
            "Embedded text layer %d chars (< %d) — running Hebrew OCR fallback",
            len(text), _MIN_TEXT_LAYER_CHARS,
        )
        ocr = _ocr_pdf(file_bytes)
        if len(ocr) > len(text):
            text = ocr

    if len(text) > _MAX_TEXT_LAYER_CHARS:
        text = text[:_MAX_TEXT_LAYER_CHARS] + "\n\n[... text layer truncated ...]"
    return text


EXTRACTION_SYSTEM_PROMPT = """אתה קורא מסמכים של חברות ביטוח (הסכמי עמלות, חוזרים, טבלאות אחוזים) ומחלץ מהם נתונים מובנים.

זוהי הקריאה היחידה שלך למסמך — לאחר מכן ה-AI יענה על שאלות המשתמש על המסמך אך ורק על בסיס הפלט שלך.

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


def _normalize_and_validate_rates(rates: list[dict], text_layer: str) -> list[dict]:
    """Normalise the model output and drop fabricated rate components.

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
                    continue
                if not _value_appears_in_text(rp, text_layer):
                    logger.warning(
                        "viz_extraction.fabricated_rate company=%s product=%s kind=%s value=%s "
                        "(not found literally in pdf text layer — dropped)",
                        r.get("company"), r.get("product"), kind, rp,
                    )
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


async def extract_pdf(file_bytes: bytes, filename: str) -> dict:
    """Send a PDF to Claude and return parsed structured output.

    Uses tool_use so the response is always a validated dict matching
    EXTRACT_TOOL.input_schema. Includes the pdfplumber-extracted text layer
    in the response under the `text_layer` key (consumed by chat to attach
    deterministic text alongside the page-images on doc-oriented questions).
    """
    if not settings.ANTHROPIC_API_KEY:
        raise RuntimeError("ANTHROPIC_API_KEY is not configured")

    text_layer = await asyncio.to_thread(extract_text_layer, file_bytes)
    has_text_layer = len(text_layer) >= _MIN_TEXT_LAYER_CHARS

    pdf_b64 = base64.standard_b64encode(file_bytes).decode("ascii")
    client = anthropic.AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)

    instruction_text = (
        f"שם הקובץ: {filename}\n\n"
        "קרא את המסמך וקרא ל-save_extracted_document עם כל השדות הנדרשים. "
        "full_content צריך לכסות את כל הסעיפים החשובים, אבל תמציתית — עד ~2500 מילים."
    )
    if has_text_layer:
        instruction_text += (
            "\n\n**מצורף שכבת הטקסט המלאה של ה-PDF (pdfplumber)**. "
            "השתמש בה כמקור אמת לשמות מוצרים, מספרים, ושמות סעיפים — "
            "ב-PDF המצורף יש גם תמונות עמוד אם תזדקק להן לפריסת טבלאות."
        )

    user_blocks: list[dict] = [
        {
            "type": "document",
            "source": {
                "type": "base64",
                "media_type": "application/pdf",
                "data": pdf_b64,
            },
        },
    ]
    if has_text_layer:
        user_blocks.append({
            "type": "text",
            "text": f"### שכבת טקסט מה-PDF (לקריאה דטרמיניסטית):\n\n{text_layer}",
        })
    user_blocks.append({"type": "text", "text": instruction_text})

    # Sonnet 4.6 reads complex Hebrew RTL agreements (scrambled pdfplumber text +
    # PDF images) far more reliably than 4.0, which silently returned `rates=[]`
    # on the Menora 2025 insurance agreement even though it set summary/doc_type.
    # max_tokens bumped to 16384 because the tool call has to fit
    # full_content (~2500 words ≈ 6K tokens) AND a potentially long rates array.
    attempts = [
        ("claude-sonnet-4-6", 0),
        ("claude-sonnet-4-6", 2),
        ("claude-haiku-4-5-20251001", 1),
    ]
    last_error: Exception | None = None

    for model, delay in attempts:
        if delay:
            await asyncio.sleep(delay)
        try:
            resp = await client.messages.create(
                model=model,
                max_tokens=16384,
                system=EXTRACTION_SYSTEM_PROMPT,
                tools=[EXTRACT_TOOL],
                tool_choice={"type": "tool", "name": "save_extracted_document"},
                messages=[{"role": "user", "content": user_blocks}],
            )

            tool_input: dict | None = None
            for block in resp.content:
                if getattr(block, "type", None) == "tool_use" and getattr(block, "name", "") == "save_extracted_document":
                    raw = getattr(block, "input", None)
                    if isinstance(raw, dict):
                        tool_input = raw
                        break
            if tool_input is None:
                raise ValueError("Model did not return a tool_use block")

            companies = tool_input.get("companies") or []
            if not isinstance(companies, list):
                companies = []
            rates = tool_input.get("rates") or []
            if not isinstance(rates, list):
                rates = []

            normalized = _normalize_and_validate_rates(rates, text_layer if has_text_layer else "")

            # Fallback: main pass returned no rates but the text layer clearly
            # holds a rate table (the מנורה miss). Run one focused rates-only
            # pass over the text to recover the table.
            if not normalized and has_text_layer and _looks_like_rate_table(text_layer):
                logger.warning(
                    "viz_extraction.empty_rates_fallback file=%s — main pass returned 0 "
                    "rates but text layer has a rate table; running rates-only pass",
                    filename,
                )
                try:
                    fb_rates = await _extract_rates_only(client, text_layer, filename)
                    normalized = _normalize_and_validate_rates(fb_rates, text_layer)
                    logger.info(
                        "viz_extraction.empty_rates_fallback file=%s recovered=%d rows",
                        filename, len(normalized),
                    )
                except (ValueError, anthropic.APIError, anthropic.APIStatusError) as e:
                    logger.warning("viz_extraction.empty_rates_fallback failed file=%s: %s", filename, e)

            if not normalized and _looks_like_rate_table(text_layer):
                logger.warning(
                    "viz_extraction.zero_rates_after_fallback file=%s — a rate table "
                    "appears present but no נפרעים rows were extracted; needs review",
                    filename,
                )

            return {
                "doc_type": tool_input.get("doc_type") or "other",
                "companies": [str(c).strip() for c in companies if c],
                "summary": (tool_input.get("summary") or "").strip() or None,
                "full_content": (tool_input.get("full_content") or "").strip() or None,
                "rates": normalized,
                "text_layer": text_layer or None,
            }
        except (ValueError, anthropic.APIError, anthropic.APIStatusError) as e:
            last_error = e
            logger.warning(f"PDF extraction attempt with {model} failed: {e}")
            continue

    raise ValueError(f"Failed to extract PDF after all retries: {last_error}")
