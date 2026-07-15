"""In-memory run registry and SSE event fan-out."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4


def now() -> str:
    return datetime.now(UTC).isoformat()


@dataclass
class Run:
    task: str
    run_id: str = field(default_factory=lambda: uuid4().hex)
    status: str = "queued"
    sandbox_id: str | None = None
    result: dict[str, Any] | None = None
    error: str | None = None
    screenshot: bytes | None = None
    created_at: str = field(default_factory=now)
    updated_at: str = field(default_factory=now)
    events: list[dict[str, Any]] = field(default_factory=list)
    condition: asyncio.Condition = field(default_factory=asyncio.Condition, repr=False)
    sandbox: Any = field(default=None, repr=False)

    def public(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "task": self.task,
            "status": self.status,
            "sandbox_id": self.sandbox_id,
            "result": self.result,
            "error": self.error,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


class RunStore:
    def __init__(self) -> None:
        self.runs: dict[str, Run] = {}

    def create(self, task: str) -> Run:
        run = Run(task=task)
        self.runs[run.run_id] = run
        return run

    def get(self, run_id: str) -> Run | None:
        return self.runs.get(run_id)

    async def emit(self, run: Run, kind: str, **data: Any) -> None:
        event = {"kind": kind, "at": now(), **data}
        async with run.condition:
            run.events.append(event)
            run.updated_at = event["at"]
            run.condition.notify_all()

    async def close_all(self) -> None:
        await asyncio.gather(*(self.destroy(run) for run in list(self.runs.values())))

    async def destroy(self, run: Run) -> None:
        sandbox, run.sandbox = run.sandbox, None
        if sandbox is not None:
            await asyncio.to_thread(sandbox.kill)
        if run.status not in {"completed", "failed"}:
            run.status = "stopped"
        await self.emit(run, "run.stopped", sandbox_id=run.sandbox_id)
