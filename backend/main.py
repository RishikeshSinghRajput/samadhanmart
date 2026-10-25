import hashlib
import hmac
import json
import logging
import os
import secrets
from base64 import urlsafe_b64decode, urlsafe_b64encode
from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import uuid4

import httpx
from fastapi import Depends, FastAPI, File, HTTPException, Query, UploadFile, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import func, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from .database import get_db
from .models import (
    Advocate,
    ActivityLog,
    Consultation,
    Electronic,
    ItemVerificationLog,
    Medicine,
    PrescriptionOrder,
    User,
)
from .notifications import dispatch_otp
from .schemas import (
    AdvocateOut,
    ActivityOut,
    AdminRequestOut,
    ApprovalDecision,
    ConsultationCreate,
    ConsultationOut,
    ElectronicsCreate,
    ElectronicsCreateResult,
    ElectronicsOut,
    ElectronicsVerification,
    MedicineOrderCreate,
    MedicineOrderOut,
    MedicineOut,
    LoginRequest,
    LoginResponse,
    PrescriptionUploadOut,
    RegistrationCreate,
    RegistrationResponse,
    Specialization,
)

logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))
logger = logging.getLogger("samadhanmart")
otp_hash_secret = os.getenv("OTP_HASH_SECRET")
if not otp_hash_secret or len(otp_hash_secret) < 32:
    raise RuntimeError("Set OTP_HASH_SECRET to a random value of at least 32 characters")
OTP_HASH_SECRET = otp_hash_secret.encode()
SESSION_SECRET = hmac.new(OTP_HASH_SECRET, b"samadhanmart-session-signing", hashlib.sha256).digest()
OTP_TTL_MINUTES = 10
SESSION_TTL_HOURS = 12
MAX_OTP_ATTEMPTS = 5
MAX_PRESCRIPTION_BYTES = 10 * 1024 * 1024
UPLOAD_DIR = Path(__file__).resolve().parent / "uploads" / "prescriptions"

app = FastAPI(title="SamadhanMart API", version="1.0.0")
cors_origins = [
    origin.strip()
    for origin in os.getenv(
        "CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173"
    ).split(",")
    if origin.strip()
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_origin_regex=r"^https?://(localhost|127\.0\.0\.1)(:\d+)?$",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
bearer_scheme = HTTPBearer(auto_error=False)


def hash_otp(otp: str) -> str:
    return hmac.new(OTP_HASH_SECRET, otp.encode(), hashlib.sha256).hexdigest()


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 310_000)
    return f"pbkdf2_sha256$310000${salt.hex()}${digest.hex()}"


def verify_password(password: str, password_hash: str | None) -> bool:
    if not password_hash:
        return False
    try:
        algorithm, rounds, salt_hex, digest_hex = password_hash.split("$", 3)
        if algorithm != "pbkdf2_sha256":
            return False
        digest = hashlib.pbkdf2_hmac(
            "sha256", password.encode(), bytes.fromhex(salt_hex), int(rounds)
        )
        return hmac.compare_digest(digest.hex(), digest_hex)
    except (ValueError, TypeError):
        return False


def create_access_token(user: User) -> str:
    payload = {
        "sub": user.user_id,
        "role": user.role,
        "is_admin": user.is_admin,
        "exp": int((datetime.now(timezone.utc) + timedelta(hours=SESSION_TTL_HOURS)).timestamp()),
    }
    encoded = urlsafe_b64encode(json.dumps(payload, separators=(",", ":")).encode()).rstrip(b"=")
    signature = hmac.new(SESSION_SECRET, encoded, hashlib.sha256).digest()
    return f"{encoded.decode()}.{urlsafe_b64encode(signature).rstrip(b'=').decode()}"


