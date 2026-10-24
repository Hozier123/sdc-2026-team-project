# Measurement evidence archive

Independent Gate 0 confirmation materials are archived here. Backend foundation acceptance records are in [backend-foundation/README.md](backend-foundation/README.md). These records are not business-effectiveness evaluations; do not prefill KPIs or outcome figures.

Archive materials as they are actually produced, including:

- Baseline definitions, freeze records, and raw manual timing data.
- Tool-assisted timings and raw first-use test records.
- Offline evaluation results and frozen-set hashes.
- Test environments, samples, measurement methods, and limitations.
- Selected demonstration or test screenshots.

Retain original records and distinguish targets, assumptions, and measured results. All business samples must use team-created synthetic data. Do not include real customer records, sensitive personal information, or platform secrets.

Formal proposals, tools declarations, and platform-use proofs belong in the repository-root `submission/` directory. This directory holds supporting experimental records.

The four-party Gate 0 confirmation materials are in this directory's `gate0/` subdirectory; the frozen specification and machine contracts are in the repository-root `gate0/`. Evidence may be appended without altering the frozen baseline.

## Official AI UOM known gaps (7 gaps / 31 lines)

The official 23-case AI-only run on `db6f0ce` contains 31 lines. UOM is 24/31 and its status is `CURRENT_WITH_KNOWN_UOM_GAPS`; it is not an all-pass UOM result.

- `KNOWN_UOM_INJECTION_GAP` (3 gaps): DEV-07 `botol`, DEV-13/27 `pail`. The T1 seed already contains botol/pail aliases, but the adapter reads only the H1 lexicon / `tenant_uom_extensions`, not database `uom_aliases`.
- `BULK_KG_REGRESSION` (4 gaps): PR #46's pack-size exclusion incorrectly excludes bulk `kg` in DEV-01/05/11/33, producing `kg→None`. This is a new regression, not a data error.

For this iteration, do not change the seed or advance Gate 0, and do not claim that all UOM checks pass. Future code fixes have two parts:

1. Inject tenant `uom_aliases` for botol/pail.
2. Distinguish bulk-product `kg` from pack-size `kg` for the 4 bulk-kg cases.

Rerun all 23 cases and replace the official evidence after the fixes.
