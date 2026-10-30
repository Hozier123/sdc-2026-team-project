# C06 检查矩阵

- 环境：`b05-env-ea709a8e70d0`（firstuse 51394 / PG 51393；protected 51391 / PG 51390）
- 源码绑定：`c8848efce1ccbe31e1dead315816c14d313e7a0f`；模式 `LOCAL_SYNTHETIC_T1_FALLBACK`
- 执行：He，2026-10-31 01:45–01:48（UTC+8）
- 复核：Zhou Jingxi **APPROVED**（技术层 API+DB；13/13，0 P0）；Zhan **形式 PASS**（`ZR-20261031-03`）
- 结论：**13/13 PASS，0 失败，0 P0**

| # | 检查 | 期望 | 实际 | 证据 | 结果 |
|---|---|---|---|---|---|
| 1 | 环境隔离 | firstuse / protected 为独立 PG cluster、独立 API；不连生产 | system_identifier `7702509799995540300` / `7702509778719010148`；API 进程 51394 / 51391 独立 | `meta/identity_after_reset.json`、`meta/b05_environment_public.json` | PASS |
| 2 | 基线 | 40 SKU / 795 库存 / 2 alias / 8 张流水表 0 | 全部一致（Milo 30、Teh 3） | `db/baseline_firstuse.json` | PASS |
| 3 | 缺货识别 | Teh 10 bag > 3 → `INSUFFICIENT_STOCK` 且 blocking | `raw/02`（parse）：`blocked_actions.APPROVE_AND_GENERATE_DO=[INSUFFICIENT_STOCK]`、`blocking_issues=[INSUFFICIENT_STOCK]`；`raw/04`（草稿详情）：`blocked_actions.APPROVE_AND_GENERATE_DO=[BLOCKING_ISSUES]`、`blocking_issues=[INSUFFICIENT_STOCK]`；问题 `ISS_AEAC2AB55E0044FEA81F7C86A20C2573`，issue code 为 `INSUFFICIENT_STOCK` | `raw/02_parse_teh_10_orders_parse-draft.json`、`raw/04_a1_draft_before_...json` | PASS |
| 4 | 缺货阻断批准 | 批准被拒，无 DO，库存不变 | 400 `DISAMBIGUATION_UNRESOLVED`，`details.issue_ids=[缺货问题]`；无 DO 返回 | `raw/05_a2_approve_shortage_...json` | PASS |
| 5 | 减量到可满足 | confirmed 3 → v2，问题清零，`READY_FOR_APPROVAL`，27.00 | v2；`issues=[]`；3 × 9.00 = 27.00 | `raw/06_a3_save_reduced_...json` | PASS |
| 6 | 减量后批准 | 生成 DO，扣库存 3→0，审计成对 | 200 `DO_20261030_77EBD4F2`，3 bag @ 9.00，27.00，`DIRECT`；库存 3→0；审计 `SAVE_LINES / APPROVE / INVENTORY_DEDUCT`；活动 `DO_CREATED / INVENTORY_DEDUCTED` | `raw/07_a4_approve_reduced_...json`、`db/after_a_shortage.json`、`reset/audit_extract.json` | PASS |
| 7 | 低价审批 | tier 19.00 → 17.00，34.00；CLERK 送审 202 PENDING | v2 `READY_FOR_APPROVAL`；202 `APR_38289BAEB48A41C79C09F185A07D3A65`，`PRICE_OVERRIDE_BELOW_TIER`，库存 30 | `raw/09_b2_save_override_...json`、`raw/10_b3_submit_owner_...json` | PASS |
| 8 | 人工改库存 | 直接 SQL 把 Milo 30→1，留前后值 | before 30 / after 1，rowcount 1，记录 SQL 与时间 | `db/b5_manual_stock_down.json` | PASS |
| 9 | 库存变化阻断 | OWNER 批准 → 409 `STOCK_CHANGED`；审批仍 PENDING；无 DO；无负库存；无审计新增 | 409，`available_qty=1 < effective_qty=2`；审批 PENDING、`decided_by=null`；草稿仍 `PENDING_OWNER_APPROVAL`；审计 5→5 | `raw/12_b6_decide_stock_changed_...json`、`raw/13`、`raw/14`、`db/after_b_409.json` | PASS |
| 10 | 恢复库存后批准 | 恢复 30 后 OWNER 批准 → DO、30→28、APPROVED | 200 `DO_20261030_6FC83E94`，2 bag @ 17.00，34.00，`OWNER_APPROVED`；库存 30→28；审批 `APPROVED`、`USR_T1_OWNER`；草稿 `DO_GENERATED`；审计 `DECIDE_APPROVE / INVENTORY_DEDUCT` | `raw/15`–`raw/18`、`db/after_b_approved.json`、`reset/audit_extract.json` | PASS |
| 11 | 库存守恒 | 795−3−2=790；任一 SKU 不为负；复位后 795 | 790；最小库存 0；复位后 795 | `db/after_b_approved.json`、`db/after_reset.json`、`db/comparison.json` | PASS |
| 12 | 复位 | dry-run + apply PASS；firstuse 回初态；protected 不变 | dry-run / apply 均 `PASS`；`firstuse_restored=true`、`firstuse_api_restarted=true`；protected 12 类业务表与检查点不变、API PID/instance 不变；firstuse PID 32720→30104，protected 36740/`f38f…` 不变 | `reset/dryrun_result.json`、`reset/apply_result.json`、`reset/reset_export.md`、`db/comparison.json`、`meta/identity_after_reset.json` | PASS |
| 13 | 证据完整性 | 原始响应、DB 快照、复位报告、逐文件哈希 | 19 条原始响应 + 8 份 DB 快照 + 3 份辅助（comparison + 2 份改库存记录）；`SHA256.txt` 覆盖全部证据文件 | `SHA256.txt`、`raw/`、`db/`、`reset/` | PASS |

