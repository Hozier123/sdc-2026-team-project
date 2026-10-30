# KiraOrder backend: implementation and acceptance boundaries

B04's minimum HTTP driver and independent handoff are complete. See the
[closeout](../docs/ops/b04-closure.md), [driver runbook](../docs/ops/b04-driver.md), and
[offline evidence auditor](../docs/ops/b04-evidence-auditor.md). This public delivery contains
tools, synthetic DEV tests, and redacted summaries; original private evidence stays offline.

Implemented features include identity and tenant permissions, explicit migrations and seed loading, PII masking, the AI HTTP boundary, the in-process RunPod adapter, field-evidence guards, catalogue resolution and customer memory, batch draft saves, conditions and clarification, trilingual replies, draft discard, price escalation, owner approval, DO/inventory transactions, query/audit/warehouse reads, AI status and wake-up, `checks_enabled` soft checks, concurrent rollback, and contract regression. Development is based on `gate0-baseline-v1` (internal `gate0-v4 / draft revision 5`). The original SQL is `gate0/migrations/0001_baseline.sql` and was not changed in this iteration.

The review dated 2026-10-23 and subsequent status are in `docs/audit/backend-audit-2026-10-23.md`. The recorded full main test suite at this checkpoint was **407 passed**. With the code default `AI_PROVIDER=auto`, the adapter still uses Stub when no HTTP service is configured. Real RunPod endpoint preflight, model quality, public deployment, and independent frontend/data UAT were external acceptance boundaries at that checkpoint; do not describe this record as completed live model extraction. For the latest recorded deployment and review access, use the [root README](../README.md).

## Install and start (Windows)

Python 3.13 and a reachable PostgreSQL 17 instance are required; acceptance used PostgreSQL 17.10. Run the following from the repository root, retain the complete repository structure, and use an editable install (a standalone wheel does not include Gate 0):

```powershell
py -3.13 -m venv backend/.venv
backend/.venv/Scripts/python -m pip install -c backend/requirements.lock -e './backend[test]'
```

Set `DATABASE_URL=postgresql://username:password@host:5432/database` in the root `.env`. With an empty value, the liveness probe can still start while readiness returns 503. Process environment variables override `.env`; its lookup location does not depend on the startup directory. URI-encode URL-special characters in the password.

Migration is an explicit management command, not an automatic web-service startup action. The migration identity needs permission to create schemas, tables, functions, and triggers; use the object-owner identity for reproduction. Complete migration successfully before starting the deployed service.

```powershell
backend/.venv/Scripts/python -m app.migrations
backend/.venv/Scripts/python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

| Path | Condition | Response |
|---|---|---|
| `/healthz` | The process can handle requests | 200 `{"status":"ok"}` |
| `/readyz` | Database queries work and Gate 0 migration version/hash registration is correct | 200 `{"status":"ready"}` |
| `/readyz` | Configuration, connection, migration, or registered hashes are missing or invalid | 503 `{"status":"not_ready"}` |

These are operational probes documented here and in runtime OpenAPI; they are not written back into the frozen business OpenAPI. Probes expose neither connection strings nor underlying exceptions. Connection timeout is 3 seconds; ordinary query and lock-wait timeouts are 5 seconds. Migration statement timeout is 30 seconds; seed-import statement timeout is 60 seconds, with a 10-second tenant-lock wait. Readiness checks connectivity and migration registration, not a full schema-drift audit on every request.

## Bearer authentication and `/api/v1/me`

Identity reads and business routes are implemented. Seed loading remains explicit; application startup does not alter the database automatically.

```http
GET /api/v1/me
Authorization: Bearer <demo-token>
```

The database representation of `demo-token` is:

```text
Lowercase hex of SHA-256(token UTF-8)
```

`/me` returns `user_id`, `tenant`, `display_name`, `role`, `permissions`, and `permission_summary`. Role and tenant come only from the token's user record and cannot be overridden by request body or query parameters.

Authentication failures return 401 `INVALID_TOKEN` with `WWW-Authenticate: Bearer`; both successful and failed responses include `X-Request-ID`. Database or other unknown server failures use the common 500 response, not a business error, and expose no connection strings. Before formal seed import, a real environment has no users, so `/me` returning 401 is expected. Tests use isolated temporary databases; the repository contains hash-verified T1/T2 canonical seed data.

## Seed loader

Import a data owner's **data-only SQL** file with an explicit command; web-service startup does not seed automatically:

```powershell
backend/.venv/Scripts/python -m app.seed `
  --tenant T1 `
  --seed-sql ..\data\seed\T1_seed.sql `
  --seed-version T1-0.1 `
  --expect-sha256 <sql-sha256> `
  --expect-products 40 `
  --expect-inventory 795
