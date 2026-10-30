# C06 He 侧交接单（2026-10-31 02:20）

## 状态

| 项 | 状态 |
|---|---|
| 环境 | B05 隔离环境 `b05-env-ea709a8e70d0`（firstuse 51394 / protected 51391） |
| 缺货阻断 | **PASS**：Teh 10 > 3 → `INSUFFICIENT_STOCK`；批准 400 `DISAMBIGUATION_UNRESOLVED`，无 DO |
| 减量/批准 | **PASS**：减到 3 → `DO_20261030_77EBD4F2`，库存 3→0 |
| 库存变化 | **PASS**：Milo 人工 30→1；OWNER 批准 409 `STOCK_CHANGED`；审批仍 PENDING，无 DO |
| 恢复/批准 | **PASS**：恢复 30 → `DO_20261030_6FC83E94`，库存 30→28，APPROVED |
| 检查矩阵 | **13/13 PASS**，0 P0 |
| 复位 | **PASS**：dry-run + apply；firstuse 795/0；protected 不变 |
| 独立复核 | **Zhou APPROVED**（技术层 API+DB，13/13，0 P0） |
| 形式复核 | **Zhan PASS**：原件 `ZR-20261031-03`；公开副本另核 `ZR-20261031-04` |
| 入库 | 未提交，按“待入库”处理 |
| Gate A | `DEFERRED`；C06 不是 Gate A 条目 |

受控目录（对外文档用占位符）：`<C06_package>`
证据包：本目录，逐文件哈希见 `SHA256.txt`（51 项）。
签字原件：`C06_stock_shortage_evidence_2026-10-31.zip`，86,506 B，SHA-256 `89AC444265CADB22DAEBF1659FFA01F7A6A3A0A86D5251F7FE271488CF2F58A6`（46/46、59/59 由 Zhan 实算通过）。本目录是公开脱敏派生副本，不含 `scripts/`。

## 0. 口径

C06 是“缺货与库存变化”的隔离库技术验收：唯一需要人为改库存的场景，必须在独占隔离库执行并在结束时复位。本包不重复 C04 的低价分支，也不消费生产 C04 的 PENDING 样例。

- 环境：`b05-env-ea709a8e70d0`，源码绑定 `c8848ef`，模式 `LOCAL_SYNTHETIC_T1_FALLBACK`
- 客户/商品：CUS_SINAR / `SKU_TEH_500G`（9.00）；CUS_RASA / `SKU_MILO_1KG`（tier 19.00 → 17.00）
- 执行：2026-10-31 01:45–01:48（UTC+8）

## 1. 产物

| 文件 | 说明 |
|---|---|
| `evidence/README.md` | 范围、结果、方法、证据、已知问题、复现 |
| `evidence/acceptance.json` | 机器可读：`PASS_TECHNICAL_SIGNED_OFF` / `SIGNED_OFF` / `PENDING_COMMIT` / `gate_a_status=DEFERRED` |
| `evidence/sample.json` | 两个场景的 ID、金额、库存前后值 |
| `evidence/environment.json` | 环境 ID、两侧端口/库、PG 17.10、源码绑定 |
| `evidence/matrix.md` | 13 条检查逐条期望/实际；含 raw/02 vs raw/04、snapshot 说明 |
| `evidence/reviews/` | Zhou APPROVED、Zhan 形式 PASS 回执 |
| `evidence/raw/` | 19 条原始 API 请求/响应（令牌、电话已剔除） |
| `evidence/db/` | 基线、缺货后、409 后、批准后、复位前后、两侧对比、改库存记录 |
| `evidence/reset/` | dry-run/apply 报告、reset 导出摘要、审计抽取、日志 |
| `evidence/meta/` | B05 交付的 technical-acceptance 与 environment-public（路径已脱敏） |
| `evidence/PUBLIC_EXPORT.md` | 公开副本与签字原件的派生、脱敏和哈希说明 |

## 2. 复核结论（已取得）

