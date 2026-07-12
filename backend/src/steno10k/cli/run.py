from __future__ import annotations

import argparse
import sys

# `build_registry` is imported at module scope (not lazily) so tests can
# monkeypatch `run.build_registry` with a stub registry, avoiding the heavy
# faster-whisper import path in unit tests.
from steno10k.api.stages import build_registry
from steno10k.api.storage import NotFound
from steno10k.cli.context import Deps, ExitCode, common_parser
from steno10k.contracts.errors import ErrorLog
from steno10k.contracts.events import Event, EventBus, EventKind
from steno10k.contracts.names import StageName
from steno10k.contracts.registry import StageRegistry
from steno10k.contracts.runner import run_set
from steno10k.contracts.stage import RunOptions, StageContext
from steno10k.contracts.status import StageStatus
from steno10k.lib.llm import make_llm


def add_run(sub: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    p = sub.add_parser("run", parents=[common_parser()], help="run the pipeline over a set")
    p.add_argument("project")
    p.add_argument("set_", metavar="SET")
    p.add_argument("--force", action="store_true", help="re-run stages even if outputs exist")
    p.add_argument("--skip-llm", action="store_true", help="skip LLM stages (clean/summarize)")
    scope = p.add_mutually_exclusive_group()
    scope.add_argument(
        "--only", choices=[s.value for s in StageName], default=None, help="run only this stage"
    )
    scope.add_argument(
        "--from",
        dest="from_stage",
        choices=[s.value for s in StageName],
        default=None,
        help="run this stage and everything after it",
    )
    p.set_defaults(func=handle)


def handle(args: argparse.Namespace, deps: Deps) -> int:
    opts = RunOptions(
        force=args.force,
        only=StageName(args.only) if args.only else None,
        from_stage=StageName(args.from_stage) if args.from_stage else None,
        skip_llm=args.skip_llm,
    )
    return execute_run(deps, args.project, args.set_, opts, verbose=deps.verbose, as_json=deps.json)


def execute_run(
    deps: Deps,
    project: str,
    set_: str,
    opts: RunOptions,
    *,
    registry: StageRegistry | None = None,
    verbose: bool = False,
    as_json: bool = False,
) -> int:
    try:
        manifest = deps.storage.load_manifest(project, set_)
    except NotFound as exc:
        print(str(exc), file=sys.stderr)
        return ExitCode.USAGE

    cfg = deps.config_service.load()
    set_dir = deps.storage.set_dir(project, set_)
    bus = EventBus()
    bus.subscribe(lambda e: _print_event(e, verbose=verbose))
    ctx = StageContext(
        set_dir=set_dir,
        cfg=cfg,
        force=opts.force,
        manifest=manifest,
        errors=ErrorLog(set_dir / "errors.log"),
        events=bus,
        llm=make_llm(cfg),
    )
    reg = registry if registry is not None else build_registry()
    try:
        run_set(reg, ctx, opts)
    except Exception as exc:  # a stage raised — persist progress, report failure
        print(f"run failed: {exc}", file=sys.stderr)
        manifest.save(deps.storage.manifest_path(project, set_))
        return ExitCode.FAILURE

    manifest.save(deps.storage.manifest_path(project, set_))
    _print_summary(project, set_, manifest.stages, manifest.errors, as_json=as_json)
    failed = any(status is StageStatus.FAILED for status in manifest.stages.values())
    return ExitCode.FAILURE if failed else ExitCode.OK


def _print_event(event: Event, *, verbose: bool) -> None:
    stage = event.payload.get("stage", "")
    if event.kind is EventKind.STAGE_STARTED:
        print(f"-> {stage}")
    elif event.kind is EventKind.STAGE_COMPLETED:
        stats = event.payload.get("stats", {})
        suffix = f"  {stats}" if verbose and stats else ""
        print(f"[ok] {stage}{suffix}")
    elif event.kind is EventKind.STAGE_SKIPPED:
        print(f"[skip] {stage}")
    elif event.kind is EventKind.STAGE_FAILED:
        print(f"[FAIL] {stage}", file=sys.stderr)
    elif verbose and event.kind is EventKind.STAGE_PROGRESS:
        print(f"  ... {stage} {event.payload}")


def _print_summary(
    project: str,
    set_: str,
    stages: dict[StageName, StageStatus],
    errors: int,
    *,
    as_json: bool,
) -> None:
    failed = any(status is StageStatus.FAILED for status in stages.values())
    if as_json:
        import json as _json

        print(
            _json.dumps(
                {
                    "project": project,
                    "set": set_,
                    "stages": {str(k): str(v) for k, v in stages.items()},
                    "errors": errors,
                    "failed": failed,
                },
                indent=2,
            )
        )
        return
    print(f"\n=== Run summary: {project}/{set_} ===")
    for name, status in stages.items():
        print(f"  {name:12} {status}")
    print(f"errors: {errors}")
    print("result: FAILED" if failed else "result: ok")
