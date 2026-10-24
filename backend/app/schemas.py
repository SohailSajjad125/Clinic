import re
import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, EmailStr, Field, field_validator, model_validator


COMMON_PASSWORDS = {"password", "password1", "password12", "password123", "passw0rd", "12345678", "123456789", "1234567890", "11111111", "00000000", "qwerty123", "qwertyuiop", "qwerty12",
                    "iloveyou", "abc12345", "abcd1234", "admin123", "admin1234", "welcome1", "welcome123", "letmein123", "changeme", "changeme123", "clinicos123", "clinic123", "pakistan123", "temp1234", "tempass123"}
_CTRL = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")


def _pw(v: str) -> str:
    if "\x00" in v:
        raise ValueError("Password contains an invalid character.")
    if len(v.encode()) > 72:
        raise ValueError("Password must be at most 72 bytes.")
    low = v.lower()
    if low in COMMON_PASSWORDS or v.isdigit() or len(set(v)) < 4:
        raise ValueError("That password is too easy to guess. Choose a longer or less common one.")
    return v


def _walk(v, key=""):
    if isinstance(v, str):
        return v if ("password" in key or "token" in key) else _CTRL.sub("", v).strip()
    if isinstance(v, dict):
        return {k: _walk(x, str(k)) for k, x in v.items()}
    if isinstance(v, list):
        return [_walk(x, key) for x in v]
    return v


class Clean(BaseModel):
    """Base for every request body: strips control characters (NUL crashes PostgreSQL) and surrounding whitespace. Passwords and tokens are left untouched."""

    @model_validator(mode="before")
    @classmethod
    def _sanitize(cls, data):
        return _walk(data) if isinstance(data, dict) else data


class RegisterClinicIn(Clean):
    clinic_name: str = Field(min_length=2, max_length=160)
    clinic_type: str = Field(min_length=2, max_length=60)
    city: str = Field(min_length=1, max_length=80)
    country: str = Field(min_length=2, max_length=80)
    full_name: str = Field(min_length=2, max_length=120)
    email: EmailStr
    password: str = Field(min_length=8)
    _v = field_validator("password")(_pw)

    @model_validator(mode="after")
    def _not_email(self):
        local = str(self.email).split("@")[0].lower()
        if len(local) >= 4 and local in self.password.lower():
            raise ValueError("Your password shouldn't contain your email name.")
        return self


class LoginIn(Clean):
    email: EmailStr
    password: str
    clinic_id: uuid.UUID | None = None
    audience: Literal["staff", "patient"] | None = None


class RefreshIn(Clean):
    refresh_token: str


class ClinicOut(Clean):
    id: uuid.UUID
    name: str


class MeOut(Clean):
    user_id: uuid.UUID
    member_id: uuid.UUID | None = None
    email: str
    full_name: str
    role: str
    clinic: ClinicOut | None = None
    email_verified: bool = False
    must_change_password: bool = False
    plan: str | None = None
    can_view_clinical: bool = False


class AuthOut(Clean):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    me: MeOut


class DoctorProfileIn(Clean):
    specialization: str = Field(default="", max_length=80)
    qualifications: str = Field(default="", max_length=200)
    license_no: str = Field(default="", max_length=40)
    experience_years: int = Field(default=0, ge=0, le=70)
    consultation_fee: int = Field(default=0, ge=0, le=1_000_000)
    phone: str = Field(default="", max_length=30)
    bio: str = Field(default="", max_length=1000)
    available_days: list[Literal["mon", "tue", "wed", "thu", "fri", "sat", "sun"]] = Field(default_factory=lambda: ["mon", "tue", "wed", "thu", "fri", "sat"], max_length=7)
    start_time: str = Field(default="09:00", pattern=r"^([01]\d|2[0-3]):[0-5]\d$")
    end_time: str = Field(default="17:00", pattern=r"^([01]\d|2[0-3]):[0-5]\d$")
    slot_minutes: int = Field(default=20, ge=5, le=120)

    @model_validator(mode="after")
    def _order(self):
        if self.end_time <= self.start_time:
            raise ValueError("Finishing time must be after the starting time.")
        return self


