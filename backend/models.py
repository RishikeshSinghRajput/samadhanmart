from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from .database import Base


class User(Base):
    __tablename__ = "Users"
    __table_args__ = (
        CheckConstraint(
            "Role IN ('buyer', 'seller_electronics', 'seller_medicine', 'advocate', 'admin')",
            name="CK_Users_Role",
        ),
        CheckConstraint(
            "(Role = 'admin' AND IsAdmin = 1) OR (Role <> 'admin' AND IsAdmin = 0)",
            name="CK_Users_IsAdminMatchesRole",
        ),
    )

    user_id: Mapped[int] = mapped_column("UserID", Integer, primary_key=True)
    full_name: Mapped[str] = mapped_column("FullName", String(120), nullable=False)
    role: Mapped[str] = mapped_column("Role", String(30), nullable=False)
    is_admin: Mapped[bool] = mapped_column("IsAdmin", Boolean, nullable=False, default=False)
    phone: Mapped[str] = mapped_column("Phone", String(20), unique=True, nullable=False)
    email: Mapped[str] = mapped_column("Email", String(254), unique=True, nullable=False)
    password_hash: Mapped[str | None] = mapped_column("PasswordHash", String(256))
    approval_status: Mapped[str] = mapped_column(
        "ApprovalStatus", String(20), nullable=False, default="APPROVED"
    )
    state: Mapped[str] = mapped_column("State", String(80), nullable=False, default="Bihar")
    district: Mapped[str] = mapped_column("District", String(80), nullable=False, default="Siwan")
    approval_note: Mapped[str | None] = mapped_column("ApprovalNote", String(500))
    approved_at: Mapped[datetime | None] = mapped_column("ApprovedAt", DateTime)
    created_at: Mapped[datetime] = mapped_column(
        "CreatedAt", DateTime, nullable=False, server_default=func.sysdatetime()
    )


class Electronic(Base):
    __tablename__ = "Electronics"
    __table_args__ = (
        CheckConstraint(
            "ListingStatus IN ('PENDING_VERIFICATION', 'VERIFIED', 'SOLD')",
            name="CK_Electronics_ListingStatus",
        ),
        CheckConstraint("Price > 0", name="CK_Electronics_Price"),
    )

    item_id: Mapped[int] = mapped_column("ItemID", Integer, primary_key=True)
    seller_id: Mapped[int] = mapped_column(
        "SellerID", ForeignKey("Users.UserID"), nullable=False, index=True
    )
    title: Mapped[str] = mapped_column("Title", String(160), nullable=False)
    description: Mapped[str] = mapped_column("Description", Text, nullable=False)
    category: Mapped[str] = mapped_column("Category", String(80), nullable=False, index=True)
    price: Mapped[Decimal] = mapped_column("Price", Numeric(12, 2), nullable=False)
    serial_imei: Mapped[str | None] = mapped_column("SerialIMEI", String(80))
    state: Mapped[str] = mapped_column("State", String(80), nullable=False, default="Bihar")
    district: Mapped[str] = mapped_column("District", String(80), nullable=False)
    listing_status: Mapped[str] = mapped_column(
        "ListingStatus", String(30), nullable=False, default="PENDING_VERIFICATION"
    )
    created_at: Mapped[datetime] = mapped_column(
        "CreatedAt", DateTime, nullable=False, server_default=func.sysdatetime()
    )


