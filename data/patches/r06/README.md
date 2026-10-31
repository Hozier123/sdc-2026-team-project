# R06 reviewed family-alias patch

Data version: `TRILINGUAL-2026-10-31-v001`. Execution revision: **r2**.

These files archive the reviewed SQL used in an isolated local candidate database. They are manual data patches, separate from the frozen `gate0/` migrations and `data/seed/` baseline. Adding this directory does not run SQL, change application code, or deploy the patch to the public demonstration environment.

| File | Purpose | SHA-256 |
| --- | --- | --- |
| `R06_trilingual_20261031_v001r2_up.sql` | Add six T1 family aliases | `e11ee51139dfcbca8f8276a916619fc577d3da389076e53f92d02769cf0d3287` |
| `R06_trilingual_20261031_v001r2_down.sql` | Remove this patch's six reserved alias rows | `921ab21eb0142de87a1ed363ff31222455f5d2977b59fde8e6b56d71ec4b6ef4` |

## Data and loading

The patch adds Chinese and English FAMILY expressions for `FAM_GULA`, `FAM_BERAS`, and `FAM_GARAM`. It does not create SKU identities, prices, stock, unit conversions, or customer memory. All existing families and aliases remain available.

The application already reads `family_id -> [family_name, aliases...]` through `backend/app/ai/catalog.py:load_family_catalog(conn, tenant)`. Its SQL scopes both families and aliases by `tenant_id`. The backend family-evidence guard also reads these aliases. No new loader or public response field was needed for the reviewed candidate implementation.

## Reviewed behavior

The recorded local sequence was up **6**, repeated up **0**, down **6**, repeated down **0**, replay up **6**. T1 alias count changed from 50 to 56; the three affected families changed from two to four aliases each. T1 retained all 25 active families, and T2 retained all 10 active families and 30 aliases.

Five rollback-only negative checks covered a conflicting family phrase, a reserved ID occupied by another tenant, a partial insertion, a missing legacy row, and a partial deletion. These checks exercise the patch's preflight and post-state assertions. They do not establish that the database UNIQUE constraint itself was exercised.

## Execution boundary and rollback

The original SQL is preserved byte-for-byte. Both scripts contain their own `BEGIN` and `COMMIT`; unexpected affected-row counts or failed post-state checks raise before commit. Revision r2 supersedes the archived v001 execution files; the six data tuples are unchanged.

The scripts do not identify the target database or cluster. A future operator must first verify the intended target, retain before/after snapshots, and check existing phrases, reserved IDs, and complete row contents. The original reviewed execution was confined to an isolated candidate environment. Applying to another database requires its own target checks and verification; this archive grants no automatic deployment status.

Retained review limitation: the r2 target post-state check counts `phrase_norm + family_id`, without jointly asserting the target `alias_id` and `language`. The reviewed candidate rows matched all six fields. A different database containing equivalent phrases under different IDs can return zero inserts without making the reserved-ID rollback appropriate. Stop on an unexpected pre-state; do not infer rollback ownership from a zero insert count.

Rollback must preserve historical aliases and human-confirmed memory. The down script only addresses the six reserved IDs and their expected phrase/family tuples. Existing rows whose contents or provenance changed require review before deletion.

See the [public closeout summary](../../../docs/ops/r06-archive.md) and [machine-readable evidence index](../../../evidence/r06/2026-11-01/summary.json). Original private evidence and acceptance files remain in the team's private archive; they are referenced by hash rather than published here.
