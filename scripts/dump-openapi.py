"""Dump the FastAPI app's OpenAPI schema as JSON to stdout.

Usage (from backend/): uv run python ../scripts/dump-openapi.py > ../openapi.json
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

from steno10k.api import create_app


def main() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        app = create_app(data_root=Path(tmp))
        print(json.dumps(app.openapi(), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
