# Stage 4 deferred items (Qazaq CRM)

- **Stand mode in DB:** `PATCH /api/stand` still mutates in-process `settings`. Persisting mode and flags in PostgreSQL would touch migrations, seed, and simulator scenarios — skipped to avoid invasive change.
- **`observe.emit`:** No shared emitter in CRM yet; logging remains via `logging_ecs.py`. Align with CSIP when a shared package exists.
- **Frontend E2E tests:** Login / list / card flows remain smoke-only (`smoke.test.ts`); full Vitest + MSW coverage deferred.
- **`stand_mode` pytest fixture:** Tests still reset `settings` inline; a autouse fixture with rollback can follow in a later pass.
