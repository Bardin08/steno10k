from __future__ import annotations

from steno10k.contracts.names import StageName
from steno10k.contracts.stage import Stage, resolve_enabled


class StageRegistry:
    """Ordered stages + dependency validation. Source of truth for stage order."""

    def __init__(self, stages: list[Stage]) -> None:
        self._stages = stages
        self._validate()

    @property
    def names(self) -> list[StageName]:
        return [s.name for s in self._stages]

    @property
    def stages(self) -> list[Stage]:
        return list(self._stages)

    def deps(self) -> dict[StageName, list[StageName]]:
        return {s.name: list(s.depends_on) for s in self._stages}

    def resolve_enabled(
        self, flags: dict[StageName, bool]
    ) -> tuple[set[StageName], dict[StageName, StageName]]:
        return resolve_enabled(self.deps(), flags)

    def _validate(self) -> None:
        seen: set[StageName] = set()
        names = self.names
        for stage in self._stages:
            for dep in stage.depends_on:
                if dep not in names:
                    raise ValueError(f"stage '{stage.name}' has unknown dependency '{dep}'")
                if dep not in seen:
                    raise ValueError(f"stage '{stage.name}' depends on '{dep}' declared after it")
            seen.add(stage.name)
