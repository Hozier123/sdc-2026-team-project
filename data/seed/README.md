# Canonical seed (T1 / T2)

Source: `seed_he_2026-10-22.zip`<br>
Package SHA-256: `865049BFA7BA0170CB02316C42679EC7A3EB1D224E5C00DBE934A0591AFF47ED`

## Files

```text
T1_seed.sql
T2_seed.sql
SEED_MANIFEST.json
```

- `T1_seed.sql` / `T2_seed.sql` are data-only SQL containing only `INSERT` statements, without DDL or transaction-control statements.
- The original package SQL has outer `BEGIN/COMMIT` statements. The copies in this directory remove only those two outer statements; data rows are unchanged.
- Original SQL SHA-256 values are retained in `SEED_MANIFEST.json` under `source_sql_sha256`.
- Plaintext demo tokens are not in the repository. The SQL contains only `demo_token_hash`.

## Versions and counts

| Tenant | seed_version | products | inventory sum | users | customers | aliases |
|---|---|---|---:|---:|---:|---:|
| T1 | `KB-T1-20261022-r1` | 40 | 795 | 3 | 8 | 50 family / 26 uom |
| T2 | `KB-T2-20261022-r1` | 16 | 450 | 3 | 5 | 30 family / 30 uom |

T2 has 2 `alias_cache` entries; T1 also has 2 entries (the two aliases for `CUS_RASA`).

## Import

Run migrations first, then import each tenant separately:

```powershell
Set-Location backend

.venv\Scripts\python -m app.seed `
  --tenant T1 `
  --seed-sql ..\data\seed\T1_seed.sql `
  --seed-version KB-T1-20261022-r1 `
  --expect-sha256 <see SEED_MANIFEST.json> `
  --expect-products 40 `
  --expect-inventory 795

.venv\Scripts\python -m app.seed `
  --tenant T2 `
  --seed-sql ..\data\seed\T2_seed.sql `
  --seed-version KB-T2-20261022-r1 `
  --expect-sha256 <see SEED_MANIFEST.json> `
  --expect-products 16 `
  --expect-inventory 450
```

Do not use `seed_all.sql` for per-tenant imports: it inserts T1/T2 together while the manifest registers only the current tenant.

## Acceptance checks

```text
kiraorder_meta.seed_manifest contains two rows
T1 products=40, inventory=795
T2 products=16, inventory=450
A repeated import returns already_loaded
```

A 200 response from `/me` requires the privately supplied plaintext token. This directory contains no plaintext tokens.
