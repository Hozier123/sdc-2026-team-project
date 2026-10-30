# C09 — T2 order workflow and tenant isolation

**Status: manual UI sequence completed; independent review by Zhou is pending.** This evidence does not constitute independent signoff or backend/DB verification.

On 31 October 2026 (MYT), Ye exercised the live API through the public frontend displaying v1.4.0. The T2 workspace was Kilat Hardware & Cleaning Supplies, using the order clerk role. The original 12 screenshots are included so the reviewer can inspect every checkpoint directly on GitHub.

## Observed workflow

- Kedai Kilat 01 (Tier A): `Liquid soap 2 btl 1L` created saved version 1. The UI showed 2 btl at RM12.00, total RM24.00, stock 40, and no blocking checks.
- Approval produced `DO_20261030_7ACFA8AF`, attributed to `USR_T2_CLERK`, bound to version 1 and displayed read-only. The local display date was 31 October; the DO identifier contains `20261030` and is preserved exactly as observed.
- The current-order trail showed Approve and Inventory deduct at 02:47 MYT. A fresh unapproved draft read stock 38: a UI comparison of 40 → 38 for the two-bottle order.
- `Liquid soap 2 btl` left 1L and 5L candidates unselected and required a pack-size decision. Their displayed Tier A prices were RM12 and RM45. A separate same-day order check also blocked approval.
- Both auxiliary drafts were closed with explicit test reasons and were not approved during this sequence.
- After reconnecting as T1 (Sinaran Food Supply), direct navigation to both the T2 original order and its DO displayed `RESOURCE_NOT_FOUND`, without rendering the resource contents.

## Review material

- [Checkpoint-to-screenshot map](CHECKPOINTS.md)
- [Structured observations and limitations](acceptance.json)
- [Original screenshot manifest](source-manifest.json)
- [Checksums for every other file in this directory](SHA256.txt)

Original approved draft: `DRF_60F98F66474843FC9D5251DC5224527D`.

Browser entry point: https://hozier123.github.io/sdc-2026-team-project/

## Limits and review questions

The deployed frontend and backend commit SHAs were not captured. The source commit for this evidence PR must not be treated as the deployed application commit. No raw API responses, HTTP status captures, DB queries, provider traces, concurrency tests, or API bypass tests were collected. The UI label “AI extraction” is recorded without claiming independently verified LLM execution.

The audit dialog only lists field changes. Since this order had no field edits, it did not expose a complete SKU/pack snapshot. The 1L original input, RM12 price, stock comparison and separately displayed 1L candidate are consistent, but do not directly prove the approved order's stored SKU. The DO line description omits the pack size. Please state this evidence boundary explicitly in the independent review and request supplemental evidence if necessary.

Zhou should record the review outcome against this PR, including any remaining evidence gaps. Until that review is recorded, C09 remains pending independent acceptance.
