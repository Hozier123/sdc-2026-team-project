# T1 E2E post-PR55 evidence

- File: `t1_e2e_23_2026-10-24_post55.json`
- Original SHA-256: `DCA16B6E5DBC54AB712C1FD1133DFA13CF5083A397B56CCA99CBE41363DAC4C0`
- Mode: `REAL`, 23 T1 E2E parse-draft cases
- Code base: `c93d6d0`
- Status: `E2E_POST55`
- Excluded from the AI-only index

## Results

- 23/23 HTTP 200
- 23/23 `ai_mode=LLM`
- fallback 0
- 7 READY / 16 DISAMBIGUATION_REQUIRED

## DEV-01

The corrected result is:

```text
DISAMBIGUATION_REQUIRED
MISSING_UOM
candidates=SKU_BAWANG_10KG / SKU_BAWANG_KG
```

It no longer incorrectly reports READY or produces an RM320 bag subtotal.

## Remaining known gaps

UOM is None in 9 cases:

```text
DEV-01/04/05/07/11/13/27/33/37
```

DEV-07/13/27 are blocked by `MISSING_UOM` and belong to the known `KNOWN_UOM_INJECTION_GAP`. This iteration does not change the seed or advance Gate 0.

## Usage rules

```text
[✓] Archive as post55 E2E evidence
[✗] Do not add to the AI-only index
[✗] Do not claim 23/23 E2E passes
[✗] Do not overwrite the old 97FEE blocker file
```

The old `97FEE667…` file remains `BLOCKER_EVIDENCE` only.
