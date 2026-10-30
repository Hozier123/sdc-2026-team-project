# A03 当前版本 AI 证据（2026-10-30）

运行窗口：2026-10-30 12:16–12:17 UTC+8，RunPod 热态 worker（无冷启动）。
应用版本：`555f0fa669ac40e2d7b9d9ceacdbfb6d24301127`。
部署：`72258e1f`（He 2026-10-30 确认，2026-10-29 23:01:39 UTC+8 发布；`7c492845` 为历史部署）。
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

### Zhou 独立复核（2026-10-30 14:28，脱敏汇总）

| 指标 | 结果 |
|---|---|
| 严格六维整例通过 | **8/23（34.8%）** |
| family | 21/27（77.8%） |
| qty | 26/27（96.3%） |
| uom | 19/27（70.4%） |
| condition 类型 | 8/8 |
| condition span 精确 | 4/8 |
| 行数一致 | 20/23 |
| UNKNOWN 行 | 9，全部显式 `LOW_CONFIDENCE_MATCH`，无静默错配商品 |

15 条失败 case，涉及：7 条 UOM 缺口（DEV-01/05/07/11/13/27/33）、5 条 family UNKNOWN（DEV-04/14/22/35/37）、4 条 condition span 截断（DEV-13/27/29/35）、DEV-37 行分割失败、DEV-40/41 安全 UNKNOWN（部分 case 重叠）。完整判分含 gold 值，留在 Zhou 本地；本文件只保留脱敏汇总，详见 `ai-review-summary.md`。

## 2. 六条 canonical

| 项 | 结果 |
|---|---|
| 执行 | 6/6 HTTP 成功，6/6 `ai_mode=LLM` |
| 评分字段（span / qty / uom / pack_size） | 5 条一致 |
| 已知限制 | `condition` 的条件 span 截断为 `kalau RM95`，期望 `kalau RM95 untuk 1 ctn boleh?`；记 1 条 `KNOWN_LIMITATION` |
| family | `family_scored=false`，不参与这 6 条判分；实际返回 T1 租户 ID（`FAM_TEPUNG/FAM_BERAS/FAM_MINYAK/FAM_GULA`），与样例的通用 ID 不同不构成失败 |
| 文件 | `evidence/ai-samples-2026-10-30/run-20261030T041632Z.json` |
| SHA-256 | `E184CC8601E92236B0193B194DAB12315598B03F6D702365F99308F1615F053B` |

**口径：6/6 是调用成功，不是 6/6 正确；** Zhou 独立复核确认 5+1 成立；`empty` 的 `ignored_spans` 合并为额外轻微差异。

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

**结论：7/7 都是 adapter 层显式标记，未出现静默错配（没有自动填错单位或错 SKU）。** Zhou 已核对业务层 `555f0fa`：`uom=None` → `MISSING_UOM`，`blocking=True`，进入候选/澄清/阻断，不自动选 SKU；**不标 P0**，但仍记 7 个模型质量缺口，不写成“单位全通过”。

## 4. 限制

- 本次是 production adapter 直调（`app/ai`），不是公开 API 端到端；公开 API 的 B01/C01 解析已在 10/29 验收。
- 单次热态运行；不是重复性、并发或 TEST32 结论。
- Zhou 已独立判分（严格六维 8/23）；本文件不把 23/23 写成准确率。
- vLLM `0.32.0` 只在报告文字；JSON 未保存 `system_fingerprint`，按报告级绑定。
- 10/29 晚的 5 条冷启动 FALLBACK 保留为独立记录，不作为模型失败，也不并入本文件。
