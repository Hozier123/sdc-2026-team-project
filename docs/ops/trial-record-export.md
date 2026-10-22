# DO 行级导出（已确认 A1/B1/C1）

> 依据：Zhou r2 复核要求，测试侧确认 `A1 / B1 / C1`。
> 工具：`backend/tools/export_trial_record.py`。
> 范围：只做**记录侧导出**，不改契约、不改 OpenAPI、不动 Gate 0。

## 1. 确认下来的规则

| 编号 | 结论 |
|---|---|
| A1 | 行序按 `lines[]` 数组顺序，标 `L1..Ln`；超过 5 行照常 `L6…`，不截断、不补空 |
| B1 | 每行带 `do_number`，一个试次多张 DO 也能区分 |
| C1 | 附 `unit`、`display_name` 只读列，不参与判分 |

## 2. 输出列

```text
case_id, do_number, line_no, sku_id, quantity, unit,
applied_unit_price, subtotal_rm, display_name
```

- `sku_id` 必须是**系统 ID**（`SKU_MILO_1KG`），不是源编码 `MILO1`；
- 金额是十进制字符串，两位小数；
- DO 行只用 `applied_unit_price`，不混用草稿的 `effective_unit_price`。

## 3. 校验

导出时逐行检查：

```text
subtotal_rm == quantity × applied_unit_price
sum(subtotal_rm) == final_total_rm
```

任一不成立：文件照写，但 JSON 里 `totals_match=false` 并列出错误，进程**退出码 2**，避免把脏记录当成通过。

## 4. 用法

```powershell
# 没有 P0-A 之前：用 Gate 0 fixture 验证格式
python -m tools.export_trial_record `
  --fixture ../gate0/contracts/fixtures/delivery_order.json `
  --case-id TEST-01 --out-dir ../evidence/records

# 试次中：从数据库导出（只读业务连接）
python -m tools.export_trial_record `
  --database-url $env:DATABASE_URL --tenant T1 `
  --case-id TEST-01 --do-number DO-20261022-0001 --out-dir ../evidence/records
```

输出：

```text
evidence/records/<case_id>_do_lines.csv    给记录表粘贴用（带 BOM，Excel 不乱码）
evidence/records/<case_id>_do_lines.json   机器可读，含 totals_match 与 errors
```

CSV 末行是 `合计`，值为 `final_total_rm`，方便人工对账；机器处理可用 `--no-total-row` 去掉。

退出码：`0` 正常；`2` 金额不一致；`1` 参数/连接/数据错误。

## 5. 与 reset 证据导出的区别

| | reset 证据（`evidence/reset/`） | 本导出（`evidence/records/`） |
|---|---|---|
| 时机 | 每次重建前 | 每单结束后 |
| 内容 | 数据库快照：DO 原文 + 审计 + 字段差异 | 行级对账表，给记录表用 |
| 用途 | 事后核查、审计留痕 | 与手工基线逐行比对 |

两份都要留，不能互相替代。

## 6. 现状与前置

- 格式与脚本现在可用，`--fixture` 模式已验证（1 单 1 行，合计一致）。
- 真实数据要等 P0-A 能产生 DO；届时用 `--database-url` 跑一次，与 Zhou 的记录表对齐。
- 期望行数：`L1..Ln` 与手工记录行数一致；不一致先查是不是漏行，不要直接改 CSV。
