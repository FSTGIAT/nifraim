import os

import aiosmtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from app.config import settings

FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:5173")


async def _send_email(msg: MIMEMultipart):
    """Send email via SMTP with proper EHLO hostname."""
    use_tls = settings.SMTP_PORT == 465
    smtp = aiosmtplib.SMTP(
        hostname=settings.SMTP_HOST,
        port=settings.SMTP_PORT,
        use_tls=use_tls,
        start_tls=not use_tls,
        local_hostname="nifraim.com",
    )
    await smtp.connect()
    await smtp.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
    await smtp.send_message(msg)
    await smtp.quit()


async def send_portal_email(to_email: str, customer_name: str, portal_url: str, password: str) -> bool:
    """Send portal link email to customer via SMTP."""
    if not settings.SMTP_HOST or not settings.SMTP_USER:
        raise ValueError("SMTP not configured")

    html_body = f"""
    <div dir="rtl" style="font-family: 'Heebo', Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 32px; background: #ffffff; border-radius: 12px;">
        <div style="text-align: center; margin-bottom: 24px;">
            <h1 style="color: #F57C00; font-size: 24px; margin: 0;">Nifraim</h1>
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
            בברכה, Nifraim
        </p>
    </div>
    """

    msg = MIMEMultipart("alternative")
    msg["Subject"] = "תיק הביטוח האישי שלך — Nifraim"
    msg["From"] = settings.SMTP_FROM_EMAIL or settings.SMTP_USER
    msg["To"] = to_email
    msg.attach(MIMEText(html_body, "html", "utf-8"))

    await _send_email(msg)
    return True


async def send_reset_password_email(to_email: str, name: str, token: str) -> bool:
    """Send password reset email via SMTP."""
    if not settings.SMTP_HOST or not settings.SMTP_USER:
        raise ValueError("SMTP not configured")

    reset_url = f"{FRONTEND_URL}/reset-password?token={token}"

    html_body = f"""
    <div dir="rtl" style="font-family: 'Heebo', Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 32px; background: #ffffff; border-radius: 12px;">
        <div style="text-align: center; margin-bottom: 24px;">
            <h1 style="color: #F57C00; font-size: 24px; margin: 0;">Nifraim</h1>
        </div>
        <h2 style="color: #181818; font-size: 20px;">שלום{' ' + name if name else ''},</h2>
        <p style="color: #3E3E3C; font-size: 16px; line-height: 1.8;">
            קיבלנו בקשה לאיפוס הסיסמה שלך. לחצו על הכפתור למטה כדי לבחור סיסמה חדשה.
        </p>
        <div style="background: #F3F3F3; border-radius: 8px; padding: 20px; margin: 24px 0; text-align: center;">
            <a href="{reset_url}" style="display: inline-block; padding: 14px 32px; background: #F57C00; color: white; text-decoration: none; border-radius: 8px; font-size: 16px; font-weight: 700;">
                איפוס סיסמה
            </a>
        </div>
        <p style="color: #706E6B; font-size: 13px; line-height: 1.6;">
            הקישור תקף לשעה אחת. אם לא ביקשתם לאפס את הסיסמה, התעלמו מהודעה זו.
        </p>
        <hr style="border: none; border-top: 1px solid #DDDBDA; margin: 24px 0;" />
        <p style="color: #706E6B; font-size: 12px; text-align: center;">
            בברכה, Nifraim
        </p>
    </div>
    """

    msg = MIMEMultipart("alternative")
    msg["Subject"] = "איפוס סיסמה — Nifraim"
    msg["From"] = settings.SMTP_FROM_EMAIL or settings.SMTP_USER
    msg["To"] = to_email
    msg.attach(MIMEText(html_body, "html", "utf-8"))

    await _send_email(msg)
    return True


