"""Demo CRM used to generate realistic errors for the triage platform.

    SENTRY_DSN=http://<public_key>@localhost:8000/<source_id> uvicorn demo_app.main:app --port 9000

The DSN points at the platform itself (Sentry-compatible intake), so no sentry.io account is needed.
It can equally point at a real Sentry project that forwards events to the platform via webhooks.
"""
import os

import httpx
import sentry_sdk
from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel

from validators import InvalidIINError, validate_iin

sentry_sdk.init(
    dsn=os.environ.get("SENTRY_DSN"),
    environment=os.environ.get("DEMO_ENVIRONMENT", "demo"),
    release="crm@1.4.2",
    server_name="crm",
    send_default_pii=True,  # realistic: many apps send request bodies with personal data
    include_local_variables=True,
    max_request_body_size="always",
    traces_sample_rate=0,
)
sentry_sdk.set_tag("service", "crm")

TAX_SERVICE_URL = os.environ.get("TAX_SERVICE_URL", "http://127.0.0.1:9/api/tax-status")
USERS = {"manager": "Manager-2026"}

app = FastAPI(title="Demo CRM")


class CustomerIn(BaseModel):
    name: str
    iin: str
    phone: str | None = None
    email: str | None = None


class LoginIn(BaseModel):
    username: str
    password: str


class AuthenticationFailed(Exception):
    pass


class CustomerNotFound(Exception):
    pass


class DatabaseError(Exception):
    pass


class NotesServiceError(Exception):
    pass


class NoteIn(BaseModel):
    note: str


@app.middleware("http")
async def tag_request(request: Request, call_next):
    sentry_sdk.set_tag("service", "crm")
    return await call_next(request)


@app.post("/customers", status_code=201)
def create_customer(payload: CustomerIn):
    try:
        validate_iin(payload.iin)
    except InvalidIINError as exc:
        sentry_sdk.set_tag("http.status_code", "422")
        sentry_sdk.capture_exception(exc)
        raise HTTPException(status_code=422, detail="Некорректный ИИН")
    return {"status": "created", "name": payload.name}


@app.post("/login")
def login(payload: LoginIn):
    try:
        if USERS.get(payload.username) != payload.password:
            raise AuthenticationFailed(f"Invalid credentials for user {payload.username}")
    except AuthenticationFailed as exc:
        sentry_sdk.set_tag("http.status_code", "401")
        sentry_sdk.capture_exception(exc)
        raise HTTPException(status_code=401, detail="Invalid credentials")
    return {"status": "ok"}


@app.get("/customers/search")
def search_customers(name: str):
    # DELIBERATE VULNERABILITY for the demo: the name goes into SQL unescaped.
    query = f"SELECT * FROM customers WHERE name = '{name}'"
    if "'" in name:
        raise DatabaseError(f"syntax error in query: {query[:200]}")
    return {"items": []}


@app.get("/customers/by-iin/{iin}")
def customer_by_iin(iin: str):
    try:
        raise CustomerNotFound(f"No customer with IIN {iin}")
    except CustomerNotFound as exc:
        sentry_sdk.set_tag("http.status_code", "404")
        sentry_sdk.capture_exception(exc)
        raise HTTPException(status_code=404, detail="Customer not found")


@app.post("/customers/{customer_id}/notes")
def add_note(customer_id: int, payload: NoteIn):
    # The notes service is down in the demo, so every note ends up in the error log with its text.
    raise NotesServiceError(f"Could not save note for customer {customer_id}")


@app.get("/customers/{customer_id}/tax-status")
def tax_status(customer_id: int):
    # The external tax service is unreachable in the demo: httpx.ConnectError reaches Sentry as a 500.
    response = httpx.get(TAX_SERVICE_URL, params={"customer": customer_id}, timeout=1.0)
    return response.json()


@app.get("/health")
def health():
    return {"status": "ok"}