```

Behavior:

- Validate the SQL file's SHA-256 before connecting to the database.
- Seed SQL permits only `INSERT`, with no DDL or `BEGIN/COMMIT/ROLLBACK`.
- Execute SQL, count checks, and `kiraorder_meta.seed_manifest` registration in one transaction.
- Repeating the same tenant + version + hash returns `already_loaded` without duplicate insertion.
- Reject automatic takeover when a tenant already has data but no manifest.
- Roll back on count mismatches or SQL failures; do not leave partial imports.
- Do not create or modify Gate 0's `public` business-table schema.

Formal T1/T2 SQL and SHA-256 values are in `data/seed/SEED_MANIFEST.json`. Tests cover both canonical seed and temporary fixtures. `.gitattributes` preserves SQL LF bytes; never re-sign a hash to bypass a failure.

## PII and the parse-draft skeleton

`POST /api/v1/orders/parse-draft` is callable. With default `AI_PROVIDER=auto` and no `AI_SERVICE_URL`, the deterministic `StubExtractor` creates a v1 draft with `DISAMBIGUATION_REQUIRED` and no formal product lines.

Provider selection:

```text
AI_PROVIDER=auto
  Use HttpAiExtractor when AI_SERVICE_URL is set; otherwise StubExtractor
AI_PROVIDER=stub
  Force StubExtractor
AI_PROVIDER=http
  HttpAiExtractor (requires AI_SERVICE_URL)
AI_PROVIDER=runpod_adapter
  In-process OrderAiAdapter + RunPodExtractor (requires RUNPOD_*)
