"""Expected / user-error scenarios (valid CRM behaviour)."""
from __future__ import annotations

import uuid

from ..iin_util import generate_iin, rng_from_seed, with_wrong_check_digit
from .base import ScenarioContext, emit


def wrong_check_digit(ctx: ScenarioContext, request_id: str | None = None) -> object:
    rid = request_id or uuid.uuid4().hex
    rng = rng_from_seed(ctx.seed)
    ctx.client.patch_stand(crm_mode="clean", FAULT_IIN_SECOND_WEIGHTS=False)
    ctx.client.login()
    iin = with_wrong_check_digit(generate_iin(rng, second_weights=False))
    res = ctx.client.post(
        "/api/customers",
        request_id=rid,
        json={"name": "Ержан Нурланов", "iin": iin, "email": "erzhan@example.kz"},
    )
    return emit(
        ctx,
        request_id=rid,
        scenario="wrong_check_digit",
        label="expected",
        http_status=res.status_code,
        detail=f"iin={iin}",
    )


def wrong_password(ctx: ScenarioContext, request_id: str | None = None) -> object:
    rid = request_id or uuid.uuid4().hex
    res = ctx.client.post(
        "/api/auth/login",
        request_id=rid,
        json={"username": "nobody", "password": "wrong-password"},
    )
    return emit(
        ctx,
        request_id=rid,
        scenario="wrong_password",
        label="expected",
        http_status=res.status_code,
        detail=None,
    )


SCENARIOS = {
    "wrong_check_digit": wrong_check_digit,
    "wrong_password": wrong_password,
}
