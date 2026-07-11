from __future__ import annotations

from pathlib import Path

import yaml

from steno10k.contracts.config import Config
from steno10k.contracts.names import StageName
from steno10k.contracts.stage import resolve_enabled


class ConfigService:
    """Loads/saves the single global config. Precedence: defaults -> file -> env."""

    def __init__(self, path: Path) -> None:
        self._path = path

    def load(self) -> Config:
        raw: dict[str, object] = {}
        if self._path.is_file():
            raw = yaml.safe_load(self._path.read_text(encoding="utf-8")) or {}
        # (env-var overrides layer here in a future task if needed; defaults+file for now)
        return Config.model_validate(raw)

    def save(self, cfg: Config) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._path.write_text(
            yaml.safe_dump(cfg.model_dump(mode="json"), sort_keys=False), encoding="utf-8"
        )

    def resolve(
        self, cfg: Config, deps: dict[StageName, list[StageName]]
    ) -> tuple[set[StageName], dict[StageName, StageName]]:
        return resolve_enabled(deps, dict(cfg.stages.enabled))
