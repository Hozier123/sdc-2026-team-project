# C06 缺货与库存变化：PASS（技术验收；已复核）

执行人：He；执行时间：2026-10-31 01:45–01:48（UTC+8）；环境：B05 隔离环境 `b05-env-ea709a8e70d0`（firstuse 侧，loopback）；模式 `LOCAL_SYNTHETIC_T1_FALLBACK`；源码绑定 `c8848ef`。

**结论：缺货阻断、人工改库存后的 409 复核、减量/恢复后的批准与扣库存、以及结束复位全部跑通。13/13 检查 PASS，0 P0；firstuse 复位回 40 SKU / 795 / 空流水，protected 侧 12 类业务表与检查点不变。状态 `PASS_TECHNICAL_SIGNED_OFF`（`SIGNED_OFF`），Zhou APPROVED、Zhan 形式 PASS（原件 `ZR-20261031-03`；公开副本另核 `ZR-20261031-04`）。**

## 0. 复核与公开副本（r2-public）

- **Zhou Jingxi**：`C06 APPROVED`（技术层 API+DB；13/13，0 P0）。两个限制接受：LIM-01 只能写 API+DB 技术验收、不能写浏览器/UI 通过；LIM-02 接受，`c8848ef` 与当时 main `f1e40fd` 的差异只有 B02 `catalog.py` + `main.py` 2 行，C06 相关 app/B05 工具/seed/gate0 一致。
- **Zhan**：形式复核 **PASS**，索引号 `ZR-20261031-03`；外层 zip `89AC…58A6`、59/59 PACK、46/46 evidence 全通过；路径 `evidence/e2e/c06/2026-10-31/` 无冲突；环境绑定与 B05 交付 4/4 一致；无 token/密码/Authorization/电话。**公开副本另核 `ZR-20261031-04`**：raw 19/19、db 11/11 与原件逐字节相同，`SHA256.txt` 51/51，11 个改动均在声明范围。
- **转录说明**：`reviews/` 两份回执均为 He 转录自微信；Zhou/Zhan 未审阅文件版式。Zhou 原消息时间未单独记录，转录时间 2026-10-31T02:46+08:00。
- **r2-public 改动**：按 Zhou/Zhan 的 P3 修正矩阵第 3 条的两个来源、补 raw/13/14 snapshot 说明、补 `gate_a_status=DEFERRED`、澄清 db 文件计数；公开副本脱敏本机路径与备份库名，**不含 `scripts/`**。技术证据（`raw/`、`db/`）字节未改。
- **签字原件**：`C06_stock_shortage_evidence_2026-10-31.zip`，86,506 B，SHA-256 `89AC444265CADB22DAEBF1659FFA01F7A6A3A0A86D5251F7FE271488CF2F58A6`（46/46、59/59 由 Zhan 实算通过）。本目录是脱敏派生副本，哈希见本目录 `SHA256.txt`（51 项）。

## 1. 本次补的是什么

C06 的任务口径：**缺货与库存变化**；唯一需要人为改库存的场景；必须在独占隔离库执行，并在结束时复位；用前后快照对齐。

本包在 B05 交付的隔离环境里补三块：

1. **缺货**：超库存下单 → `INSUFFICIENT_STOCK` 阻断批准；减量到可满足后放行。
2. **库存变化**：草稿已送老板后，直接 SQL 把 Milo 30→1；老板批准返回 `409 STOCK_CHANGED`，不生成 DO、不扣负库存；恢复库存后批准成功，库存 30→28。
3. **复位**：`reset-firstuse` dry-run + apply；firstuse 回初态，protected 侧不变。

## 2. 结果

