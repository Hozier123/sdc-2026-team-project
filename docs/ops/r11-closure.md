# R11 End-to-End Trilingual Regression — Closure Record

**Status: `CLOSED` / `NOT_RUN` — the regression was not executed in this round.**

This is an independent closure record for R11. It exists so that R11 has its own documented outcome rather than appearing only as a "pending" or "NOT_RUN" line inside other materials. Closing a task is not the same as passing it: R11 is closed with the status `NOT_RUN`, because no case was executed and no result exists.

Nothing in this document supports a passing claim for R11, for any E-case, or for overall readiness.

---

## 1. What R11 was meant to verify

R11 is the end-to-end trilingual regression: take the answers frozen in advance (the gold standard), run them against a candidate build with a real model, and score each case as `PASS` / `FAIL` / `BLOCKED` / `NOT_RUN`.

| Aspect | Requirement |
|---|---|
| Cases | main trilingual order, single-language variants, held-out variants, ambiguity, missing price, unit conflict, unknown product, missing quantity, price condition, permission/version/tenant boundaries, untouched-family regression |
| Evidence per case | new run id, real request and response, `actual_ai_mode`, raw model output, page evidence where applicable, before/after state for approval cases |
| Version binding | the scored commit and the release commit must be identical |
| Scoring | performed by the independent reviewer against the pre-frozen answers; not by the implementer |

Reference: the alias scope and the verification that *was* completed are documented in [`docs/trilingual-alias-and-verification.md`](../trilingual-alias-and-verification.md).

---

## 2. Prerequisite status at closure time

| Prerequisite | Status | Note |
|---|---|---|
| Gold standard frozen and independently accepted | **Met** | answers locked before execution; unchanged since acceptance |
| Alias table loaded into a candidate database | **Met** | six family-level aliases loaded; see the R06 archive |
| Alias data reaching a real model request | **Not met** | prompt change never deployed; no accepted live capture |
| Technical sign-off for that model path | **Not met** | not signed |
| Backend matching and save rules | `PASS_WITH_LIMITATIONS` | evidence produced in fallback/extractor-fixture mode, not model mode |
| Frontend review and manual confirmation | `PASS_WITH_LIMITATIONS` | extractor was a fixture; recorded as candidate-only, not live |
| Candidate version frozen for release | **Not met** | no release candidate was frozen |
| Real model provider available | **Not met** | all frontend/API observations in this round recorded `ai_mode=FALLBACK` |
| Page + real API path available | **Not met** | frontend and API were shut down before closure |

With the prerequisites above unmet, executing R11 would not have produced admissible evidence: it would have produced fallback-mode output, which is explicitly not acceptable as model evidence.

---

## 3. Why it was not executed

The round was frozen by decision, not by accident:

- the candidate API was stopped and its credentials were cleaned up;
- the candidate source and database were left as they were, without a release;
- no fallback-mode or fixture-mode observation was promoted to an R11 result.

The freeze was reconfirmed when R11 closure was raised, so `NOT_RUN` is the recorded outcome by decision rather than a transient environment failure.

Two specific near-misses are worth recording, because both look like passes and are not:

1. **A three-line order that matches the gold standard exactly, produced in `FALLBACK` mode.** The values (three line items, correct SKUs, correct total) matched the expected answer, but the run was not a model run. It cannot be counted as the main case.
2. **A missing-price scenario that blocked correctly.** It showed that a later candidate revision no longer auto-selects the priced variant when one variant has no configured price. That is a useful finding about backend behaviour, but it is not the formal missing-price case, which requires model mode plus approval-blocking verification.

---

## 4. What R11 does and does not establish

**Establishes**

- R11 was not executed; no case has a result.
- The prerequisites were not all met at closure time.
- The absence of results is documented rather than implied.

**Does not establish**

- That trilingual input works end to end.
- That the model recognises the added surface forms.
- That any E-case passes or fails.
- That the system is ready, deployable, or deployed.

---

## 5. Boundary with neighbouring work

| Item | Status | Relationship to R11 |
|---|---|---|
| Alias table (scope, load, guard-layer behaviour) | accepted; loaded to candidate | provides vocabulary, not model evidence |
| Gold standard | frozen and accepted | supplies the answers R11 would score against |
| Backend matching and save rules | `PASS_WITH_LIMITATIONS` | covers rules in fallback/fixture mode |
| Frontend review | `PASS_WITH_LIMITATIONS` | candidate-only, not live |
| Interface contract item (R08) | not closed | explicitly waits for R11; this closure does not close it |
| Release | not performed this round | no release candidate to bind |

R08 remains open. Closing R11 as `NOT_RUN` does not close R08 and does not substitute for it.

---

## 6. Conditions to re-open R11

R11 can only be re-opened as a new run, with a new run id. The minimum set:

1. Restore the candidate database and candidate API; confirm the target database identity.
2. Restore a real model provider, confirm model mode can be reproduced, and keep credentials out of all artifacts.
3. Deploy the alias-aware prompt change to the candidate build and record the exact commit.
4. Restore the frontend and confirm the origin/CORS configuration.
5. Freeze the candidate version; record the commit that will be scored.
6. Prepare the approval-case preconditions, including inventory before/after and the agreed approval cap.
7. Execute case by case, one new run id, recording `actual_ai_mode` and the raw model output.
8. Score against the pre-frozen answers; do not adjust answers to match observed output.

Any result produced before the answers were frozen, or in fallback mode, or under a different commit than the scored one, is not admissible.

---

## 7. How to read claims about this work

**Supported**

- R11 is closed with status `NOT_RUN`.
- No end-to-end case was executed this round.
- The alias table itself was loaded and verified at the data and guard layers.

**Not supported**

- "R11 passed" or "R11 partially passed" — zero cases were executed.
- "Trilingual end-to-end verified".
- "Any E-case passed".
- "The model consumes the alias table".
- "Ready for release".

---

## 8. References

- Alias scope, verification and limits: [`docs/trilingual-alias-and-verification.md`](../trilingual-alias-and-verification.md)
- Alias patch (byte-identical to the executed revision): [`data/patches/r06/`](../../data/patches/r06/)
- Candidate load archive: [`docs/ops/r06-archive.md`](r06-archive.md)