- **Zhou Jingxi**：`C06 APPROVED`（技术层 API+DB；13/13，0 P0）。LIM-01 接受但只能写 API+DB、不能写浏览器/UI；LIM-02 接受（`c8848ef` 与复核时 main `f1e40fd` 差异仅 B02 `catalog.py` + `main.py` 2 行）。**He 转录自微信，Zhou 未审阅文件版式。**
- **Zhan**：形式 PASS + 索引号 `ZR-20261031-03`；PACK 59/59、evidence 46/46、外层 zip `89AC…58A6`、路径 `evidence/e2e/c06/2026-10-31/` 无冲突、环境绑定 4/4、无 token/密码/Authorization/电话。**公开副本另核 `ZR-20261031-04`**：raw 19/19、db 11/11 与原件逐字节相同，`SHA256.txt` 51/51，11 个改动均在声明范围。**He 转录，Zhan 未审阅文件版式。**

复核回执见 `evidence/reviews/01-Zhou-approval-2026-10-31.md`、`evidence/reviews/02-Zhan-formal-2026-10-31.md`。

## 3. 入库（Draft PR，别写“全通过”）

```powershell
$src  = "<C06_public_package>"
$repo = "<sdc-2026-team-project 本地路径>"
git -C $repo switch -c c06/stock-shortage-evidence

New-Item -ItemType Directory -Force "$repo\evidence\e2e\c06\2026-10-31" | Out-Null
Copy-Item "$src\evidence\*" "$repo\evidence\e2e\c06\2026-10-31\" -Recurse
Copy-Item "$src\HANDOFF_C06.md" "$repo\evidence\e2e\c06\2026-10-31\"

git -C $repo add evidence/e2e/c06/2026-10-31
git -C $repo commit -m "evidence(c06): stock shortage and manual stock change in isolated env (signed off)"
git -C $repo push -u origin c06/stock-shortage-evidence
```

Draft PR 建议：

- 标题：`evidence(c06): stock shortage and manual stock change in isolated env (signed off)`
- 正文：
  - 缺货 `INSUFFICIENT_STOCK` 阻断；减量 3 后 `DO_20261030_77EBD4F2`；
  - 人工改库存 30→1；OWNER 批准 409 `STOCK_CHANGED`；恢复后 `DO_20261030_6FC83E94`，30→28；
  - 复位 PASS：firstuse 795/0，protected 不变；
  - 13/13 检查；Zhou APPROVED（转录）、Zhan 形式 PASS + `ZR-20261031-03`，公开副本 `ZR-20261031-04`；
  - 状态 `PASS_TECHNICAL_SIGNED_OFF` / `SIGNED_OFF`；API+DB 技术验收，无浏览器/UI 通过；
  - 源码绑定 `c8848ef`；原件 zip SHA-256 `89AC…58A6`；公开副本脱敏路径、不含 `scripts/`。

## 4. 注意事项

1. **不要连生产**：本包只在 `b05-env-ea709a8e70d0` 的 firstuse 侧执行；生产 C04/C08 未改动。
2. **不要消费 C04 的 PENDING**：它仍在生产，留给生产侧主线；C06 用的是隔离库新样例。
3. **复位入口只接受该环境**：`reset-firstuse` 只接受生成的目标；不要用生产 DSN。
4. **版本**：环境绑定 `c8848ef`；换环境或换源码需重新 create 并记录新版本。
5. **公开副本**：`scripts/` 不入库；`evidence/` 已脱敏本机路径与备份库名；技术证据 `raw/`、`db/` 字节未改。
6. **Gate A**：C06 不是 Gate A 条目；`gate_a_status=DEFERRED`，本包不改变 Gate A 状态。

## 5. 与 C04/C08 的关系

- C06 与 C04 独立：C04 证明“低价 → 送老板审批”；C06 证明“缺货/库存变化与复位”。C04 的生产 PENDING 未被 C06 消费。
- C06 与 C08 独立：C08 锚定生产 `DO_20261029_453C4BC2`；本包未连接生产库，未 reset。
- 本包不改变 C04/C08 的结论，也不替代 Gate A 签字。
