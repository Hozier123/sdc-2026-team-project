# D01 Data Version Status

Updated: 2026-10-31. Status: **SNAPSHOT_RECEIVED / FILE_VERIFIED / PENDING_OWNER_ACCEPTANCE**.

This public summary records version provenance, not a completed evaluation or a live database snapshot. Prepared by Kilo from existing records; it is not a new signature by Zhou or an independent reviewer. The reference repository revision used for the byte checks is `e0094f573ab00dde05402bc67a26b15f9d5d9f01`, not a deployed application revision.

## Seed Provenance

| Object | Version | Git blob bytes | SHA-256 |
| --- | --- | --- | --- |
| [T1 loader](../../data/seed/T1_seed.sql) | KB-T1-20261022-r1 | 52457 | `A7BE80BD8658C376F78065FA370ED9EB4875143B1B501548BB875925CC7ED773` |
| [T2 loader](../../data/seed/T2_seed.sql) | KB-T2-20261022-r1 | 27611 | `134EFDC78DA5889A548CC28AC5C953199B1CBF7C8D6B3C181E7CDE9BD1625464` |
| [Seed manifest](../../data/seed/SEED_MANIFEST.json) | LF repository representation | 1889 | `38E144B9886908F620C61FA477EA40DCD2987A72030A9613D520F459B17502DD` |

The historical manifest copy of 1946 bytes and SHA-256 `788BDAE099DC9AADC173827475616E513563A6408CE88B3C40629125A6BEE582` uses CRLF. Both representations were checked separately; neither seed nor manifest was rewritten. Loader and source SQL hashes are different objects, as documented in the manifest.

## Private Evaluation Assets

Only metadata is published here. Answers, frozen inputs, private scope/scorer files and private evidence remain outside the public repository.

| Object | Recorded status | SHA-256 |
| --- | --- | --- |
| Answer key TEST32-ANSWERS-2026-10-31-v6 | FROZEN, 69050 bytes | `115449D75FAACC7B4891A4DE358F7420AE389A4A26FEE0882ACF1315609BCFEC` |
| Preconditions v6 | CONFIRMED_BY_HE globally; amendment independently reviewed, 4680 bytes | `AF7D7A0EED051A80C23C824A7E343C89653ED2C84E299FE02B3955C700A90BDB` |
| Scope TEST32-SCOPE-2026-10-24-v4 | DRAFT_SCOPE_ONLY / frozen=false | `9FD0BBBA89F2393CB98CAAD7012A52D99D1CE11813E8A7F7E62648CB0BAB90A0` |
| Scorer TEST32-SCORER-2026-10-24-v1 | Price/amount assertions only; not rerun for this update | `004177ABFB8D2ABC41E486D6F52D34D9F72C49EEBDE086841ED7C98A38EB59FF` |

The retained freeze record attributes a v5-to-v6 diff and reverse v4-to-v5 check to Zhan. This is not evidence that all 32 business answer cases were independently rescored. The v5 business spot-check checklist remains unfilled; no boxes or signatures were filled for this publication. Local asset hashes were checked without publishing answer contents or running the scorer.

The [2026-10-24 freeze manifest](2026-10-24-data/TEST32_FREEZE_MANIFEST_2026-10-24.md) is retained as historical v5 metadata. Its pending state is not silently rewritten. Freezing the answer-key amendment does not freeze the D04 scope or prove formal TEST32 execution. Formal TEST32 remains **NOT_RUN: 0/34 executions** in the current review record; 32 logical cases and 34 executions are planned, not completed results.

## Snapshot Handoff

### Final Frontend Handoff

