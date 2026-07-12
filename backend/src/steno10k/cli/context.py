from __future__ import annotations

import argparse
from dataclasses import dataclass
from enum import IntEnum
from pathlib import Path

import yaml
from pydantic import ValidationError

from steno10k.api.configsvc import ConfigService
from steno10k.api.storage import Storage
from steno10k.contracts.config import Config


class ExitCode(IntEnum):
    OK = 0
    FAILURE = 1  # a run/stage failed, or an unexpected runtime error
    USAGE = 2  # bad usage, unknown project/set, or config error


class CliUsageError(Exception):
    """A user/environment error that should exit with ExitCode.USAGE (2)."""


@dataclass
class Deps:
    """Resolved services + global flags handed to every command handler."""

    data_root: Path
    storage: Storage
    config_service: ConfigService
    json: bool
    verbose: bool


def load_config(deps: Deps) -> Config:
    """Load config, mapping config-file errors to a CliUsageError (exit 2)."""
    try:
        return deps.config_service.load()
    except (OSError, yaml.YAMLError, ValidationError) as exc:
        raise CliUsageError(f"config error: {exc}") from exc


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
