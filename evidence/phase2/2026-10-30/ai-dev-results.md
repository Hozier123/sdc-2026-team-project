# A03 当前版本 AI 证据（2026-10-30）

运行窗口：2026-10-30 12:16–12:17 UTC+8，RunPod 热态 worker（无冷启动）。
应用版本：`555f0fa669ac40e2d7b9d9ceacdbfb6d24301127`。
AI 模块标识：`app/ai@db6f0ce`（DEV 脚本自报 code_base）。
模型：`Qwen/Qwen2.5-7B-Instruct-AWQ`；vLLM `0.32.0`（`system_fingerprint=vllm-0.32.0-cde58403`）。
业务超时：`LLM_TIMEOUT_S=4.1`。

## 1. 23 条 DEV AI-only

| 项 | 结果 |
|---|---|
| 执行 | 23/23 |
| `ai_mode` | LLM 23 / FALLBACK 0 / MIXED 0 |
| 超过 4.1s | 0 |
| UNKNOWN 行 | 9（分布在 7 个 case，供 Zhou 复核，不在此判错） |
| 报告文件 | `evidence/dev41_ai_only_v1_prod_2026-10-30.json` |
| SHA-256 | `30EAFF548FE096A587C824E9336CDA675C13A5CACB3B08112729128D0CDC6BC3` |

**口径：23/23 是调用成功，不是识别准确率。** 准确率仍由 Zhou 用独立答案键判分。

## 2. 六条 canonical

| 项 | 结果 |
|---|---|
| 执行 | 6/6 HTTP 成功，6/6 `ai_mode=LLM` |
| 评分字段（span / qty / uom / pack_size） | 5 条一致 |
| 已知限制 | `condition` 的条件 span 截断为 `kalau RM95`，期望 `kalau RM95 untuk 1 ctn boleh?`；记 1 条 `KNOWN_LIMITATION` |
| family | `family_scored=false`，不参与这 6 条判分；实际返回 T1 租户 ID（`FAM_TEPUNG/FAM_BERAS/FAM_MINYAK/FAM_GULA`），与样例的通用 ID 不同不构成失败 |
| 文件 | `evidence/ai-samples-2026-10-30/run-20261030T041632Z.json` |
| SHA-256 | `E184CC8601E92236B0193B194DAB12315598B03F6D702365F99308F1615F053B` |

**口径：6/6 是调用成功，不是 6/6 正确；** 上述 5+1 是初步核对，最终由 Zhou 独立复核。

## 3. 七个已知 UOM 缺口

| case | 缺口 | 实际输出 | 判定 |
|---|---|---|---|
| DEV-01 | bulk-kg | `10kg Bawang Bsr India`：`uom=NULL`，`LOW_CONFIDENCE_MATCH` / `FIELD_NOT_EVIDENCED` | 显式阻断 |
| DEV-05 | bulk-kg | `Bawang Bsr India 50kg`：同上 | 显式阻断 |
| DEV-11 | bulk-kg | `50kg Bawang Bsr India`：同上；其余两行正常 | 显式阻断 |
| DEV-33 | bulk-kg | `kalau ada bagi 50kg Bawang Bsr India`：同上 | 显式阻断 |
| DEV-07 | botol | `4 botol minyak 5kg`：同上 | 显式阻断 |
| DEV-13 | pail | `1 pail Minyak 17kg`：同上 | 显式阻断 |
| DEV-27 | pail | `5 pail Minyak 17kg`：同上 | 显式阻断 |

**结论：7/7 都是 adapter 层显式标记，未出现静默错配（没有自动填错单位或错 SKU）。** 业务层的候选/澄清/阻断表现需 Zhou 在完整流程中复核；本记录不冒充“单位全通过”。

## 4. 限制

- 本次是 production adapter 直调（`app/ai`），不是公开 API 端到端；公开 API 的 B01/C01 解析已在 10/29 验收。
- 单次热态运行；不是重复性、并发或 TEST32 结论。
- 没有 Zhou 的独立判分；上面 5+1 只是 Xiong 的初步核对。
- 10/29 晚的 5 条冷启动 FALLBACK 保留为独立记录，不作为模型失败，也不并入本文件。
