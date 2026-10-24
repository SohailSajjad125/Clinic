import uuid
from datetime import date, datetime, timezone

from sqlalchemy import JSON, CheckConstraint, Boolean, Date, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .core.database import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Role:
    OWNER = "owner"
    DOCTOR = "doctor"
    RECEPTIONIST = "receptionist"
    NURSE = "nurse"
    PATIENT = "patient"
    STAFF = (OWNER, DOCTOR, RECEPTIONIST, NURSE)
    INVITABLE = (DOCTOR, RECEPTIONIST, NURSE)


class Clinic(Base):
    __tablename__ = "clinics"
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(160))
    clinic_type: Mapped[str] = mapped_column(String(60))
    city: Mapped[str] = mapped_column(String(80))
    country: Mapped[str] = mapped_column(String(80))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    public_listing: Mapped[bool] = mapped_column(Boolean, default=True)
    plan: Mapped[str] = mapped_column(String(20), default="starter")
    status: Mapped[str] = mapped_column(String(12), default="active")
    working_hours: Mapped[dict] = mapped_column(JSON, default=dict)
    public_listing: Mapped[bool] = mapped_column(Boolean, default=True)  # patients can find this clinic when signing up


class User(Base):
    __tablename__ = "users"
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(254), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(100))
    full_name: Mapped[str] = mapped_column(String(120))
    phone: Mapped[str | None] = mapped_column(String(30), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_superadmin: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    failed_logins: Mapped[int] = mapped_column(Integer, default=0)
    locked_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    email_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    must_change_password: Mapped[bool] = mapped_column(Boolean, default=False)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class ClinicMember(Base):
    """A user's role inside one clinic. Soft-deleted rows form the staff 'deleted history'."""

    __tablename__ = "clinic_members"
    __table_args__ = (UniqueConstraint("user_id", "clinic_id", name="uq_member_user_clinic"),)
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    clinic_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("clinics.id", ondelete="CASCADE"), index=True)
    role: Mapped[str] = mapped_column(String(20))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    deleted_by: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)
    can_view_clinical: Mapped[bool] = mapped_column(Boolean, default=False)
    user: Mapped[User] = relationship()
    clinic: Mapped[Clinic] = relationship()


class AuditLog(Base):
    """No foreign keys on purpose: entries survive permanent deletion and hold ids only, no personal data."""

    __tablename__ = "audit_logs"
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    clinic_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True, index=True)
    actor_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)
    action: Mapped[str] = mapped_column(String(60))
    entity_type: Mapped[str] = mapped_column(String(40))
    entity_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class ContactMessage(Base):
    """Messages sent from the public website contact form."""

    __tablename__ = "contact_messages"
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(120))
    email: Mapped[str] = mapped_column(String(254))
    clinic_name: Mapped[str | None] = mapped_column(String(160), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(30), nullable=True)
    topic: Mapped[str] = mapped_column(String(20))
    message: Mapped[str] = mapped_column(Text)
    handled: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class NewsletterSubscriber(Base):
    __tablename__ = "newsletter_subscribers"
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(254), unique=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class SoftDelete:
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    deleted_by: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)


def _pk():
    return mapped_column(Uuid, primary_key=True, default=uuid.uuid4)


def _clinic_fk():
    return mapped_column(ForeignKey("clinics.id", ondelete="CASCADE"), index=True)


