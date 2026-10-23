# Family 计分口径（Zhou 2026-10-24 决策 B）

## 1. 结论

| 数据 | `family_scored` | family 真值 |
|---|---|---|
| `docs/ai_contract/samples` 6 条 generic 合同样例 | `false`（`GENERIC_CONTRACT_SAMPLE`） | 不评 family，只评 span / qty / uom / pack_size / conditions |
| T1 `dev_41`（23 条 AI-only） | `true` | 必须用 T1 ID（`FAM_TEPUNG` 等），不得出现 `FAM_FLOUR` |
| `frozen_eval_32` | `true` | 同上 |
| DEV-02 / DEV-08 / DEV-23 | 不适用 | resolver-only，不计 AI-only family |

其余口径不变：span 逐字、qty 正整数或 null、uom / pack_size 原样、
AI 不产出 sku / price / stock / approval。

## 2. 代码落点

生产路径 `AI_PROVIDER=runpod_adapter`：

- `backend/app/parse.py`：每次 parse-draft 按 `user.tenant_id` 调用
  `load_family_catalog`，把 tenant catalog 注入 `RunPodAdapterProvider`。
- `backend/app/ai/catalog.py`：只从 `product_families` / `family_aliases`
  读取当前租户的 active family，无硬编码 ID。
- `backend/app/ai/adapter.py`：`fam` 必须命中注入 catalog，否则记为
  `UNKNOWN`；不做任何 `FAM_FLOUR → FAM_TEPUNG` 转换。
- `backend/app/extraction/runpod_adapter.py`：把 `family_id` 原样透传为
  `RawRow.fam`，无 family 映射。

旧 HTTP 兼容路径（`AI_PROVIDER=http`，deprecated）：

- `backend/app/extraction/ai.py` 的 `LEGACY_HTTP_FAMILY_ALIASES` 只在
  `HttpAiExtractor` 内显式使用，用于把合同通用 ID 翻成 tenant ID。
- `to_raw_extraction` 默认不做任何 family 转换；传入映射是显式 opt-in。
- 该表只是 legacy shim：不得进入 eval truth，也不得作为 T1 family 真值。

## 3. 样例元数据

6 个 generic 样例 JSON 顶层新增：

```json
"family_scored": false,
"reason": "GENERIC_CONTRACT_SAMPLE",
```

`backend/tools/run_ai_samples.py` 会把这两个字段写进 evidence，便于对照时
区分「family 不计分」与「family 判错」。

## 4. 回归约束

- `backend/tests/test_ai_contract.py`：默认不翻译 generic family；
  legacy 映射必须显式传入；HTTP transport 仍保留旧翻译。
- `backend/tests/test_runpod_adapter_provider.py`：runpod 边界不做
  `FAM_FLOUR → FAM_TEPUNG` 转换。
- `backend/tests/test_run_ai_samples.py`：6 条样例必须全部
  `family_scored=false` / `GENERIC_CONTRACT_SAMPLE`。
- `backend/tests/test_ai_catalog.py`、`test_parse_runpod_adapter.py`：
  catalog 逐租户构建、parse-draft 注入 DB catalog（集成测试，需
  `TEST_DATABASE_ADMIN_URL`）。
