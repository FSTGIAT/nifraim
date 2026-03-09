import aiosmtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from app.config import settings


async def send_portal_email(to_email: str, customer_name: str, portal_url: str, password: str) -> bool:
    """Send portal link email to customer via SMTP."""
    if not settings.SMTP_HOST or not settings.SMTP_USER:
        raise ValueError("SMTP not configured")

    html_body = f"""
    <div dir="rtl" style="font-family: 'Heebo', Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 32px; background: #ffffff; border-radius: 12px;">
        <div style="text-align: center; margin-bottom: 24px;">
            <h1 style="color: #F57C00; font-size: 24px; margin: 0;">InsureFlow</h1>
        </div>
        <h2 style="color: #181818; font-size: 20px;">שלום {customer_name},</h2>
        <p style="color: #3E3E3C; font-size: 16px; line-height: 1.8;">
            הסוכן שלך שיתף איתך את תיק הביטוח האישי שלך.
        </p>
        <div style="background: #F3F3F3; border-radius: 8px; padding: 20px; margin: 24px 0; text-align: center;">
            <a href="{portal_url}" style="display: inline-block; padding: 14px 32px; background: #F57C00; color: white; text-decoration: none; border-radius: 8px; font-size: 16px; font-weight: 700;">
                צפייה בתיק הביטוח
            </a>
            <p style="color: #706E6B; font-size: 14px; margin-top: 16px;">
                סיסמה: <strong dir="ltr" style="color: #181818; letter-spacing: 1px;">{password}</strong>
            </p>
        </div>
        <p style="color: #706E6B; font-size: 13px; line-height: 1.6;">
            התיק כולל מידע על המוצרים, הפרמיות והצבירות שלך.
        </p>
        <hr style="border: none; border-top: 1px solid #DDDBDA; margin: 24px 0;" />
        <p style="color: #706E6B; font-size: 12px; text-align: center;">
            בברכה, InsureFlow
        </p>
    </div>
    """

    msg = MIMEMultipart("alternative")
    msg["Subject"] = "תיק הביטוח האישי שלך — InsureFlow"
    msg["From"] = settings.SMTP_FROM_EMAIL or settings.SMTP_USER
    msg["To"] = to_email
    msg.attach(MIMEText(html_body, "html", "utf-8"))

    await aiosmtplib.send(
        msg,
        hostname=settings.SMTP_HOST,
        port=settings.SMTP_PORT,
        username=settings.SMTP_USER,
        password=settings.SMTP_PASSWORD,
        start_tls=True,
    )
    return True
