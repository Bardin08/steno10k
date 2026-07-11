from __future__ import annotations

import uuid


def new_id() -> str:
    """A fresh GUID string. Called at object-creation boundaries only."""
    return str(uuid.uuid4())
