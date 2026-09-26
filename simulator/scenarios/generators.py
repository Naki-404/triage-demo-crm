"""Invariance / contrast generators for robustness sets."""
from __future__ import annotations

import uuid

from .base import ScenarioContext, emit
from .bug import valid_iin_rejected
from .expected import wrong_check_digit, wrong_password


def invariance_wrong_password(ctx: ScenarioContext, request_id: str | None = None) -> list:
    """Three isomorphic wrong-password events (same label, varied seeds)."""
    events = []
    base = request_id or uuid.uuid4().hex
    for i in range(3):
        sub = ScenarioContext(
            client=ctx.client,
            journal=ctx.journal,
            seed=ctx.seed + i,
            set_name="invariance",
            target=ctx.target,
        )
        events.append(wrong_password(sub, request_id=f"{base}-inv-{i}"))
    return events


def contrast_iin_pair(ctx: ScenarioContext, request_id: str | None = None) -> list:
    """Same surface form family, different labels: wrong digit (expected) vs W2 reject (bug)."""
    base = request_id or uuid.uuid4().hex
    a = ScenarioContext(client=ctx.client, journal=ctx.journal, seed=ctx.seed, set_name="contrast", target=ctx.target)
    b = ScenarioContext(
        client=ctx.client, journal=ctx.journal, seed=ctx.seed + 1, set_name="contrast", target=ctx.target
    )
    return [
        wrong_check_digit(a, request_id=f"{base}-a"),
        valid_iin_rejected(b, request_id=f"{base}-b"),
    ]


def invariance_list_noise(ctx: ScenarioContext, request_id: str | None = None) -> list:
    """Benign list calls with different page sizes — same expected success class."""
    rid = request_id or uuid.uuid4().hex
    ctx.client.login()
    events = []
    for i, size in enumerate((5, 10, 20)):
        r = ctx.client.get("/api/customers", request_id=f"{rid}-{i}", params={"page_size": size})
        events.append(
            emit(
                ctx,
                request_id=f"{rid}-{i}",
                scenario="invariance_list_noise",
                label="expected",
                http_status=r.status_code,
                detail=f"page_size={size}",
            )
        )
    return events


GENERATORS = {
    "invariance_wrong_password": invariance_wrong_password,
    "contrast_iin_pair": contrast_iin_pair,
    "invariance_list_noise": invariance_list_noise,
}
