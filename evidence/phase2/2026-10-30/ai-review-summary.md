# A03 独立复核汇总（脱敏）

- 复核人：Zhou Jingxi
- 复核时间：2026-10-30 14:28（UTC+8）
- 范围：23 条 DEV AI-only、6 条 canonical、7 个 UOM 缺口
- 说明：本文件只保留汇总、case ID 和失败类别；**完整复核含 gold 值，保留在 Zhou 本地，不进入公开仓库。**

## 1. 23 条 DEV

| 指标 | 结果 |
|---|---|
| 调用成功 | 23/23 LLM，0 FALLBACK，0 超过 4.1s |
| 严格六维整例通过 | **8/23（34.8%）** |
| family | 21/27（77.8%） |
| qty | 26/27（96.3%） |
| uom | 19/27（70.4%） |
| condition 类型 | 8/8 |
| condition span 精确 | 4/8 |
| 行数一致 | 20/23 |
| UNKNOWN 行 | 9，全部显式 `LOW_CONFIDENCE_MATCH` |

没有静默错配商品：所有 family/uom 错都带显式标记；DEV-37 的额外行也都是 UNKNOWN。

### 15 条失败类别

- **7 条 UOM 缺口**：DEV-01/05/07/11/13/27/33（kg/btl/pail → null）
- **5 条 family UNKNOWN**：DEV-04/14/22/35/37
- **4 条 condition span 截断**：DEV-13/27/29/35（截断处未标 issue）
- **DEV-37 行分割失败**：预期 2 行，实际 4 行
- **DEV-40/41 安全 UNKNOWN**：预期 0 条确定行，实际 1 条 UNKNOWN

## 2. 六条 canonical

- **5+1 成立**：5 条行级一致 + 1 条 condition span 截断。
- 额外轻微差异：`empty` 的 `ignored_spans` 期望两条，实际合并成一条；若计分，是第二处差异。
- family 不参与这 6 条判分。

## 3. 七个 UOM 缺口

- 结论：**业务层可接受，不标 P0**。
- 业务层 `555f0fa`：`uom=None` → `MISSING_UOM`，`blocking=True`；进入候选/澄清/阻断，不自动选 SKU。
- 但仍记录为 **7 个模型质量缺口**，不能写成“单位全部通过”。

## 4. 边界

- production adapter 直调、单次热态；不是公开 API 端到端、TEST32、重复性/并发结论。
- 10/29 冷启动 5 条 FALLBACK 未并入。
- vLLM 0.32.0 只在报告文字级；JSON 未保存 fingerprint。

## 5. 备注

- 完整复核文件 `A03_HOT_STATE_REVIEW.md` 与答案键/模型原始输出只留本地，不贴群、不进公开仓库。
- 本汇总的 SHA-256 见 `SHA256.txt`。
