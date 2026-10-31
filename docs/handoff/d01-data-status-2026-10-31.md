# D01 Data Version Status

Updated: 2026-10-31. Status: **PARTIAL / SNAPSHOT_PENDING**.

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

## Snapshot Gap

### Final Frontend Handoff

The live [Pages release record](https://hozier123.github.io/sdc-2026-team-project/release.json), read on 2026-10-31, identifies frontend **v1.5.2**, source `2a313fb534bf6c17a5ac6ec295d9dfd5ad2f37ac`, published at `2026-10-31T07:51:48.277129+00:00`. It links `asset-manifest.json`, records backend application source `520556cd64a7e6e6a17dfe84d0cdd386d0fef94e`, and states `backend_redeployed=false` and `ai_state_at_verification=OFFLINE`. Reading this metadata is not a new resource-hash or business-flow verification.

Per Zhou's final handoff, the [workbench](https://hozier123.github.io/sdc-2026-team-project/#/workspace) starts in **LOCAL DEMO**, using browser-local synthetic data without a backend connection. Real API checks require **Connect API**, the Replit FastAPI base `https://kiraorder-api.replit.app/api/v1`, and privately supplied role sessions; the backend uses Neon PostgreSQL. Do not publish session tokens. A reported `/readyz` HTTP 200 proves neither model readiness nor complete workflow acceptance.

Use the repository's [Judges Quick Start Guide](https://github.com/Hozier123/sdc-2026-team-project#judges-quick-start-guide) for demonstration steps. The guide is operational documentation, not proof that a participant study or formal evaluation was run.

B06/F05 observations of v1.5.1 and earlier notes saying v1.5.2 was not published remain historical snapshots. The new release binding does not upgrade old screenshots/tests or provide the missing current database snapshot below.

No complete same-environment, same-time snapshot of catalog, tier prices, inventory and rules has been delivered for D01. Existing evidence has narrower coverage:

- Frozen seeds describe initial data, not a database after business writes.
- B05 material contains partial inventory/alias baselines and table fingerprints, not all four required data groups.
- The [PR91 post-release summary](../../evidence/deployment-verification/2026-10-31-pr91/post-release-read-only-summary.json) contains checks, not row-level exports.
- [B06 source observations](../../evidence/b06/2026-10-31/source-observations.json) describe an earlier deployment/configuration observation, not a current consistent database snapshot.

Zhou must identify the target environment, tenants, application revision and sampling point. An authorized environment custodian must supply existing suitable artifacts or a read-only consistent export, with capture time, schema/field coverage, row counts, tool revision and raw-byte hashes. Credentials, user authentication records and real contact details must be excluded. Do not reset production, change seed/Gate 0, broaden permissions, or combine different environments to fill the gap.

Until that delivery and review occur, D01 remains partial. See the [D06 public citation index](../audit/d06-public-citation-index-2026-10-31.md) for publication boundaries.