| 检查 | 结果 |
|---|---|
| 缺货识别（Teh 10 > 3） | PASS `INSUFFICIENT_STOCK`，blocking |
| 缺货时批准 | PASS 400 `DISAMBIGUATION_UNRESOLVED`，无 DO |
| 减量 10→3 | PASS v2 `READY_FOR_APPROVAL`，27.00 |
| 减量后批准 | PASS `DO_20261030_77EBD4F2`，库存 3→0 |
| 低价审批（19.00→17.00，34.00） | PASS 202 `APR_38289BAEB48A41C79C09F185A07D3A65` PENDING |
| 人工改库存（Milo 30→1） | PASS SQL rowcount 1，前后值留档 |
| 库存变化后批准（OWNER） | PASS 409 `STOCK_CHANGED`，审批仍 PENDING，无 DO |
| 恢复库存后批准 | PASS `DO_20261030_6FC83E94`，库存 30→28，APPROVED |
| 库存守恒 | PASS 795−3−2=790，无负库存 |
| 复位 | PASS firstuse 795/0；protected 不变 |

## 3. 方法：为什么这个结果可信

1. **独占隔离库**：firstuse 与 protected 是两个独立 PG 17.10 cluster / 两个独立 API（51394 / 51391）；与生产 C04/C08 演示库完全隔离，未连接、未 reset。
2. **人为改库存是真实 SQL**：`UPDATE inventory SET available_qty=1 ...`，记录 before/after、rowcount 与时间；不是 mock。
3. **三重对齐**：API 原始响应 + 数据库前后快照 + 复位前导出（含 audit/activity/field_diff）。
4. **阻断无副作用**：409 前后 `audit_logs` 均为 5，审批仍 PENDING、`decided_by=null`，草稿仍 `PENDING_OWNER_APPROVAL`。
5. **字节级存证**：19 条原始响应、8 份 DB 快照 + 3 份辅助、复位报告与日志全部落盘；逐文件 SHA-256 见 `SHA256.txt`。
6. **复位可验证**：B05 工具自身断言 protected 12 类业务表/检查点与 API PID/instance 不变；本包再用独立 DB 快照复核 firstuse 795/0、protected 793/1 DO 不变。

## 4. 证据清单

| 文件 | 说明 |
|---|---|
| `acceptance.json` | 机器可读结论、13 项检查、复核与边界 |
| `sample.json` | 两个场景的 ID、金额、库存前后值、时间 |
| `environment.json` | 环境 ID、两侧端口/库、PG 版本、源码绑定 |
| `matrix.md` | 13 条检查逐条期望/实际/证据；含 P3 修正说明 |
| `reviews/` | Zhou APPROVED、Zhan 形式 PASS 回执 |
| `raw/` | 19 条原始 API 请求/响应（令牌、电话已剔除） |
| `db/` | 基线、缺货后、409 后、批准后、复位前后、两侧对比、两次改库存记录 |
| `reset/` | dry-run/apply 报告、reset 导出摘要、审计抽取、日志 |
| `meta/` | B05 交付的 technical-acceptance 与 environment-public（路径/备份名已脱敏） |
| `PUBLIC_EXPORT.md` | 公开副本与签字原件的派生、脱敏和哈希说明 |

关键 ID：

- 缺货草稿 `DRF_7E91987524DA4A6C857E170769EDAE94` → `DO_20261030_77EBD4F2`（3 × 9.00 = 27.00）
- 低价审批草稿 `DRF_BDBE7DE379764193A467498773FC80AE` → `APR_38289BAEB48A41C79C09F185A07D3A65` → `DO_20261030_6FC83E94`（2 × 17.00 = 34.00）
- 库存：Milo 30 →（人工）1 →（恢复）30 →（批准扣减）28；Teh 3 → 0；总量 795 → 790 → 795（复位）

## 5. 已知问题与限制