def add_activity(
    db: Session,
    action: str,
    target_type: str,
    description: str,
    target_id: int | None = None,
    actor_user_id: int | None = None,
) -> None:
    db.add(
        ActivityLog(
            actor_user_id=actor_user_id,
            action=action,
            target_type=target_type,
            target_id=target_id,
            description=description[:500],
        )
    )


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(status_code=401, detail="Sign in is required")
    try:
        encoded, signature = credentials.credentials.split(".", 1)
        expected = hmac.new(SESSION_SECRET, encoded.encode(), hashlib.sha256).digest()
        supplied = urlsafe_b64decode(signature + "=" * (-len(signature) % 4))
        if not hmac.compare_digest(expected, supplied):
            raise ValueError("Invalid signature")
        payload_bytes = urlsafe_b64decode(encoded + "=" * (-len(encoded) % 4))
        payload = json.loads(payload_bytes)
        if int(payload["exp"]) < int(datetime.now(timezone.utc).timestamp()):
            raise ValueError("Expired token")
        user_id = int(payload["sub"])
    except (ValueError, KeyError, TypeError, json.JSONDecodeError) as exc:
        raise HTTPException(status_code=401, detail="Session is invalid or expired") from exc
    user = db.get(User, user_id)
    if (
        not user
        or user.role != payload.get("role")
        or user.is_admin != payload.get("is_admin")
    ):
        raise HTTPException(status_code=401, detail="Session user is no longer valid")
    return user


def require_admin(user: User = Depends(get_current_user)) -> User:
    if not user.is_admin or user.role != "admin" or user.approval_status != "APPROVED":
        raise HTTPException(status_code=403, detail="Admin access is required")
    return user


@app.post("/api/auth/register", response_model=RegistrationResponse, status_code=201)
def register_account(payload: RegistrationCreate, db: Session = Depends(get_db)) -> RegistrationResponse:
    email = str(payload.email).lower()
    if db.scalar(select(User.user_id).where((User.email == email) | (User.phone == payload.phone))):
        raise HTTPException(status_code=409, detail="This email or phone number is already registered")

    user = User(
        full_name=payload.full_name,
        role=payload.role,
        phone=payload.phone,
        email=email,
        is_admin=False,
        state=payload.state,
        district=payload.district,
        password_hash=hash_password(payload.password),
        approval_status="PENDING",
    )
    db.add(user)
    try:
        db.flush()
        if payload.role == "advocate":
            db.add(
                Advocate(
                    user_id=user.user_id,
                    full_name=payload.full_name,
                    bar_council_number=payload.bar_council_number,
                    experience_years=payload.experience_years,
                    consultation_fee=payload.consultation_fee,
                    specialization=payload.specialization,
                    state=payload.state,
                    district=payload.district,
                    verified=False,
                )
            )
        add_activity(
            db,
            "REGISTRATION_REQUESTED",
            "User",
            f"{payload.role} registration requested by {payload.full_name}",
            user.user_id,
            user.user_id,
        )
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="Registration conflicts with an existing account or profile") from exc
    return RegistrationResponse(
        user_id=user.user_id,
        role=user.role,
        approval_status=user.approval_status,
        message="Your registration request was sent to the admin for approval.",
    )


@app.post("/api/auth/login", response_model=LoginResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)) -> LoginResponse:
    user = db.scalar(select(User).where(User.email == str(payload.email).lower()))
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Email or password is incorrect")
    if user.is_admin != (user.role == "admin"):
        logger.error("User %s has inconsistent admin role and IsAdmin flag", user.user_id)
        raise HTTPException(status_code=403, detail="Account role configuration is invalid")
    if user.approval_status != "APPROVED":
        raise HTTPException(
            status_code=403,
            detail=f"Your registration is {user.approval_status.lower()}. Admin approval is required before sign in.",
        )
    return LoginResponse(
        access_token=create_access_token(user),
        user_id=user.user_id,
        full_name=user.full_name,
        role=user.role,
        is_admin=user.is_admin,
        approval_status=user.approval_status,
    )


