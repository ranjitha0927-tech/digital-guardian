from __future__ import annotations

import base64
import json
import os
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from flask_mail import Message

from ..extensions import mail
from ..models import ParentUser


SMS_PROVIDER = os.getenv("SMS_PROVIDER", "simulated").strip().lower()
DEFAULT_SMS_COUNTRY_CODE = os.getenv("DEFAULT_SMS_COUNTRY_CODE", "").strip()


def normalize_sms_recipient(raw_number: str) -> str:
    number = (raw_number or "").strip().replace(" ", "").replace("-", "").replace("(", "").replace(")", "")
    if not number:
        return ""
    if number.startswith("00"):
        number = f"+{number[2:]}"
    if number.startswith("+"):
        return number
    digits = "".join(ch for ch in number if ch.isdigit())
    if not digits:
        return ""
    if DEFAULT_SMS_COUNTRY_CODE:
        prefix = DEFAULT_SMS_COUNTRY_CODE if DEFAULT_SMS_COUNTRY_CODE.startswith("+") else f"+{DEFAULT_SMS_COUNTRY_CODE.lstrip('+')}"
        return f"{prefix}{digits}"
    if len(digits) == 10:
        return ""
    return digits


def dispatch_sms(parent: ParentUser | None, message: str) -> dict:
    if parent is None:
        return {"provider": "none", "delivery_status": "skipped", "reference": None, "details": "Parent not found."}
    recipient = normalize_sms_recipient(parent.phone_number or "")
    if not recipient:
        return {
            "provider": "none",
            "delivery_status": "skipped",
            "reference": None,
            "details": "Parent mobile number missing or invalid.",
        }
    if parent.settings and not parent.settings.notification_enabled:
        return {
            "provider": "disabled",
            "delivery_status": "skipped",
            "reference": None,
            "details": "SMS notifications are disabled in settings.",
        }

    if SMS_PROVIDER == "twilio":
        account_sid = os.getenv("TWILIO_ACCOUNT_SID", "").strip()
        auth_token = os.getenv("TWILIO_AUTH_TOKEN", "").strip()
        from_number = os.getenv("TWILIO_FROM_NUMBER", "").strip()
        if account_sid and auth_token and from_number:
            try:
                payload = urlencode({"To": recipient, "From": from_number, "Body": message}).encode("utf-8")
                request = Request(
                    f"https://api.twilio.com/2010-04-01/Accounts/{account_sid}/Messages.json",
                    data=payload,
                    method="POST",
                    headers={
                        "Authorization": "Basic "
                        + base64.b64encode(f"{account_sid}:{auth_token}".encode("utf-8")).decode("utf-8"),
                        "Content-Type": "application/x-www-form-urlencoded",
                    },
                )
                with urlopen(request, timeout=15) as response:
                    raw = response.read().decode("utf-8")
                    data = json.loads(raw) if raw else {}
                return {"provider": "twilio", "delivery_status": "sent", "reference": data.get("sid"), "details": "Twilio SMS sent."}
            except (HTTPError, URLError, TimeoutError, json.JSONDecodeError, OSError) as exc:
                return {"provider": "twilio", "delivery_status": "failed", "reference": None, "details": f"Twilio failed: {exc}"}

    if SMS_PROVIDER == "fast2sms":
        api_key = os.getenv("FAST2SMS_API_KEY", "").strip()
        sender_id = os.getenv("FAST2SMS_SENDER_ID", "").strip()
        if api_key:
            try:
                payload = urlencode({"route": "q", "message": message, "language": "english", "flash": 0, "numbers": recipient}).encode("utf-8")
                request = Request(
                    "https://www.fast2sms.com/dev/bulkV2",
                    data=payload,
                    method="POST",
                    headers={"authorization": api_key, "Content-Type": "application/x-www-form-urlencoded", **({"sender_id": sender_id} if sender_id else {})},
                )
                with urlopen(request, timeout=15) as response:
                    raw = response.read().decode("utf-8")
                    data = json.loads(raw) if raw else {}
                return {"provider": "fast2sms", "delivery_status": "sent", "reference": data.get("return") or data.get("request_id"), "details": "Fast2SMS sent."}
            except (HTTPError, URLError, TimeoutError, json.JSONDecodeError, OSError) as exc:
                return {"provider": "fast2sms", "delivery_status": "failed", "reference": None, "details": f"Fast2SMS failed: {exc}"}

    if SMS_PROVIDER == "textlocal":
        api_key = os.getenv("TEXTLOCAL_API_KEY", "").strip()
        sender = os.getenv("TEXTLOCAL_SENDER", "DGAPP").strip()
        if api_key:
            try:
                payload = urlencode({"apikey": api_key, "numbers": recipient, "message": message, "sender": sender}).encode("utf-8")
                request = Request(
                    "https://api.textlocal.in/send/",
                    data=payload,
                    method="POST",
                    headers={"Content-Type": "application/x-www-form-urlencoded"},
                )
                with urlopen(request, timeout=15) as response:
                    raw = response.read().decode("utf-8")
                    data = json.loads(raw) if raw else {}
                return {"provider": "textlocal", "delivery_status": "sent", "reference": data.get("batch_id"), "details": "Textlocal sent."}
            except (HTTPError, URLError, TimeoutError, json.JSONDecodeError, OSError) as exc:
                return {"provider": "textlocal", "delivery_status": "failed", "reference": None, "details": f"Textlocal failed: {exc}"}

    return {"provider": "simulated_twilio", "delivery_status": "sent", "reference": None, "details": "Simulated demo SMS delivery."}


def dispatch_email(parent: ParentUser | None, subject: str, body: str) -> dict:
    if parent is None or not parent.email:
        return {"provider": "none", "delivery_status": "skipped", "reference": None, "details": "Parent email missing."}
    if parent.settings and not parent.settings.email_notifications_enabled:
        return {"provider": "disabled", "delivery_status": "skipped", "reference": None, "details": "Email notifications disabled in settings."}
    try:
        if not mail:
            raise RuntimeError("Mail service unavailable")
        message = Message(subject=subject, recipients=[parent.email], body=body)
        mail.send(message)
        return {"provider": "flask-mail", "delivery_status": "sent", "reference": parent.email, "details": "Email sent."}
    except Exception as exc:
        return {"provider": "simulated_email", "delivery_status": "sent", "reference": parent.email, "details": f"Email simulated for demo mode: {exc}"}
