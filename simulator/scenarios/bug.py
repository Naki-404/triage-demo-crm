"""Bug-class scenarios (need CRM_MODE=experiment + stand switches)."""
from __future__ import annotations

import uuid

from ..iin_util import generate_iin, rng_from_seed
from .base import ScenarioContext, emit
from .data_infra import export_empty_field


def valid_iin_rejected(ctx: ScenarioContext, request_id: str | None = None) -> object:
    """Valid IIN that needs W2 — rejected when FAULT_IIN_SECOND_WEIGHTS is on."""
    rid = request_id or uuid.uuid4().hex
    rng = rng_from_seed(ctx.seed)
    ctx.client.patch_stand(crm_mode="experiment", FAULT_IIN_SECOND_WEIGHTS=True)
    ctx.client.login()
    iin = generate_iin(rng, second_weights=True)
    res = ctx.client.post(
        "/api/customers",
        request_id=rid,
        json={"name": "Айгерим Сапарова", "iin": iin, "phone": "+77011234567"},
    )
    return emit(
        ctx,
        request_id=rid,
        scenario="valid_iin_rejected",
        label="bug",
        http_status=res.status_code,
        detail=f"iin={iin}",
    )


def name_search_raw_sql(ctx: ScenarioContext, request_id: str | None = None) -> object:
    rid = request_id or uuid.uuid4().hex
    ctx.client.patch_stand(crm_mode="experiment", FAULT_NAME_SEARCH_RAW_SQL=True)
    ctx.client.login()
    payload = "O'Brien"
    res = ctx.client.get("/api/customers/search", request_id=rid, params={"name": payload})
    return emit(
        ctx,
        request_id=rid,
        scenario="name_search_raw_sql",
        label="bug",
        http_status=res.status_code,
        detail=payload,
    )


def installment_rounding(ctx: ScenarioContext, request_id: str | None = None) -> object:
    rid = request_id or uuid.uuid4().hex
    ctx.client.patch_stand(crm_mode="experiment", FAULT_INSTALLMENT_ROUNDING=True)
    ctx.client.login(username="admin", password="Admin-2026!")
    customers = ctx.client.get("/api/customers").json()["items"]
    courses = ctx.client.get("/api/courses").json()
    enr = ctx.client.post(
        "/api/enrollments",
        json={"client_id": customers[0]["id"], "course_id": courses[0]["id"], "discount_pct": 0},
    ).json()
    contract = ctx.client.post(
        "/api/contracts",
        json={
            "client_id": customers[0]["id"],
            "number": f"BA-BUG-{ctx.seed}",
            "enrollment_ids": [enr[0]["id"]],
            "discount_pct": 0,
        },
    ).json()
    res = ctx.client.post(f"/api/contracts/{contract['id']}/installments", request_id=rid, json={"months": 3})
    return emit(ctx, request_id=rid, scenario="installment_rounding", label="bug", http_status=res.status_code)


def export_no_contract(ctx: ScenarioContext, request_id: str | None = None) -> object:
    rid = request_id or uuid.uuid4().hex
    ctx.client.patch_stand(crm_mode="experiment", FAULT_EXPORT_NO_CONTRACT=True)
    ctx.client.login()
    res = ctx.client.get("/api/customers/export", request_id=rid, params={"fmt": "csv"})
    return emit(ctx, request_id=rid, scenario="export_no_contract", label="bug", http_status=res.status_code)


def discount_stack(ctx: ScenarioContext, request_id: str | None = None) -> object:
    rid = request_id or uuid.uuid4().hex
    ctx.client.patch_stand(crm_mode="experiment", FAULT_DISCOUNT_STACK=True)
    ctx.client.login(username="admin", password="Admin-2026!")
    customers = ctx.client.get("/api/customers").json()["items"]
    packages = ctx.client.get("/api/packages").json()
    res = ctx.client.post(
        "/api/enrollments",
        request_id=rid,
        json={"client_id": customers[0]["id"], "package_id": packages[0]["id"], "discount_pct": 10},
    )
    return emit(ctx, request_id=rid, scenario="discount_stack", label="bug", http_status=res.status_code)


SCENARIOS = {
    "valid_iin_rejected": valid_iin_rejected,
    "name_search_raw_sql": name_search_raw_sql,
    "export_empty_field": export_empty_field,
    "installment_rounding": installment_rounding,
    "export_no_contract": export_no_contract,
    "discount_stack": discount_stack,
}
