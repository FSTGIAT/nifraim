import httpx
import logging

from app.config import settings

logger = logging.getLogger(__name__)

CARDCOM_CREATE_URL = "https://secure.cardcom.solutions/api/v11/LowProfile/Create"
CARDCOM_LP_RESULT_URL = "https://secure.cardcom.solutions/api/v11/LowProfile/GetLpResult"
CARDCOM_CHARGE_URL = "https://secure.cardcom.solutions/api/v11/Transactions/Transaction"


def is_cardcom_configured() -> bool:
    """Check if Cardcom credentials are set."""
    return bool(settings.CARDCOM_TERMINAL and settings.CARDCOM_API_NAME and settings.CARDCOM_API_PASSWORD)


async def create_payment_page(
    amount: float,
    description: str,
    user_email: str,
    user_id: str,
    plan: str,
) -> tuple[str | None, str | None]:
    """Create a Cardcom low-profile payment page with token creation.
    Returns (payment_url, low_profile_code) tuple."""
    if not is_cardcom_configured():
        logger.warning("Cardcom not configured — dev mode, skipping payment")
        return None, None
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
                "CreateToken": True,
            })
            resp.raise_for_status()
            data = resp.json()
            if data.get("LowProfileUrl"):
                return data["LowProfileUrl"], data.get("LowProfileCode")
            logger.error(f"Cardcom response missing URL: {data}")
            return None, None
    except Exception as e:
        logger.error(f"Cardcom create payment failed: {e}")
        return None, None


async def get_lp_result(low_profile_code: str) -> dict | None:
    """Retrieve token and payment details from a completed LowProfile transaction."""
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(CARDCOM_LP_RESULT_URL, json={
                "TerminalNumber": settings.CARDCOM_TERMINAL,
                "ApiName": settings.CARDCOM_API_NAME,
                "ApiPassword": settings.CARDCOM_API_PASSWORD,
                "LowProfileCode": low_profile_code,
            })
            resp.raise_for_status()
            data = resp.json()
            return {
                "token": data.get("Token"),
                "token_exp_date": data.get("TokenExDate"),
                "last4_digits": data.get("Last4Digits"),
                "card_brand": data.get("CardBrand"),
                "amount": data.get("Amount"),
            }
    except Exception as e:
        logger.error(f"Cardcom GetLpResult failed: {e}")
        return None


async def charge_token(token: str, amount: float) -> dict | None:
    """Charge a saved card token for recurring payment. Returns transaction data or None on failure."""
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(CARDCOM_CHARGE_URL, json={
                "TerminalNumber": settings.CARDCOM_TERMINAL,
                "ApiName": settings.CARDCOM_API_NAME,
                "ApiPassword": settings.CARDCOM_API_PASSWORD,
                "Token": token,
                "Amount": amount,
                "Currency": "1",  # ILS
                "Document": {
                    "Type": "1",  # Invoice
                },
            })
            resp.raise_for_status()
            data = resp.json()
            # Cardcom returns ResponseCode 0 on success
            if data.get("ResponseCode") == 0:
                return data
            logger.error(f"Cardcom charge failed: code={data.get('ResponseCode')}, desc={data.get('Description')}")
            return None
    except Exception as e:
        logger.error(f"Cardcom charge_token failed: {e}")
        return None


def verify_webhook(data: dict) -> dict | None:
    """Parse and validate Cardcom webhook payload. Returns user_id, plan, and token info if valid."""
    try:
        terminal = data.get("TerminalNumber")
        if str(terminal) != str(settings.CARDCOM_TERMINAL):
            logger.warning(f"Webhook terminal mismatch: {terminal}")
            return None

        return {
            "user_id": data.get("CustomFields", {}).get("Field1"),
            "plan": data.get("CustomFields", {}).get("Field2"),
            "cardcom_token": data.get("Token"),
            "token_exp_date": data.get("TokenExDate"),
            "last4_digits": data.get("Last4Digits"),
            "card_brand": data.get("CardBrand"),
            "amount": data.get("Amount"),
        }
    except Exception as e:
        logger.error(f"Webhook parse failed: {e}")
        return None
