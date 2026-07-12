from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from steno10k.api.configsvc import ConfigService
from steno10k.api.storage import Storage
from steno10k.cli import commands, run
from steno10k.cli.context import CliUsageError, Deps, ExitCode


def _resolve_data_root(raw: str | None) -> Path:
    if raw:
        return Path(raw)
    return Path(os.environ.get("STENO10K_DATA_ROOT", "./data"))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="steno10k", description="steno10k terminal driver")
    sub = parser.add_subparsers(dest="command", required=True)
    commands.add_projects(sub)
    commands.add_sets(sub)
    commands.add_import(sub)
    commands.add_recordings(sub)
    commands.add_status(sub)
    run.add_run(sub)
    commands.add_config(sub)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    data_root = _resolve_data_root(getattr(args, "data_root", None))
    deps = Deps(
        data_root=data_root,
        storage=Storage(data_root),
        config_service=ConfigService(data_root / "config.yaml"),
        json=getattr(args, "json", False),
        verbose=getattr(args, "verbose", False),
    )
    try:
        return int(args.func(args, deps))
    except CliUsageError as exc:
        print(str(exc), file=sys.stderr)
        return int(ExitCode.USAGE)
