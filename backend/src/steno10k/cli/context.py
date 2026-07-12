from __future__ import annotations

import argparse
from dataclasses import dataclass
from enum import IntEnum
from pathlib import Path

from steno10k.api.configsvc import ConfigService
from steno10k.api.storage import Storage


class ExitCode(IntEnum):
    OK = 0
    FAILURE = 1  # a run/stage failed, or an unexpected runtime error
    USAGE = 2  # bad usage, unknown project/set, or config error


@dataclass
class Deps:
    """Resolved services + global flags handed to every command handler."""

    data_root: Path
    storage: Storage
    config_service: ConfigService
    json: bool
    verbose: bool


def common_parser() -> argparse.ArgumentParser:
    """Global options attached (as a parent) to every leaf subparser, so they
    can be passed after the subcommand, e.g. `steno10k projects list --json`.

    A fresh instance per call avoids argparse parent-sharing state issues.
    """
    p = argparse.ArgumentParser(add_help=False)
    p.add_argument(
        "--data-root", default=None, help="store root (default: $STENO10K_DATA_ROOT or ./data)"
    )
    p.add_argument("--json", action="store_true", help="machine-readable JSON output")
    p.add_argument("-v", "--verbose", action="store_true", help="verbose output")
    return p
