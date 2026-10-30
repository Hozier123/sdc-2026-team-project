# AI 降级与恢复记录（2026-10-30）

本文件只记录实际观察到的运行状态与证据，不把降级写成通过，不把调用成功写成准确率。

## 1. 时间线

| 时间（UTC+8） | 场景 | 实际结果 | 证据 |
|---|---|---|---|
| 2026-10-29 22:45–23:15 | B01/C01 热态联调 | B01 2176.5ms、C01 2363.1ms，均 HTTP 200 / `ai_mode=LLM`；三轮六次 parse 6/6 LLM、FALLBACK=0 | `evidence/ai-integration/2026-10-29-b01/`；PR #71 |
| 2026-10-29 23:27–23:33 | 冷启动重跑 23 条 DEV | warmup 180s `ReadTimeout`；warmup + 前 5 条（DEV-01/03/04/05/06）FALLBACK；DEV-07 起恢复 LLM，延迟 1.7–3.9s | `evidence/dev41_ai_only_v1_prod_2026-10-29.json`（保留，不覆盖） |
| 2026-10-30：23 条报告 12:16:11；6 条报告 12:16:32（精确起始未记录） | A03 热态重跑 | 23/23 LLM、0 FALLBACK、0 超过 4.1s；p50 1930ms / p90 2637ms / p95 3633ms；6/6 canonical LLM | `evidence/dev41_ai_only_v1_prod_2026-10-30.json`、`evidence/ai-samples-2026-10-30/run-20261030T041632Z.json` |

## 2. 解释与边界

- **冷启动不是模型失败。** 10/29 23:27 的重跑在 180s 预热处 `ReadTimeout`，前 5 条走 FALLBACK；worker 变热后同一版本恢复 LLM。历史冷启动约 198.5s，是旧测量，不是当前 SLA。
- **FALLBACK 不是成功。** 它表示本次没有拿到有效 LLM 结果，业务侧必须交人工确认或安全终止；历史 C01 FALLBACK + 人工确认的记录保留，不回写成 LLM。
- **恢复证据成立。** 10/29 B01/C01 与 10/30 A03 都是在 worker 热态、同一模型/版本/超时下取得的 LLM 结果；10/30 的 23 条无超时、无 FALLBACK。
- **Zhou 独立复核（2026-10-30 14:28）：** 23/23 是调用成功，严格六维整例 **8/23**；7 个 UOM 缺口在业务层 `MISSING_UOM` 阻断，不标 P0；6 条 canonical 5+1 成立。冷启动/恢复结论不变，但**不得把 23/23 写成准确率**。
- **10/30 没有做主动故障注入。** 本次没有重复性、并发或 TEST32 验收结论；调用成功不作为准确率，质量评分采用 Zhou 的独立复核汇总。
- **7 个已知 UOM 缺口**在 10/30 的 23 条里全部为 adapter 层显式标记（`uom=NULL` + `LOW_CONFIDENCE_MATCH` / `FIELD_NOT_EVIDENCED`），没有静默错配；Zhou 已完成业务层复核：本候选的缺失单位进入 `MISSING_UOM`、`blocking=True` 的候选/澄清/阻断路径；这不构成七例公开 API 端到端复跑证据。
- **23/23 是调用成功，不是识别准确率；6/6 是调用成功，不是 6/6 正确。** 6 条 canonical 的初步核对是 5 条评分字段一致 + 1 条 `condition` 条件 span 截断（`kalau RM95`），family 不参与判分。

## 3. Gate C 可直接使用的三句话

1. AI 只做非结构化文本抽取，不决定价格、库存、审批和 DO；规则与人工始终在回路里。
2. 10/30 热态 23/23 调用为 LLM、0 FALLBACK、0 超时，p50 1.93s / p95 3.63s；7 个已知单位缺口全部显式阻断、0 静默错配。
3. 模型为 `Qwen/Qwen2.5-7B-Instruct-AWQ`（vLLM 0.32.0），业务超时 4.1s；冷启动约 198.5s 时降级交人工，不静默猜单位。

## 4. 版本与参考

- 应用：`555f0fa669ac40e2d7b9d9ceacdbfb6d24301127`
- AI 模块：`app/ai@db6f0ce`
- 模型：`Qwen/Qwen2.5-7B-Instruct-AWQ`；vLLM `0.32.0` 为报告级记录，fingerprint `vllm-0.32.0-cde58403` 来自历史 B01，本轮 JSON 未保存 fingerprint
- 业务超时：`LLM_TIMEOUT_S=4.1`
- 10/30 证据摘要：`evidence/phase2/2026-10-30/ai-dev-results.md`
- 10/29 B01 证据：`evidence/ai-integration/2026-10-29-b01/`