class StaffCreateIn(Clean):
    email: EmailStr
    full_name: str = Field(min_length=2, max_length=120)
    role: Literal["doctor", "receptionist", "nurse"]
    password: str = Field(min_length=8, description="Temporary password for a new account")
    _v = field_validator("password")(_pw)
    profile: DoctorProfileIn | None = None


class StaffOut(Clean):
    member_id: uuid.UUID
    user_id: uuid.UUID
    email: str
    full_name: str
    role: str
    created_at: datetime
    deleted_at: datetime | None = None
    can_view_clinical: bool = False
    profile: dict | None = None


class ContactIn(Clean):
    name: str = Field(min_length=2, max_length=120)
    email: EmailStr
    clinic_name: str | None = Field(default=None, max_length=160)
    phone: str | None = Field(default=None, max_length=30)
    topic: Literal["demo", "sales", "support", "partnership", "other"]
    message: str = Field(min_length=10, max_length=2000)
    website: str = ""  # honeypot: real visitors never fill this


class NewsletterIn(Clean):
    email: EmailStr
    website: str = ""


# ---------- Phase 3: clinical, billing, realtime ----------
from datetime import date  # noqa: E402

from pydantic import ConfigDict  # noqa: E402


class PatientIn(Clean):
    full_name: str = Field(min_length=2, max_length=120)
    phone: str | None = Field(default=None, max_length=30)
    email: EmailStr | None = None
    gender: Literal["male", "female", "other"] | None = None
    date_of_birth: date | None = None
    address: str | None = Field(default=None, max_length=255)
    allergies: str | None = Field(default=None, max_length=2000)
    medical_history: str | None = Field(default=None, max_length=5000)
    current_medications: str | None = Field(default=None, max_length=3000)
    emergency_contact_name: str | None = Field(default=None, max_length=120)
    emergency_contact_phone: str | None = Field(default=None, max_length=30)


class PatientPatch(Clean):
    full_name: str | None = Field(default=None, min_length=2, max_length=120)
    phone: str | None = Field(default=None, max_length=30)
    email: EmailStr | None = None
    gender: Literal["male", "female", "other"] | None = None
    date_of_birth: date | None = None
    address: str | None = Field(default=None, max_length=255)
    allergies: str | None = Field(default=None, max_length=2000)
    medical_history: str | None = Field(default=None, max_length=5000)
    current_medications: str | None = Field(default=None, max_length=3000)
    emergency_contact_name: str | None = Field(default=None, max_length=120)
    emergency_contact_phone: str | None = Field(default=None, max_length=30)


class PatientOut(PatientIn):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    created_at: datetime
    email: str | None = None
    user_id: uuid.UUID | None = None


APPT_STATUSES = Literal["booked", "confirmed", "arrived", "in_consultation", "completed", "cancelled", "no_show"]


class AppointmentIn(Clean):
    patient_id: uuid.UUID
    doctor_id: uuid.UUID | None = None
    scheduled_at: datetime
    reason: str | None = Field(default=None, max_length=200)
    location_id: uuid.UUID | None = None
    repeat_every_days: int | None = Field(default=None, ge=1, le=90)
    repeat_count: int | None = Field(default=None, ge=2, le=12)


class WalkInIn(Clean):
    patient_id: uuid.UUID
    doctor_id: uuid.UUID | None = None
    reason: str | None = Field(default=None, max_length=200)
    location_id: uuid.UUID | None = None


class AppointmentPatch(Clean):
    doctor_id: uuid.UUID | None = None
    scheduled_at: datetime | None = None
    reason: str | None = Field(default=None, max_length=200)
    status: APPT_STATUSES | None = None
    location_id: uuid.UUID | None = None


