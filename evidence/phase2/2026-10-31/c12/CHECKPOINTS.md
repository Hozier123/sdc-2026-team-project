# C12 checkpoint map

Execution PASS; independent review by Zhou is PENDING. All timestamps above are original backend UTC values with explicit MYT conversion.

| Checkpoint | Original screenshot | Backend capture | Observation |
| --- | --- | --- | --- |
| Fresh approval baseline | [c12-before-approval.png](screenshots/c12-before-approval.png) | [JSON](api/c12-approved-draft-before.json) | Kantin Aman, v1, Milo 1kg, 1 bag, RM18; current live saved draft. |
| Fresh DO and actor | [c12-approved-do.png](screenshots/c12-approved-do.png) | [JSON](api/c12-do-clerk-initial.json) | DO_20261030_D8ED6398; USR_T1_CLERK; RM18; bound to saved v1. |
| Approval log before reload | [c12-approval-trail-clerk.png](screenshots/c12-approval-trail-clerk.png) | [JSON](api/c12-approval-audit-clerk.json) | APPROVE and INVENTORY_DEDUCT: USR_T1_CLERK / CLERK, 2026-10-30T22:37:57.018398Z = 31 Oct 06:37:57 MYT. |
| Hard reload and OWNER readback | [c12-approval-after-reload-owner.png](screenshots/c12-approval-after-reload-owner.png) | [JSON](api/c12-approval-audit-owner-after-reload.json) | Same events after browser reload, reconnect as OWNER and reopen the DO; see browser-observations.json for reload gate and role identity. |
| Fresh rejection result | [c12-owner-rejected.png](screenshots/c12-owner-rejected.png) | [JSON](api/c12-rejection-owner-initial.json) | Owner rejection APR_03CD078FA6B740D89903D80968052FA6, decided_by USR_T1_OWNER, decided_at 2026-10-30T22:43:39.584808Z; reason retained. |
| Owner rejection activity | [c12-owner-rejection-log.png](screenshots/c12-owner-rejection-log.png) | [JSON](api/c12-rejection-activity-owner-initial.json) | Current-order OWNER_REJECTED, requester and saved-version events with actors, timestamps and rejection note. |
| Hard reload and CLERK readback | [c12-clerk-rejection-log-after-reload.png](screenshots/c12-clerk-rejection-log-after-reload.png) | [JSON](api/c12-rejection-activity-clerk-after-reload.json) | Same activity IDs, actors, timestamps and payloads after reload and reconnect as CLERK; see browser-observations.json. |
| Closed draft after reconnect | [c12-open-closed-draft-after-reload.png](screenshots/c12-open-closed-draft-after-reload.png) | [JSON](api/c12-closed-draft-clerk-after-reload.json) | REJECTED / Closed, termination reason preserved, do_number null; no write action shown. |

The initial rejection draft is captured in [its parse response](api/c12-rejection-draft-created.json). [Persistence comparison](persistence-comparison.json) asserts identical approval events and identical rejection activity across roles. These are separate authenticated reads of real backend records, not independent reviewer signoff. All nine response captures were HTTP 200. Review status must be updated only after Zhou provides a conclusion.

Limits: no second-browser, DB inspection, backend restart, concurrency, deployment-SHA binding or API bypass claim. The in-memory session intentionally requires reconnection after reload. Phone/contact fields are redacted. The original screenshots are unchanged and individually hashed.
