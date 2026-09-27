"""Data / infrastructure failure scenarios (experiment stand switches)."""
from __future__ import annotations

import uuid

from ..iin_util import generate_iin, rng_from_seed
from .base import ScenarioContext, emit


def _ensure_client_id(ctx: ScenarioContext) -> int:
    rng = rng_from_seed(ctx.seed + 17)
    ctx.client.patch_stand(crm_mode="clean")
    ctx.client.login()
    iin = generate_iin(rng, second_weights=False)
    res = ctx.client.post(
        "/api/customers",
        json={
            "name": f"Tax Client {ctx.seed}",
            "iin": iin,
            "phone": "+77010000000",
            "email": f"tax{ctx.seed}@example.kz",
        },
    )
    if res.status_code == 201:
        return res.json()["id"]
    # duplicate / race — list and take first
    listed = ctx.client.get("/api/customers", params={"page_size": 1})
    items = listed.json().get("items") or []
    if items:
        return items[0]["id"]
    raise RuntimeError(f"cannot create client for data_infra: {res.status_code} {res.text}")


def tax_timeout(ctx: ScenarioContext, request_id: str | None = None) -> object:
    rid = request_id or uuid.uuid4().hex
    client_id = _ensure_client_id(ctx)
    ctx.client.patch_stand(crm_mode="experiment", FAULT_TAX_TIMEOUT=True)
    ctx.client.login()
    res = ctx.client.get(f"/api/customers/{client_id}/tax", request_id=rid)
    return emit(
        ctx,
        request_id=rid,
        scenario="tax_timeout",
        label="data_infra",
        http_status=res.status_code,
        detail=f"client_id={client_id}",
    )


def notes_down(ctx: ScenarioContext, request_id: str | None = None) -> object:
    rid = request_id or uuid.uuid4().hex
    client_id = _ensure_client_id(ctx)
    ctx.client.patch_stand(crm_mode="experiment", FAULT_NOTES_DOWN=True)
    ctx.client.login()
    res = ctx.client.post(
        f"/api/customers/{client_id}/notes",
        request_id=rid,
        json={"body": "Follow-up call tomorrow"},
    )
    return emit(
        ctx,
        request_id=rid,
        scenario="notes_down",
        label="data_infra",
        http_status=res.status_code,
        detail=f"client_id={client_id}",
    )


def corrupt_record(ctx: ScenarioContext, request_id: str | None = None) -> object:
    rid = request_id or uuid.uuid4().hex
    ctx.client.patch_stand(crm_mode="experiment", FAULT_CORRUPT_RECORD=True)
    ctx.client.login()
    created = None
    client_id = None
    for attempt in range(6):
        iin = generate_iin(rng_from_seed(ctx.seed + 41 + attempt), second_weights=False)
        created = ctx.client.post(
            "/api/customers",
            json={"name": f"Corrupt {ctx.seed}-{attempt}", "iin": iin, "phone": "+77012223344", "email": "c@example.kz"},
        )
        if created.status_code == 201:
            client_id = created.json()["id"]
            break
    if client_id is None:
        raise RuntimeError(f"corrupt setup failed: {created.status_code if created else 'none'}")
    res = ctx.client.get(f"/api/customers/{client_id}", request_id=rid)
    return emit(
        ctx,
        request_id=rid,
        scenario="corrupt_record",
        label="data_infra",
        http_status=res.status_code,
        detail=f"client_id={client_id}",
    )


def export_empty_field(ctx: ScenarioContext, request_id: str | None = None) -> object:
    rid = request_id or uuid.uuid4().hex
    rng = rng_from_seed(ctx.seed + 3)
    ctx.client.patch_stand(crm_mode="clean")
    ctx.client.login()
    iin = generate_iin(rng, second_weights=False)
    ctx.client.post("/api/customers", json={"name": "No Contact", "iin": iin})
    ctx.client.patch_stand(crm_mode="experiment", FAULT_EXPORT_EMPTY_FIELD=True)
    ctx.client.login()
    res = ctx.client.get("/api/customers/export", request_id=rid, params={"fmt": "csv"})
    return emit(
        ctx,
        request_id=rid,
        scenario="export_empty_field",
        label="bug",
        http_status=res.status_code,
        detail=None,
    )


def pool_exhausted(ctx: ScenarioContext, request_id: str | None = None) -> object:
    rid = request_id or uuid.uuid4().hex
    ctx.client.patch_stand(crm_mode="experiment", FAULT_POOL_EXHAUSTED=True)
    ctx.client.login()
    res = ctx.client.get("/api/customers", request_id=rid)
    return emit(ctx, request_id=rid, scenario="pool_exhausted", label="data_infra", http_status=res.status_code)


def payment_webhook_stale(ctx: ScenarioContext, request_id: str | None = None) -> object:
    import json
    import time

    rid = request_id or uuid.uuid4().hex
    ctx.client.patch_stand(crm_mode="experiment", FAULT_PAYMENT_WEBHOOK=True)
    body = json.dumps({"contract_id": 1, "amount_kzt": "1000", "external_id": f"stale-{ctx.seed}"}).encode()
    res = ctx.client.post(
        "/api/payments/webhook",
        request_id=rid,
        content=body,
        headers={"Content-Type": "application/json", "X-Signature": "x", "X-Timestamp": str(int(time.time()))},
    )
    return emit(ctx, request_id=rid, scenario="payment_webhook_stale", label="data_infra", http_status=res.status_code)


SCENARIOS = {
    "tax_timeout": tax_timeout,
    "notes_down": notes_down,
    "corrupt_record": corrupt_record,
    "pool_exhausted": pool_exhausted,
    "payment_webhook_stale": payment_webhook_stale,
}
