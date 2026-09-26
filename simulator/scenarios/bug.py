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
    ctx.client.login()  # manager session for create
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


SCENARIOS = {
    "valid_iin_rejected": valid_iin_rejected,
    "name_search_raw_sql": name_search_raw_sql,
    "export_empty_field": export_empty_field,
}
