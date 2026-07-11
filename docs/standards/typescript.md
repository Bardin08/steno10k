# TypeScript / React standard

Guiding rule: **least code wins; the best code is the code never written.**

## Language

- Strict `tsconfig` (`strict`, `noUnusedLocals`, `noUnusedParameters`).
- No `any`. Model types explicitly; generate API types from the OpenAPI schema
  (`openapi-typescript`) — never hand-write the client.
- Function components + hooks. No class components.

## Tooling (CI-enforced)

- **`eslint`** + **`prettier`** — lint and format.
- **`tsc --noEmit`** — typecheck.
- **`vitest`** + Testing Library — unit tests.

## UI

- **Import from the primitive component library — do not re-invent** buttons,
  inputs, cards, etc.
- Icons from **Phosphor** (or Radix icons). **Never emoji.**
- All styling flows from the design tokens (`frontend/src/design/tokens.css`).
  No raw hex in components — use tokens.
- Follow `docs/standards/ui-design-system.md` for every visual decision.
