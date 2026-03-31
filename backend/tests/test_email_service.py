"""Tests for email alert service."""
from datetime import date
from decimal import Decimal
from unittest.mock import MagicMock, patch

from app.services.email_service import send_price_alert


def make_settings(
    smtp_host="smtp.example.com",
    smtp_port=587,
    smtp_use_tls=False,
    smtp_username=None,
    smtp_password=None,
    smtp_from_address="alerts@example.com",
):
    mock_settings = MagicMock()
    mock_settings.smtp_host = smtp_host
    mock_settings.smtp_port = smtp_port
    mock_settings.smtp_use_tls = smtp_use_tls
    mock_settings.smtp_username = smtp_username
    mock_settings.smtp_password = smtp_password
    mock_settings.smtp_from_address = smtp_from_address
    return mock_settings


def base_call(**kwargs):
    """Return default keyword arguments for send_price_alert."""
    defaults = dict(
        to_address="user@example.com",
        origin="JFK",
        destination="LAX",
        departure_date_from=date(2026, 4, 1),
        departure_date_to=date(2026, 4, 5),
        return_date_from=None,
        return_date_to=None,
        best_price=Decimal("299.99"),
        currency="USD",
        threshold_price=Decimal("350.00"),
    )
    defaults.update(kwargs)
    return defaults


# ---------------------------------------------------------------------------
# Test 1: uses SMTP (not SMTP_SSL) when smtp_use_tls=False
# ---------------------------------------------------------------------------
def test_smtp_called_when_tls_false(monkeypatch):
    monkeypatch.setattr(
        "app.services.email_service.get_settings",
        lambda: make_settings(smtp_use_tls=False),
    )
    with patch("smtplib.SMTP") as mock_smtp, patch("smtplib.SMTP_SSL") as mock_ssl:
        mock_smtp.return_value.__enter__ = MagicMock(return_value=mock_smtp.return_value)
        mock_smtp.return_value.__exit__ = MagicMock(return_value=False)
        send_price_alert(**base_call())
    mock_smtp.assert_called_once_with("smtp.example.com", 587)
    mock_ssl.assert_not_called()


# ---------------------------------------------------------------------------
# Test 2: uses SMTP_SSL when smtp_use_tls=True
# ---------------------------------------------------------------------------
def test_smtp_ssl_called_when_tls_true(monkeypatch):
    monkeypatch.setattr(
        "app.services.email_service.get_settings",
        lambda: make_settings(smtp_use_tls=True, smtp_port=465),
    )
    with patch("smtplib.SMTP") as mock_smtp, patch("smtplib.SMTP_SSL") as mock_ssl:
        mock_ssl.return_value.__enter__ = MagicMock(return_value=mock_ssl.return_value)
        mock_ssl.return_value.__exit__ = MagicMock(return_value=False)
        send_price_alert(**base_call())
    mock_ssl.assert_called_once_with("smtp.example.com", 465)
    mock_smtp.assert_not_called()


# ---------------------------------------------------------------------------
# Test 3: login() called when username and password are set
# ---------------------------------------------------------------------------
def test_login_called_with_credentials(monkeypatch):
    monkeypatch.setattr(
        "app.services.email_service.get_settings",
        lambda: make_settings(smtp_username="user", smtp_password="pass"),
    )
    with patch("smtplib.SMTP") as mock_smtp:
        server_instance = MagicMock()
        mock_smtp.return_value.__enter__ = MagicMock(return_value=server_instance)
        mock_smtp.return_value.__exit__ = MagicMock(return_value=False)
        send_price_alert(**base_call())
    server_instance.login.assert_called_once_with("user", "pass")


# ---------------------------------------------------------------------------
# Test 4: login() NOT called when smtp_username is None
# ---------------------------------------------------------------------------
def test_login_not_called_when_no_credentials(monkeypatch):
    monkeypatch.setattr(
        "app.services.email_service.get_settings",
        lambda: make_settings(smtp_username=None, smtp_password=None),
    )
    with patch("smtplib.SMTP") as mock_smtp:
        server_instance = MagicMock()
        mock_smtp.return_value.__enter__ = MagicMock(return_value=server_instance)
        mock_smtp.return_value.__exit__ = MagicMock(return_value=False)
        send_price_alert(**base_call())
    server_instance.login.assert_not_called()


# ---------------------------------------------------------------------------
# Test 5: subject contains origin, destination, currency, and best_price
# ---------------------------------------------------------------------------
def test_subject_contains_route_and_price(monkeypatch):
    monkeypatch.setattr(
        "app.services.email_service.get_settings",
        lambda: make_settings(),
    )
    sent_messages = []
    with patch("smtplib.SMTP") as mock_smtp:
        server_instance = MagicMock()
        mock_smtp.return_value.__enter__ = MagicMock(return_value=server_instance)
        mock_smtp.return_value.__exit__ = MagicMock(return_value=False)
        server_instance.send_message.side_effect = lambda msg: sent_messages.append(msg)
        send_price_alert(
            **base_call(
                origin="JFK",
                destination="LAX",
                best_price=Decimal("199.00"),
                currency="USD",
            )
        )
    assert len(sent_messages) == 1
    subject = sent_messages[0]["Subject"]
    assert "JFK" in subject
    assert "LAX" in subject
    assert "USD" in subject
    assert "199.00" in subject