class Patient(SoftDelete, Base):
    __tablename__ = "patients"
    id: Mapped[uuid.UUID] = _pk()
    clinic_id: Mapped[uuid.UUID] = _clinic_fk()
    full_name: Mapped[str] = mapped_column(String(120))
    phone: Mapped[str | None] = mapped_column(String(30), nullable=True)
    email: Mapped[str | None] = mapped_column(String(254), nullable=True)
    gender: Mapped[str | None] = mapped_column(String(10), nullable=True)
    date_of_birth: Mapped[date | None] = mapped_column(Date, nullable=True)
    address: Mapped[str | None] = mapped_column(String(255), nullable=True)
    allergies: Mapped[str | None] = mapped_column(Text, nullable=True)
    medical_history: Mapped[str | None] = mapped_column(Text, nullable=True)
    current_medications: Mapped[str | None] = mapped_column(Text, nullable=True)
    emergency_contact_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    emergency_contact_phone: Mapped[str | None] = mapped_column(String(30), nullable=True)
    user_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)  # portal login
    self_registered: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Appointment(SoftDelete, Base):
    __tablename__ = "appointments"
    id: Mapped[uuid.UUID] = _pk()
    clinic_id: Mapped[uuid.UUID] = _clinic_fk()
    patient_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("patients.id", ondelete="CASCADE"), index=True)
    doctor_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("clinic_members.id", ondelete="SET NULL"), nullable=True)
    scheduled_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    reason: Mapped[str | None] = mapped_column(String(200), nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="booked")
    queue_no: Mapped[int | None] = mapped_column(Integer, nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    series_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)
    is_walk_in: Mapped[bool] = mapped_column(Boolean, default=False)
    location_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("locations.id", ondelete="SET NULL"), nullable=True)
    reminded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    patient: Mapped[Patient] = relationship()
    doctor: Mapped["ClinicMember | None"] = relationship(foreign_keys=[doctor_id])


class Consultation(SoftDelete, Base):
    __tablename__ = "consultations"
    id: Mapped[uuid.UUID] = _pk()
    clinic_id: Mapped[uuid.UUID] = _clinic_fk()
    patient_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("patients.id", ondelete="CASCADE"), index=True)
    appointment_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("appointments.id", ondelete="SET NULL"), nullable=True)
    doctor_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("clinic_members.id", ondelete="SET NULL"), nullable=True)
    complaint: Mapped[str | None] = mapped_column(Text, nullable=True)
    examination: Mapped[str | None] = mapped_column(Text, nullable=True)
    assessment: Mapped[str | None] = mapped_column(Text, nullable=True)
    plan: Mapped[str | None] = mapped_column(Text, nullable=True)
    vitals: Mapped[dict] = mapped_column(JSON, default=dict)
    prescription: Mapped[list] = mapped_column(JSON, default=list)
    follow_up_on: Mapped[date | None] = mapped_column(Date, nullable=True)
    ai_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    shared_with_patient: Mapped[bool] = mapped_column(Boolean, default=True)
    reminded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    patient: Mapped[Patient] = relationship()


class Invoice(SoftDelete, Base):
    __tablename__ = "invoices"
    __table_args__ = (UniqueConstraint("clinic_id", "number", name="uq_invoice_number"), CheckConstraint("paid >= 0 AND total >= 0 AND paid <= total", name="ck_invoice_amounts"))
    id: Mapped[uuid.UUID] = _pk()
    clinic_id: Mapped[uuid.UUID] = _clinic_fk()
    patient_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("patients.id", ondelete="CASCADE"), index=True)
    number: Mapped[int] = mapped_column(Integer)
    items: Mapped[list] = mapped_column(JSON, default=list)
    discount: Mapped[int] = mapped_column(Integer, default=0)
    tax: Mapped[int] = mapped_column(Integer, default=0)
    total: Mapped[int] = mapped_column(Integer, default=0)
    paid: Mapped[int] = mapped_column(Integer, default=0)
    refunded: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    patient: Mapped[Patient] = relationship()