@app.get("/api/admin/requests", response_model=list[AdminRequestOut])
def list_registration_requests(
    approval_status: str | None = Query(default=None, pattern="^(PENDING|APPROVED|REJECTED)$"),
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> list[AdminRequestOut]:
    query = select(User).where(User.role.in_(("seller_electronics", "seller_medicine", "advocate")))
    if approval_status:
        query = query.where(User.approval_status == approval_status)
    users = db.scalars(query.order_by(User.created_at.desc())).all()
    profiles = {
        profile.user_id: profile
        for profile in db.scalars(select(Advocate).where(Advocate.user_id.in_(
            [user.user_id for user in users if user.role == "advocate"]
        ))).all()
    } if any(user.role == "advocate" for user in users) else {}
    return [
        AdminRequestOut(
            user_id=user.user_id,
            full_name=user.full_name,
            email=user.email,
            phone=user.phone,
            role=user.role,
            approval_status=user.approval_status,
            state=user.state,
            district=user.district,
            approval_note=user.approval_note,
            created_at=user.created_at,
            advocate=(
                AdvocateOut.model_validate(profiles[user.user_id])
                if user.user_id in profiles
                else None
            ),
        )
        for user in users
    ]


@app.post("/api/admin/requests/{user_id}/decision", response_model=AdminRequestOut)
def decide_registration(
    user_id: int,
    payload: ApprovalDecision,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> AdminRequestOut:
    user = db.get(User, user_id)
    if not user or user.role not in ("seller_electronics", "seller_medicine", "advocate"):
        raise HTTPException(status_code=404, detail="Registration request not found")
    if user.approval_status != "PENDING":
        raise HTTPException(status_code=409, detail="This registration request has already been reviewed")
    user.approval_status = payload.decision
    user.approval_note = payload.note
    user.approved_at = datetime.now() if payload.decision == "APPROVED" else None
    advocate = db.scalar(select(Advocate).where(Advocate.user_id == user.user_id))
    if advocate:
        advocate.verified = payload.decision == "APPROVED"
    add_activity(
        db,
        f"REGISTRATION_{payload.decision}",
        "User",
        f"Admin {admin.full_name} {payload.decision.lower()} {user.role} registration for {user.full_name}",
        user.user_id,
        admin.user_id,
    )
    db.commit()
    db.refresh(user)
    return AdminRequestOut(
        user_id=user.user_id,
        full_name=user.full_name,
        email=user.email,
        phone=user.phone,
        role=user.role,
        approval_status=user.approval_status,
        state=user.state,
        district=user.district,
        approval_note=user.approval_note,
        created_at=user.created_at,
        advocate=AdvocateOut.model_validate(advocate) if advocate else None,
    )


@app.get("/api/admin/activity", response_model=list[ActivityOut])
def list_admin_activity(
    limit: int = Query(default=100, ge=1, le=500),
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> list[ActivityLog]:
    return list(
        db.scalars(select(ActivityLog).order_by(ActivityLog.created_at.desc()).limit(limit)).all()
    )


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post(
    "/api/electronics/create",
    response_model=ElectronicsCreateResult,
    status_code=status.HTTP_201_CREATED,
)
async def create_electronics_listing(
    payload: ElectronicsCreate, db: Session = Depends(get_db)
) -> ElectronicsCreateResult:
    seller = db.scalar(
        select(User).where(
            (User.email == str(payload.seller_email).lower())
            | (User.phone == payload.seller_phone)
        )
    )
    if not seller:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Register as an electronics seller and get admin approval before listing.",
        )
    if seller.email.lower() != str(payload.seller_email).lower() or seller.phone != payload.seller_phone:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Seller email and phone do not match the registered account",
        )
    if seller.role != "seller_electronics":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This account is not registered as an electronics seller",
        )
    if seller.approval_status != "APPROVED":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Seller registration is {seller.approval_status.lower()}. Admin approval is required before listing.",
        )

    otps = {
        "EMAIL": f"{secrets.randbelow(1_000_000):06d}",
        "WHATSAPP": f"{secrets.randbelow(1_000_000):06d}",
    }
    expires_at = datetime.now() + timedelta(minutes=OTP_TTL_MINUTES)
    item = Electronic(
        seller_id=seller.user_id,
        title=payload.title,
        description=payload.description,
        category=payload.category,
        price=payload.price,
        serial_imei=payload.serial_imei,
        state=payload.state,
        district=payload.district,
        listing_status="PENDING_VERIFICATION",
    )
    db.add(item)
    db.flush()
    logs = [
        ItemVerificationLog(
            item_id=item.item_id,
            recipient_email=str(payload.seller_email).lower(),
            recipient_phone=payload.seller_phone,
            otp_code_hash=hash_otp(otps[channel]),
            channel=channel,
            event_type="DISPATCH",
            dispatch_status="PENDING",
            expires_at=expires_at,
        )
        for channel in ("EMAIL", "WHATSAPP")
    ]
    db.add_all(logs)
    add_activity(
        db,
        "ELECTRONICS_LISTING_CREATED",
        "Electronics",
        f"{seller.full_name} submitted listing '{item.title}' for OTP verification",
        item.item_id,
        seller.user_id,
    )
    db.commit()

    recipients = {"EMAIL": str(payload.seller_email).lower(), "WHATSAPP": payload.seller_phone}
    dispatch_statuses: dict[str, str] = {}
    for log in logs:
        try:
            log.dispatch_status = await dispatch_otp(
                log.channel, recipients[log.channel], otps[log.channel], item.item_id
            )
        except httpx.HTTPError:
            log.dispatch_status = "FAILED"
            logger.exception("OTP dispatch failed for item %s via %s", item.item_id, log.channel)
        dispatch_statuses[log.channel] = log.dispatch_status
    db.commit()

    expose_mock_otp = os.getenv("SAMADHAN_EXPOSE_MOCK_OTP", "false").lower() == "true"
    development_otps = (
        otps
        if expose_mock_otp
        and all(dispatch_statuses[channel] == "MOCKED" for channel in dispatch_statuses)
        else None
    )
    return ElectronicsCreateResult(
        item_id=item.item_id,
        listing_status=item.listing_status,
        dispatch_statuses=dispatch_statuses,
        development_otps=development_otps,
        message="Enter both six-digit codes sent separately to your email and WhatsApp.",
    )

