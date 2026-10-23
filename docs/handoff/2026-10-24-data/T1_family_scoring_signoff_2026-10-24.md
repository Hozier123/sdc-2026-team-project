# T1 Family 计分口径签字（决策 B）

- 签字人：Zhou Jingxi（数据与质量）
- 日期：2026-10-24
- 依据：PR #44，commit `3c745207d1bfa8d18784f89635885a145bdde1a4`
- 结论：**按 B**

## 1. 计分口径

| 数据 | family_scored | family 真值 |
|---|---|---|
| `docs/ai_contract/samples` 6 条 generic 合同样例 | `false` / `GENERIC_CONTRACT_SAMPLE` | 不评 family；只评 span / qty / uom / pack_size / conditions |
| T1 `dev_41` 的 23 条 AI-only | `true` | 必须用 T1 ID（如 `FAM_TEPUNG`），不得出现 `FAM_FLOUR` |
| `frozen_eval_32` | `true` | 同上 |
| DEV-02 / DEV-08 / DEV-23 | 不适用 | resolver-only，不计 AI-only family |

其余口径不变：span 逐字、qty 正整数或 null、uom / pack_size 原样；AI 不产出 sku / price / stock / approval。

## 2. 已核对

- `backend/app/extraction/ai.py`：`to_raw_extraction` 默认不做 family 转换；`LEGACY_HTTP_FAMILY_ALIASES` 只在 deprecated `HttpAiExtractor` 内显式使用。
- `backend/app/extraction/runpod_adapter.py` / `backend/app/ai/adapter.py`：runpod 路径按注入的 tenant catalog 做闭集校验，不做 `FAM_FLOUR→FAM_TEPUNG` 转换。
- `docs/ai_contract/samples` 6 条：均含 `family_scored:false`、`reason:GENERIC_CONTRACT_SAMPLE`。
- `docs/ai_contract/family-scoring-caliber.md` 与本签字口径一致。
- He 报告 PR #44 CI 通过；本签字以该 commit 为准。

## 3. 签字边界

- 本签字只确认 **family 计分口径 B**，不代表 PR #41 的 `ai_contract/` 重复、`backend/ai` 与 `backend/app/ai` 双实现问题已关闭。
- PR #44 若后续有新 commit 改动 family 映射、样例元数据或计分脚本，需要重新签字。
- TEST-32 的 TEST-31 数值错误、TEST-08 库存冲突仍未解决，冻结继续暂停。
- AI-only 23 条与 resolver-only 3 条的真实结果尚未跑完；本签字不构成准确率或生产集成结论。
