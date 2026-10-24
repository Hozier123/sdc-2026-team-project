# Data handoff snapshot · 2026-10-24

This directory preserves the data-side handoff snapshot from 2026-10-24 so the team can check family-scoring scope, v1/v2 acceptance order, AI-only scope, and the available v1 run records.

**This is a handoff snapshot, not a contract or answer key, and not evidence of completed production acceptance.** The contract is the repository's frozen [gate0/](../../../gate0/). This directory changes no contracts, database, seed, or business implementation. Sign-offs, TODOs, and unfinished items in the source documents reflect their preparation dates, not the complete acceptance status of current main.

> **Historical evidence notice:** `dev41_ai_only_v1_prod_2026-10-24.json` was generated with `app/ai@657ad5d`.
> The source handoff records that main `db6f0ce` contains PR #46's UOM fix. UOM errors in this snapshot are historical results and must not be used as current quality conclusions. At handoff preparation, the 23-case AI-only rerun on `db6f0ce` was pending.

## File index

| File | Purpose and boundaries |
| --- | --- |
| [T1_family_scoring_signoff_2026-10-24.md](T1_family_scoring_signoff_2026-10-24.md) | Sign-off snapshot for family-scoring scope B; the original states its PR/commit basis and sign-off boundaries. |
| [v1_v2_acceptance_checklist_2026-10-24.md](v1_v2_acceptance_checklist_2026-10-24.md) | Fixed inputs, v1/v2 comparison order, scoring dimensions, and preregistered v2 adoption criteria; not a completed acceptance report. |
| [dev_41_parse_scope.json](dev_41_parse_scope.json) | r2 scope record labeled `DRAFT_SCOPE_ONLY`; separates 23 AI-only cases, 3 resolver-only cases, and remaining workflow cases. It contains no answer key. |
| [dev41_ai_only_v1_prod_2026-10-24.json](dev41_ai_only_v1_prod_2026-10-24.json) | Snapshot of the available v1 run with 23 results; `input_status=DRAFT_NOT_ANSWER_KEY`, `accuracy=NOT_COMPUTED`, and `eligible_for_quality_claim=false`. Model outputs are not standard answers. |

The scope file is the local `ai-eval-scope-2026-10-24-r2` version; its SHA-256 matches the acceptance checklist. The result file's 23 case IDs match that scope's `parse_eligible_case_ids`. Resolver-only DEV-02, DEV-08, and DEV-23 are excluded from the AI-only denominator.

## Usage

1. Read the family sign-off boundaries and acceptance checklist, then verify the scope file.
2. Run records are only for tracing outputs and runtime parameters at that time. This archive did not rerun the model, compute accuracy, or decide whether to adopt v2.
3. Source documents may reference inputs, answer keys, or evidence not published here. Those references do not mean the files were uploaded or authorize loading answers from this directory or substituting them for the formal contract.
4. Do not treat outputs in this directory as ground truth, frozen evaluation answers, or an application runtime data source.

## Source-file integrity

The following four source files retain their original UTF-8 content and line endings. Hashes identify this snapshot; they do not establish completed business acceptance.

| File | SHA-256 |
| --- | --- |
| `T1_family_scoring_signoff_2026-10-24.md` | `21DF0911FE4B225F202099F1B1C14E1FCEAA7880D4365BCFCBAB029A9FE02065` |
| `v1_v2_acceptance_checklist_2026-10-24.md` | `E296DF9B6CB22374FB6CE8A733BCEDA7A46FC92AEBB669F435AD255C124153BA` |
| `dev_41_parse_scope.json` | `6AE86B6B4CE58EB546A27EBDAE2E9C3F2608040A332836E47B802F0659F128F0` |
| `dev41_ai_only_v1_prod_2026-10-24.json` | `60A28A7CDC3D5E90F0BCFD584F79136BBEB4347942B105187548ECD717350B46` |

The original handoff change contained only the five allowlisted files in this directory. Other inputs, answer keys, private seed data, credentials, and archives were outside that delivery.
