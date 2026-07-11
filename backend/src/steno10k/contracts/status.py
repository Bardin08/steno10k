from __future__ import annotations

from enum import StrEnum


class StageStatus(StrEnum):
    OK = "ok"
    FAILED = "failed"
    SKIPPED = "skipped"
    PENDING = "pending"
