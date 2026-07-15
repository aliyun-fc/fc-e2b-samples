"""REST and SSE API for browser runs."""

from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncIterator

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import Response, StreamingResponse
from pydantic import BaseModel, Field

from src.browser.service import BrowserService
from src.core.runs import Run

router = APIRouter(prefix="/api/runs", tags=["runs"])


class CreateRun(BaseModel):
    task: str = Field(min_length=8, max_length=4_000, examples=["打开 https://example.com 并截图"])


def get_run(request: Request, run_id: str) -> Run:
    run = request.app.state.runs.get(run_id)
    if not run:
        raise HTTPException(404, "Run not found")
    return run


@router.post("", status_code=201)
async def create_run(payload: CreateRun, request: Request):
    run = request.app.state.runs.create(payload.task)
    await request.app.state.runs.emit(run, "run.queued", task=payload.task)
    service: BrowserService = request.app.state.browser_service
    asyncio.create_task(service.execute(run), name=f"browser-run-{run.run_id}")
    return {**run.public(), "events_url": f"/api/runs/{run.run_id}/events"}


@router.get("/{run_id}")
async def read_run(run_id: str, request: Request):
    return get_run(request, run_id).public()


@router.get("/{run_id}/events")
async def events(run_id: str, request: Request):
    run = get_run(request, run_id)

    async def stream() -> AsyncIterator[str]:
        index = 0
        while True:
            async with run.condition:
                if index >= len(run.events):
                    try:
                        await asyncio.wait_for(run.condition.wait(), timeout=15)
                    except TimeoutError:
                        yield ": keepalive\n\n"
                        continue
                pending = run.events[index:]
                index = len(run.events)
            for event in pending:
                yield f"event: {event['kind']}\ndata: {json.dumps(event)}\n\n"
            if run.status in {"completed", "failed", "stopped"} and index == len(run.events):
                return

    return StreamingResponse(stream(), media_type="text/event-stream", headers={"Cache-Control": "no-cache"})


@router.get("/{run_id}/screenshot")
async def screenshot(run_id: str, request: Request):
    run = get_run(request, run_id)
    if not run.screenshot:
        raise HTTPException(404, "Screenshot not available yet")
    return Response(run.screenshot, media_type="image/png")


@router.delete("/{run_id}", status_code=204)
async def stop_run(run_id: str, request: Request):
    run = get_run(request, run_id)
    await request.app.state.runs.destroy(run)
    return Response(status_code=204)