class Payment(Base):
    __tablename__ = "payments"
    id: Mapped[uuid.UUID] = _pk()
    clinic_id: Mapped[uuid.UUID] = _clinic_fk()
    invoice_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("invoices.id", ondelete="CASCADE"), index=True)
    amount: Mapped[int] = mapped_column(Integer)  # negative = refund
    method: Mapped[str] = mapped_column(String(12), default="cash")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Notification(Base):
    __tablename__ = "notifications"
    id: Mapped[uuid.UUID] = _pk()
    clinic_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("clinics.id", ondelete="CASCADE"), nullable=True, index=True)  # null = platform notification
    user_id: Mapped[uuid.UUID] = mapped_column(Uuid, index=True)
    title: Mapped[str] = mapped_column(String(160))
    body: Mapped[str] = mapped_column(Text, default="")
    category: Mapped[str] = mapped_column(String(24), default="general", index=True)  # which feature gets the red dot
    link: Mapped[str | None] = mapped_column(String(160), nullable=True)
    read: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class ChatMessage(Base):
    __tablename__ = "chat_messages"
    id: Mapped[uuid.UUID] = _pk()
    clinic_id: Mapped[uuid.UUID] = _clinic_fk()
    sender_id: Mapped[uuid.UUID] = mapped_column(Uuid)
    sender_name: Mapped[str] = mapped_column(String(120))
    body: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class AIAction(Base):
    """An action the assistant proposed. Nothing runs until the user confirms it."""

    __tablename__ = "ai_actions"
    id: Mapped[uuid.UUID] = _pk()
    clinic_id: Mapped[uuid.UUID] = _clinic_fk()
    user_id: Mapped[uuid.UUID] = mapped_column(Uuid, index=True)
    tool: Mapped[str] = mapped_column(String(40))
    args: Mapped[dict] = mapped_column(JSON, default=dict)
    summary: Mapped[str] = mapped_column(String(300))
    status: Mapped[str] = mapped_column(String(12), default="pending")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Location(Base):
    __tablename__ = "locations"
    id: Mapped[uuid.UUID] = _pk()
    clinic_id: Mapped[uuid.UUID] = _clinic_fk()
    name: Mapped[str] = mapped_column(String(120))
    address: Mapped[str | None] = mapped_column(String(255), nullable=True)


class Service(Base):
    __tablename__ = "services"
    id: Mapped[uuid.UUID] = _pk()
    clinic_id: Mapped[uuid.UUID] = _clinic_fk()
    name: Mapped[str] = mapped_column(String(120))
    price: Mapped[int] = mapped_column(Integer, default=0)


class MedicineTemplate(Base):
    __tablename__ = "medicine_templates"
    id: Mapped[uuid.UUID] = _pk()
    clinic_id: Mapped[uuid.UUID] = _clinic_fk()
    medicine: Mapped[str] = mapped_column(String(120))
    dose: Mapped[str] = mapped_column(String(60), default="")
    frequency: Mapped[str] = mapped_column(String(60), default="")
    duration: Mapped[str] = mapped_column(String(60), default="")
    instructions: Mapped[str] = mapped_column(String(300), default="")


class Document(SoftDelete, Base):
    __tablename__ = "documents"
    id: Mapped[uuid.UUID] = _pk()
    clinic_id: Mapped[uuid.UUID] = _clinic_fk()
    patient_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("patients.id", ondelete="CASCADE"), index=True)
    filename: Mapped[str] = mapped_column(String(200))
    content_type: Mapped[str] = mapped_column(String(80))
    size: Mapped[int] = mapped_column(Integer)
    storage_key: Mapped[str] = mapped_column(String(80))
    category: Mapped[str] = mapped_column(String(12), default="other")
    shared_with_patient: Mapped[bool] = mapped_column(Boolean, default=False)
    uploaded_by: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    patient: Mapped[Patient] = relationship()


