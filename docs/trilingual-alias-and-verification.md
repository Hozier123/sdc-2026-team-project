# Trilingual Product-Family Aliases — Scope, Verification, and Limits

Status: **content accepted; data loaded into an isolated candidate database; end-to-end regression NOT_RUN; overall NOT_READY.**

This document describes one narrow deliverable: a tenant-scoped alias table that lets a single product family be recognised from Malay, Chinese, and English surface forms, together with the rules and the verification that back it. It is written so that every claim below can be checked against this repository.

---

## 1. Scope

| Item | Value |
|---|---|
| Tenants affected | 1 (the primary tenant catalogue only) |
| Product families covered | 3 (sugar, rice, salt) |
| Language surfaces | Malay, Chinese, English |
| Records after this round | 9 (3 pre-existing + **6 new**) |
| Alias granularity | **Family level only** |
| New products / SKUs / prices / inventory identities | **None** |
| SKU-level exact aliases | **Intentionally excluded** (see §3.3) |

The patch is in this repository:

```
data/patches/r06/R06_trilingual_20261031_v001r2_up.sql
data/patches/r06/R06_trilingual_20261031_v001r2_down.sql
```

Both files are byte-identical to the revision that was executed:

| File | SHA-256 |
|---|---|
| `R06_trilingual_20261031_v001r2_up.sql` | `e11ee51139dfcbca8f8276a916619fc577d3da389076e53f92d02769cf0d3287` |
| `R06_trilingual_20261031_v001r2_down.sql` | `921ab21eb0142de87a1ed363ff31222455f5d2977b59fde8e6b56d71ec4b6ef4` |

Verify with:

```bash
sha256sum data/patches/r06/R06_trilingual_20261031_v001r2_up.sql
sha256sum data/patches/r06/R06_trilingual_20261031_v001r2_down.sql
```

---

## 2. Design rules

1. **One identity, many surfaces.** A language variant never becomes a separate product, SKU, price row, or inventory identity.
2. **Family and SKU are layered.** A family alias locates the family; the concrete pack size is resolved afterwards by the backend from the requested specification, never from the alias.
3. **No SKU-level exact aliases this round** (§3.3 explains why this is a safety rule, not an omission).
4. **Unit synonyms are normalisation, not conversion.** `bag/bags/袋`, `ctn/箱`, `papan/托`, `btl/瓶`, `tin/桶` map to one canonical unit. There is **no quantity conversion** between different canonical units, and none is inferred from a pack description.
5. **Pack size is not quantity.** In `2 bag ... 1kg`, `2` is the ordered quantity and `1kg` is the pack size.
6. **Conflicts are rejected, never overwritten.** A phrase that already points to another family in the same tenant aborts the import.
7. **Idempotent and reversible.** Re-running the patch inserts nothing; the rollback removes only the rows this patch created.
8. **No context trimming.** The model catalogue keeps every active family of the tenant; it is not reduced to the three families that gained new expressions.

---

## 3. Normalisation and matching behaviour

### 3.1 Normalisation

Phrases are normalised with **NFKC + case folding + whitespace collapsing**. The patch therefore stores `sugar`, `rice`, `salt` for the English surfaces and the Chinese forms unchanged.

### 3.2 Uniqueness

`family_aliases` enforces `UNIQUE (tenant_id, phrase_norm)`. A phrase that already belongs to a different family cannot be imported: the pre-check raises, the transaction rolls back, and the existing mapping is preserved. A single phrase is never allowed to mean two families.

### 3.3 Why SKU-level exact aliases are excluded

Confirmed SKU-level or whole-sentence aliases enter a separate "confirmed memory" path. When a whole message matches such an alias, extraction is bypassed and the run is recorded with `ai_mode=ALIAS_ONLY`. The acceptance requirement for the main trilingual case is an actual model extraction (`ai_mode=LLM`), so adding SKU-level exact aliases would silently invalidate the very case the table exists to support. Family-level aliases do **not** take that path.

### 3.4 Unit semantics

`1kg`, `2kg`, `5kg` are pack sizes, not quantities. Missing quantity is never defaulted to 1, missing unit is never defaulted to `bag`, and a unit that does not exist in the catalogue is rejected rather than converted.

---

## 4. What was verified

Verification ran against an isolated candidate database, never against a shared or production database.

### 4.1 Patch lifecycle

| Step | Result |
|---|---|
| Apply | 6 rows inserted |
| Apply again | 0 rows inserted (idempotent) |
| Roll back | 6 rows removed |
| Roll back again | 0 rows removed |
| Apply once more | 6 rows inserted |

Family-alias count for the tenant moved **50 → 56**; the second tenant's alias count stayed unchanged.

### 4.2 Negative cases (all rejected and rolled back)

1. A phrase that already points to a **different family** is refused and the old mapping is untouched.
2. A reserved alias identifier already used by **another tenant** is refused (global primary key).
3. A partially pre-populated state that would make the patch insert only **5 rows** is refused.
4. A **missing historical row** is detected by the post-state guard and the patch aborts.
5. A rollback that would remove only **1 row** is refused.

