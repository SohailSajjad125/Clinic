"""Settings that platform admins can change at runtime (API keys, model, e-mail, SMS, switches).

Order of precedence: value saved by an admin (database) > environment variable > built-in default.
Secret values (API keys, passwords) are encrypted with Fernet before they are stored and are never sent back to a browser.
"""
import base64
import hashlib
import ipaddress
import time
from urllib.parse import urlparse

from cryptography.fernet import Fernet, InvalidToken
from sqlalchemy import select

from .core.config import settings as env
from .core.database import SessionLocal
from .models import PlatformSetting, utcnow

# name -> (group, label, kind, secret, env attribute)
SPEC = {
    "groq_api_key": ("assistant", "Groq API key", "text", True, "groq_api_key"),
    "groq_model": ("assistant", "Groq model", "text", False, "groq_model"),
    "groq_base_url": ("assistant", "Groq API base URL", "url", False, "groq_base_url"),
    "assistant_enabled": ("assistant", "AI assistant enabled", "bool", False, None),
    "smtp_host": ("email", "SMTP host", "text", False, "smtp_host"),
    "smtp_port": ("email", "SMTP port", "int", False, "smtp_port"),
    "smtp_user": ("email", "SMTP username", "text", False, "smtp_user"),
    "smtp_password": ("email", "SMTP password", "text", True, "smtp_password"),
    "smtp_from": ("email", "From address", "text", False, "smtp_from"),
    "smtp_tls": ("email", "Use STARTTLS", "bool", False, "smtp_tls"),
    "twilio_sid": ("sms", "Twilio account SID", "text", False, "twilio_sid"),
    "twilio_token": ("sms", "Twilio auth token", "text", True, "twilio_token"),
    "twilio_sms_from": ("sms", "SMS from number", "text", False, "twilio_sms_from"),
    "twilio_whatsapp_from": ("sms", "WhatsApp from number", "text", False, "twilio_whatsapp_from"),
    "allow_clinic_signups": ("platform", "Allow new clinics to sign up", "bool", False, None),
    "allow_patient_signups": ("platform", "Allow patients to sign up online", "bool", False, None),
}
DEFAULTS = {"assistant_enabled": True, "allow_clinic_signups": True, "allow_patient_signups": True}
_cache: dict = {"at": 0.0, "rows": {}}


def _fernet() -> Fernet:
    import os

    seed = os.getenv("SETTINGS_ENCRYPTION_KEY") or env.jwt_secret
    return Fernet(base64.urlsafe_b64encode(hashlib.sha256(("clinicos-settings:" + seed).encode()).digest()))


def _rows() -> dict:
    if time.monotonic() - _cache["at"] > 10:
        with SessionLocal() as db:
            _cache["rows"] = {r.key: (r.value, r.is_secret) for r in db.scalars(select(PlatformSetting))}
        _cache["at"] = time.monotonic()
    return _cache["rows"]


def invalidate():
    _cache["at"] = 0.0


def _convert(kind: str, raw: str):
    if kind == "bool":
        return raw == "1"
    if kind == "int":
        return int(raw)
    return raw


def source(name: str) -> str:
    row = _rows().get(name)
    if row is not None:
        return "database"
    attr = SPEC[name][4]
    return "environment" if attr and getattr(env, attr) not in ("", None) else "default"


def get(name: str):
    group, label, kind, secret, attr = SPEC[name]
    row = _rows().get(name)
    if row is not None:
        value, is_secret = row
        if is_secret:
            try:
                value = _fernet().decrypt(value.encode()).decode()
            except InvalidToken:  # key rotated: fall back to the environment instead of crashing
                return getattr(env, attr) if attr else DEFAULTS.get(name)
        try:
            return _convert(kind, value)
        except ValueError:
            pass
    if attr:
        return getattr(env, attr)
    return DEFAULTS.get(name, "")


def validate(name: str, value):
    """Returns the cleaned string to store, or raises ValueError with a message the admin can read."""
    group, label, kind, secret, _ = SPEC[name]
    if kind == "bool":
        if not isinstance(value, bool):
            raise ValueError(f"{label} must be on or off.")
        return "1" if value else "0"
    v = str(value).strip()
    if any(ord(c) < 32 for c in v) or len(v) > 300:
        raise ValueError(f"{label} contains invalid characters or is too long.")
    if kind == "int":
        if not v.isdigit() or not (1 <= int(v) <= 65535):
            raise ValueError(f"{label} must be a number between 1 and 65535.")
    if kind == "url" and v:
        u = urlparse(v)
        host = (u.hostname or "").lower()
        if u.scheme != "https" or not host:
            raise ValueError(f"{label} must be an https:// address.")
        try:
            ip = ipaddress.ip_address(host)
            bad = ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved
        except ValueError:
            bad = host == "localhost" or host.endswith((".local", ".internal", ".localdomain"))
        if bad:
            raise ValueError(f"{label} may not point at a private or local address.")
    if name == "groq_model" and v and not all(c.isalnum() or c in "-_.:/" for c in v):
        raise ValueError("Model names can only contain letters, numbers and - _ . : /")
    return v


def save(db, values: dict, clear: list, admin_id) -> list:
    changed = []
    for name, value in values.items():
        stored = validate(name, value)
        secret = SPEC[name][3]
        if secret and stored == "":
            continue  # blank secret box means "leave as is"
        if secret:
            stored = _fernet().encrypt(stored.encode()).decode()
        row = db.get(PlatformSetting, name) or PlatformSetting(key=name)
        row.value, row.is_secret, row.updated_at, row.updated_by = stored, secret, utcnow(), admin_id
        db.add(row)
        changed.append(name)
    for name in clear:
        row = db.get(PlatformSetting, name)
        if row:
            db.delete(row)
            changed.append(name)
    return changed


def view() -> list:
    out = []
    for name, (group, label, kind, secret, _) in SPEC.items():
        v = get(name)
        item = {"name": name, "group": group, "label": label, "kind": kind, "secret": secret, "source": source(name)}
        if secret:
            item.update(is_set=bool(v), hint=("…" + str(v)[-4:]) if v and len(str(v)) >= 8 else ("set" if v else ""))
        else:
            item["value"] = v
        out.append(item)
    return out
