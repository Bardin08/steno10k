from __future__ import annotations

import ast
from pathlib import Path

_STAGES_DIR = Path(__file__).resolve().parents[2] / "src" / "steno10k" / "stages"
_FORBIDDEN = ("steno10k.api",)


def _imports(path: Path) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    names: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.extend(a.name for a in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            names.append(node.module)
    return names


def test_stages_never_import_api() -> None:
    offenders: list[str] = []
    for py in _STAGES_DIR.glob("*.py"):
        for mod in _imports(py):
            if any(mod == f or mod.startswith(f + ".") for f in _FORBIDDEN):
                offenders.append(f"{py.name} -> {mod}")
    assert offenders == [], f"stages must not import api: {offenders}"