class ItemVerificationLog(Base):
    __tablename__ = "ItemVerificationLogs"
    __table_args__ = (
        CheckConstraint("Channel IN ('EMAIL', 'WHATSAPP')", name="CK_ItemVerificationLogs_Channel"),
        CheckConstraint(
            "EventType IN ('DISPATCH', 'VERIFICATION_ATTEMPT')",
            name="CK_ItemVerificationLogs_EventType",
        ),
        CheckConstraint("AttemptNumber >= 0", name="CK_ItemVerificationLogs_AttemptNumber"),
    )

    log_id: Mapped[int] = mapped_column("LogID", Integer, primary_key=True)
    item_id: Mapped[int] = mapped_column(
        "ItemID", ForeignKey("Electronics.ItemID"), nullable=False, index=True
    )
    recipient_email: Mapped[str] = mapped_column("RecipientEmail", String(254), nullable=False)
    recipient_phone: Mapped[str] = mapped_column("RecipientPhone", String(20), nullable=False)
    otp_code_hash: Mapped[str] = mapped_column("OTPCodeHash", String(64), nullable=False)
    channel: Mapped[str] = mapped_column("Channel", String(20), nullable=False)
    event_type: Mapped[str] = mapped_column("EventType", String(30), nullable=False)
    dispatch_status: Mapped[str] = mapped_column("DispatchStatus", String(30), nullable=False)
    verification_status: Mapped[str | None] = mapped_column("VerificationStatus", String(20))
    attempt_number: Mapped[int] = mapped_column("AttemptNumber", Integer, nullable=False, default=0)
    expires_at: Mapped[datetime] = mapped_column("ExpiresAt", DateTime, nullable=False)
    attempted_at: Mapped[datetime | None] = mapped_column("AttemptedAt", DateTime)
    verification_timestamp: Mapped[datetime | None] = mapped_column(
        "VerificationTimestamp", DateTime
    )
    created_at: Mapped[datetime] = mapped_column(
        "CreatedAt", DateTime, nullable=False, server_default=func.sysdatetime()
    )


