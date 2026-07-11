from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from steno10k.api.deps import get_run_queue
from steno10k.api.dto import RunDTO
from steno10k.api.envelope import ApiError, ok
from steno10k.api.runq import RunQueue
from steno10k.api.sse import sse_stream
from steno10k.contracts.events import Event

router = APIRouter(prefix="/api/v1/runs", tags=["runs"])


class EnqueueRunRequest(BaseModel):
    project: str
    set: str
    stage_overrides: dict[str, bool] | None = None
    force: bool = False


@router.post("")
def create_run(
    body: EnqueueRunRequest, run_queue: Annotated[RunQueue, Depends(get_run_queue)]
) -> dict[str, Any]:
    # `stage_overrides`/`force` are accepted per the API contract but not yet
    # threaded through to `RunQueue.enqueue` (Task 9, frozen): F2 ships with an
    # empty `StageRegistry`, so there are no concrete stages for per-stage
    # overrides to apply to. Wiring belongs with the fan-out that adds stages.
    run = run_queue.enqueue(project=body.project, set_=body.set)
    return ok(RunDTO.from_domain(run).model_dump())


@router.get("")
def list_runs(run_queue: Annotated[RunQueue, Depends(get_run_queue)]) -> dict[str, Any]:
    return ok([RunDTO.from_domain(r).model_dump() for r in run_queue.list()])


@router.get("/{run_id}")
def get_run(run_id: str, run_queue: Annotated[RunQueue, Depends(get_run_queue)]) -> dict[str, Any]:
    try:
        run = run_queue.get(run_id)
    except KeyError as exc:
        raise ApiError(404, "run_not_found", f"run not found: {run_id}") from exc
    return ok(RunDTO.from_domain(run).model_dump())


@router.delete("/{run_id}")
def cancel_run(
    run_id: str, run_queue: Annotated[RunQueue, Depends(get_run_queue)]
) -> dict[str, Any]:
    try:
        run_queue.get(run_id)
    except KeyError as exc:
        raise ApiError(404, "run_not_found", f"run not found: {run_id}") from exc
    cancelled = run_queue.cancel(run_id)
    return ok({"cancelled": cancelled})


@router.get("/{run_id}/events")
def stream_events(
    run_id: str, run_queue: Annotated[RunQueue, Depends(get_run_queue)]
) -> StreamingResponse:
    bus = run_queue.get_bus(run_id)
    if bus is None:
        raise ApiError(404, "run_not_found", f"run not found: {run_id}")

    # `history` replays events emitted before this client attached -- see
    # `sse_stream`'s docstring: without it, a run that finishes before the
    # client opens the stream (routine for the empty F2 `StageRegistry`)
    # would leave the generator polling forever for a `run_completed` that
    # already happened.
    def _history() -> list[Event]:
        return run_queue.get(run_id).events

    return StreamingResponse(sse_stream(bus, history=_history), media_type="text/event-stream")