class AppointmentOut(Clean):
    id: uuid.UUID
    patient_id: uuid.UUID
    patient_name: str
    doctor_id: uuid.UUID | None
    doctor_name: str | None
    scheduled_at: datetime
    reason: str | None
    status: str
    queue_no: int | None
    is_walk_in: bool = False
    location_id: uuid.UUID | None = None
    series_id: uuid.UUID | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None


class RxItem(Clean):
    medicine: str = Field(min_length=1, max_length=120)
    dose: str = Field(default="", max_length=60)
    frequency: str = Field(default="", max_length=60)
    duration: str = Field(default="", max_length=60)
    instructions: str = Field(default="", max_length=300)


class ConsultationIn(Clean):
    patient_id: uuid.UUID
    appointment_id: uuid.UUID | None = None
    complaint: str | None = Field(default=None, max_length=5000)
    examination: str | None = Field(default=None, max_length=5000)
    assessment: str | None = Field(default=None, max_length=5000)
    plan: str | None = Field(default=None, max_length=5000)
    vitals: dict[str, str] = Field(default_factory=dict, max_length=12)
    prescription: list[RxItem] = Field(default_factory=list, max_length=30)
    follow_up_on: date | None = None
    shared_with_patient: bool = True


class ConsultationPatch(Clean):
    complaint: str | None = Field(default=None, max_length=5000)
    examination: str | None = Field(default=None, max_length=5000)
    assessment: str | None = Field(default=None, max_length=5000)
    plan: str | None = Field(default=None, max_length=5000)
    vitals: dict[str, str] | None = Field(default=None, max_length=12)
    prescription: list[RxItem] | None = Field(default=None, max_length=30)
    follow_up_on: date | None = None
    shared_with_patient: bool | None = None


class ConsultationOut(Clean):
    id: uuid.UUID
    patient_id: uuid.UUID
    patient_name: str
    appointment_id: uuid.UUID | None
    complaint: str | None
    examination: str | None
    assessment: str | None
    plan: str | None
    vitals: dict
    prescription: list
    follow_up_on: date | None
    ai_summary: str | None
    shared_with_patient: bool = True
    created_at: datetime


class InvoiceItem(Clean):
    description: str = Field(min_length=1, max_length=200)
    qty: int = Field(default=1, ge=1, le=1000)
    price: int = Field(ge=0, le=10_000_000)


class InvoiceIn(Clean):
    patient_id: uuid.UUID
    items: list[InvoiceItem] = Field(min_length=1, max_length=50)
    discount: int = Field(default=0, ge=0)
    tax: int = Field(default=0, ge=0)


class PaymentIn(Clean):
    amount: int = Field(ge=1, le=100_000_000)
    method: Literal["cash", "card", "bank", "online"] = "cash"


class InvoiceOut(Clean):
    id: uuid.UUID
    number: int
    patient_id: uuid.UUID
    patient_name: str
    items: list
    discount: int
    tax: int
    total: int
    paid: int
    status: str
    created_at: datetime


class ChatIn(Clean):
    body: str = Field(min_length=1, max_length=2000)


class AIMessage(Clean):
    role: Literal["user", "assistant"]
    content: str = Field(max_length=4000)


class AIChatIn(Clean):
    messages: list[AIMessage] = Field(min_length=1, max_length=30)
    tz_offset_minutes: int = Field(default=0, ge=-840, le=840)


class ForgotIn(Clean):
    email: EmailStr


class ResetIn(Clean):
    token: str = Field(min_length=10, max_length=200)
    password: str = Field(min_length=8)
    _v = field_validator("password")(_pw)


class TokenIn(Clean):
    token: str = Field(min_length=10, max_length=200)


class ChangePasswordIn(Clean):
    current_password: str
    new_password: str = Field(min_length=8)
    _v = field_validator("new_password")(_pw)


