# Stage 4 deferred items (Qazaq CRM)

- **Stand mode in DB:** `PATCH /api/stand` still mutates in-process `settings`. Persisting mode and flags in PostgreSQL would touch migrations, seed, and simulator scenarios — skipped to avoid invasive change.
- **`observe.emit`:** No shared emitter in CRM yet; logging remains via `logging_ecs.py`. Align with CSIP when a shared package exists.
- **Frontend E2E tests:** Login / list / card flows remain smoke-only (`smoke.test.ts`); full Vitest + MSW coverage deferred.
- **`stand_mode` pytest fixture:** Tests still reset `settings` inline; a autouse fixture with rollback can follow in a later pass.

## Stage 6 (lint / automation)

- **Ruff:** Extended rule set in `backend/pyproject.toml` (aligned with CSIP Stage 6). Same gradual `ignore` list for import/typing churn, complexity, and timezone rules until a dedicated cleanup pass.
- **Pre-commit:** Root `.pre-commit-config.yaml` — ruff, ruff-format, commit-msg hook rejecting `Co-authored-by:` (install locally; not required for demo).
- **CI:** No `.github/workflows` yet — add a minimal `ruff check` job when the repo is wired to GitHub Actions (CSIP CI remains the reference).
- **`ruff format`:** Not enforced in repo; run via pre-commit when reformatting is acceptable.
