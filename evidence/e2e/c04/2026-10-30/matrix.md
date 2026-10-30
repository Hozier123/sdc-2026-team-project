# C04 检查矩阵

执行：2026-10-30 16:55–17:00（UTC+8）
环境：生产 API `https://kiraorder-api.replit.app/api/v1`；前端 v1.4.0 / f8ff1d7；后端 555f0fa
样例：draft `DRF_AFC94FC488144FC6932FA4800D73B0EC` v2；approval `APR_7A1382B29D5C44FFB6242D15477A60B7`

| # | 检查 | 期望 | 实际 | 证据 | 结果 |
|---|---|---|---|---|---|
| 1 | CLERK 身份 | `/me` 200，role=CLERK，tenant=T1 | 200，CLERK，Sinaran Food Supply | `c04_01` 顶栏 Siti / Order clerk | PASS |
| 2 | 客户 | Kedai Rasa，Tier B | Kedai Rasa，Tier B | `c04_01` 标题 | PASS |
| 3 | 原文输入 | `Milo 1kg 2 bag, kalau RM17 boleh?` | 原文一致 | `c04_01` Original message | PASS |
| 4 | 解析行 | 1 行：Milo 1kg，2 bag | SKU_MILO_1KG，requested/effective qty=2，uom=bag | `sample.json`、`c04_02` | PASS |
| 5 | PRICE 条件 | span 含 “kalau RM17” | condition_kind=PRICE，span=`kalau RM17`，resolved=true，resolution=ACCEPT_REQUESTED_PRICE | `sample.json` → `condition` | PASS |
| 6 | 成交价低于 tier | 17.00 < 19.00 | tier 19.00，override 17.00，effective 17.00 | `c04_02`、`c04_04` | PASS |
| 7 | 保存版本 | v2，锁定 | v2，`PENDING_OWNER_APPROVAL` | `c04_01` 顶部 v2、`c04_03` Locked v2 | PASS |
| 8 | escalation | `PRICE_OVERRIDE_BELOW_TIER`，detail 19.00→17.00 | 完全一致 | `sample.json`、`c04_03` | PASS |
| 9 | 只送老板，不直接生成 DO | `SUBMIT_FOR_OWNER`，无 DO | 审批 PENDING，无 DO；总额 34.00 < 1500.00，只有低价一条原因 | `sample.json`、`acceptance.json` | PASS |
| 10 | 草稿状态 | `PENDING_OWNER_APPROVAL` | `PENDING_OWNER_APPROVAL` v2 | `sample.json` | PASS |
| 11 | 审批 | PENDING，1 行，RM 34.00 | PENDING，line_count=1，total_rm=34.00 | `sample.json`、`c04_03` | PASS |
| 12 | OWNER 侧数字 | 19.00 → 17.00；38.00 → 34.00 | Changes 表完全一致 | `c04_04` | PASS |

合计：12/12 PASS，0 失败，0 P0。

## 备注

- 第 8、12 条的页面卡片存在 UI-01 显示 bug（`Tier price RM 0.00`），但 `c04_02` 的商品表、`c04_04` 的 Changes 表与 `sample.json` 的接口值均为 19.00 → 17.00；详见 `README.md` §5。
- 第 9 条“无 DO”在取证时点成立；C06 批准后才会生成 DO。

## r2 修订

第 5 条的 condition 全字段已落盘到 `sample.json.condition`，来源 `GET /api/v1/orders/drafts/DRF_AFC94FC488144FC6932FA4800D73B0EC → conditions[0]`；12/12 的材料支撑完整。r2 已重算 `SHA256.txt` 与 `PACK_SHA256.txt`。
