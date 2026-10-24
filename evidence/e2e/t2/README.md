# T2 E2E evidence

- File: `t2-e2e-active-20261024.json`
- Original SHA-256: `70A1BF9B9ACADECF8764C0CF1B748CB9D9B9DC85BE1444C3F92CA1E5E19ACDB8`
- Mode: `REAL`
- Code base: `c93d6d0`
- Status: `T2_E2E_PASS`

## Results

```text
GET  /api/v1/me                 200, tenant=T2, role=CLERK
POST /api/v1/orders/parse-draft 200
ai_mode=LLM
request-id=t2-e2e-active-20261024
lines=1, uom=ctn
```

T2 customer: `CUS_KILAT_01`. The family is `UNKNOWN` because the T2 catalogue does not contain Tepung; this is not a 401 or a pipeline failure.

## Usage rules

```text
[✓] Use as T2 E2E evidence
[✗] Do not add to the AI-only index
[✗] Do not claim 23/23 T1 E2E passes
[✗] Do not claim all UOM checks pass
```