# ---------- full-spec additions ----------
class ClinicPatch(Clean):
    name: str | None = Field(default=None, min_length=2, max_length=160)
    clinic_type: str | None = Field(default=None, min_length=2, max_length=60)
    city: str | None = Field(default=None, max_length=80)
    country: str | None = Field(default=None, max_length=80)
    working_hours: dict[str, dict | None] | None = None
    public_listing: bool | None = None

    @field_validator("working_hours")
    @classmethod
    def _hours(cls, v):
        if v is None:
            return v
        ok = re.compile(r"^([01]\d|2[0-3]):[0-5]\d$")
        for day, h in v.items():
            if day not in ("mon", "tue", "wed", "thu", "fri", "sat", "sun"):
                raise ValueError("Unknown day.")
            if h is not None and (set(h) != {"open", "close"} or not all(isinstance(x, str) and ok.match(x) for x in h.values())):
                raise ValueError("Hours must look like 09:00.")
        return v


class ServiceIn(Clean):
    name: str = Field(min_length=1, max_length=120)
    price: int = Field(ge=0, le=10_000_000)


class TemplateIn(Clean):
    medicine: str = Field(min_length=1, max_length=120)
    dose: str = Field(default="", max_length=60)
    frequency: str = Field(default="", max_length=60)
    duration: str = Field(default="", max_length=60)
    instructions: str = Field(default="", max_length=300)


class LocationIn(Clean):
    name: str = Field(min_length=1, max_length=120)
    address: str | None = Field(default=None, max_length=255)


class PermissionsIn(Clean):
    can_view_clinical: bool


class InventoryIn(Clean):
    name: str = Field(min_length=1, max_length=120)
    unit: str = Field(default="pcs", max_length=20)
    quantity: int = Field(default=0, ge=0, le=1_000_000)
    reorder_level: int = Field(default=0, ge=0, le=1_000_000)
    unit_price: int = Field(default=0, ge=0, le=10_000_000)


class InventoryPatch(Clean):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    unit: str | None = Field(default=None, max_length=20)
    reorder_level: int | None = Field(default=None, ge=0, le=1_000_000)
    unit_price: int | None = Field(default=None, ge=0, le=10_000_000)


class AdjustIn(Clean):
    delta: int = Field(ge=-1_000_000, le=1_000_000)
    reason: str = Field(default="", max_length=200)


class DocumentPatch(Clean):
    category: Literal["report", "scan", "lab", "other"] | None = None
    shared_with_patient: bool | None = None


class PortalInviteIn(Clean):
    email: EmailStr
    password: str = Field(min_length=8)
    _v = field_validator("password")(_pw)


class PortalBookIn(Clean):
    scheduled_at: datetime
    doctor_id: uuid.UUID | None = None
    reason: str | None = Field(default=None, max_length=200)


class MessageIn(Clean):
    body: str = Field(min_length=1, max_length=2000)


class AdminClinicPatch(Clean):
    plan: Literal["starter", "clinic", "group", "enterprise"] | None = None
    status: Literal["active", "suspended"] | None = None


class RegisterPatientIn(Clean):
    clinic_id: uuid.UUID
    full_name: str = Field(min_length=2, max_length=120)
    email: EmailStr
    phone: str | None = Field(default=None, max_length=30)
    date_of_birth: date | None = None
    password: str = Field(min_length=8)
    accept_terms: bool
    _v = field_validator("password")(_pw)

    @model_validator(mode="after")
    def _ok(self):
        if not self.accept_terms:
            raise ValueError("Please accept the terms to create an account.")
        local = str(self.email).split("@")[0].lower()
        if len(local) >= 4 and local in self.password.lower():
            raise ValueError("Your password shouldn't contain your email name.")
        return self


class SettingsUpdateIn(Clean):
    values: dict[str, str | int | bool] = Field(default_factory=dict, max_length=30)
    clear: list[str] = Field(default_factory=list, max_length=30)


class AdminUserPatch(Clean):
    is_active: bool