class InventoryItem(SoftDelete, Base):
    __tablename__ = "inventory_items"
    __table_args__ = (CheckConstraint("quantity >= 0", name="ck_inventory_quantity"),)
    id: Mapped[uuid.UUID] = _pk()
    clinic_id: Mapped[uuid.UUID] = _clinic_fk()
    name: Mapped[str] = mapped_column(String(120))
    unit: Mapped[str] = mapped_column(String(20), default="pcs")
    quantity: Mapped[int] = mapped_column(Integer, default=0)
    reorder_level: Mapped[int] = mapped_column(Integer, default=0)
    unit_price: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Session(Base):
    """One signed-in device. Refresh tokens rotate; reuse of an old one revokes the session."""

    __tablename__ = "sessions"
    id: Mapped[uuid.UUID] = _pk()
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    member_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)
    refresh_jti: Mapped[str] = mapped_column(String(40))
    user_agent: Mapped[str | None] = mapped_column(String(200), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    last_used_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class EmailToken(Base):
    __tablename__ = "email_tokens"
    id: Mapped[uuid.UUID] = _pk()
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    kind: Mapped[str] = mapped_column(String(10))  # reset | verify
    token_hash: Mapped[str] = mapped_column(String(64), index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class PortalMessage(Base):
    __tablename__ = "portal_messages"
    id: Mapped[uuid.UUID] = _pk()
    clinic_id: Mapped[uuid.UUID] = _clinic_fk()
    patient_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("patients.id", ondelete="CASCADE"), index=True)
    sender_id: Mapped[uuid.UUID] = mapped_column(Uuid)
    sender_name: Mapped[str] = mapped_column(String(120))
    from_patient: Mapped[bool] = mapped_column(Boolean, default=False)
    body: Mapped[str] = mapped_column(Text)
    read: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class OutboundMessage(Base):
    """Log of email/SMS/WhatsApp attempts."""

    __tablename__ = "outbound_messages"
    id: Mapped[uuid.UUID] = _pk()
    clinic_id: Mapped[uuid.UUID] = _clinic_fk()
    patient_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True, index=True)
    channel: Mapped[str] = mapped_column(String(10))
    recipient: Mapped[str] = mapped_column(String(254))
    subject: Mapped[str] = mapped_column(String(200), default="")
    body: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(10))  # sent | failed | skipped
    error: Mapped[str | None] = mapped_column(String(300), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class ChatRead(Base):
    """When each staff member last opened team chat; anything newer from others shows a red dot."""

    __tablename__ = "chat_reads"
    user_id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True)
    clinic_id: Mapped[uuid.UUID] = _clinic_fk()
    last_read_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class DoctorProfile(Base):
    __tablename__ = "doctor_profiles"
    member_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("clinic_members.id", ondelete="CASCADE"), primary_key=True)
    specialization: Mapped[str | None] = mapped_column(String(120), nullable=True)
    qualifications: Mapped[str | None] = mapped_column(String(200), nullable=True)
    license_no: Mapped[str | None] = mapped_column(String(60), nullable=True)
    experience_years: Mapped[int | None] = mapped_column(Integer, nullable=True)
    consultation_fee: Mapped[int | None] = mapped_column(Integer, nullable=True)
    phone: Mapped[str | None] = mapped_column(String(30), nullable=True)
    bio: Mapped[str | None] = mapped_column(Text, nullable=True)
    available_days: Mapped[list] = mapped_column(JSON, default=lambda: ["mon", "tue", "wed", "thu", "fri", "sat"])
    start_time: Mapped[str] = mapped_column(String(5), default="09:00")
    end_time: Mapped[str] = mapped_column(String(5), default="17:00")
    slot_minutes: Mapped[int] = mapped_column(Integer, default=20)


class PlatformSetting(Base):
    """Runtime settings edited by platform admins. Secret values are stored encrypted."""

    __tablename__ = "platform_settings"
    key: Mapped[str] = mapped_column(String(40), primary_key=True)
    value: Mapped[str] = mapped_column(Text, default="")
    is_secret: Mapped[bool] = mapped_column(Boolean, default=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_by: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)


class ChatClear(Base):
    """"Clear chat" is per person: it hides older messages from that person's view only. Nobody else's view changes."""

    __tablename__ = "chat_clears"
    __table_args__ = (UniqueConstraint("user_id", "scope", name="uq_chat_clear_user_scope"),)
    id: Mapped[uuid.UUID] = _pk()
    user_id: Mapped[uuid.UUID] = mapped_column(Uuid, index=True)
    clinic_id: Mapped[uuid.UUID] = _clinic_fk()
    scope: Mapped[str] = mapped_column(String(60))  # "team" | "patient:<id>" (staff) | "portal" (a patient's own thread)
    cleared_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
