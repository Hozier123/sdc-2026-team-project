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

## Public deployment and execution

On 2026-10-31 UTC+8 the fix was deployed as Replit **9cff61ed**, Published/Live with all
five stages successful. Application source baseline is `9dfee3382b6191adb314c09bbe8ff779eff9ddac`
(PR #79); main at publication was `f3110d068561be5fff686a799467277b6e9ec1e4` with documentation-only
changes since that application commit. Compared with the prior `555f0fa` application baseline,
only `backend/app/approvals.py` changes.

Six public HTTPS/Neon scenarios passed: serial direct/owner retries, both four-request races,
two drafts competing for the last stock unit, and replay/change of a rejected decision. The
acceptance ledger maps **34 requests and 194 offline checks**; lock waits were observed for
4/4, 4/4 and 2/2 participants. Stock, delivery orders and approval/deduction audit counts match.
Replit runtime logs for the synthetic draft save/approve/retry explicitly identify 9cff61ed.

The initial full run retained FAIL because C07-05's observation window elapsed before the
requests reached its database lock, although business outcomes were correct. Only C07-05 was
repeated on the same deployment; it passed with both database waiters captured. Five other PASS
cases and that explicit retry form the ledger. A driver identity-field initialization failure
is separately retained. No failed record was overwritten.

Only new C07LIVE synthetic tenants/products/users/drafts were written; no existing tenant data,
reset/delete/migration or model/GPU calls. Drafts are explicit fixtures followed by real public
save and approval actions. Runtime environment recovery preserved the original build/run,
ports, CORS and provider/model settings; the deployment configuration reference is
[replit-c07-deployment.toml](replit-c07-deployment.toml).

See [online acceptance](../../evidence/e2e/c07/2026-10-31/online-acceptance.json),
[C07 status](c07-status.md) and [runbook](c07-runbook.md). He-side online execution is complete;
Zhou's independent online review is pending. The prior local P2 signature does not cover the
new online version. C07-06 fault rollback remains the isolated main-candidate/CI proof; no fault
was injected into the shared public service. Browser clicks, TEST32 and AI accuracy are excluded.
