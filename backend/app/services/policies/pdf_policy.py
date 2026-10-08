"""A policy PDF (an insurer's העתק פוליסה / דף פרטי ביטוח) → Markdown + metadata via Claude.

Reuses document_extraction: the pdfplumber text layer (Hebrew OCR when the PDF is a scan —
Phoenix/Menora "Print To PDF" copies are images) plus the PDF itself as a native document
block, so Claude reads the page images too. One forced tool call returns the Markdown and the
fields we index by (company, policy number, insured persons). Numbers are copied, never computed.
"""
from __future__ import annotations

import asyncio
import base64
import json
import logging
import time

import anthropic

from app.config import settings
from app.services.document_extraction import _MIN_TEXT_LAYER_CHARS, extract_text_layer_with_source

logger = logging.getLogger(__name__)

MODELS = ("claude-sonnet-5-5", "claude-sonnet-4-6")   # 5.x rejects forced tool_choice → structured outputs
_SLOTS = asyncio.Semaphore(4)

SYSTEM = """אתה ממיר פוליסות ביטוח ישראליות (העתק פוליסה, דף פרטי ביטוח, תנאים) למסמך Markdown נקי בעברית,
שסוכן ביטוח ובינה מלאכותית יקראו כדי לענות על שאלות לקוח.

כללים:
- העתק מספרים, תאריכים, סכומים, אחוזים ומספרי נספח בדיוק כפי שהם במסמך. לעולם אל תחשב, תעגל או תשלים.
- אם נתון לא מופיע — אל תמציא. השאר ריק.
- שכבת הטקסט לפעמים הפוכה/מבולגנת (עברית RTL); השתמש בתמונת העמוד כדי לסדר טבלאות נכון.
- מבנה המסמך:
  # <סוג הפוליסה> — <חברה> · פוליסה <מספר>
  ## פרטים כלליים (חברה, מספר פוליסה, מועד הדפסה, סוכן/סוכנות, אמצעי תשלום, פרמיה כוללת חודשית/רבעונית)
  ## מבוטחים — לכל מבוטח: שם, ת.ז, תאריך לידה, מין
  ## כיסויים — <שם מבוטח>: טבלה | נספח | שם מוצר | סוג מוצר | תחילה | משך | סכום ביטוח | עלות חודשית לפני הנחה | הנחה | מחיר אחרי הנחה |
  ## הנחות (טבלה: מוצר, אחוז, תחילה, סיום)
  ## תנאים מיוחדים / החרגות (לכל מבוטח)
  ## ערכי סילוק / פדיון (אם יש — טבלה מקוצרת)
  ## סעיפים חשובים (תקופות אכשרה, השתתפות עצמית, תקרות, השתנות פרמיה לפי גיל, ביטול) — תמציתי
- כל כותרת כיסויים כוללת את שם המבוטח, כדי שקטע שנחתך לבדו עדיין יגיד של מי הכיסוי.
- בלי מלל שיווקי ובלי הסברים כלליים על חוקים. עד ~3000 מילים."""

SCHEMA = {
    "type": "object",
    "properties": {
        "is_policy": {"type": "boolean"},
        "markdown": {"type": "string"},
        "title": {"type": "string"},
        "company": {"type": "string"},
        "policy_number": {"type": "string"},
        "policy_kind": {"type": "string"},
        "insured": {"type": "array", "items": {
            "type": "object",
            "properties": {"name": {"type": "string"}, "id_number": {"type": "string"}, "birth_date": {"type": "string"}},
            "required": ["name", "id_number", "birth_date"], "additionalProperties": False}},
    },
    "required": ["is_policy", "markdown", "title", "company", "policy_number", "policy_kind", "insured"],
    "additionalProperties": False,
}
FIELDS_HELP = ("החזר JSON: is_policy = false אם המסמך ריק או שאינו פוליסת ביטוח / דף פרטי ביטוח (אז markdown ריק); markdown = המסמך המלא; title = כותרת קצרה ('בריאות וסיעוד — הראל · 891708061'); "
               "company; policy_number; policy_kind (בריאות/סיעוד/חיים/מחלות קשות/אובדן כושר/תאונות/רכב/דירה/אחר); "
               "insured = כל המבוטחים (name, id_number, birth_date dd/mm/yyyy). שדה לא ידוע = מחרוזת ריקה.")


async def _call(client, blocks: list[dict], timing: dict) -> dict:
    last: Exception | None = None
    for model in MODELS:
        async with _SLOTS:
            t = time.monotonic()
            try:
                resp = await client.messages.create(
                    model=model, max_tokens=16000, system=SYSTEM,
                    messages=[{"role": "user", "content": blocks}],
                    output_config={"format": {"type": "json_schema", "schema": SCHEMA}},
                )
            except anthropic.APIError as e:
                last = e
                logger.warning("policy_pdf model=%s failed after %.1fs: %s", model, time.monotonic() - t, e)
                continue
        timing.update(model=model, secs=round(time.monotonic() - t, 1), stop=resp.stop_reason,
                      in_tok=resp.usage.input_tokens, out_tok=resp.usage.output_tokens)
        if resp.stop_reason in ("refusal", "max_tokens"):
            last = ValueError(f"{model} stop_reason={resp.stop_reason}")
            continue
        text = next((b.text for b in resp.content if b.type == "text"), "")
        try:
            return json.loads(text)
        except ValueError as e:
            last = e
    raise ValueError(f"policy PDF conversion failed: {last}")


async def extract_policy_pdf(file_bytes: bytes, filename: str) -> dict:
    """→ {markdown, title, company, policy_number, policy_kind, insured[], timing}."""
    if not settings.ANTHROPIC_API_KEY:
        raise RuntimeError("ANTHROPIC_API_KEY is not configured")
    timing: dict = {}
    t0 = time.monotonic()
    text_layer, source = await asyncio.to_thread(extract_text_layer_with_source, file_bytes, timing)
    blocks: list[dict] = [{"type": "document", "source": {
        "type": "base64", "media_type": "application/pdf",
        "data": base64.standard_b64encode(file_bytes).decode("ascii")}}]
    if len(text_layer) >= _MIN_TEXT_LAYER_CHARS:
        blocks.append({"type": "text", "text": f"### שכבת טקסט ({source}):\n\n{text_layer[:60000]}"})
    blocks.append({"type": "text", "text": f"שם הקובץ: {filename}\n\nהמר את הפוליסה. {FIELDS_HELP}"})
    client = anthropic.AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY, max_retries=0, timeout=600)
    out = await _call(client, blocks, timing)
    timing["total"] = round(time.monotonic() - t0, 1)
    timing["text_source"] = source
    insured = [i for i in (out.get("insured") or []) if isinstance(i, dict)]
    for i in insured:
        i["id_number"] = "".join(c for c in str(i.get("id_number") or "") if c.isdigit()).lstrip("0")
    return {
        "is_policy": bool(out.get("is_policy", True)),
        "markdown": (out.get("markdown") or "").strip() if out.get("is_policy", True) else "",
        "title": (out.get("title") or filename)[:300],
        "company": (out.get("company") or None),
        "policy_number": ("".join(c for c in str(out.get("policy_number") or "") if c.isalnum()) or None),
        "policy_kind": out.get("policy_kind"),
        "insured": insured,
        "timing": timing,
    }
