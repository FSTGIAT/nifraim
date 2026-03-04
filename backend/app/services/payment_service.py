import httpx
import logging

from app.config import settings

logger = logging.getLogger(__name__)

CARDCOM_CREATE_URL = "https://secure.cardcom.solutions/api/v11/LowProfile/Create"


async def create_payment_page(
    amount: float,
    description: str,
    user_email: str,
    user_id: str,
    plan: str,
) -> str | None:
    """Create a Cardcom low-profile payment page. Returns the URL to redirect the user to."""
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(CARDCOM_CREATE_URL, json={
                "TerminalNumber": settings.CARDCOM_TERMINAL,
                "ApiName": settings.CARDCOM_API_NAME,
                "ApiPassword": settings.CARDCOM_API_PASSWORD,
                "Amount": amount,
                "Currency": "1",  # ILS
                "Description": description,
                "SuccessRedirectUrl": f"{settings.CARDCOM_SUCCESS_URL}&user_id={user_id}",
                "FailedRedirectUrl": settings.CARDCOM_FAILURE_URL,
                "WebhookUrl": settings.CARDCOM_WEBHOOK_URL,
                "Document": {
                    "Type": "1",  # Invoice
                    "Email": user_email,
                },
                "CustomFields": {
                    "Field1": user_id,
                    "Field2": plan,
                },
                "MaxPayments": 1,
            })
            resp.raise_for_status()
            data = resp.json()
            if data.get("LowProfileUrl"):
                return data["LowProfileUrl"]
            logger.error(f"Cardcom response missing URL: {data}")
            return None
    except Exception as e:
        logger.error(f"Cardcom create payment failed: {e}")
        return None


def verify_webhook(data: dict) -> dict | None:
    """Parse and validate Cardcom webhook payload. Returns user_id and plan if valid."""
    try:
        terminal = data.get("TerminalNumber")
        if str(terminal) != str(settings.CARDCOM_TERMINAL):
            logger.warning(f"Webhook terminal mismatch: {terminal}")
            return None

        return {
            "user_id": data.get("CustomFields", {}).get("Field1"),
            "plan": data.get("CustomFields", {}).get("Field2"),
            "cardcom_token": data.get("Token"),
            "amount": data.get("Amount"),
        }
    except Exception as e:
        logger.error(f"Webhook parse failed: {e}")
        return None