- **C06-LIM-01**：本包是 **API + DB 技术验收**，没有浏览器截图；不能写成“浏览器/UI 通过”。隔离环境的 UI 呈现未做交互验收。
- **C06-LIM-02**：环境绑定源码 `c8848ef`，非当前 main。复核时 main `f1e40fd`；PR base `bc8f4aa`；当前 main `befac4c`。Zhou 核对时差异只有 B02 `catalog.py` + `main.py` 2 行，C06 相关 `backend/app`、B05 工具、seed、gate0 一致。证据只对该绑定成立，换环境需重新 create 并记录新版本。
- **C06-LIM-03**：探测阶段创建过一条未使用草稿 `DRF_198ABA85C3FC4DB8A4C334E9E7FDCD7F`（Milo 2 bag，v1 READY，未保存/未批准），复位时清除，不计入检查与库存差额。
- 缺货时批准返回的是 `DISAMBIGUATION_UNRESOLVED`（先阻断未解决问题），不是 `INSUFFICIENT_STOCK`；缺货本身由 issue code 证明。
- 409 由 OWNER 决定路径触发；CLERK 直接批准路径在同场景下返回 400 `INSUFFICIENT_STOCK`，两者都阻断，本包只记录实际走到的路径。
- `raw/13`、`raw/14` 的 `available_qty=30` 是送审 snapshot，不是 409 当时的实时值；实时值是 1（见 `raw/12` 与 `db/b5_manual_stock_down.json`）。
- 无真实 LLM、无真实受试者、无 TEST32；FALLBACK 模式。

## 6. 复现

环境已由 B05 交付；本包未重新 create，只使用并复位。复跑时：

```powershell
# 1) 进入 B05 worktree 的 backend，使用交付环境
python -m tools.b05_environment --state "<b05-env>/environment.json" status
python -m tools.b05_environment --state "<b05-env>/environment.json" start
python -m tools.b05_environment --state "<b05-env>/environment.json" check

# 2) 按 raw/ 里的顺序重放：
#    parse-draft -> approve(缺货 400) -> PUT lines(3) -> approve(DO)
#    parse-draft(低价) -> PUT lines(override 17) -> approve(202)
#    SQL 改库存 30→1 -> decide(409) -> SQL 恢复 30 -> decide(DO)
#    snapshot -> reset-firstuse (dry-run) -> reset-firstuse --apply

# 3) 复位
python -m tools.b05_environment --state "<b05-env>/environment.json" reset-firstuse
python -m tools.b05_environment --state "<b05-env>/environment.json" reset-firstuse --apply
```

注意：`reset-firstuse` 只接受该环境生成的 firstuse 目标；不要用生产 DSN、不要 reset 生产演示库。

## 7. 边界与未签字项

- **独立复核**：`independent_review_status=PASSED`；Zhou APPROVED（转录，2026-10-31），Zhan 形式 PASS + `ZR-20261031-03`；公开副本 `ZR-20261031-04`。
- **入库**：`repo_status=PENDING_COMMIT`；路径 `evidence/e2e/c06/2026-10-31/`。
- **Gate A**：`gate_a_status=DEFERRED`；C06 不是 Gate A 条目，本包不改变 Gate A 状态。
- **生产**：未连接、未 reset、未改动；本包所有 API 请求都发往 `127.0.0.1:51394`；C04 的生产 PENDING 样例未被消费。
- **C04/C08**：C06 不改变两者结论；C08 的 DO 锚点与 C04 的样例均未触碰。
- **复位能力**：属于 B05 交付；本包只证明本次 C06 使用它并复核了保护侧不变。
- **公开副本**：相对签字原件只做了路径/备份名脱敏与 P3 措辞修正；技术证据字节未改。原件 zip SHA-256 `89AC…58A6`。

## 8. 结论

- C06 的缺货、库存变化、批准/扣库存、复位链路已跑通，状态 `PASS_TECHNICAL_SIGNED_OFF`。
- 技术层：Zhou APPROVED（转录）；形式层：Zhan PASS + `ZR-20261031-03`，公开副本 `ZR-20261031-04`；`repo_status=PENDING_COMMIT`，待 Draft PR 入库。
