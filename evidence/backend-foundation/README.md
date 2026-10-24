# Backend foundation acceptance record

Record date: 2026-10-22. Scope: the first P0-A backend PR. This record does not cover seed loading, authentication, parsing, order approval, business KPIs, or platform deployment proof.

## Local environment and results

- Windows, Python 3.13.5, PostgreSQL 17.10; dependency versions are in `backend/requirements.lock`.
- The database was a separately initialized, temporary local instance listening only on `127.0.0.1:55432`; no existing business database was connected. Each integration test created a randomly named test database and removed only that database afterward.
- Command: run `.venv/Scripts/python -m pytest -q` from `backend/`, with the test connection supplied through `TEST_DATABASE_ADMIN_URL`.
- Measured result: **17 passed, 0 failed, 0 skipped**.
- One third-party deprecation warning remained: Starlette TestClient recommends moving from httpx to httpx2 in the future. Tests passed with the locked versions; the warning was neither disabled nor hidden. Revalidate when upgrading test dependencies.
- Ruff linting, formatting checks, and `pip check` ran separately; dependency compatibility checks reported no errors.
- Original Gate 0 validation entry point `gate0/scripts/bootstrap_gate0.ps1 -SkipInstall`: 42 passed and 73 controlled-file checks passed; `git diff gate0-baseline-v1 -- gate0/` showed no differences.

## Verified behavior

1. A real Uvicorn subprocess starts and HTTP `/healthz` returns 200.
2. `/readyz` returns 503 when configuration, migration, or connection is missing; it returns 200 after migration registration is correct.
3. The real CLI reports `applied` on the first migration and `already_applied` on repetition, preserving inserted synthetic data.
4. `public` contains exactly 18 base tables, 6 non-internal trigger objects, and 12 UPDATE/DELETE event entries. The migration ledger is separate under `kiraorder_meta`.
5. Two concurrent migration requests apply the migration only once. An intentionally injected database error before commit rolls back both DDL and the ledger, and a subsequent retry succeeds.
6. Incorrect SQL or manifest hashes are rejected before database connection. Ledger conflicts, existing tables without a ledger, and disabled triggers are rejected rather than silently repaired.
7. The real database blocks illegal UPDATE/DELETE operations on approval snapshots while allowing the valid PENDING → APPROVED transition.
8. Probes and the migration CLI do not print connection passwords or raw database exceptions.

## Reproduction and limitations

Full reproduction commands and database permissions are documented in the [backend README](../../backend/README.md). CI is defined in `.github/workflows/backend-foundation.yml` and uses a PostgreSQL 17.10 service. Actual remote status is determined by the corresponding PR's Actions records; this document does not predeclare CI success.

Do not mix database counting methods: `pg_trigger` counts 6 objects, while `information_schema.triggers` expands them into 12 event entries. These checks are neither a complete schema-drift audit nor business end-to-end acceptance.

The frozen baseline is `gate0-baseline-v1`. SQL SHA-256: `6DDFD6160A2416237A73ADC16A3B26F4DDE0657FD42BDB2A7C355682711FE471`. Controlled-manifest SHA-256: `6A44089C623C1B4AE8F444660DBD89422C663E7EBDD141EA6FDA549DDD833770`. This PR did not modify `gate0/`, move the tag, or update frozen sign-off status. Formal confirmation remains in `evidence/gate0/`.