The live [Pages release record](https://hozier123.github.io/sdc-2026-team-project/release.json), read on 2026-10-31, identifies frontend **v1.5.2**, source `2a313fb534bf6c17a5ac6ec295d9dfd5ad2f37ac`, published at `2026-10-31T07:51:48.277129+00:00`. It links `asset-manifest.json`, records backend application source `520556cd64a7e6e6a17dfe84d0cdd386d0fef94e`, and states `backend_redeployed=false` and `ai_state_at_verification=OFFLINE`. Reading this metadata is not a new resource-hash or business-flow verification.

Per Zhou's final handoff, the [workbench](https://hozier123.github.io/sdc-2026-team-project/#/workspace) starts in **LOCAL DEMO**, using browser-local synthetic data without a backend connection. Real API checks require **Connect API**, the Replit FastAPI base `https://kiraorder-api.replit.app/api/v1`, and privately supplied role sessions; the backend uses Neon PostgreSQL. Do not publish session tokens. A reported `/readyz` HTTP 200 proves neither model readiness nor complete workflow acceptance.

Use the repository's [Judges Quick Start Guide](https://github.com/Hozier123/sdc-2026-team-project#judges-quick-start-guide) for demonstration steps. The guide is operational documentation, not proof that a participant study or formal evaluation was run.

B06/F05 observations of v1.5.1 and earlier notes saying v1.5.2 was not published remain historical snapshots. The new release binding does not upgrade old screenshots/tests. The subsequently received database snapshot is recorded separately below.

### Received Data Baseline

The custodian supplied a private baseline package covering catalog, tier prices, inventory and tenant rules for T1/T2. Its recorded transaction time is **2026-10-31 16:41:07.984893 UTC+8**, with WAL LSN `0/260C2E8` and transaction snapshot `102420:102420:`. This supersedes the earlier missing-snapshot status; the package is retained privately and is not included in this publication.

| Tenant | Families | Products | Tier-price rows | Inventory rows | Recomputed snapshot stock | Reported seed stock | Difference |
| --- | --- | --- | --- | --- | --- | --- | --- |
| T1 | 25 | 40 | 80 | 40 | 774 | 795 | -21 across four SKUs |
| T2 | 10 | 16 | 32 | 16 | 446 | 450 | -4 across one SKU |

Read-only package verification found 19 files: **18/18** raw-byte hashes matched the internal manifest excluding itself, and **10/10** snapshot-index hashes and byte lengths matched. JSON/CSV exports, rules, row counts, relationships, uniqueness, A/B price coverage and inventory deltas were internally consistent. All 26 declared quality checks agreed with the independent file checks. No database connection, SQL execution, seed/reset or business rerun was performed.

| Private object | Raw-byte SHA-256 |
| --- | --- |
| Baseline ZIP | `28962718B360C78F6E387FFA00E17D493909ABC081E86E42F9172D3C7014158F` |
| snapshot_T1.json | `81EEBBCF4FF4168D6999E3EE60C27EEB4ECD97743464F3B1277F9E1C161EBE12` |
| snapshot_T2.json | `FBA086D4D5D1D22C9460A6346E963C5CF1CA2E1BF830620203A9134FCDA25995` |
| collection_record.json | `592E6242BCA3B9FF5F7FA7413F78DB75C8ACA1B16898578192F7181A6469A3E3` |
| deployment_binding.json | `2F9FD45B7C42786F7BBD09E09595428238EE7E376ABF9CCCC512A36D1346ACD0` |

The supplied SQL uses a REPEATABLE READ READ ONLY transaction, a transaction-local timeout, six SELECT statements (metadata and five tables), and ROLLBACK. Static inspection found no business writes; it does not prove how the original collection was executed. Shared snapshot metadata is consistent across both tenants. A transaction snapshot is not proof of no concurrent writes throughout collection, and WAL/TXID identifiers are not a restorable backup.

The custodian reports catalog, prices and rules equal to canonical seed. This update independently checked package consistency, **not an external seed comparison** or attribution of stock differences to specific orders. Tenant rules are included; not all platform runtime configuration is represented. Deployment binding relies on prior release records, not atomic runtime attestation during collection. No customer/user export or suspicious credential/contact values were found by heuristic scanning; this is not an absolute secrecy guarantee.

The data-baseline gap is filled at the file-delivery level. Owner acceptance remains unrecorded; this status does not imply formal TEST32 execution, D05 participant results or a new business sign-off. Do not restore stock to seed merely to remove differences. See the [D06 public citation index](../audit/d06-public-citation-index-2026-10-31.md) for publication boundaries.
