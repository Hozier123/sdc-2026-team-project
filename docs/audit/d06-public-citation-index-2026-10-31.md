# D06 Public Citation Index

Updated: 2026-10-31. Status: **CLOSEOUT_DRAFT / PENDING_ZHOU_REVIEW**.

This is a public-safe subset of the local 29-row working index, not a publication of that private index. It adds no experiment, signature, participant result or claim of complete acceptance. Existing reports retain their authors and limits; Kilo checked references and selected bytes, not the underlying business flows. Zhou's acceptance of this revised index and Zhan's receipt are **NOT_CONFIRMED**.

Identity clarification: on 2026-10-31, the user explicitly confirmed that they are Zhou Jingxi and own GitHub account `Hozier123`. This corrects the earlier role inference from the team plan. Identity confirmation and permission to upload documents do not themselves constitute a new evidence sign-off.

## Citation Scope

Sources below refer to evidence already present at repository revision `e0094f573ab00dde05402bc67a26b15f9d5d9f01`. Later code changes do not retroactively validate these runs. Local-only records without public evidence are not reproduced as independently verified public results.

Final frontend handoff is a separate later observation: the live [release.json](https://hozier123.github.io/sdc-2026-team-project/release.json) identifies v1.5.2 / source `2a313fb534bf6c17a5ac6ec295d9dfd5ad2f37ac`, published `2026-10-31T07:51:48.277129+00:00`, with AI OFFLINE at verification and no backend redeployment. The workbench defaults to browser-only LOCAL DEMO; Connect API and private role sessions are required for real backend use. See [D01 final frontend handoff](../handoff/d01-data-status-2026-10-31.md#final-frontend-handoff). Earlier B06/F05 v1.5.1 records are historical, not the current frontend release. The release file was read, but its test counts/resource hashes were not independently rerun/recomputed for this publication; `/readyz` 200 is not model or workflow acceptance.

| Area | Source | Permitted interpretation | Limits |
| --- | --- | --- | --- |
| D01 | [Data version and received baseline](../handoff/d01-data-status-2026-10-31.md) | SNAPSHOT_RECEIVED / FILE_VERIFIED; private ZIP and 18/18 internal hashes matched | Owner acceptance pending; external seed equality and per-order stock attribution not independently checked; not full business rescoring |
| D02 | [Backend guard record](d02-uom-blocking-2026-10-31.md), [PR #91](https://github.com/Hozier123/sdc-2026-team-project/pull/91) | DONE_WITH_KNOWN_LIMITATIONS; merged backend guard | UOM remains 24/31 with seven model-side gaps; not an AI accuracy rerun |
| PR91 deployment, local index row 29 | [Deployment report](../ops/pr91-deployment-verification-2026-10-31.md), [guard summary](../../evidence/deployment-verification/2026-10-31-pr91/live-guard-summary.json) | Existing execution report, pending Zhou's acceptance for this new citation | FALLBACK; one synthetic draft; not B05, TEST32, D05 or model-quality validation |
| C11 | [Closeout](../ops/c11-closeout.md), [acceptance](../../evidence/e2e/c11/2026-10-31/acceptance.json) | Repository records SIGNED_OFF / MERGED; form index ZR-C11-20261031-01 | Checks 8/9 are limitations; historical local review/repack timing remains unresolved; not TEST32/Gate A |
| C04 | [Retained r3 review](../../evidence/e2e/c04/2026-10-30/reviews/01-Zhou-review-r3-2026-10-30.md) | Use the sourced r3 report | Do not cite the unsourced r4 hash; no change to the original acceptance |
| C06 | [Public export boundary](../../evidence/e2e/c06/2026-10-31/PUBLIC_EXPORT.md), [acceptance](../../evidence/e2e/c06/2026-10-31/acceptance.json) | Existing scoped API/DB evidence | Public package verification does not prove that the private signed ZIP was independently rehashed |
| C09 / C12 | [PR #100](https://github.com/Hozier123/sdc-2026-team-project/pull/100), [PR #102](https://github.com/Hozier123/sdc-2026-team-project/pull/102) | OPEN / APPROVED at the status check; retain individual review limits | Hozier123 is Zhou's account per explicit user confirmation; these historical approvals do not sign off this new index; not merged evidence at that check |
| Formal TEST32 | [Historical manifest](../handoff/2026-10-24-data/TEST32_FREEZE_MANIFEST_2026-10-24.md), D01 update above | NOT_RUN; 0/34 formal executions in the current review record | Isolated workflow evidence is not a formal complete batch |
| D05 | Prepared protocol; no participant records | PREPARED / NOT_RUN | No sample, median completion time, accuracy or benefit figure; do not substitute developer demos or automated runs |

The private working index retains C13 FAIL, C10 PARTIAL and separate old/new workflow records. This public subset does not promote those records to PASS or reproduce private case expectations. Unresolved historical execution/approval timestamp ordering remains a limitation, not proof of either compliance or misconduct.

## Deployment Evidence Boundaries

The existing PR91 report binds application source `520556cd64a7e6e6a17dfe84d0cdd386d0fef94e` to Replit `5cae3434`. It reports 67 local tests, 16 checks over one synthetic draft/6 HTTP requests, and 58 checks over 18 GET requests on each side of the release. These are different denominators and must not be summed into a single pass count. The guard run finished at 2026-10-31 14:44:20 UTC+8; the post-release read-only check finished at 14:44:43. These are existing technical records, not D05 participant timing.

For five JSON files, repository raw-byte SHA-256 values differ from the published `sha256.json`; converting their LF text to CRLF in memory reproduces all five listed hashes. Raw repository matching is **0/5**, while the CRLF representation matches **5/5**. No source files were rewritten to hide this difference. Images and private raw HTTP were not reverified for this update.

Paths below are relative to [the deployment evidence directory](../../evidence/deployment-verification/2026-10-31-pr91/).

| File | Repository LF raw-byte SHA-256 | Existing manifest / CRLF SHA-256 |
| --- | --- | --- |
| live-guard-summary.json | `38bf2656046bbbc3e027d9bf34c8561c6499e79325fbc4eee206a3b7587a5122` | `2227479fbd5abf38919f42f7cb401f3885710fba60705ff473c1328efbb8d0e6` |
| local-validation-summary.json | `bda6b550fa35979e5fe1dc2a5b39c2bbb85f8d286a7b935655664918a9a6b8c1` | `0df93e53cef3bea21612490d7489f2492d2f7af07001271c725c55a93c82ea4d` |
| post-release-read-only-summary.json | `2d10a259566d8236bbc0251bd54ffd46f75d1e1f0b22a4942a229da47dc6bd89` | `4512a393215ca4d33da875cfe75955f3dd9afda7a1c3cab248c48e591a4eb347` |
| pre-release-read-only-summary.json | `d68c951e7788b7611b99667a9b8fad608e70d94cdbd16de0d508ad5074cc71d2` | `b66ece1b5532aef88758a87501f48b363b343cc008908b3d3786f3607183fcc6` |
| release-manifest.json | `87b4eb3766e91421ce6b078e9e89f2db7e3181460dff1817ef22e16683dd5618` | `e1505db8e53e930f3932128f6c359ed01c2711a3141991988035aee4bdb8e8e5` |

## Review Gate

- Zhou must confirm the new citation scope, especially the deployment row; publication or a GitHub approval is not a substituted business signature.
- Zhan should record receipt of the confirmed revision before incorporating new claims in final materials.
- Existing authorized claims remain limited to their original report, version and environment. Missing artifacts, unverified timing and unsigned additions remain explicitly restricted.
- No private answer keys, frozen inputs, per-case expected answers, local absolute paths, credentials or private packages are included here.
- No claim of time savings, replacement of human work or real-SME validation is supported by this index.
