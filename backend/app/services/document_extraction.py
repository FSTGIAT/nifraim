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

import anthropic
import pdfplumber

from app.config import settings


logger = logging.getLogger(__name__)


# Below this length, we treat the text layer as essentially absent (likely a
# scanned PDF) and let Claude rely purely on vision.
_MIN_TEXT_LAYER_CHARS = 200
# Cap how much we forward as a text block to keep the call fast.
_MAX_TEXT_LAYER_CHARS = 60000


def extract_text_layer(file_bytes: bytes) -> str:
    """Pull the embedded text layer from a PDF using pdfplumber.

    Returns an empty string when the PDF is image-only / scanned, or when
    extraction fails for any reason. Each page is separated with a marker so
    Claude can cite page numbers in answers.
    """
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
        if len(text) > _MAX_TEXT_LAYER_CHARS:
            text = text[:_MAX_TEXT_LAYER_CHARS] + "\n\n[... text layer truncated ...]"
        return text
    except Exception as e:
        logger.warning(f"pdfplumber extraction failed: {e}")
        return ""


EXTRACTION_SYSTEM_PROMPT = """אתה קורא מסמכים של חברות ביטוח (הסכמי עמלות, חוזרים, טבלאות אחוזים) ומחלץ מהם נתונים מובנים.

זוהי הקריאה היחידה שלך למסמך — לאחר מכן ה-AI יענה על שאלות המשתמש על המסמך אך ורק על בסיס הפלט שלך. הקפד למלא את full_content בצורה מקיפה ומדויקת, אבל תמציתית (~2500 מילים מקסימום).

**מה חייב להיכלל ב-full_content (אם קיים במסמך):**
1. פרטי הצדדים (חברות, סוכן, תאריכים, מועדי תוקף).
2. **טבלאות שיעורי עמלה** — לפי קטגוריות (חיים/ריסק, בריאות, פנסיה/גמל, רכוש/כללי). כלול ספר + תוספת + סה״כ **רק כאשר המסמך מציג אותם בפועל**.
3. **עמלות היקף** — שיעורים חד-פעמיים על גיוס חדש.
4. **תנאי החזר עמלה / Clawback / ניכויי ביטולים** — חובה! כמעט בכל הסכם עמלה בישראל יש סעיף כזה. חפש לפי: 'ביטול', 'החזר', 'ניכוי', 'פדיון', 'משיכה', 'ניוד', 'מחיקת תפוקה', 'הפסקת גבייה', 'Clawback'. כלול את כל טבלת אחוזי ההחזר לפי משך זמן, ואת כל הטריגרים.
5. **תנאים מיוחדים** — בלעדיות, מינימום תפוקה, יעדים, סנקציות.
6. **חידוש / הארכה / סיום** — תקופת הסכם וכללי חידוש/ביטול.
7. **חתימות ותאריכים**.

==========================================================================
חוקים קריטיים לחילוץ rates (אל תפר — שגיאות כאן מוזרמות ישירות לטבלת ה-DB):
==========================================================================

1. **אסור להמציא עמודות**. אם המסמך מציג בטבלה רק עמודה אחת (לדוגמה: רק "עמלת ספר"), החזר רכיב אחד מסוג `single` או `book`. אל תוסיף "תוספת" שאינה כתובה במפורש, ואל תכפיל שורות.

2. **אסור לחבר ידנית סה״כ**. אם המסמך לא מציג עמודת "סה״כ" שכבר חושבה, השאר את `total_rate_percent` כ-null. אסור להחזיר rate_percent שהוא תוצאה של חיבור שני מספרים מהמסמך אלא אם הסה״כ עצמו מודפס שם.

3. **כל מספר באובייקט components חייב להופיע מילולית במסמך**. אם אתה לא בטוח שמספר מסוים נמצא בטקסט — דלג עליו. עדיף שורה אחת נכונה מאשר שלוש שורות מומצאות.

4. **לכל רכיב חייב להיות `kind`** מתוך הסט הסגור הבא:
   - `book` — עמלת ספר (שיעור בסיס לקטגוריה)
   - `reward` — שיעור תגמול / תוספת נפרעים מודפסת בנפרד
   - `addition` — שורת תוספת נפרדת (לא תיכנס ל-DB כשורה עצמאית — היא נשמרת רק לתיעוד)
   - `total` — סה״כ המודפס במסמך (לא חישוב שלך)
   - `single` — כשהמסמך מציג רק מספר אחד לכל מוצר ולא מבדיל בין רכיבים

5. **דוגמה נכונה לפלט**: אם המסמך מראה לטור "השתלות וטיפולים מיוחדים" את הערכים `15%`, `15%`, `5%` תחת "עמלת ספר" עם שלוש עמודות שנים (1-5 / 6-15 / 16+), והערכים `7.2%`, `7.2%` תחת "שיעור תגמול" לעמודות 6-15 / 16+ — החזר אך ורק את 5 הערכים האלה, כל אחד כרשומה נפרדת ב-`components`, עם `kind=book` / `kind=reward` ו-`product="השתלות וטיפולים מיוחדים"`. אסור להמציא עמודת "תוספת 10.4%" או "סה״כ 25.4%" — אלה לא קיימים במסמך.

6. אם יש טווח (לדוגמה "0.4%–0.6%"), החזר את שני קצוות הטווח כשתי רשומות עם הערה ב-`notes`.

7. `companies`: שמות חברות עיקריות בלבד.
8. `summary`: 2–3 משפטים בעברית.
9. אם נושא לא קיים במסמך — דלג עליו. אבל אם הוא כן קיים — חובה לכלול.

**תקופת תוקף ההסכם — חשוב מאוד:**
חפש בהקדמה / סעיפי "תוקף" / "מועדי תוקף" את התאריכים שמגדירים מתי ההסכם בתוקף
(לדוגמה: "תוקף הנספח: 01/01/2025 עד 31/12/2026"). חלץ אותם פעם אחת ושים אותם
ב-**כל** רשומת rate שאתה מחזיר, ב-effective_from / effective_to (בפורמט YYYY-MM-DD).
אם המסמך לא מציין תאריכים — השאר את השדות ריקים. הקפדה על השדות האלה חיונית
כדי שהמערכת תדע איזה הסכם להחיל על איזו פוליסה (פוליסה משנת 2018 צריכה להישפט
לפי הסכם 2018, לא לפי הסכם 2025).
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
                                "ONE row PER rate cell PRINTED in the document. "
                                "Each component is a single number (kind+rate_percent) "
                                "that appears literally in the doc. NEVER add "
                                "fabricated rows."
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
                                        "description": "Optional context, e.g. 'years 1-5' / 'years 16+'.",
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
