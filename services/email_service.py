import smtplib
from email.message import EmailMessage

import markdown

from config import Settings
from logging_config import get_logger

logger = get_logger("email_service")


def send_report_email(
    settings: Settings,
    to_address: str,
    subject: str,
    markdown_text: str,
) -> None:
    html_body = markdown.markdown(markdown_text, extensions=["tables", "fenced_code"])

    msg = EmailMessage()
    msg["From"] = settings.email_address
    msg["To"] = to_address
    msg["Subject"] = subject
    msg.set_content(markdown_text)
    msg.add_alternative(html_body, subtype="html")

    try:
        with smtplib.SMTP(settings.email_smtp_server, 587) as server:
            server.starttls()
            server.login(settings.email_address, settings.email_app_password)
            server.send_message(msg)
        logger.info("email_sent", to=to_address, subject=subject)
    except Exception as e:
        logger.error("email_failed", error=str(e))
        raise
