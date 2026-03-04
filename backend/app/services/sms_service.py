import httpx
import logging

from app.config import settings

logger = logging.getLogger(__name__)

TOKEN_URL = "https://019sms.co.il/api/token"
SEND_URL = "https://019sms.co.il/api/sms"


async def _get_token() -> str:
    async with httpx.AsyncClient() as client:
        resp = await client.post(TOKEN_URL, json={
            "username": settings.SMS_019_USERNAME,
            "password": settings.SMS_019_PASSWORD,
            "companyId": settings.SMS_019_COMPANY_ID,
        })
        resp.raise_for_status()
        return resp.json()["token"]


async def send_sms(phone: str, message: str) -> bool:
    try:
        token = await _get_token()
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                SEND_URL,
                headers={"Authorization": f"Bearer {token}"},
                json={
                    "phone": phone,
                    "message": message,
                },
            )
            resp.raise_for_status()
            logger.info(f"SMS sent to {phone}")
            return True
    except Exception as e:
        logger.error(f"SMS send failed for {phone}: {e}")
        return False


async def send_password_sms(phone: str, password: str) -> bool:
    message = f"הסיסמא שלך ל-Nifraim: {password}"
    return await send_sms(phone, message)
