# DO 行级导出（A1/B1/C1 + Zhou 补充）

> 依据：Zhou r2 复核要求，测试侧确认 `A1 / B1 / C1`，并追加三项。
> 工具：`backend/tools/export_trial_record.py`。
> 范围：只做**记录侧导出**，不改契约、不改 OpenAPI、不动 Gate 0。

## 1. 确认下来的规则

| 编号 | 结论 |
|---|---|
| A1 | 行序按 `lines[]` 数组顺序，标 `L1..Ln`；超过 5 行照常 `L6…`，不截断、不补空 |
| B1 | 每行带 `do_number`，一个试次多张 DO 也能区分 |
| C1 | 附 `unit`、`display_name` 只读列，不参与判分 |
| 补充 1 | 每行带 `customer_id`，便于独立复核等级价 |
| 补充 2 | 每行带 `final_total_rm`，订单总额错时不会被行合计掩盖 |
| 补充 3 | 带 `pack_size` / `grade`，并记录 products 快照版本与哈希 |

## 2. 输出列

```text
case_id, do_number, customer_id, ai_mode, ai_mode_mixed, line_no,
sku_id, pack_size, grade, quantity, unit, applied_unit_price,
subtotal_rm, final_total_rm, display_name
```

- `sku_id` 是**系统 ID**（`SKU_MILO_1KG`），不是源编码 `MILO1`；
- 金额是十进制字符串，两位小数；
- DO 行只用 `applied_unit_price`，不混用草稿的 `effective_unit_price`；
- `pack_size` / `grade` 来自 `products` 表，导出时用 `--products-version`、`--products-sha256` 记录读的是哪一版。

## 3. 三条校验

```text
1) subtotal_rm == quantity × applied_unit_price
2) sum(subtotal_rm) == final_total_rm
3) 行序一致：DO lines[] 的 line_id 顺序 == 草稿 working_lines 的 line_id 顺序
```

任一条不成立：文件照写，但 JSON 标 `false`、列出错误，进程**退出码 2**。

第 3 条对应 Zhou 的硬要求：L1 是规格疑点、L2 是缺货，行序错位会让三类错误整批判错。DO 行本身不含“消息行号”，所以导出端只能校验“DO 序 = 草稿序”；**“消息序 = 草稿序”必须由 P0-A 的后端保证**，并在开测前抽 3 单人工比对三者一致。

## 4. AI 模式与 MIXED

- `ai_mode` 取自 `orders.ai_mode`，逐行导出；
- `ai_mode == MIXED` 表示试次中发生了自动降级（RunPod 掉线/超时）；
- 导出会在 `ai_mode_mixed` 列标 `True`，并在 JSON 的 `mixed_orders` 单独列出；
- **MIXED 的单不得混入中位数**，必须单独报告；只写“AI 模式”而不记实际生效模式，整批数据作废。

## 5. 用法

```powershell
# 没有 P0-A 之前：用 Gate 0 fixture 验证格式
python -m tools.export_trial_record `
  --fixture ../gate0/contracts/fixtures/delivery_order.json `
  --case-id TEST-01 --out-dir ../evidence/records

# 试次中：从数据库导出（只读业务连接）
python -m tools.export_trial_record `
  --database-url $env:DATABASE_URL --tenant T1 `
  --case-id TEST-01 --do-number DO-20261022-0001 --out-dir ../evidence/records `
  --products-version T1-0.1 --products-sha256 <sha>
```

输出：

```text
evidence/records/<case_id>_do_lines.csv    给记录表粘贴用（UTF-8 BOM）
evidence/records/<case_id>_do_lines.json   机器可读，含 totals_match / mixed_orders / products
```

CSV 末行是 `合计`，值为 `final_total_rm`；机器处理可用 `--no-total-row` 去掉。

退出码：`0` 正常；`2` 金额或行序不一致；`1` 参数/连接/数据错误。

## 6. 与 reset 证据导出的区别

| | reset 证据（`evidence/reset/`） | 本导出（`evidence/records/`） |
|---|---|---|
| 时机 | 每次重建前 | 每单结束后 |
| 内容 | 数据库快照：DO 原文 + 审计 + 字段差异 | 行级对账表，给记录表用 |
| 用途 | 事后核查、审计留痕 | 与手工基线逐行比对 |

两份都要留，不能互相替代。

## 7. 现状与前置

- 格式与脚本现在可用，`--fixture` 模式已验证。
- 真实数据要等 P0-A 能产生 DO；届时 `--database-url` 跑一次，与 Zhou 的记录表对齐。
- 开测前必须完成：抽 3 单验证“消息行序 = working_lines 序 = 导出 line_no 序”，三者逐一相等；不过不进计时。
