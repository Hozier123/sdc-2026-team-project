# 数据交接快照 · 2026-10-24

本目录保存 2026-10-24 的数据侧 handoff 快照，供团队核对 family 计分口径、v1/v2 验收顺序、AI-only 范围与已有 v1 运行记录。

**这是交接快照，不是契约，不是答案键，也不代表完成生产验收。** 契约以仓库冻结的 [gate0/](../../../gate0/) 为准；本目录不改变契约、数据库、seed 或业务实现。原文中的签字、待办和未完成事项属于源文件制作时的记录，不应解读为当前 main 的完整验收状态。

> **历史证据提示**：`dev41_ai_only_v1_prod_2026-10-24.json` 产生于 `app/ai@657ad5d`。
> 当前 main `db6f0ce` 已包含 PR #46 的 uom 修复；本文件中的 uom 错误属于历史结果，
> 不能作为当前质量结论。`db6f0ce` 的 23 条 AI-only 重跑结果待补。

## 文件索引

| 文件 | 用途与边界 |
| --- | --- |
| [T1_family_scoring_signoff_2026-10-24.md](T1_family_scoring_signoff_2026-10-24.md) | family 计分口径 B 的签字快照；原文注明所依据的 PR/commit 及签字边界。 |
| [v1_v2_acceptance_checklist_2026-10-24.md](v1_v2_acceptance_checklist_2026-10-24.md) | 固定输入、v1/v2 对照次序、计分维度与预先登记的 v2 采用条件；不是已执行完成的验收报告。 |
| [dev_41_parse_scope.json](dev_41_parse_scope.json) | r2 范围说明，标记为 `DRAFT_SCOPE_ONLY`；划分 23 条 AI-only、3 条 resolver-only 及其余工作流用例，不包含答案键。 |
| [dev41_ai_only_v1_prod_2026-10-24.json](dev41_ai_only_v1_prod_2026-10-24.json) | 已有 v1 运行记录快照，23 条结果；`input_status=DRAFT_NOT_ANSWER_KEY`、`accuracy=NOT_COMPUTED`、`eligible_for_quality_claim=false`。模型输出不是标准答案。 |

范围文件选用本地 `ai-eval-scope-2026-10-24-r2` 版本，其 SHA-256 与验收清单引用值一致。结果文件的 23 个 case ID 与该范围中的 `parse_eligible_case_ids` 一致。resolver-only 的 DEV-02、DEV-08、DEV-23 不计入 AI-only 分母。

## 使用方式

1. 阅读 family 签字边界和验收清单，再核对范围文件。
2. 运行记录只用于追溯当时的输出与运行参数；本次归档未重跑模型、未计算准确率、未判定 v2 是否采用。
3. 源文档可能引用未随本目录发布的输入、答案键或 evidence 文件；这些引用不表示文件已上传，也不授权从本目录加载答案或替代正式契约。
4. 不把本目录的输出当作 ground truth、冻结评测答案或应用运行时的数据源。

## 源文件完整性

以下四个源文件按原始 UTF-8 内容和换行保留。哈希用于识别本次快照，不代表内容已经完成所有业务验收。

| 文件 | SHA-256 |
| --- | --- |
| `T1_family_scoring_signoff_2026-10-24.md` | `21DF0911FE4B225F202099F1B1C14E1FCEAA7880D4365BCFCBAB029A9FE02065` |
| `v1_v2_acceptance_checklist_2026-10-24.md` | `E296DF9B6CB22374FB6CE8A733BCEDA7A46FC92AEBB669F435AD255C124153BA` |
| `dev_41_parse_scope.json` | `6AE86B6B4CE58EB546A27EBDAE2E9C3F2608040A332836E47B802F0659F128F0` |
| `dev41_ai_only_v1_prod_2026-10-24.json` | `60A28A7CDC3D5E90F0BCFD584F79136BBEB4347942B105187548ECD717350B46` |

本次变更仅包含本目录的五个白名单文件。其他输入、答案键、私有 seed、凭据及压缩包不属于本次交付。
