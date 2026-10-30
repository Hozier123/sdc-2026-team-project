# C02 Pack-Size Ambiguity Acceptance Record

## Result and scope

- Result: PASS for this manual browser run of the plan's C02 business scenario.
- Execution date and timezone: 2026-10-30, UTC+08:00.
- Execution and review: the operator used the public frontend and supplied screenshots of successive steps. The operator and assistant reviewed the results together.
- Frontend: the production GitHub Pages workspace, displaying version 1.4.0.
- Backend: real API connection as reported by the operator; historical extraction mode FALLBACK.
- Test data: synthetic T1 business data, customer Warung Sinar, CLERK role.
- Frontend deployment SHA, backend deployment SHA, raw HTTP responses, and request IDs: not captured during this run.
- This record covers manual C02 business acceptance. It is not a formal private TEST32 run. Independent manual UI review by Zhou passed on 2026-10-31; see [review record](independent-review.json).

## Order details

| Field | Observed result |
| --- | --- |
| Original input | `Milo 2 bag` |
| Draft ID | `DRF_1A40577F823E44C2A18F5E75F7E957A7` |
| Saved draft version | v2 |
| Confirmed SKU | `SKU_MILO_1KG` |
| Pack size | 1kg |
| Quantity and transaction unit | 2 bag |
| Customer tier | A |
| Unit price | RM18.00 / bag |
| Order total | RM36.00 |
| Delivery order | `DO_20261030_71A20EE4` |
| Confirmed match source | `MANUAL_SELECTED` |
| Remember-phrase option | Not selected |

## Steps, expectations, and observations

| Step | Expected behavior | UI and audit observation | Result |
| --- | --- | --- | --- |
| Create a draft without a pack size | Offer valid pack-size candidates and block approval | The 1kg and 2kg candidates were both unselected. The page showed 1 pending check, Which pack size?, and Resolve checks. | PASS |
| Select 1kg without saving | Keep the unsaved-change protection active | Quantity remained 2. The page showed Unsaved changes and Pending save; approval was disabled. | PASS |
| Save the manual selection | Return a saved version, resolve the pack-size blocker, and calculate the price | The page showed Saved v2, Blocking checks clear, and Ready to approve. Unit price was RM18.00, total was RM36.00, and approval became available. | PASS |
| Approve the saved draft | Generate a delivery order from the saved contents | A read-only approved delivery order was generated: 2 bag x RM18.00 = RM36.00, bound to draft version 2. | PASS |
| Inspect field changes | Trace the confirmed SKU, pack size, and manual selection | SKU changed from Not specified to SKU_MILO_1KG. Pack size was 1kg. Match source changed from RAPIDFUZZ_FALLBACK to MANUAL_SELECTED. | PASS |
| Inspect the approval trail | Associate the save and approval with an actor and timestamps | Save lines was recorded at 21:52; Inventory deduct and Approve at 21:55. All showed the synthetic actor USR_T1_CLERK. | PASS |

## Evidence handling

This public archive contains the manual acceptance summary, structured result, and hashes of the original screenshots. The six original screenshots are retained locally and are not included in the public archive. Readers cannot inspect the original images from this directory alone. The public files contain no session tokens, API keys, private test answers, or absolute local filesystem paths.

## Observed presentation improvement

The delivery order shows the product name without the 1kg pack size. The change record confirms the correct final SKU and pack size, so this does not block C02 acceptance. A separate UI improvement can add the pack size to the delivery-order item description.

## Evidence limitations

The screenshots show the sequence of UI blocking before saving, approval becoming available after saving, and delivery-order generation. No direct API request was made to attempt to bypass the unsaved-change protection. An inventory-deduction log entry alone does not establish the actual database stock delta or protection against duplicate deduction; those require separate verification in scenarios such as C01/C07. Archiving this evidence did not repeat the order, modify stock, reset the database, or change application code.

## Archive files and verification

- [Structured acceptance result](acceptance.json): scope, individual observations, and fields not captured.
- [Private-source image manifest](source-manifest.json): filenames, byte sizes, and exact-byte SHA-256 hashes of the privately retained original screenshots.
- [Directory checksums](SHA256.txt): exact-byte SHA-256 hashes of the public files, excluding the checksum file itself.

Original-image hashes bind the record to privately retained sources; they do not mean the images have been published or replace inspection of those images. This directory's `.gitattributes` disables line-ending conversion. `SHA256.txt` covers the exact bytes of this directory's public files and is separate from existing checksum lists elsewhere in the repository.

## Independent review — 31 October 2026

**PASSED — Zhou, manual UI scope.** The reviewer reported 6/6 original screenshots and 33/33 supplemental checks verified. The reviewed PR head and merge SHAs are preserved in [independent-review.json](independent-review.json).

- Original 30 October HTTP responses and request IDs were not captured.
- Supplemental audit response was a read-only reread on 31 October, not an original-run HTTP capture.
- Post-approval stock was not measured.
- Manual UI acceptance does not prove API bypass protection.

Repository evidence reported by the reviewer: frontend v1.4.0 refs `f8ff1d7` / `94f0a6e`; backend refs `555f0fa` / `72258e1f`. These are repository references, not newly captured historical deployment SHAs. The supplemental synthetic phone number is internal-only and is omitted from this public update. The DO description issue remains P3.
