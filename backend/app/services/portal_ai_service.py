import json
import logging
import time
from typing import AsyncGenerator

import anthropic

from app.config import settings

logger = logging.getLogger(__name__)

PORTAL_SYSTEM_PROMPT = """אתה יועץ ביטוח מנוסה (בן 40 בערך) שעוזר ללקוחות להבין את תיק הביטוח שלהם.
יש לך גישה רק לנתונים של הלקוח המוצגים למטה. עליך:
- לענות רק על שאלות הקשורות לנתוני הביטוח של הלקוח. לסרב בנימוס לכל שאלה אחרת.
- לענות תמיד בעברית.
- להיות תמציתי, ידידותי ומקצועי.
- להשתמש במספרים ונתונים ספציפיים מההקשר.
- אם נשאלת על משהו שלא בנתונים, אמור שאין לך את המידע הזה.
- להשתמש בטבלאות markdown עם | עמודות | כשמציג רשימות או השוואות.
- לעצב ערכי כסף עם סימן ₪ ופסיקים (למשל ₪1,234).
- להשתמש ב-**bold** למספרים חשובים ותובנות מרכזיות.

=== נתוני הלקוח ===
{context}
==="""

# Simple in-memory rate limiter: token -> (count, first_msg_time)
_rate_limits: dict[str, tuple[int, float]] = {}
RATE_LIMIT_MAX = 20
RATE_LIMIT_TTL = 3600  # 1 hour


def check_rate_limit(token: str) -> bool:
    """Check if token is within rate limit. Returns True if allowed."""
    now = time.time()

    if token in _rate_limits:
        count, start = _rate_limits[token]
        if now - start > RATE_LIMIT_TTL:
            _rate_limits[token] = (1, now)
            return True
        if count >= RATE_LIMIT_MAX:
            return False
        _rate_limits[token] = (count + 1, start)
        return True

    _rate_limits[token] = (1, now)
    return True


def build_portal_context(dashboard_data: dict) -> str:
    """Format customer dashboard data as text context for the AI."""
    parts = []

    parts.append(f"שם לקוח: {dashboard_data.get('customer_name', '')}")
    parts.append(f"ת.ז: {dashboard_data.get('id_number', '')}")
    if dashboard_data.get("period"):
        parts.append(f"תקופה: {dashboard_data['period']}")

    kpi = dashboard_data.get("kpi", {})
    parts.append(f"סה\"כ מוצרים: {kpi.get('product_count', 0)}")
    parts.append(f"סה\"כ פרמיה: {kpi.get('total_premium', 0):,.0f}₪")
    parts.append(f"סה\"כ צבירה: {kpi.get('total_accumulation', 0):,.0f}₪")
    parts.append(f"מספר חברות: {kpi.get('company_count', 0)}")

    # Company breakdown
    breakdown = dashboard_data.get("company_breakdown", [])
    if breakdown:
        co_lines = []
        for co in breakdown:
            co_lines.append(
                f"{co['company']}: {co['count']} מוצרים, פרמיה: {co['premium']:,.0f}₪, צבירה: {co['accumulation']:,.0f}₪"
            )
        parts.append(f"פירוט לפי חברה: {'; '.join(co_lines)}")

    # Products
    products = dashboard_data.get("products", [])
    if products:
        parts.append(f"\nפירוט מוצרים ({len(products)}):")
        for i, p in enumerate(products[:20], 1):
            prem = f"{p['total_premium']:,.0f}₪" if p.get("total_premium") else "—"
            accum = f"{p['accumulation']:,.0f}₪" if p.get("accumulation") else "—"
            parts.append(
                f"{i}. {p.get('product') or 'ללא שם'} | {p.get('receiving_company') or ''} | "
                f"פרמיה: {prem} | צבירה: {accum} | סטטוס: {p.get('product_status') or ''}"
            )
        if len(products) > 20:
            parts.append(f"... ועוד {len(products) - 20} מוצרים")

    return "\n".join(parts)


async def stream_portal_chat(
    dashboard_data: dict, question: str, history: list[dict]
) -> AsyncGenerator[str, None]:
    """Stream AI chat response for portal customer."""
    context = build_portal_context(dashboard_data)
    system_prompt = PORTAL_SYSTEM_PROMPT.format(context=context)

    messages = []
    for msg in history[-6:]:
        messages.append({"role": msg["role"], "content": msg["content"]})
    messages.append({"role": "user", "content": question})

    if not settings.ANTHROPIC_API_KEY:
        yield f"data: {json.dumps({'text': 'שגיאה: שירות ה-AI אינו זמין כרגע.'}, ensure_ascii=False)}\n\n"
        yield f"data: {json.dumps({'done': True})}\n\n"
        return

    client = anthropic.AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)

    try:
        async with client.messages.stream(
            model="claude-haiku-4-5-20251001",
            max_tokens=512,
            system=system_prompt,
            messages=messages,
        ) as stream:
            async for text in stream.text_stream:
                yield f"data: {json.dumps({'text': text}, ensure_ascii=False)}\n\n"
    except anthropic.AuthenticationError:
        yield f"data: {json.dumps({'text': 'שגיאה: שירות ה-AI אינו זמין כרגע.'}, ensure_ascii=False)}\n\n"
    except Exception as e:
        logger.error(f"Portal AI chat error: {type(e).__name__}: {e}")
        yield f"data: {json.dumps({'text': 'שגיאה: לא ניתן לעבד את הבקשה כרגע.'}, ensure_ascii=False)}\n\n"

    yield f"data: {json.dumps({'done': True})}\n\n"
