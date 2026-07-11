from __future__ import annotations

from pathlib import Path


class ErrorLog:
    """Per-set error sink. Appends to errors.log and counts."""

    def __init__(self, path: Path) -> None:
        self._path = path
        self.count = 0

    def log(self, stage: str, item: str, error: object) -> None:
        self.count += 1
        self._path.parent.mkdir(parents=True, exist_ok=True)
        with self._path.open("a", encoding="utf-8") as fh:
            fh.write(f"[{stage}] {item}: {error}\n")