Each negative case left no residue: the table returned to its pre-run state.

### 4.3 Protected data unchanged

Before/after digests were compared for 20 tables. Everything except `family_aliases` was **byte-identical**, including inventory, tier prices, products, unit aliases, confirmed-memory aliases, customers, users, orders, drafts, approvals, delivery orders, and audit tables. In particular:

- inventory was untouched (the zero-buffer salt line remained at its planned quantity);
- no confirmed-memory alias was written, so `ALIAS_ONLY` cannot be triggered by this patch.

### 4.4 Recognition at the guard layer

Using the production guard function with fixed family fixtures (no model, no HTTP parse):

| Input | Before load | After load |
|---|---|---|
| `2 bag 白糖 1kg` | `UNKNOWN` | `FAM_GULA` |
| `2 bag Sugar 1kg` | `UNKNOWN` | `FAM_GULA` |
| `2 bag 大米 5kg` | `UNKNOWN` | `FAM_BERAS` |
| `2 bag Rice 5kg` | `UNKNOWN` | `FAM_BERAS` |
| `2 bag 食盐 1kg` | `UNKNOWN` | `FAM_GARAM` |
| `2 bag Salt 1kg` | `UNKNOWN` | `FAM_GARAM` |
| `2 bag Gula 1kg` (pre-existing) | `FAM_GULA` | `FAM_GULA` |
| `2 bag Milo 2kg` (untouched family) | `FAM_MILO` | `FAM_MILO` |

The same eight inputs evaluated under the second tenant remained `UNKNOWN` before **and** after the load.

### 4.5 What this does *not* prove

The guard-layer check is not an extraction result. It shows that the catalogue and the backend guard now accept these six surface forms; it does not show that a model extracts orders from them, and it does not produce any end-to-end case result.

---

## 5. Not verified in this round

| Item | Status |
|---|---|
| End-to-end trilingual regression (main case, variants, ambiguity, missing price, unit conflict, unknown product, missing quantity, full approve-and-deliver closure) | **NOT_RUN** |
| Real model evidence for the alias table (new run id, `actual_ai_mode=LLM`, raw response) | **NOT_RUN** |
| Deployment to a public or production environment | **NOT_RUN** |
| Overall readiness | **NOT_READY** |

The candidate environment was deliberately shut down after the load was accepted. No end-to-end case was executed, so none can be reported as passed or partially passed.

---

## 6. Known limitations

- **Word-form coverage is exactly three Chinese forms** (`白糖`, `大米`, `食盐`). This is not "Chinese product names are supported"; a longer form such as `白砂糖` does not match, and single-character aliases (`糖`, `米`, `盐`) are deliberately not added because they would collide with future families.
- **Exact matching only.** No misspelling tolerance, no fuzzy matching, no semantic search.
- **No polysemy support.** One phrase cannot map to two families; such a conflict is rejected by design.
- **The second tenant's trilingual set was not extended.** Its catalogue and alias count were verified as unchanged, not extended.
- **Unit synonyms only.** Cross-unit conversion is not implemented and will not be inferred.
- **No claim about model quality.** The table provides vocabulary; it does not demonstrate recognition rates.

---

## 7. How to read claims about this work

**Supported by the evidence above**

- A tenant-scoped, family-level alias table with three language surfaces for three families exists and is version-pinned.
- The patch is idempotent, reversible, and rejects conflicting imports instead of overwriting.
- Loading it does not alter products, prices, inventory, unit aliases, confirmed memory, or any business table.
- After loading, the backend guard resolves the six new surface forms and keeps the second tenant isolated.

**Not supported**

- "Trilingual input works end to end" — the regression was not run.
- "The model recognises these names" — no model evidence was produced.
- "The table is deployed" — the candidate environment was shut down; nothing was published.
- "Chinese/English product names are supported in general" — coverage is three word forms.

---

## 8. Reproducing the verification

```bash
# 1. Verify the patch bytes
sha256sum data/patches/r06/R06_trilingual_20261031_v001r2_up.sql
sha256sum data/patches/r06/R06_trilingual_20261031_v001r2_down.sql

# 2. Apply against a disposable database (never a shared one)
psql "$DATABASE_URL" -f data/patches/r06/R06_trilingual_20261031_v001r2_up.sql

# 3. Re-apply to confirm idempotency (expect 0 rows)
psql "$DATABASE_URL" -f data/patches/r06/R06_trilingual_20261031_v001r2_up.sql

# 4. Roll back and confirm only this patch's rows are removed
psql "$DATABASE_URL" -f data/patches/r06/R06_trilingual_20261031_v001r2_down.sql
```

The scripts assert their own preconditions inside the transaction: an unexpected affected-row count, a conflicting phrase, a reserved identifier, or a changed historical row raises an exception and rolls the transaction back. A run that does not end in "6 or 0 rows" cannot commit.
