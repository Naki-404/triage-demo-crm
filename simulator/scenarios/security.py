"""Security scenarios (brute force, enumeration, SQLi probe)."""
from __future__ import annotations

import uuid

from ..iin_util import generate_iin, rng_from_seed
from .base import ScenarioContext, emit


def brute_force(ctx: ScenarioContext, request_id: str | None = None) -> object:
    rid = request_id or uuid.uuid4().hex
    last = None
    for i in range(8):
        last = ctx.client.post(
            "/api/auth/login",
            request_id=f"{rid}-{i}",
            json={"username": "viewer", "password": f"guess-{i}"},
        )
    assert last is not None
    return emit(
        ctx,
        request_id=rid,
        scenario="brute_force",
        label="security",
        http_status=last.status_code,
        detail="attempts=8",
    )


def iin_enumeration(ctx: ScenarioContext, request_id: str | None = None) -> object:
    rid = request_id or uuid.uuid4().hex
    rng = rng_from_seed(ctx.seed)
    ctx.client.login()
    last = None
    for i in range(15):
        iin = generate_iin(rng)
        last = ctx.client.get(
            "/api/customers/search",
            request_id=f"{rid}-{i}",
            params={"iin": iin},
        )
    assert last is not None
    return emit(
        ctx,
        request_id=rid,
        scenario="iin_enumeration",
        label="security",
        http_status=last.status_code,
        detail="lookups=15",
    )


def sql_injection(ctx: ScenarioContext, request_id: str | None = None) -> object:
    """Probe search with injection string; with FAULT_NAME_SEARCH_RAW_SQL this becomes a bug path."""
    rid = request_id or uuid.uuid4().hex
    ctx.client.patch_stand(crm_mode="experiment", FAULT_NAME_SEARCH_RAW_SQL=True)
    ctx.client.login()
    payload = "x' OR '1'='1' --"
    res = ctx.client.get("/api/customers/search", request_id=rid, params={"name": payload})
    return emit(
        ctx,
        request_id=rid,
        scenario="sql_injection",
        label="security",
        http_status=res.status_code,
        detail=payload,
    )


SCENARIOS = {
    "brute_force": brute_force,
    "iin_enumeration": iin_enumeration,
    "sql_injection": sql_injection,
}