@app.post("/api/electronics/verify")
def verify_electronics_listing(
    payload: ElectronicsVerification, db: Session = Depends(get_db)
) -> dict[str, str]:
    item = db.get(Electronic, payload.item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Listing not found")
    if item.listing_status == "VERIFIED":
        return {"status": "VERIFIED", "message": "This listing is already verified."}
    if item.listing_status != "PENDING_VERIFICATION":
        raise HTTPException(status_code=409, detail="Listing cannot be verified")

    dispatch_logs = db.scalars(
        select(ItemVerificationLog).where(
            ItemVerificationLog.item_id == payload.item_id,
            ItemVerificationLog.event_type == "DISPATCH",
        )
    ).all()
    if not dispatch_logs:
        raise HTTPException(status_code=404, detail="Verification code was not issued")
    previous_attempt = db.scalar(
        select(func.max(ItemVerificationLog.attempt_number))
        .select_from(ItemVerificationLog)
        .where(
            ItemVerificationLog.item_id == payload.item_id,
            ItemVerificationLog.event_type == "VERIFICATION_ATTEMPT",
        )
    ) or 0
    if previous_attempt >= MAX_OTP_ATTEMPTS:
        raise HTTPException(status_code=429, detail="Too many attempts. Contact support to reissue a code.")
    now = datetime.now()
    submitted_codes = {"EMAIL": payload.email_otp, "WHATSAPP": payload.whatsapp_otp}
    valid_channels = {
        log.channel: now <= log.expires_at
        and hmac.compare_digest(log.otp_code_hash, hash_otp(submitted_codes[log.channel]))
        for log in dispatch_logs
    }
    is_valid = len(valid_channels) == 2 and all(valid_channels.values())
    db.add_all(
        [
            ItemVerificationLog(
                item_id=payload.item_id,
                recipient_email=log.recipient_email,
                recipient_phone=log.recipient_phone,
                otp_code_hash=log.otp_code_hash,
                channel=log.channel,
                event_type="VERIFICATION_ATTEMPT",
                dispatch_status=log.dispatch_status,
                verification_status="VERIFIED" if valid_channels.get(log.channel, False) else "FAILED",
                attempt_number=previous_attempt + 1,
                expires_at=log.expires_at,
                attempted_at=now,
                verification_timestamp=now if is_valid else None,
            )
            for log in dispatch_logs
        ]
    )
    if is_valid:
        item.listing_status = "VERIFIED"
        for log in dispatch_logs:
            log.verification_timestamp = now
        add_activity(
            db,
            "ELECTRONICS_LISTING_VERIFIED",
            "Electronics",
            f"Electronics listing {item.item_id} passed email and WhatsApp OTP verification",
            item.item_id,
            item.seller_id,
        )
    db.commit()
    if not is_valid:
        raise HTTPException(status_code=400, detail="Invalid or expired verification code")
    return {"status": "VERIFIED", "message": "Listing verified and published."}


@app.get("/api/electronics", response_model=list[ElectronicsOut])
def list_electronics(
    category: str | None = Query(default=None, max_length=80),
    min_price: float | None = Query(default=None, ge=0),
    max_price: float | None = Query(default=None, ge=0),
    state: str | None = Query(default=None, max_length=80),
    district: str | None = Query(default=None, max_length=80),
    db: Session = Depends(get_db),
) -> list[Electronic]:
    if min_price is not None and max_price is not None and min_price > max_price:
        raise HTTPException(status_code=422, detail="min_price cannot exceed max_price")
    query = select(Electronic).where(Electronic.listing_status == "VERIFIED")
    if category:
        query = query.where(Electronic.category == category)
    if state:
        query = query.where(Electronic.state == state)
    if district:
        query = query.where(Electronic.district == district)
    if min_price is not None:
        query = query.where(Electronic.price >= min_price)
    if max_price is not None:
        query = query.where(Electronic.price <= max_price)
    return list(db.scalars(query.order_by(Electronic.created_at.desc())).all())


@app.post("/api/medicines/prescriptions", response_model=PrescriptionUploadOut)
async def upload_prescription(file: UploadFile = File(...)) -> PrescriptionUploadOut:
    allowed_types = {
        "application/pdf": (".pdf", b"%PDF-"),
        "image/jpeg": (".jpg", b"\xff\xd8\xff"),
        "image/png": (".png", b"\x89PNG\r\n\x1a\n"),
    }
    spec = allowed_types.get(file.content_type or "")
    if not spec:
        raise HTTPException(status_code=415, detail="Upload a PDF, JPEG, or PNG prescription")
    content = await file.read(MAX_PRESCRIPTION_BYTES + 1)
    if len(content) > MAX_PRESCRIPTION_BYTES:
        raise HTTPException(status_code=413, detail="Prescription must be 10 MB or smaller")
    extension, signature = spec
    if not content.startswith(signature):
        raise HTTPException(status_code=415, detail="File content does not match its declared type")
    filename = f"{uuid4().hex}{extension}"
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    (UPLOAD_DIR / filename).write_bytes(content)
    return PrescriptionUploadOut(
        prescription_path=f"prescriptions/{filename}",
        message="Prescription uploaded securely.",
    )


@app.get("/api/medicines", response_model=list[MedicineOut])
def list_medicines(
    state: str | None = Query(default=None, max_length=80),
    district: str | None = Query(default=None, max_length=80),
    search: str | None = Query(default=None, max_length=160),
    db: Session = Depends(get_db),
) -> list[Medicine]:
    query = (
        select(Medicine)
        .join(User, Medicine.seller_id == User.user_id)
        .where(Medicine.stock > 0, User.approval_status == "APPROVED")
    )
    if state:
        query = query.where(Medicine.state == state)
    if district:
        query = query.where(Medicine.district == district)
    if search:
        query = query.where(Medicine.name.ilike(f"%{search}%"))
    return list(db.scalars(query.order_by(Medicine.name)).all())


@app.post(
    "/api/medicines/order",
    response_model=MedicineOrderOut,
    status_code=status.HTTP_201_CREATED,
)
def place_medicine_order(
    payload: MedicineOrderCreate, db: Session = Depends(get_db)
) -> MedicineOrderOut:
    medicine = db.get(Medicine, payload.medicine_id)
    if not medicine:
        raise HTTPException(status_code=404, detail="Medicine not found")
    if medicine.prescription_required and not payload.prescription_path:
        raise HTTPException(status_code=422, detail="A prescription is required for this medicine")
    if payload.prescription_path:
        filename = payload.prescription_path.removeprefix("prescriptions/")
        prescription_file = (UPLOAD_DIR / filename).resolve()
        if (
            not payload.prescription_path.startswith("prescriptions/")
            or Path(filename).name != filename
            or prescription_file.parent != UPLOAD_DIR.resolve()
            or not prescription_file.is_file()
        ):
            raise HTTPException(status_code=422, detail="Uploaded prescription could not be found")
    result = db.execute(
        update(Medicine)
        .where(Medicine.medicine_id == payload.medicine_id, Medicine.stock >= payload.quantity)
        .values(stock=Medicine.stock - payload.quantity)
    )
    if result.rowcount != 1:
        db.rollback()
        raise HTTPException(status_code=409, detail="Insufficient medicine stock")
    order = PrescriptionOrder(
        medicine_id=payload.medicine_id,
        customer_name=payload.customer_name,
        customer_phone=payload.customer_phone,
        customer_email=str(payload.customer_email).lower(),
        quantity=payload.quantity,
        prescription_path=payload.prescription_path,
        is_chronic_refill=payload.is_chronic_refill,
        refill_interval_days=payload.refill_interval_days,
        next_refill_at=(
            datetime.now() + timedelta(days=payload.refill_interval_days)
            if payload.is_chronic_refill and payload.refill_interval_days
            else None
        ),
        order_status="PLACED",
    )
    db.add(order)
    db.flush()
    buyer = db.scalar(select(User).where(User.email == str(payload.customer_email).lower()))
    add_activity(
        db,
        "MEDICINE_ORDER_PLACED",
        "PrescriptionOrder",
        f"Medicine order for {medicine.name} placed by {payload.customer_name}",
        order.order_id,
        buyer.user_id if buyer else None,
    )
    db.commit()
    db.refresh(order)
    return MedicineOrderOut(
        order_id=order.order_id,
        order_status=order.order_status,
        message="Order placed. A local chemist will confirm availability.",
    )


@app.get("/api/advocates", response_model=list[AdvocateOut])
def list_advocates(
    specialization: Specialization | None = None,
    state: str | None = Query(default=None, max_length=80),
    district: str | None = Query(default=None, max_length=80),
    db: Session = Depends(get_db),
) -> list[Advocate]:
    query = select(Advocate).where(Advocate.verified == True)  # noqa: E712
    if specialization:
        query = query.where(Advocate.specialization == specialization)
    if state:
        query = query.where(Advocate.state == state)
    if district:
        query = query.where(Advocate.district == district)
    return list(db.scalars(query.order_by(Advocate.full_name)).all())


@app.post(
    "/api/advocates/book",
    response_model=ConsultationOut,
    status_code=status.HTTP_201_CREATED,
)
def book_consultation(
    payload: ConsultationCreate, db: Session = Depends(get_db)
) -> ConsultationOut:
    advocate = db.get(Advocate, payload.advocate_id)
    if not advocate or not advocate.verified:
        raise HTTPException(status_code=404, detail="Verified advocate not found")
    booking = Consultation(
        advocate_id=payload.advocate_id,
        client_name=payload.client_name,
        client_email=str(payload.client_email).lower(),
        client_phone=payload.client_phone,
        slot_start=payload.slot_start.astimezone(timezone.utc).replace(tzinfo=None),
        slot_end=(payload.slot_start.astimezone(timezone.utc) + timedelta(minutes=30)).replace(tzinfo=None),
        booking_status="BOOKED",
    )
    db.add(booking)
    db.flush()
    client = db.scalar(select(User).where(User.email == str(payload.client_email).lower()))
    add_activity(
        db,
        "CONSULTATION_BOOKED",
        "Consultation",
        f"Consultation booked with {advocate.full_name} by {payload.client_name}",
        booking.consultation_id,
        client.user_id if client else None,
    )
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="That consultation slot is already booked") from exc
    db.refresh(booking)
    return ConsultationOut(
        consultation_id=booking.consultation_id,
        advocate_id=booking.advocate_id,
        slot_start=booking.slot_start.replace(tzinfo=timezone.utc),
        slot_end=booking.slot_end.replace(tzinfo=timezone.utc),
        booking_status=booking.booking_status,
    )
