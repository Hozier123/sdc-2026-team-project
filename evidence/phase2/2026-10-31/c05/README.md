# C05 Owner Rejection Acceptance Record

## Result and scope

**PASS for this manual browser run.** The operator created a new C05 order, submitted a below-tier price, confirmed that an empty rejection reason disabled submission, and rejected the request as the owner. The original draft then showed a closed terminal state with the reason preserved. A fresh, unapproved auxiliary draft showed the same stock reading before it was closed with an explanatory note.

Execution: 2026-10-31, approximately 01:42-02:03 MYT (UTC+08:00). The operator performed application actions through the real API session and supplied eleven screenshots. The operator and assistant reviewed the evidence together; no independent reviewer or formal private TEST32 run is claimed.

The displayed frontend version was **1.4.0**, with historical extraction mode **FALLBACK**. Frontend/backend deployment SHAs, raw HTTP responses, and request IDs were not captured.

## Test identity and values

| Field | Observed value |
| --- | --- |
| Tenant and synthetic customer | T1 / Kedai Rasa / Tier B |
| Input | `Milo 2 bag 1kg` |
| Original C05 draft | `DRF_144B527074074DC1A7CE64FDE2E2E559` |
| Submitted version | v2 |
| Approval request | `APR_EC4CFECC0B01471387B9A97CCB817203` |
| Quantity and unit | 2 bag |
| Tier unit price | RM19.00 |
| Requested unit price | RM17.00 |
| Saved total | RM34.00 |
| Decision | Rejected; original draft closed |
| Rejection reason | C05 synthetic test: RM17.00 per bag is below the tier price of RM19.00. Discount declined. |

## Acceptance observations

| Check | Evidence observed | Result |
| --- | --- | --- |
| Low-price submission | Saved v2, RM34.00, Send to owner; then Awaiting owner and submitted-version lock | PASS |
| Required rejection reason | Empty reason field with Reject order disabled | PASS, UI validation |
| Owner rejection | Owner result showed Rejected and the complete supplied reason | PASS |
| Terminal state | Reopening original draft #144B52 showed This order is closed, retained the reason, and displayed no save or approve action | PASS, UI observation |
| No delivery order | Closed original draft showed no generated-DO entry; displayed order trail contained no approval or DO-generation event | PASS within UI evidence scope |
| Audit trail | Draft version created at 01:45; owner approval requested by USR_T1_CLERK at 01:46; owner rejected by USR_T1_OWNER at 01:53 with the reason visible | PASS |
| Stock unchanged | Original newly created draft showed 28 bag; separate fresh post-rejection draft also showed 28 bag | PASS, fresh-draft UI comparison |
| Auxiliary cleanup | Stock-check draft #02C1DA was closed with an explanatory reason, without approval | COMPLETE |

## Stock-check method and cleanup

The original C05 draft's initial stock reading was 28 bag. After rejection, the operator created a separate auxiliary draft with input `Milo 1 bag 1kg`, customer Kedai Rasa, and observed 28 bag again. This avoided relying on the saved stock-at-review snapshot of the rejected approval.

Auxiliary draft: `DRF_02C1DA1421DF4237A20FE04CAEF96517`, v1, RM19.00. It was not approved. At 02:03, the page showed Closed and the note: `C05 stock verification completed. Close this auxiliary draft without approval.` The success toast stated that the draft was closed and its activity record preserved.

The comparison establishes equal stock values displayed for two fresh drafts. It is not a direct database inspection or a concurrency/idempotency test.

## Evidence files and privacy

- [Structured acceptance result](acceptance.json)
- [Private-source screenshot manifest](source-manifest.json): eleven original filenames, byte sizes, capture times, and exact-byte SHA-256 hashes
- [Public-file checksums](SHA256.txt)

Original screenshots are retained locally and are not part of the public candidate. Readers cannot inspect those images from this directory alone. No session tokens, API keys, private test answers, or absolute local filesystem paths are included. A source-image hash binds the retained original; it does not mean the image has been published or independently reviewed.

This directory's `.gitattributes` disables line-ending conversion. `SHA256.txt` covers exact public-file bytes and excludes itself.

## Known display issue and evidence boundaries

The legacy owner-review summary still displayed RM0.00 to RM0.00. The actual item price and stored rejection reason showed RM19.00 and RM17.00. This previously observed display issue is tracked in PR #86 and is not silently reported as fixed in the frontend used for this run.

No direct API bypass or repeat-decision attempt was performed. The no-DO result is supported by the closed page and displayed order-specific trail, not a direct read of API `do_number` or database rows. This run does not establish LLM readiness, concurrency behavior, stock idempotency, or private TEST32 acceptance. Publication of this record remains separate from the completed browser run.
