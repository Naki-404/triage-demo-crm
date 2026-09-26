"""JSONL run journal for simulator → dataset collect."""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, TextIO


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


@dataclass
class JournalEvent:
    request_id: str
    scenario: str
    label: str
    set: str
    seed: int
    http_status: int | None
    detail: str | None
    time: str
    target: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class Journal:
    def __init__(self, path: Path | None):
        self.path = path
        self._fh: TextIO | None = None
        self.events: list[JournalEvent] = []
        if path is not None:
            path.parent.mkdir(parents=True, exist_ok=True)
            self._fh = path.open("a", encoding="utf-8")

    def write(self, event: JournalEvent) -> None:
        self.events.append(event)
        if self._fh is not None:
            self._fh.write(json.dumps(event.to_dict(), ensure_ascii=False) + "\n")
            self._fh.flush()

    def close(self) -> None:
        if self._fh is not None:
            self._fh.close()
            self._fh = None
