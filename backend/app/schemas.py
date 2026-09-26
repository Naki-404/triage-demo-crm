from datetime import datetime
from typing import Literal

from pydantic import BaseModel, EmailStr, Field

from .models import UserRole


class LoginIn(BaseModel):
    username: str = Field(min_length=1, max_length=64)
    password: str = Field(min_length=1, max_length=128)


class UserOut(BaseModel):
    id: int
    username: str
    email: EmailStr
    role: UserRole
    is_active: bool

    model_config = {"from_attributes": True}


class AuthOut(BaseModel):
    user: UserOut


class ClientCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    iin: str = Field(min_length=12, max_length=12)
    phone: str | None = Field(default=None, max_length=32)
    email: EmailStr | None = None


class ClientUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    phone: str | None = Field(default=None, max_length=32)
    email: EmailStr | None = None


class ClientOut(BaseModel):
    id: int
    name: str
    iin: str
    phone: str | None
    email: str | None
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


class StandPatch(BaseModel):
    crm_mode: Literal["clean", "experiment"] | None = None
    FAULT_IIN_SECOND_WEIGHTS: bool | None = None
    FAULT_NAME_SEARCH_RAW_SQL: bool | None = None
    FAULT_EXPORT_EMPTY_FIELD: bool | None = None
    FAULT_CORRUPT_RECORD: bool | None = None
    FAULT_TAX_TIMEOUT: bool | None = None
    FAULT_NOTES_DOWN: bool | None = None
    FAULT_POOL_EXHAUSTED: bool | None = None


class HealthOut(BaseModel):
    status: str
    version: str
    crm_mode: str