async def send_debt_email(
    to_email: str,
    company_name: str,
    agent_name: str,
    debts_list: list[dict],
) -> bool:
    """Send a debt summary email to an insurance company contact."""
    total = sum(d["amount"] for d in debts_list)

    rows_html = ""
    for d in debts_list:
        rows_html += f"""
        <tr>
            <td style="padding:8px 12px;border-bottom:1px solid #eee;text-align:right;">{d['customer_name']}</td>
            <td style="padding:8px 12px;border-bottom:1px solid #eee;text-align:right;">{d['customer_id']}</td>
            <td style="padding:8px 12px;border-bottom:1px solid #eee;text-align:right;">{d['product']}</td>
            <td style="padding:8px 12px;border-bottom:1px solid #eee;text-align:right;">{d['policy_number']}</td>
            <td style="padding:8px 12px;border-bottom:1px solid #eee;text-align:left;font-weight:600;color:#e65100;">&#8362;{d['amount']:,.2f}</td>
        </tr>"""

    html_body = f"""
    <html dir="rtl">
    <body style="font-family:Heebo,Arial,sans-serif;background:#f8f9fa;margin:0;padding:20px;">
        <div style="max-width:640px;margin:0 auto;background:#fff;border-radius:12px;overflow:hidden;box-shadow:0 2px 12px rgba(0,0,0,0.08);">
            <div style="background:linear-gradient(135deg,#F57C00,#FF9800);padding:24px 32px;">
                <h1 style="color:#fff;margin:0;font-size:20px;">Nifraim — סיכום עמלות לגבייה</h1>
            </div>
            <div style="padding:28px 32px;">
                <p style="font-size:15px;color:#333;line-height:1.6;">
                    שלום רב,<br>
                    להלן פירוט עמלות שטרם שולמו עבור לקוחות הסוכן <strong>{agent_name}</strong>
                    בחברת <strong>{company_name}</strong>:
                </p>

                <table style="width:100%;border-collapse:collapse;margin:20px 0;font-size:13px;">
                    <thead>
                        <tr style="background:#f8f9fa;">
                            <th style="padding:10px 12px;text-align:right;font-weight:700;color:#666;border-bottom:2px solid #eee;">שם לקוח</th>
                            <th style="padding:10px 12px;text-align:right;font-weight:700;color:#666;border-bottom:2px solid #eee;">ת.ז</th>
                            <th style="padding:10px 12px;text-align:right;font-weight:700;color:#666;border-bottom:2px solid #eee;">מוצר</th>
                            <th style="padding:10px 12px;text-align:right;font-weight:700;color:#666;border-bottom:2px solid #eee;">מספר פוליסה</th>
                            <th style="padding:10px 12px;text-align:left;font-weight:700;color:#666;border-bottom:2px solid #eee;">סכום</th>
                        </tr>
                    </thead>
                    <tbody>
                        {rows_html}
                    </tbody>
                    <tfoot>
                        <tr style="background:#fff8e1;">
                            <td colspan="4" style="padding:10px 12px;text-align:right;font-weight:700;font-size:14px;">סה״כ</td>
                            <td style="padding:10px 12px;text-align:left;font-weight:700;font-size:14px;color:#e65100;">&#8362;{total:,.2f}</td>
                        </tr>
                    </tfoot>
                </table>

                <p style="font-size:13px;color:#666;line-height:1.5;">
                    סה״כ <strong>{len(debts_list)}</strong> פריטים בסך <strong>&#8362;{total:,.2f}</strong><br>
                    אנא בדקו ועדכנו בהקדם.
                </p>

                <p style="font-size:13px;color:#999;margin-top:24px;">
                    בברכה,<br>
                    {agent_name}<br>
                    <span style="font-size:11px;color:#bbb;">נשלח דרך מערכת Nifraim</span>
                </p>
            </div>
        </div>
    </body>
    </html>
    """

    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"סיכום עמלות לגבייה — {company_name}"
    msg["From"] = settings.SMTP_FROM_EMAIL or settings.SMTP_USER
    msg["To"] = to_email
    msg.attach(MIMEText(html_body, "html", "utf-8"))

    await _send_email(msg)
    return True
