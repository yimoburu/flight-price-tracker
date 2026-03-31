import logging
import smtplib
from datetime import date
from decimal import Decimal
from email.mime.text import MIMEText
from typing import Optional

from app.config import get_settings

logger = logging.getLogger(__name__)


def send_price_alert(
    to_address: str,
    origin: str,
    destination: str,
    departure_date_from: date,
    departure_date_to: date,
    return_date_from: Optional[date],
    return_date_to: Optional[date],
    best_price: Decimal,
    currency: str,
    threshold_price: Decimal,
    previous_best_price: Optional[Decimal] = None,
) -> None:
    settings = get_settings()
    subject = f"Price alert: {origin} \u2192 {destination} now {currency}{best_price}"

    if previous_best_price is None:
        intro = "A price has been found"
    else:
        intro = "The price has dropped"

    lines = [
        intro,
        f"Route: {origin} \u2192 {destination}",
        f"Departure: {departure_date_from} to {departure_date_to}",
    ]
    if return_date_from is not None:
        lines.append(f"Return: {return_date_from} to {return_date_to}")
    lines += [
        f"Best price: {currency}{best_price}",
        f"Your threshold: {currency}{threshold_price}",
    ]
    body = "\n".join(lines)

    msg = MIMEText(body)
    msg["Subject"] = subject
    msg["From"] = settings.smtp_from_address
    msg["To"] = to_address

    try:
        if settings.smtp_use_tls:
            server_cls = smtplib.SMTP_SSL
        else:
            server_cls = smtplib.SMTP
        with server_cls(settings.smtp_host, settings.smtp_port) as server:
            if settings.smtp_username and settings.smtp_password:
                server.login(settings.smtp_username, settings.smtp_password)
            server.send_message(msg)
    except Exception:
        logger.error("send_price_alert failed", exc_info=True)
