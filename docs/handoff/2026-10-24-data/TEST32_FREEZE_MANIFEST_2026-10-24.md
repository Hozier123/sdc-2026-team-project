# TEST32 Freeze Manifest (2026-10-24)

> 状态：**FREEZE_CANDIDATE_PENDING_GITHUB_APPROVAL**。
> 冻结对象：TEST32-ANSWERS-2026-10-24-v5（离线答案键）。
> 本文件是 public-safe 元数据；答案键全文、seed 私密包、token 不上传 GitHub。

## 1. 冻结对象

- 答案键：`TEST32-ANSWERS-2026-10-24-v5`
- scope：`TEST32-SCOPE-2026-10-24-v4`
- scope review：`TEST32-SCOPE-2026-10-24-v6`
- scorer：`TEST32-SCORER-2026-10-24-v1`
- 计数：32 cases；19 AI-only / 1 resolver-only / 12 E2E-workflow；32 items / 34 executions。
- workflow：12 条 `NOT_RUN`（无 workflow harness）；不得写 E2E 通过。

## 2. 文件哈希

| 对象 | 文件 | SHA-256 | bytes |
|---|---|---|---:|
| `answer_key_v5` | `TEST32_answers_2026-10-24_v5.json` | `1C522AB9F60E05323284E9098E00AEEA7D249584685AD4BDACA5D33ED0907C1D` | 67625 |
| `input_draft` | `frozen_eval_32_draft.json` | `5240B94F24422DCEBB9CAC90E7780FEF6E887B024EEBFD72DB9E97C543653C10` | 10666 |
| `scope_json_v4` | `frozen_eval_32_parse_scope_v4.json` | `9FD0BBBA89F2393CB98CAAD7012A52D99D1CE11813E8A7F7E62648CB0BAB90A0` | 5381 |
| `scope_review_v6` | `TEST32_scope_review_2026-10-24_v6.md` | `EB7EE8F209E13914A44EF995DBA40C798F427D3F4367EA7BA6810C95FC200F97` | 2898 |
| `preconditions_json` | `TEST32_E2E_preconditions_2026-10-24.json` | `8AEC3778C13E8158F582DE92B76944772E1A6DAF96376E4645D7BA3CC89925B0` | 4006 |
| `preconditions_md` | `TEST32_E2E_preconditions_he_2026-10-24.md` | `395BC2AB8A5C6296FFD20134EA57D46E7727A10FB43735A4FDE5AE69D7A12C8E` | 3037 |
| `scorer` | `scoring.py` | `004177ABFB8D2ABC41E486D6F52D34D9F72C49EEBDE086841ED7C98A38EB59FF` | 4921 |
| `scorer_test` | `test_scoring_assertions.py` | `89F9E735B4F553F36FCB43DF382771A208AF990D20A99CBBBE4E402AD6BE3EC3` | 3074 |
| `scorer_selftest` | `TEST32_scorer_selftest_2026-10-24.txt` | `FC94A7EC02B372370C1BE945350A1E1177BD607E5E6F219A6B2DBB7B036A157A` | 359 |
| `verification_csv_v5` | `TEST32_verification_record_v5.csv` | `DD62A744961D6590AE956D5FF5B33769E2F2138259C06C135D9143C84574FF56` | 6078 |
| `v5_package` | `TEST32_review_v5_2026-10-24_PRIVATE.zip` | `1AE2CD48F0121D7A40BCFE336F2EAD5FB259F60740931F855FFB3540E40BECBA` | 33748 |

## 3. 评分口径

- 非空 unit_price_rm / subtotal_rm / expected_total_rm 默认 REQUIRED。
- 只有显式 `amount_assertion=NOT_ASSERTED` 的金额字段跳过；null 不代表系统必须返回 null。
- unit_price_rm 独立评分，不因 subtotal/total NOT_ASSERTED 跳过。
- scorer 回归测试：3/3 PASS。

## 4. 核验状态

- He：v3/v4 结构、字段、tenant mapping PASS；v5 scoring 增量待 GitHub 手动确认。
- Zhan：v4 静态业务复核无新增异议；v5 业务栏待 GitHub 手动确认。
- workflow：12 条 NOT_RUN；没有 harness，不声称 E2E 通过。
- 本 manifest 合并前保持 PENDING；GitHub PR 手动确认并 merge 后，冻结生效。

## 5. 上传约束

- GitHub 只上传本 manifest（可另附 `TEST32_FROZEN_SHA256.txt`）。
- 不上传 `TEST32_answers_2026-10-24_v5.json`、seed 私密包、token、原始测试全文。
- 目标路径：`docs/handoff/2026-10-24-data/TEST32_FREEZE_MANIFEST_2026-10-24.md`。

- 生成时间：2026-10-24T22:37:45+08:00
