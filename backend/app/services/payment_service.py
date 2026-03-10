import httpx
import logging

from app.config import settings

logger = logging.getLogger(__name__)

CARDCOM_BASE = "https://secure.cardcom.solutions/api/v11"
CARDCOM_CREATE_URL = f"{CARDCOM_BASE}/LowProfile/Create"
CARDCOM_LP_RESULT_URL = f"{CARDCOM_BASE}/LowProfile/GetLpResult"
CARDCOM_CHARGE_URL = f"{CARDCOM_BASE}/Transactions/Transaction"
CARDCOM_INVOICE_URL = f"{CARDCOM_BASE}/Documents/CreateTaxInvoice"


def _auth_payload() -> dict:
    """Common auth fields for every Cardcom API call."""
    return {
        "TerminalNumber": int(settings.CARDCOM_TERMINAL),
        "ApiName": settings.CARDCOM_API_NAME,
        "ApiPassword": settings.CARDCOM_API_PASSWORD,
    }


def is_cardcom_configured() -> bool:
    """Check if Cardcom credentials are set."""
    return bool(settings.CARDCOM_TERMINAL and settings.CARDCOM_API_NAME and settings.CARDCOM_API_PASSWORD)


async def create_payment_page(
    amount: float,
    description: str,
    user_email: str,
    user_name: str,
    user_id: str,
    plan: str,
) -> tuple[str | None, str | None]:
    """Create a Cardcom LowProfile payment page with token creation.
    Returns (payment_url, low_profile_code) tuple."""
    if not is_cardcom_configured():
        logger.warning("Cardcom not configured — dev mode, skipping payment")
        return None, None
    try:
        payload = {
            **_auth_payload(),
            "ReturnValue": f"signup_{user_id}_{plan}",
            "Amount": amount,
            "CoinID": 1,  # ILS
            "SuccessRedirectUrl": f"{settings.CARDCOM_SUCCESS_URL}&user_id={user_id}",
            "FailedRedirectUrl": settings.CARDCOM_FAILURE_URL,
            "WebHookUrl": settings.CARDCOM_WEBHOOK_URL,
            "CreateToken": True,
            "MaxNumOfPayments": 1,
            "Language": "he",
            "Document": {
                "DocTypeToCreate": 101,  # Tax Invoice + Receipt (חשבונית מס/קבלה)
                "Name": user_name,
                "Email": user_email,
                "SendByEmail": True,
                "Products": [{
                    "Description": description,
                    "UnitCost": amount,
                    "Quantity": 1,
                }],
            },
            "CustomFields": {
                "Field1": user_id,
                "Field2": plan,
            },
        }
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(CARDCOM_CREATE_URL, json=payload)
            resp.raise_for_status()
            data = resp.json()
            # v11 returns "Url" for the payment page URL
            url = data.get("Url") or data.get("LowProfileUrl")
            lp_code = data.get("LowProfileCode")
            if url:
                logger.info(f"Cardcom payment page created for user {user_id}, LPCode: {lp_code}")
                return url, lp_code
            logger.error(f"Cardcom response missing URL: {data}")
            return None, None
    except Exception as e:
        logger.error(f"Cardcom create payment failed: {e}")
        return None, None


async def get_lp_result(low_profile_code: str) -> dict | None:
    """Retrieve token and payment details from a completed LowProfile transaction.
    Checks OperationResponse, DealResponse, and TokenResponse for success."""
    try:
        payload = {
            **_auth_payload(),
            "LowProfileCode": low_profile_code,
        }
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(CARDCOM_LP_RESULT_URL, json=payload)
            resp.raise_for_status()
            data = resp.json()

            # Check operation success (0 = OK)
            op_response = data.get("OperationResponse")
            if op_response != 0:
                logger.error(f"Cardcom LowProfile operation failed: OperationResponse={op_response}, "
                             f"OperationResponseText={data.get('OperationResponseText')}")
                return None

            # Check deal/billing success
            deal_response = data.get("DealResponse")
            if deal_response is not None and deal_response != 0:
                logger.warning(f"Cardcom deal response non-zero: {deal_response}")

            # Check token creation success
            token_response = data.get("TokenResponse")
            if token_response is not None and token_response != 0:
                logger.warning(f"Cardcom token creation response non-zero: {token_response}")

            result = {
                "token": data.get("Token"),
                "token_exp_date": data.get("TokenExDate"),
                "last4_digits": data.get("Last4Digits") or data.get("Last4CardDigits"),
                "card_brand": data.get("CardBrand") or data.get("CardName"),
                "amount": data.get("Amount"),
                "deal_number": data.get("InternalDealNumber"),
                "approval_number": data.get("ApprovalNumber"),
                "return_value": data.get("ReturnValue"),
            }
            logger.info(f"Cardcom GetLpResult success: token={'yes' if result['token'] else 'no'}, "
                         f"last4={result['last4_digits']}")
            return result
    except Exception as e:
        logger.error(f"Cardcom GetLpResult failed: {e}")
        return None