# ---------------------------------------------------------------------------
# Test 6: body contains origin, destination, best_price, and threshold_price
# ---------------------------------------------------------------------------
def test_body_contains_route_and_prices(monkeypatch):
    monkeypatch.setattr(
        "app.services.email_service.get_settings",
        lambda: make_settings(),
    )
    sent_messages = []
    with patch("smtplib.SMTP") as mock_smtp:
        server_instance = MagicMock()
        mock_smtp.return_value.__enter__ = MagicMock(return_value=server_instance)
        mock_smtp.return_value.__exit__ = MagicMock(return_value=False)
        server_instance.send_message.side_effect = lambda msg: sent_messages.append(msg)
        send_price_alert(
            **base_call(
                origin="JFK",
                destination="LAX",
                best_price=Decimal("199.00"),
                threshold_price=Decimal("300.00"),
                currency="USD",
            )
        )
    body = sent_messages[0].get_payload(decode=True).decode()
    assert "JFK" in body
    assert "LAX" in body
    assert "199.00" in body
    assert "300.00" in body


# ---------------------------------------------------------------------------
# Test 7: body contains "A price has been found" when previous_best_price=None
# ---------------------------------------------------------------------------
def test_body_first_alert_intro(monkeypatch):
    monkeypatch.setattr(
        "app.services.email_service.get_settings",
        lambda: make_settings(),
    )
    sent_messages = []
    with patch("smtplib.SMTP") as mock_smtp:
        server_instance = MagicMock()
        mock_smtp.return_value.__enter__ = MagicMock(return_value=server_instance)
        mock_smtp.return_value.__exit__ = MagicMock(return_value=False)
        server_instance.send_message.side_effect = lambda msg: sent_messages.append(msg)
        send_price_alert(**base_call(previous_best_price=None))
    body = sent_messages[0].get_payload(decode=True).decode()
    assert "A price has been found" in body


# ---------------------------------------------------------------------------
# Test 8: body contains "The price has dropped" when previous_best_price is set
# ---------------------------------------------------------------------------
def test_body_drop_intro(monkeypatch):
    monkeypatch.setattr(
        "app.services.email_service.get_settings",
        lambda: make_settings(),
    )
    sent_messages = []
    with patch("smtplib.SMTP") as mock_smtp:
        server_instance = MagicMock()
        mock_smtp.return_value.__enter__ = MagicMock(return_value=server_instance)
        mock_smtp.return_value.__exit__ = MagicMock(return_value=False)
        server_instance.send_message.side_effect = lambda msg: sent_messages.append(msg)
        send_price_alert(**base_call(previous_best_price=Decimal("350.00")))
    body = sent_messages[0].get_payload(decode=True).decode()
    assert "The price has dropped" in body


# ---------------------------------------------------------------------------
# Test 9: SMTP exception is caught; function does not raise
# ---------------------------------------------------------------------------
def test_smtp_exception_does_not_propagate(monkeypatch):
    monkeypatch.setattr(
        "app.services.email_service.get_settings",
        lambda: make_settings(),
    )
    with patch("smtplib.SMTP") as mock_smtp:
        mock_smtp.side_effect = Exception("Connection refused")
        # Should not raise
        send_price_alert(**base_call())


# ---------------------------------------------------------------------------
# Test 10: return date range IS included when return_date_from is not None
# ---------------------------------------------------------------------------
def test_return_dates_included_in_body(monkeypatch):
    monkeypatch.setattr(
        "app.services.email_service.get_settings",
        lambda: make_settings(),
    )
    sent_messages = []
    with patch("smtplib.SMTP") as mock_smtp:
        server_instance = MagicMock()
        mock_smtp.return_value.__enter__ = MagicMock(return_value=server_instance)
        mock_smtp.return_value.__exit__ = MagicMock(return_value=False)
        server_instance.send_message.side_effect = lambda msg: sent_messages.append(msg)
        send_price_alert(
            **base_call(
                return_date_from=date(2026, 4, 10),
                return_date_to=date(2026, 4, 15),
            )
        )
    body = sent_messages[0].get_payload(decode=True).decode()
    assert "Return:" in body
    assert "2026-04-10" in body
    assert "2026-04-15" in body


# ---------------------------------------------------------------------------
# Test 11: return date range is NOT included when return_date_from is None
# ---------------------------------------------------------------------------
def test_return_dates_not_included_when_one_way(monkeypatch):
    monkeypatch.setattr(
        "app.services.email_service.get_settings",
        lambda: make_settings(),
    )
    sent_messages = []
    with patch("smtplib.SMTP") as mock_smtp:
        server_instance = MagicMock()
        mock_smtp.return_value.__enter__ = MagicMock(return_value=server_instance)
        mock_smtp.return_value.__exit__ = MagicMock(return_value=False)
        server_instance.send_message.side_effect = lambda msg: sent_messages.append(msg)
        send_price_alert(**base_call(return_date_from=None, return_date_to=None))
    body = sent_messages[0].get_payload(decode=True).decode()
    assert "Return:" not in body
