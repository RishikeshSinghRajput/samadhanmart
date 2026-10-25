from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator, model_validator


class ElectronicsCreate(BaseModel):
    seller_name: str = Field(min_length=2, max_length=120)
    seller_email: EmailStr
    seller_phone: str = Field(pattern=r"^\+?[0-9\s()-]{7,20}$")
    title: str = Field(min_length=2, max_length=160)
    description: str = Field(min_length=5, max_length=4000)
    category: str = Field(min_length=2, max_length=80)
    price: Decimal = Field(gt=0, max_digits=12, decimal_places=2)
    serial_imei: str | None = Field(default=None, max_length=80)
    state: str = Field(min_length=2, max_length=80)
    district: str = Field(min_length=2, max_length=80)


class ElectronicsCreateResult(BaseModel):
    item_id: int
    listing_status: str
    dispatch_statuses: dict[str, str]
    development_otps: dict[str, str] | None = None
    message: str


class ElectronicsOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    item_id: int
    title: str
    description: str
    category: str
    price: Decimal
    state: str
    district: str
    created_at: datetime


class ElectronicsVerification(BaseModel):
    item_id: int = Field(gt=0)
    email_otp: str = Field(pattern=r"^\d{6}$")
    whatsapp_otp: str = Field(pattern=r"^\d{6}$")


class MedicineOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    medicine_id: int
    name: str
    description: str
    batch_number: str
    stock: int
    price: Decimal
    prescription_required: bool
    chemist_name: str
    state: str
    district: str


class MedicineOrderCreate(BaseModel):
    medicine_id: int = Field(gt=0)
    customer_name: str = Field(min_length=2, max_length=120)
    customer_phone: str = Field(pattern=r"^\+?[0-9\s()-]{7,20}$")
    customer_email: EmailStr
    quantity: int = Field(gt=0, le=100)
    prescription_path: str | None = Field(default=None, max_length=500)
    is_chronic_refill: bool = False
    refill_interval_days: Literal[30, 60, 90] | None = None

    @field_validator("prescription_path")
    @classmethod
    def validate_prescription_path(cls, value: str | None) -> str | None:
        if value is not None and not value.startswith("prescriptions/"):
            raise ValueError("Use a path returned by the prescription upload endpoint")
        return value

    @model_validator(mode="after")
    def validate_refill_schedule(self) -> "MedicineOrderCreate":
        if self.is_chronic_refill and self.refill_interval_days is None:
            raise ValueError("Choose a refill interval for a chronic refill request")
        if not self.is_chronic_refill and self.refill_interval_days is not None:
            raise ValueError("Refill interval is only valid for a chronic refill request")
        return self


class MedicineOrderOut(BaseModel):
    order_id: int
    order_status: str
    message: str


Specialization = Literal["Civil", "Criminal", "Corporate", "Land Disputes"]


class AdvocateOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    advocate_id: int
    full_name: str
    bar_council_number: str
    experience_years: int
    consultation_fee: Decimal
    specialization: str
    state: str
    district: str
    verified: bool


class ConsultationCreate(BaseModel):
    advocate_id: int = Field(gt=0)
    client_name: str = Field(min_length=2, max_length=120)
    client_email: EmailStr
    client_phone: str = Field(pattern=r"^\+?[0-9\s()-]{7,20}$")
    slot_start: datetime

    @model_validator(mode="after")
    def require_future_slot(self) -> "ConsultationCreate":
        if self.slot_start.tzinfo is None:
            raise ValueError("Consultation slot must include a timezone")
        if self.slot_start <= datetime.now(self.slot_start.tzinfo):
            raise ValueError("Consultation slot must be in the future")
        return self


class ConsultationOut(BaseModel):
    consultation_id: int
    advocate_id: int
    slot_start: datetime
    slot_end: datetime
    booking_status: str


class PrescriptionUploadOut(BaseModel):
    prescription_path: str
    message: str


class RegistrationCreate(BaseModel):
    full_name: str = Field(min_length=2, max_length=120)
    email: EmailStr
    phone: str = Field(pattern=r"^\+?[0-9\s()-]{7,20}$")
    password: str = Field(min_length=12, max_length=128)
    role: Literal["seller_electronics", "seller_medicine", "advocate"]
    state: str = Field(min_length=2, max_length=80)
    district: str = Field(min_length=2, max_length=80)
    bar_council_number: str | None = Field(default=None, max_length=80)
    experience_years: int | None = Field(default=None, ge=0, le=70)
    consultation_fee: Decimal | None = Field(default=None, ge=0, max_digits=10, decimal_places=2)
    specialization: Specialization | None = None

    @model_validator(mode="after")
    def validate_advocate_profile(self) -> "RegistrationCreate":
        advocate_fields = (
            self.bar_council_number,
            self.experience_years,
            self.consultation_fee,
            self.specialization,
        )
        if self.role == "advocate" and any(value is None for value in advocate_fields):
            raise ValueError("Advocate registrations require bar council number, experience, fee, and specialization")
        if self.role != "advocate" and any(value is not None for value in advocate_fields):
            raise ValueError("Advocate profile details are only valid for advocate registration")
        return self


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: int
    full_name: str
    role: str
    is_admin: bool
    approval_status: str


class RegistrationResponse(BaseModel):
    user_id: int
    role: str
    approval_status: str
    message: str


class AdminRequestOut(BaseModel):
    user_id: int
    full_name: str
    email: str
    phone: str
    role: str
    approval_status: str
    state: str
    district: str
    approval_note: str | None
    created_at: datetime
    advocate: AdvocateOut | None = None


class ApprovalDecision(BaseModel):
    decision: Literal["APPROVED", "REJECTED"]
    note: str | None = Field(default=None, max_length=500)


class ActivityOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    activity_id: int
    actor_user_id: int | None
    action: str
    target_type: str
    target_id: int | None
    description: str
    created_at: datetime
