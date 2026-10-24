"""Email (SMTP), SMS and WhatsApp (Twilio REST). Each channel is used only when configured; every attempt is logged."""
import logging
import smtplib
import threading
from email.message import EmailMessage

import httpx

from . import platform_settings as ps
from .core.config import settings as cfg
from .core.database import SessionLocal
from .models import OutboundMessage, Patient

log = logging.getLogger("clinicos.messaging")


def send_email(to: str, subject: str, body: str) -> None:
    if not ps.get('smtp_host'):
        raise RuntimeError("skipped: SMTP not configured")
    m = EmailMessage()
    m["From"], m["To"], m["Subject"] = ps.get('smtp_from'), to, subject
    m.set_content(body)
    with smtplib.SMTP(ps.get('smtp_host'), ps.get('smtp_port'), timeout=15) as s:
        if ps.get('smtp_tls'):
            s.starttls()
        if ps.get('smtp_user'):
            s.login(ps.get('smtp_user'), ps.get('smtp_password'))
        s.send_message(m)


def _twilio(to: str, frm: str, body: str) -> None:
    if not (ps.get('twilio_sid') and ps.get('twilio_token') and frm):
        raise RuntimeError("skipped: Twilio not configured")
    r = httpx.post(f"https://api.twilio.com/2010-04-01/Accounts/{ps.get('twilio_sid')}/Messages.json", data={"To": to, "From": frm, "Body": body},
                   auth=(ps.get('twilio_sid'), ps.get('twilio_token')), timeout=15)
    if r.status_code >= 400:
        raise RuntimeError(f"Twilio error {r.status_code}")


def send_sms(to: str, body: str) -> None:
    _twilio(to, ps.get('twilio_sms_from'), body)


def send_whatsapp(to: str, body: str) -> None:
    _twilio(f"whatsapp:{to}", ps.get('twilio_whatsapp_from'), body)


def _deliver(clinic_id, patient_id, subject, body, email, phone):
    plan = []
    if email:
        plan.append(("email", email, lambda: send_email(email, subject, body)))
    if phone:
        plan.append(("sms", phone, lambda: send_sms(phone, f"{subject}: {body}")))
        plan.append(("whatsapp", phone, lambda: send_whatsapp(phone, f"{subject}: {body}")))
    with SessionLocal() as db:
        for channel, to, fn in plan:
            try:
                fn()
                status, err = "sent", None
            except Exception as e:
                msg = str(e)
                status, err = ("skipped", msg[9:]) if msg.startswith("skipped:") else ("failed", msg[:300])
                if status == "failed":
                    log.warning("%s to patient failed: %s", channel, err)
            db.add(OutboundMessage(clinic_id=clinic_id, patient_id=patient_id, channel=channel, recipient=to, subject=subject[:200], body=body, status=status, error=err))
        db.commit()


def notify_patient(clinic_id, patient_id, subject: str, body: str) -> None:
    """Best-effort: never raises, never blocks the request (unless MESSAGING_SYNC=1, used by tests)."""
    try:
        with SessionLocal() as db:
            p = db.get(Patient, patient_id)
            if not p:
                return
            email, phone = p.email, p.phone
        if not (email or phone):
            return
        args = (clinic_id, patient_id, subject, body, email, phone)
        if cfg.messaging_sync:
            _deliver(*args)
        else:
            threading.Thread(target=_deliver, args=args, daemon=True).start()
    except Exception:
        log.exception("notify_patient failed")


def email_user(to: str, subject: str, body: str) -> None:
    """Account emails (reset/verify). Logged as a warning when SMTP isn't configured."""
    def run():
        try:
            send_email(to, subject, body)
        except Exception as e:
            log.warning("account email not sent: %s", e)
    if cfg.messaging_sync:
        run()
    else:
        threading.Thread(target=run, daemon=True).start()
