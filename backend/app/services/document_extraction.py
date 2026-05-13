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
2. **טבלאות שיעורי עמלה** — לפי קטגוריות (חיים/ריסק, בריאות, פנסיה/גמל, רכוש/כללי). כלול ספר + תוספת + סה״כ אם המסמך מבחין ביניהם.
3. **עמלות היקף** — שיעורים חד-פעמיים על גיוס חדש.
4. **תנאי החזר עמלה / Clawback / ניכויי ביטולים** — חובה! כמעט בכל הסכם עמלה בישראל יש סעיף כזה. חפש לפי: 'ביטול', 'החזר', 'ניכוי', 'פדיון', 'משיכה', 'ניוד', 'מחיקת תפוקה', 'הפסקת גבייה', 'Clawback'. כלול את כל טבלת אחוזי ההחזר לפי משך זמן, ואת כל הטריגרים.
5. **תנאים מיוחדים** — בלעדיות, מינימום תפוקה, יעדים, סנקציות.
6. **חידוש / הארכה / סיום** — תקופת הסכם וכללי חידוש/ביטול.
7. **חתימות ותאריכים**.

חוקים:
- full_content: Markdown — ## כותרות סעיף, טבלאות, רשימות.
- rates: רק שיעורי עמלה ממשיים מהמסמך. אל תמציא.
- rate_percent חייב להיות מספר. אם יש טווח, החזר את הממוצע.
- companies: שמות חברות עיקריות.
- summary: 2–3 משפטים בעברית.
- אם נושא לא קיים במסמך — דלג עליו. אבל אם הוא כן קיים — חובה לכלול.
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
                    "required": ["company", "rate_percent"],
                    "properties": {
                        "company": {"type": "string"},
                        "product": {"type": ["string", "null"]},
                        "rate_percent": {"type": "number"},
                        "frequency": {"type": ["string", "null"]},
                        "notes": {"type": ["string", "null"]},
                    },
                },
            },
        },
    },
}


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

    attempts = [
        ("claude-sonnet-4-20250514", 0),
        ("claude-sonnet-4-20250514", 2),
        ("claude-haiku-4-5-20251001", 1),
    ]
    last_error: Exception | None = None

    for model, delay in attempts:
        if delay:
            await asyncio.sleep(delay)
        try:
            resp = await client.messages.create(
                model=model,
                max_tokens=8192,
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

            return {
                "doc_type": tool_input.get("doc_type") or "other",
                "companies": [str(c).strip() for c in companies if c],
                "summary": (tool_input.get("summary") or "").strip() or None,
                "full_content": (tool_input.get("full_content") or "").strip() or None,
                "rates": rates,
                "text_layer": text_layer or None,
            }
        except (ValueError, anthropic.APIError, anthropic.APIStatusError) as e:
            last_error = e
            logger.warning(f"PDF extraction attempt with {model} failed: {e}")
            continue

    raise ValueError(f"Failed to extract PDF after all retries: {last_error}")
