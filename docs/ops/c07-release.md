# C07 approval retry release

Owner decisions on an already approved request used to return `409 PENDING_OWNER_APPROVAL`
and a message saying the draft was waiting. The request was safely rejected, but both serial
retries and losing concurrent requests described the wrong state.

Approved requests now return `409 ALREADY_APPROVED`; rejected requests return
`409 DRAFT_REJECTED`. A real pending submission retry still returns
`PENDING_OWNER_APPROVAL`. Order and approval locks, transaction boundaries, delivery creation,
inventory deduction and audit writes are unchanged.

## Validation and acceptance

- Zhou signed the original C07 safety goals at 2026-10-30 17:41 UTC+8 and signed the P2 fix
  at 23:06 UTC+8 for local source/evidence only.
- Original signed fix batch: `c07-20261030T110202Z-6eef77`, 6/6 HTTP/DB scenarios,
  3 existing concurrency tests and 4 terminal replay tests; 129 offline checks.
- Latest-main candidate batch: `c07-20261030T151749Z-c4a6ae`, based on
  `d98658f261c17ebbd5943286e389fe9567843fc2` plus only this C07 change. All six scenarios,
  33 real HTTP requests, three existing tests and four terminal regressions passed again.
- The new test covers both same and opposite decisions after approval/rejection; every
  replay must return the correct 409 error and leave eight business-table snapshots unchanged.
- The local runner creates a separate loopback PostgreSQL cluster and synthetic identities,
  observes real concurrent PostgreSQL lock waits, and stops its services. No GPU or public
  API is used by this local test.

Run `backend/tools/verify_c07_local.py` with `--postgres-bin` and `--output` to reproduce the
isolated checks using Python 3.13 and the pinned backend dependencies.

## Public deployment

Public deployment and version-bound HTTP/DB checks are still pending in this commit.
Record the actual Replit deployment and source version, then verify owner serial retries,
concurrent losers, rejected terminal requests and genuine pending submissions with synthetic
data. Confirm one delivery and one deduction, with no retry writes. Local signatures do not
constitute acceptance of the deployed version, browser clicks, TEST32 or AI accuracy.