## 备注

- **第 3 条的两个来源不要混**：`raw/02` 是 parse 响应，缺货码直接写在 `blocked_actions`；`raw/04` 是草稿详情，`blocked_actions` 显示为 `BLOCKING_ISSUES`，`blocking_issues` 仍是 `INSUFFICIENT_STOCK`。缺货事实以 issue code 为准。
- **raw/13、raw/14 的 `available_qty=30` 是送审时的 snapshot，不是 409 当时的实时值**。409 当时的实时库存是 `1`，见 `raw/12` 的 `details.lines[0].available_qty` 与 `db/b5_manual_stock_down.json`；两者不要混读。
- 第 9 条是本次唯一一次“人为改库存”：`UPDATE inventory SET available_qty=1 ...`，复位时随库重建清除；之后又恢复到 30，属于同一测试步骤。
- 第 4 条的错误码是 `DISAMBIGUATION_UNRESOLVED`（缺货问题阻塞），不是 `INSUFFICIENT_STOCK`；这是当前实现“先阻断未解决问题、再复核库存”的顺序。
- 第 9 条的 409 由 OWNER 决定路径触发（`_lock_and_verify_stock` 默认 `StockChangedError`）；CLERK 直接批准路径在同样场景下会返回 400 `INSUFFICIENT_STOCK`，两者都阻断，本包只记录实际走到的 OWNER 路径。
- `db/` 共 11 个文件：8 份快照 + `comparison.json` + `b5_manual_stock_down.json` + `b9_restore_stock.json`。
- 本包没有浏览器截图；证据是 API 原始响应 + DB 前后快照 + 复位报告。UI/浏览器未做交互验收。
- 探测阶段创建过一条未使用草稿 `DRF_198ABA85C3FC4DB8A4C334E9E7FDCD7F`（Milo 2 bag，v1 READY，未保存/未批准），复位时清除，不计入库存差额。
- 公开副本：本文件相对签字原件只改了 P3 措辞/口径并脱敏本机路径；原件 zip SHA-256 `89AC444265CADB22DAEBF1659FFA01F7A6A3A0A86D5251F7FE271488CF2F58A6`。
