# C12 — Current-order logs survive reload and role changes

**Execution: PASS. Independent review: PENDING (Zhou).** This PR includes eight original screenshots, nine scoped and redacted API response captures, successful browser reload/role observations, and reproducible equality checks for direct review on GitHub. It records fresh operations from 31 October 2026 (MYT), not seeded historical logs.

## Results

- Approval: draft `DRF_D66F2FAEEF82493E8F30D8C0FC8DC8CD` generated `DO_20261030_D8ED6398`, one bag at RM18.00, approved by `USR_T1_CLERK` at **06:37:57 MYT**. The approval and inventory-deduction events remained identical after hard reload and reconnecting as OWNER.
- Rejection: `APR_03CD078FA6B740D89903D80968052FA6`, draft `DRF_D9F88405F74547A99C14A73AE6BE3390`, was rejected by `USR_T1_OWNER` at **06:43:39 MYT**. After hard reload and reconnecting as CLERK, the activity IDs, actors, timestamps and payloads were unchanged; the terminal draft retained the reason and returned `do_number: null`.
- The frontend displayed **v1.5.1**. Reload cleared the in-memory token and displayed a reconnect gate; after explicit reconnection, the persisted backend records were readable again.

[Checkpoint-to-screenshot/API map](CHECKPOINTS.md) · [Acceptance](acceptance.json) · [Browser observations](browser-observations.json) · [Persistence comparison](persistence-comparison.json) · [Original image manifest](source-manifest.json) · [Checksums](SHA256.txt)

## Review scope and limits

The C12 plan permits refresh or role/browser switching. This execution covers hard reload plus CLERK/OWNER switching; it does not claim a second-browser run. API rereads support backend persistence, not direct DB inspection, server restart durability, concurrency or API bypass protection. Frontend/backend deployed commit SHAs were not captured, and the evidence commit must not be treated as an application deployment SHA.

Most business actions were performed in the live browser UI. The rejection draft was initially created through the real parse API using the CLERK session, then edited, submitted and rejected through the UI. The role-change API comparisons use separate authenticated GETs. The nine API files are redacted structured captures with HTTP status/request IDs, not byte-for-byte raw HTTP dumps.

Only synthetic C12 test data is included. Tokens, phone/contact values, private token-file paths, unrelated approval queues and execution scripts are excluded. PNGs preserve the original screenshot bytes. One authorized synthetic DO intentionally deducted one bag; the rejected draft generated no DO. Reserved C06 samples were not modified. C10/C13 evidence and their unresolved issues are outside this PR.

Zhou: please review the linked original screenshots and API captures, confirm the checkpoint results and accepted limitations, and record the independent outcome on this PR. Until that outcome is recorded, `independent_review` remains `PENDING`. This PR is evidence only; no application code or deployment changes are included.