async def charge_token(
    token: str,
    amount: float,
    token_exp_date: str | None = None,
    customer_name: str | None = None,
    customer_email: str | None = None,
    description: str | None = None,
) -> dict | None:
    """Charge a saved card token for recurring payment.
    Returns transaction data or None on failure.

    token_exp_date: "MMYY" or "MM/YY" format from Cardcom.
    """
    try:
        payload = {
            **_auth_payload(),
            "Token": token,
            "Amount": amount,
            "CoinID": 1,  # ILS
        }

        # Parse token expiration into month/year if available
        if token_exp_date:
            exp = token_exp_date.replace("/", "")
            if len(exp) >= 4:
                payload["CardValidityMonth"] = exp[:2]
                payload["CardValidityYear"] = exp[2:]

        # Include document for automatic invoice + receipt generation
        doc_desc = description or "Nifraim - חידוש מנוי"
        payload["Document"] = {
            "DocTypeToCreate": 101,  # Tax Invoice + Receipt
            "Products": [{
                "Description": doc_desc,
                "UnitCost": amount,
                "Quantity": 1,
            }],
        }
        if customer_name:
            payload["Document"]["Name"] = customer_name
        if customer_email:
            payload["Document"]["Email"] = customer_email
            payload["Document"]["SendByEmail"] = True

        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(CARDCOM_CHARGE_URL, json=payload)
            resp.raise_for_status()
            data = resp.json()
            # Cardcom returns ResponseCode 0 on success
            if data.get("ResponseCode") == 0:
                logger.info(f"Cardcom token charge success: amount={amount}, "
                            f"deal={data.get('InternalDealNumber')}")
                return data
            logger.error(f"Cardcom charge failed: code={data.get('ResponseCode')}, "
                         f"desc={data.get('Description')}")
            return None
    except Exception as e:
        logger.error(f"Cardcom charge_token failed: {e}")
        return None


async def create_invoice(
    customer_name: str,
    customer_email: str,
    amount: float,
    description: str,
    deal_number: int | None = None,
    send_by_email: bool = True,
) -> dict | None:
    """Create and email a standalone tax invoice+receipt via Cardcom Documents API.
    Use this for manual/retroactive invoices. Regular payments auto-generate invoices
    via the Document object in LowProfile/Create and charge_token."""
    if not is_cardcom_configured():
        return None
    try:
        payload = {
            **_auth_payload(),
            "InvoiceType": 101,  # Tax Invoice + Receipt
            "InvoiceHead": {
                "CustName": customer_name,
                "Email": customer_email,
                "SendByEmail": send_by_email,
                "CoinID": 1,  # ILS
                "Language": "he",
            },
            "InvoiceLines": [{
                "Description": description,
                "Price": amount,
                "Quantity": 1,
                "IsPriceIncludeVAT": True,
            }],
        }
        if deal_number:
            payload["DealNumbers"] = [{"DealNumber": deal_number}]

        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(CARDCOM_INVOICE_URL, json=payload)
            resp.raise_for_status()
            data = resp.json()
            logger.info(f"Cardcom invoice created: {data.get('InvoiceNumber')}")
            return data
    except Exception as e:
        logger.error(f"Cardcom create_invoice failed: {e}")
        return None


def verify_webhook(data: dict) -> dict | None:
    """Parse and validate Cardcom webhook payload.
    Cardcom webhook sends LowProfileCode — we must call get_lp_result() separately
    to get full payment details. This function extracts what's available in the webhook."""
    try:
        terminal = data.get("TerminalNumber") or data.get("terminalnumber")
        if terminal and str(terminal) != str(settings.CARDCOM_TERMINAL):
            logger.warning(f"Webhook terminal mismatch: {terminal}")
            return None

        # Cardcom may send data in different formats (query string vs JSON)
        lp_code = (data.get("LowProfileCode") or data.get("lowprofilecode")
                    or data.get("lowProfileCode"))
        return_value = data.get("ReturnValue") or data.get("returnvalue")

        # Parse ReturnValue to extract user_id and plan (format: "signup_{user_id}_{plan}")
        user_id = None
        plan = None
        if return_value and return_value.startswith("signup_"):
            parts = return_value.split("_", 2)
            if len(parts) >= 3:
                user_id = parts[1]
                plan = parts[2]

        # Also check CustomFields if available
        custom_fields = data.get("CustomFields", {})
        if not user_id:
            user_id = custom_fields.get("Field1")
        if not plan:
            plan = custom_fields.get("Field2")

        return {
            "low_profile_code": lp_code,
            "return_value": return_value,
            "user_id": user_id,
            "plan": plan,
            # These may or may not be in the webhook — get_lp_result() is more reliable
            "cardcom_token": data.get("Token"),
            "token_exp_date": data.get("TokenExDate"),
            "last4_digits": data.get("Last4Digits"),
            "card_brand": data.get("CardBrand"),
            "amount": data.get("Amount"),
        }
    except Exception as e:
        logger.error(f"Webhook parse failed: {e}")
        return None
