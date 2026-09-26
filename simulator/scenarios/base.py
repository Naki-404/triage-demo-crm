from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from ..client import CrmClient
from ..journal import Journal, JournalEvent, utc_now


@dataclass
class ScenarioContext:
    client: CrmClient
    journal: Journal
    seed: int
    set_name: str
    target: str


ScenarioFn = Callable[[ScenarioContext, str], JournalEvent]


def emit(
    ctx: ScenarioContext,
    *,
    request_id: str,
    scenario: str,
    label: str,
    http_status: int | None,
    detail: str | None = None,
) -> JournalEvent:
    event = JournalEvent(
        request_id=request_id,
        scenario=scenario,
        label=label,
        set=ctx.set_name,
        seed=ctx.seed,
        http_status=http_status,
        detail=detail,
        time=utc_now(),
        target=ctx.target,
    )
    ctx.journal.write(event)
    return event