class Medicine(Base):
    __tablename__ = "Medicines"
    __table_args__ = (
        CheckConstraint("Stock >= 0", name="CK_Medicines_Stock"),
        CheckConstraint("Price >= 0", name="CK_Medicines_Price"),
    )

    medicine_id: Mapped[int] = mapped_column("MedicineID", Integer, primary_key=True)
    seller_id: Mapped[int] = mapped_column(
        "SellerID", ForeignKey("Users.UserID"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column("Name", String(160), nullable=False, index=True)
    description: Mapped[str] = mapped_column("Description", Text, nullable=False, default="")
    batch_number: Mapped[str] = mapped_column("BatchNumber", String(80), nullable=False)
    stock: Mapped[int] = mapped_column("Stock", Integer, nullable=False, default=0)
    price: Mapped[Decimal] = mapped_column("Price", Numeric(10, 2), nullable=False)
    prescription_required: Mapped[bool] = mapped_column(
        "PrescriptionRequired", Boolean, nullable=False, default=False
    )
    chemist_name: Mapped[str] = mapped_column("ChemistName", String(120), nullable=False)
    state: Mapped[str] = mapped_column("State", String(80), nullable=False, default="Bihar")
    district: Mapped[str] = mapped_column("District", String(80), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(
        "CreatedAt", DateTime, nullable=False, server_default=func.sysdatetime()
    )


class PrescriptionOrder(Base):
    __tablename__ = "PrescriptionOrders"
    __table_args__ = (
        CheckConstraint("Quantity > 0", name="CK_PrescriptionOrders_Quantity"),
        CheckConstraint(
            "(IsChronicRefill = 0 AND RefillIntervalDays IS NULL AND NextRefillAt IS NULL) "
            "OR (IsChronicRefill = 1 AND RefillIntervalDays IN (30, 60, 90) AND NextRefillAt IS NOT NULL)",
            name="CK_PrescriptionOrders_RefillSchedule",
        ),
        CheckConstraint(
            "OrderStatus IN ('PLACED', 'MATCHED', 'FULFILLED', 'CANCELLED')",
            name="CK_PrescriptionOrders_OrderStatus",
        ),
    )

    order_id: Mapped[int] = mapped_column("OrderID", Integer, primary_key=True)
    medicine_id: Mapped[int] = mapped_column(
        "MedicineID", ForeignKey("Medicines.MedicineID"), nullable=False, index=True
    )
    customer_name: Mapped[str] = mapped_column("CustomerName", String(120), nullable=False)
    customer_phone: Mapped[str] = mapped_column("CustomerPhone", String(20), nullable=False)
    customer_email: Mapped[str] = mapped_column("CustomerEmail", String(254), nullable=False)
    quantity: Mapped[int] = mapped_column("Quantity", Integer, nullable=False)
    prescription_path: Mapped[str | None] = mapped_column("PrescriptionPath", String(500))
    is_chronic_refill: Mapped[bool] = mapped_column(
        "IsChronicRefill", Boolean, nullable=False, default=False
    )
    refill_interval_days: Mapped[int | None] = mapped_column("RefillIntervalDays", Integer)
    next_refill_at: Mapped[datetime | None] = mapped_column("NextRefillAt", DateTime)
    order_status: Mapped[str] = mapped_column("OrderStatus", String(20), nullable=False, default="PLACED")
    created_at: Mapped[datetime] = mapped_column(
        "CreatedAt", DateTime, nullable=False, server_default=func.sysdatetime()
    )


class Advocate(Base):
    __tablename__ = "Advocates"
    __table_args__ = (
        UniqueConstraint("BarCouncilNumber", name="UQ_Advocates_BarCouncilNumber"),
        CheckConstraint("ExperienceYears >= 0", name="CK_Advocates_ExperienceYears"),
        CheckConstraint("ConsultationFee >= 0", name="CK_Advocates_ConsultationFee"),
    )

    advocate_id: Mapped[int] = mapped_column("AdvocateID", Integer, primary_key=True)
    user_id: Mapped[int | None] = mapped_column("UserID", ForeignKey("Users.UserID"))
    full_name: Mapped[str] = mapped_column("FullName", String(120), nullable=False)
    bar_council_number: Mapped[str] = mapped_column("BarCouncilNumber", String(80), nullable=False)
    experience_years: Mapped[int] = mapped_column("ExperienceYears", Integer, nullable=False)
    consultation_fee: Mapped[Decimal] = mapped_column("ConsultationFee", Numeric(10, 2), nullable=False)
    specialization: Mapped[str] = mapped_column("Specialization", String(80), nullable=False, index=True)
    state: Mapped[str] = mapped_column("State", String(80), nullable=False, default="Bihar")
    district: Mapped[str] = mapped_column("District", String(80), nullable=False)
    verified: Mapped[bool] = mapped_column("Verified", Boolean, nullable=False, default=False)


class Consultation(Base):
    __tablename__ = "Consultations"
    __table_args__ = (
        UniqueConstraint("AdvocateID", "SlotStart", name="UQ_Consultations_AdvocateSlot"),
        CheckConstraint(
            "BookingStatus IN ('BOOKED', 'CANCELLED', 'COMPLETED')",
            name="CK_Consultations_BookingStatus",
        ),
        CheckConstraint("SlotEnd > SlotStart", name="CK_Consultations_Slot"),
    )

    consultation_id: Mapped[int] = mapped_column("ConsultationID", Integer, primary_key=True)
    advocate_id: Mapped[int] = mapped_column(
        "AdvocateID", ForeignKey("Advocates.AdvocateID"), nullable=False, index=True
    )
    client_name: Mapped[str] = mapped_column("ClientName", String(120), nullable=False)
    client_email: Mapped[str] = mapped_column("ClientEmail", String(254), nullable=False)
    client_phone: Mapped[str] = mapped_column("ClientPhone", String(20), nullable=False)
    slot_start: Mapped[datetime] = mapped_column("SlotStart", DateTime, nullable=False)
    slot_end: Mapped[datetime] = mapped_column("SlotEnd", DateTime, nullable=False)
    booking_status: Mapped[str] = mapped_column("BookingStatus", String(20), nullable=False, default="BOOKED")
    created_at: Mapped[datetime] = mapped_column(
        "CreatedAt", DateTime, nullable=False, server_default=func.sysdatetime()
    )


class ActivityLog(Base):
    __tablename__ = "ActivityLogs"

    activity_id: Mapped[int] = mapped_column("ActivityID", Integer, primary_key=True)
    actor_user_id: Mapped[int | None] = mapped_column("ActorUserID", ForeignKey("Users.UserID"))
    action: Mapped[str] = mapped_column("Action", String(80), nullable=False, index=True)
    target_type: Mapped[str] = mapped_column("TargetType", String(40), nullable=False)
    target_id: Mapped[int | None] = mapped_column("TargetID", Integer)
    description: Mapped[str] = mapped_column("Description", String(500), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        "CreatedAt", DateTime, nullable=False, server_default=func.sysdatetime(), index=True
    )