```

`runpod_adapter` configuration:

```text
AI_PROVIDER=runpod_adapter
RUNPOD_API_KEY=...
RUNPOD_ENDPOINT_ID=...
RUNPOD_MODEL_NAME=Qwen/Qwen2.5-7B-Instruct-AWQ
LLM_TIMEOUT_S=4.1
```

The AI adapter is called only in-process by `parse-draft`; it adds no `/api/v1/extract` endpoint. Extraction, status and warmup share the provider configuration resolved by `app/ai_runtime.py`. After the public RunPod endpoint recovers, run the three-stage preflight in `docs/ops/ai-sample-runbook.md` before the six-sample runner.

Retained HTTP-boundary configuration:

```text
AI_SERVICE_URL=https://.../api/v1/extract
AI_HEALTH_URL=https://.../health
AI_WAKE_URL=https://.../wake
AI_API_KEY=...
AI_TIMEOUT_S=8.0
AI_WAKE_RATE_LIMIT_S=60
AI_WARMUP_TIMEOUT_S=180
AI_READINESS_TTL_S=60
```

`GET /api/v1/ai/status` returns `OFFLINE/WARMING/READY/DEGRADED`. RunPod mode derives `/health` and `/v1/models` from the extraction endpoint and checks the exact model name. Health 200 alone cannot establish READY: a valid inference within the last 60 seconds is also required. A real LLM parse refreshes this evidence; fallback clears it; customer-memory bypasses do not establish inference readiness. Status polling does not create inference tasks.

`POST /api/v1/ai/wake` immediately accepts a background verification job with `accepted=true/state=WARMING`; read status for the final result. RunPod warmup uses the configured model and production extraction prompt with a synthetic order, never `{"wake":true}` at chat-completions. Legacy HTTP mode calls only an explicitly configured wake URL, then verifies extraction. Warmup has a separate default 180-second budget; business parsing retains `LLM_TIMEOUT_S=4.1`. The process runs one warmup at a time, with a default 60-second per-user limit and the existing 429 `RATE_LIMITED/Retry-After` response. `AI_WARMUP_GRACE_S` is accepted for old configurations but no longer controls state transitions. Stub stays OFFLINE with `accepted=false`; API keys never appear in responses.

See [B01 provider readiness and acceptance](../docs/ops/b01-provider-readiness.md) for configuration and GPU-free regressions. Local mock success is not real RunPod acceptance. GPU worker lifecycle remains under Xiong's control.

Flow:

```text
Bearer → customer tenant check → PII mask
→ Stub / HttpAiExtractor / in-process RunPod adapter
→ HTTP: AI-Contract-v1.3 schema validation + explicit generic FAM_* mapping
→ Adapter: injected DB family catalogue + Pre-Resolver output
→ conds / ignored_spans conversion
→ Basic RawExtraction validation
→ AI lines enter the draft (NO_CANDIDATE when no SKU is selected)
→ inbound_messages / orders / draft_versions
→ OrderDraft
```

- AI contracts, samples, and H1/H5 mappings are in `docs/ai_contract/`.
- AI returns only Pre-Resolver data, never `sku_id`, prices, stock, approval, or DO.
- The HTTP path still explicitly maps `FAM_FLOUR`/`FAM_RICE`/`FAM_OIL`/`FAM_SUGAR` to canonical T1. The `runpod_adapter` path injects DB `product_families` + `family_aliases` directly into the adapter, without a second tenant mapping.
- Real endpoint/key credentials are not in the repository; the default does not fabricate AI calls.
- Only `[REDACTED_PHONE]`, `[REDACTED_MYKAD]`, and `[REDACTED_EMAIL]` are permitted PII mask tokens.
- Only `CLERK` / `OWNER` may call parsing; `WAREHOUSE` receives 403 `FORBIDDEN_ACTION`.
- Raw `message_text` is neither logged, stored, nor sent to the provider.
- `masked_text` exceeding 4000 code points returns 422 `MESSAGE_TOO_LONG`.
- A missing or cross-tenant customer returns 404 `RESOURCE_NOT_FOUND`.
- Real H1/H5 accuracy still requires an AI endpoint and evaluation set; the adapter does not invent those results.

## Clarification, CORS, and AI failures

The backend generates `clarification_draft` from unresolved issues/conditions:

```text
language
message
unresolved_issue_ids
```

`COPY_CLARIFICATION` is returned only when `clarification_draft` is nonempty. Supported languages are `ms` / `en` / `zh`. Clarification contains no original PII and does not claim confirmed price, SKU, or quantity.

Default CORS origins are local frontends:

```text
http://127.0.0.1:5173
http://localhost:5173
http://127.0.0.1:4173
http://localhost:4173
```

Override them with `CORS_ALLOW_ORIGINS`; do not use `*`.

AI-service timeouts, 5xx responses, invalid JSON, or invalid payloads return:

```text
503 AI_AND_FALLBACK_UNAVAILABLE
```

## Draft lines, approval, and DO

Implemented routes:

```text
PUT  /api/v1/orders/drafts/{draft_id}/lines
POST /api/v1/orders/drafts/{draft_id}/discard
POST /api/v1/orders/drafts/{draft_id}/clarification-copied
POST /api/v1/orders/{draft_id}/approve
POST /api/v1/approvals/{approval_id}/decide
GET  /api/v1/delivery-orders/{do_number}
GET  /api/v1/approvals
GET  /api/v1/approvals/{approval_id}
```

`discard` is the P1 CLERK/OWNER termination action. It requires `expected_version` and a nonempty `note`, and accepts only `DISAMBIGUATION_REQUIRED` / `READY_FOR_APPROVAL` drafts. Success sets `status=REJECTED` and `termination_reason=CLERK_DISCARDED`, and writes `CANCEL_DRAFT` audit and `DRAFT_DISCARDED` activity records. Pending or issued drafts cannot be discarded.

`clarification-copied` only appends `COPY_CLARIFICATION` audit and `CLARIFICATION_COPIED` activity records. It binds draft/version, clarification issue_ids, corresponding line_ids, language, and message SHA-256, without retaining the complete message or changing the draft/version.

The same-day check examines only that customer's existing DOs for the day. `SEPARATE_ADD_ON` requires an explicit `related_do_number` when saving resolutions. The new DO records it; the original DO is unchanged. `DUPLICATE` / `CHANGE_EXISTING` use P1-02 discard to close the current draft with a reason, without automatically modifying the original order. A `SEPARATE_ADD_ON` decision survives subsequent saves unless the same-day DO set changes.

**`confirmed_items` is a deprecated compatibility path.** New frontends must still save first:

```text
PUT /api/v1/orders/drafts/{draft_id}/lines
→ POST /api/v1/orders/{draft_id}/approve
```

For an old client supplying `confirmed_items`, the backend performs the following in one transaction:

```text
1. Save a new version using PUT lines rules
2. Revalidate stock, escalation, and conditions
3. Approve that new version
4. Roll back the entire transaction if any step fails
```

The response returns the version actually approved; unsaved details are never silently approved. This compatibility path no longer returns 422, but remains deprecated in OpenAPI.

## Migration execution rules

1. Before connecting, validate the original SQL-byte SHA-256 and controlled-manifest SHA-256 against the frozen tag.
2. Use the PostgreSQL parser to split SQL at statement boundaries. Read original statement text; do not manually split function bodies at semicolons or generate rewritten SQL.
3. Execute the original script's `BEGIN` and acquire a transaction-level advisory lock. Create the ledger in `kiraorder_meta.schema_migrations`; business objects remain in `public`.
4. If unregistered, run original DDL sequentially only when `public` has no business base tables, then register the version, SQL hash, and baseline-manifest hash. Reject automatic takeover of existing tables without a ledger.
5. If registration matches, skip DDL but recheck the table-name set, trigger events/enabled state, and existence/validity of the three unique indexes.
6. After acceptance checks, execute the original script's `COMMIT`. DDL, ledger creation, and registration share one transaction; any intermediate error rolls back. Locks serialize concurrent runs; lock timeouts can be retried.

The first command returns `status=applied`; repetition returns `status=already_applied`. Registration conflicts or schema anomalies exit with code 1 without attempting repairs or deleting existing data. Future migrations need version-sequence management; this PR supports only `0001_baseline`.

Acceptance counts are schema-specific: `public` has **18 base tables, 6 trigger objects, and 12 UPDATE/DELETE event entries**. `kiraorder_meta` has one additional migration ledger. Check object names and target tables, not just counts. Continuous full-field/constraint drift detection is outside this phase.

## Tests

Database-free tests (explicitly excluding integration tests):

```powershell
Set-Location backend
.venv/Scripts/python -m pytest -q -m 'not integration'
```

Full acceptance requires `TEST_DATABASE_ADMIN_URL`, an administrator connection with CREATEDB permission. Each integration test creates a randomly named `kiraorder_test_<uuid>` database and removes only that database afterward. Tests do not use application `DATABASE_URL` as a target. Without the test connection, the full suite fails explicitly instead of silently skipping.

```powershell
$env:TEST_DATABASE_ADMIN_URL = 'postgresql://test_user:test_password@127.0.0.1:5432/postgres'
.venv/Scripts/python -m pytest -q
.venv/Scripts/python -m ruff check app tests
.venv/Scripts/python -m ruff format --check app tests
.venv/Scripts/python -m pip check
```

Coverage includes real Uvicorn startup, HTTP liveness/readiness, migration CLI, empty-database install, data preservation on repeat runs, concurrent exclusion, full rollback on precommit failure, incorrect hashes, ledger conflicts, protection of existing tables without a ledger, disabled-trigger detection, and approval-snapshot UPDATE/DELETE protection.

GitHub Actions runs full acceptance against an isolated PostgreSQL 17.10 service. Gate 0's own 42 contract checks still use `gate0/scripts/bootstrap_gate0.ps1`; do not mix its dependencies with the new backend environment.

## Recorded acceptance boundaries

The internal backend workflow was implemented with automated tests; the recorded full main suite at this checkpoint was **407 passed**. The AI adapter was merged but defaulted to Stub. Outstanding external evidence or live acceptance covered RunPod preflight, model quality/independent accuracy, public deployment, independent frontend/data UAT, and real-user trials. The six-sample runner is in the [runbook](../docs/ops/ai-sample-runbook.md). The v1.3 working documents 01–04 are under `docs/rules/`, updated in separate commits with implementation changes rather than written back into frozen files. Consult the [root README](../README.md) for later deployment and evidence updates.

Implementation references: [psycopg transaction management](https://www.psycopg.org/psycopg3/docs/basic/transactions.html), [pglast SQL parser](https://pglast.readthedocs.io/en/v7/parser.html), and [PostgreSQL advisory locks](https://www.postgresql.org/docs/17/explicit-locking.html#ADVISORY-LOCKS).
