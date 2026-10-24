"""Automated reminders. Runs every few minutes in a background thread (disable with RUN_SCHEDULER=0)."""
import logging
import threading
import time
from datetime import timedelta

from sqlalchemy import select

from . import messaging
from .core.config import settings
from .core.database import SessionLocal
from .models import Appointment, Clinic, Consultation, Patient, utcnow

log = logging.getLogger("clinicos.scheduler")


def run_reminders() -> int:
    now, sent = utcnow(), 0
    with SessionLocal() as db:
        appts = db.scalars(select(Appointment).join(Patient, Patient.id == Appointment.patient_id).join(Clinic, Clinic.id == Appointment.clinic_id).where(
            Appointment.deleted_at.is_(None), Patient.deleted_at.is_(None), Clinic.status == "active", Appointment.status.in_(("booked", "confirmed")),
            Appointment.reminded_at.is_(None), Appointment.scheduled_at > now, Appointment.scheduled_at <= now + timedelta(hours=24))).all()
        for a in appts:
            a.reminded_at = now
            messaging.notify_patient(a.clinic_id, a.patient_id, "Appointment reminder", f"Reminder: you have an appointment at {a.scheduled_at:%d %b %Y, %H:%M} UTC.")
            sent += 1
        day = (now + timedelta(days=1)).date()
        cons = db.scalars(select(Consultation).join(Patient, Patient.id == Consultation.patient_id).where(
            Consultation.deleted_at.is_(None), Patient.deleted_at.is_(None), Consultation.follow_up_on == day, Consultation.reminded_at.is_(None))).all()
        for c in cons:
            c.reminded_at = now
            messaging.notify_patient(c.clinic_id, c.patient_id, "Follow-up reminder", f"Your follow-up visit is due on {c.follow_up_on:%d %b %Y}. Please book a time with the clinic.")
            sent += 1
        db.commit()
    return sent


def start():
    if not settings.run_scheduler:
        return
    def loop():
        while True:
            try:
                run_reminders()
            except Exception:
                log.exception("reminder run failed")
            time.sleep(300)
    threading.Thread(target=loop, daemon=True, name="reminders").start()
