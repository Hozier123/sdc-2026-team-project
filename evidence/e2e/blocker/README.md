# T1 E2E blocker evidence

- File: `t1_e2e_23_2026-10-24.json`
- Original SHA-256: `97FEE66743809D748E4C571749777D69D0CF2B01F6AAA8770C16289AB8F390D8`
- Mode: `REAL`, 23 T1 E2E parse-draft cases
- Status: `BLOCKER_EVIDENCE`
- Not valid for: current E2E, READY, passing, or accuracy claims

## Why this is blocker evidence

Under the old resolver, `DEV-01` (`3 ctn Ayam A1, 10kg Bawang Bsr India`) produced:

```text
uom=bag
sku_id=SKU_BAWANG_10KG
qty=10
tier_unit_price=32.00
subtotal=320.00
status=READY_FOR_APPROVAL
```

This was an incorrect approvable result: bulk Bawang should use `SKU_BAWANG_KG`, with 10 × RM3.50 = RM35.00.

Root cause: when `row.uom=None`, the resolver still filtered by `pack_size=10kg` and incorrectly selected the bag SKU. PR #55 (`c93d6d0`) blocks this behavior: when UOM is missing and a family has multiple `base_unit` values, return `MISSING_UOM` plus candidates instead of automatically selecting a SKU.

## Other known issues

- `DEV-04/05/11/33/37` still have `uom=None`.
- As a result, `DEV-05/33` reach `MISSING_UOM` rather than the insufficient-stock check.
- `uom=None / MISSING_UOM` remains a known gap.

## Usage rules

```text
[✓] Use only as blocker / historical evidence
[✓] Preserve original CRLF bytes and SHA
[✗] Do not label CURRENT_E2E
[✗] Do not label READY
[✗] Do not claim a pass
```

A rerun must use the fixed code and a new evidence file. Do not overwrite the old file.
