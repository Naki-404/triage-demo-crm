"""Background manager traffic mixed with scenario runs."""
from __future__ import annotations

import uuid

from ..iin_util import generate_iin, rng_from_seed
from .base import ScenarioContext, emit


def background_manager(ctx: ScenarioContext, request_id: str | None = None) -> object:
    rid = request_id or uuid.uuid4().hex
    ctx.client.patch_stand(crm_mode="clean")
    ctx.client.login()
    # list
    ctx.client.get("/api/customers", request_id=f"{rid}-list", params={"page_size": 10})
    # occasional create with valid IIN
    res = None
    for attempt in range(8):
        iin = generate_iin(rng_from_seed(ctx.seed + attempt * 17), second_weights=False)
        res = ctx.client.post(
            "/api/customers",
            request_id=rid,
            json={
                "name": f"Manager Lead {ctx.seed % 1000}-{attempt}",
                "iin": iin,
                "phone": f"+7701{(ctx.seed + attempt) % 10000000:07d}",
                "email": f"mgr{ctx.seed}-{attempt}@example.kz",
            },
        )
        if res.status_code != 409:
            break
    assert res is not None
    return emit(
        ctx,
        request_id=rid,
        scenario="background_manager",
        label="expected",
        http_status=res.status_code,
        detail="traffic",
    )


SCENARIOS = {
    "background_manager": background_manager,
}
