from __future__ import annotations

from enum import StrEnum


class StageName(StrEnum):
    NORMALIZE = "normalize"
    CHUNK = "chunk"
    TRANSCRIBE = "transcribe"
    CLEAN = "clean"
    MERGE = "merge"
    SUMMARIZE = "summarize"
    BUNDLE = "bundle"
    NOTIFY = "notify"
