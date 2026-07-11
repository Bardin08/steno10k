# Python standard

Guiding rule: **least code wins; reuse over rewrite; DRY / SOLID / KISS.**

## Language

- `from __future__ import annotations` at the top of every module.
- Modern type syntax: `X | None`, `list[X]`, `dict[K, V]`. Never
  `typing.Optional` / `typing.List`.
- Fully typed. `mypy` runs strict; no `Any` without a comment justifying it.

## Tooling (CI-enforced)

- **`ruff`** — lint **and** format (replaces black/isort/flake8).
- **`mypy`** — strict-ish type checking.
- **`pytest`** — tests; pure functions get unit tests.
- Packaged with `pyproject.toml`, managed by `uv`.

## Design

- Prefer the standard library and vetted dependencies over bespoke code.
- Small, focused modules with one clear responsibility.
- **Narrow exceptions** (`OSError`, `RuntimeError`, …). Broad `except Exception`
  is allowed **only** at documented isolation boundaries, with an inline comment
  explaining why.
- No clock/random reads inside pure functions — inject them at the boundary
  (keeps code testable and workflows reproducible).
