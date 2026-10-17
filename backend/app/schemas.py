from datetime import date, datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, EmailStr, Field, create_model

from . import faults
from .models import ContractStatus, InstallmentStatus, PaymentStatus, UserRole
from .vulns import all_keys as vuln_keys


class LoginIn(BaseModel):
    username: str = Field(min_length=1, max_length=64)
    password: str = Field(min_length=1, max_length=128)


class UserOut(BaseModel):
    id: int
    username: str
    email: EmailStr
    role: UserRole
    is_active: bool
    max_discount_pct: int = 10
    webhook_url: str | None = None

    model_config = {"from_attributes": True}


class UserPatch(BaseModel):
    """Profile patch."""

    email: EmailStr | None = None
    phone: str | None = None
    role: UserRole | None = None
    webhook_url: str | None = Field(default=None, max_length=512)


class WebhookTestOut(BaseModel):
    status_code: int
    preview: str | None = None


class AuthOut(BaseModel):
    user: UserOut


class ClientCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    iin: str = Field(min_length=12, max_length=12)
    phone: str | None = Field(default=None, max_length=32)
    email: EmailStr | None = None
    birth_date: date | None = None


class ClientUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    phone: str | None = Field(default=None, max_length=32)
    email: EmailStr | None = None
    birth_date: date | None = None


class ClientOut(BaseModel):
    id: int
    name: str
    iin: str
    phone: str | None
    email: str | None
    birth_date: date | None = None
    owner_id: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ClientListOut(BaseModel):
    items: list[ClientOut]
    total: int
    page: int
    page_size: int


class NoteCreate(BaseModel):
    body: str = Field(min_length=1, max_length=4000)


class NoteOut(BaseModel):
    id: int
    client_id: int
    author_id: int
    body: str
    created_at: datetime

    model_config = {"from_attributes": True}


class CourseOut(BaseModel):
    id: int
    code: str
    title: str
    description: str | None
    price_kzt: Decimal
    is_active: bool

    model_config = {"from_attributes": True}


class PackageOut(BaseModel):
    id: int
    code: str
    title: str
    price_kzt: Decimal
    is_active: bool
    course_ids: list[int] = []

    model_config = {"from_attributes": True}


class EnrollIn(BaseModel):
    client_id: int
    course_id: int | None = None
    package_id: int | None = None
    discount_pct: int = Field(default=0, ge=0, le=100)
    price_kzt: Decimal | None = None


class EnrollmentOut(BaseModel):
    id: int
    client_id: int
    course_id: int
    contract_id: int | None
    package_id: int | None
    price_kzt: Decimal
    discount_pct: int
    created_at: datetime

    model_config = {"from_attributes": True}


class ContractCreate(BaseModel):
    client_id: int
    number: str = Field(min_length=3, max_length=64)
    enrollment_ids: list[int]
    discount_pct: int = Field(default=0, ge=0, le=100)


class ContractOut(BaseModel):
    id: int
    number: str
    client_id: int
    status: ContractStatus
    total_kzt: Decimal
    discount_pct: int
    created_at: datetime
    signed_at: datetime | None

    model_config = {"from_attributes": True}


class InstallmentPlanIn(BaseModel):
    months: Literal[3, 6, 12]
    first_due: date | None = None


class InstallmentOut(BaseModel):
    id: int
    contract_id: int
    seq: int
    due_date: date
    amount_kzt: Decimal
    status: InstallmentStatus

    model_config = {"from_attributes": True}


class PaymentOut(BaseModel):
    id: int
    contract_id: int
    amount_kzt: Decimal
    status: PaymentStatus
    card_last4: str | None
    external_id: str | None
    paid_at: datetime | None

    model_config = {"from_attributes": True}


class PaymentWebhookIn(BaseModel):
    contract_id: int
    amount_kzt: Decimal
    external_id: str
    card_token: str | None = None
    card_last4: str | None = Field(default=None, max_length=4)


_stand_fields: dict = {"crm_mode": (Literal["clean", "experiment", "vuln"] | None, None)}
for _key in faults.FAULT_KEYS:
    _stand_fields[_key] = (bool | None, None)
for _key in vuln_keys():
    _stand_fields[_key] = (bool | None, None)

StandPatch = create_model("StandPatch", **_stand_fields)


class HealthOut(BaseModel):
    status: str
    version: str
    crm_mode: str
    company: str = "Bilim Academy"
