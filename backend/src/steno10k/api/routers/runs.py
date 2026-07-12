from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from steno10k.api.deps import get_run_queue
from steno10k.api.dto import CancelResult, Envelope, RunDTO
from steno10k.api.envelope import ApiError, ok
from steno10k.api.runq import RunQueue, RunStatus
from steno10k.api.sse import sse_stream
from steno10k.contracts.events import Event

router = APIRouter(prefix="/api/v1/runs", tags=["runs"])


class EnqueueRunRequest(BaseModel):
    project: str
    set: str
    stage_overrides: dict[str, bool] | None = None
    force: bool = False


@router.post("", response_model=Envelope[RunDTO])
def create_run(
    body: EnqueueRunRequest, run_queue: Annotated[RunQueue, Depends(get_run_queue)]
) -> dict[str, Any]:
    # `force` is threaded through; `stage_overrides` is accepted on the request
    # for forward-compatibility but intentionally NOT applied per-run yet — each
    # run uses config-level `stages.enabled`. See docs/adr/0002-deferred-run-options.md.
    run = run_queue.enqueue(project=body.project, set_=body.set, force=body.force)
    return ok(RunDTO.from_domain(run).model_dump())


@router.get("", response_model=Envelope[list[RunDTO]])
def list_runs(run_queue: Annotated[RunQueue, Depends(get_run_queue)]) -> dict[str, Any]:
    return ok([RunDTO.from_domain(r).model_dump() for r in run_queue.list()])


@router.get("/{run_id}", response_model=Envelope[RunDTO])
def get_run(run_id: str, run_queue: Annotated[RunQueue, Depends(get_run_queue)]) -> dict[str, Any]:
    try:
        run = run_queue.get(run_id)
    except KeyError as exc:
        raise ApiError(404, "run_not_found", f"run not found: {run_id}") from exc
    return ok(RunDTO.from_domain(run).model_dump())


@router.delete("/{run_id}", response_model=Envelope[CancelResult])
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

    # Backstop against the lock-ordering race documented in `sse_stream`'s
    # docstring: even if the `run_completed` event is never observed by this
    # bridge, the run's own recorded status is the source of truth for
    # whether it has finished, and lets the stream close deterministically.
    def _is_terminal() -> bool:
        return run_queue.get(run_id).status in {
            RunStatus.COMPLETED,
            RunStatus.FAILED,
            RunStatus.CANCELLED,
        }

    return StreamingResponse(
        sse_stream(bus, history=_history, is_terminal=_is_terminal),
        media_type="text/event-stream",
    )
