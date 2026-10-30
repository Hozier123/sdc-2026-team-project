# C04 He 侧交接单（2026-10-30 17:10；r4 签字 23:21）

## 状态

| 项 | 状态 |
|---|---|
| 低价分支（tier 19.00 → 成交 17.00） | **PASS** |
| “待老板批”样例 | **PENDING**：`APR_7A1382B29D5C44FFB6242D15477A60B7`，RM 34.00 |
| 截图 | **已补 4 张**（CLERK 2 + OWNER 2） |
| 检查矩阵 | **12/12 PASS**，0 P0 |
| 独立复核 | **Zhou 2026-10-30 23:21 通过（数据/流程）；UI-01 P3 接受** |
| 入库 | 待 PR；`repo_status=PENDING_COMMIT` |
| C06 | 可直接沿用该 PENDING 样例 |
| Gate A | 已顺延 |
| 包版本 | **r4（SIGNED_OFF）**（ZR-20261030-02-r3 的签字版；r1~r3 已归档） |

受控目录：`C:\Users\n_bom\Desktop\小项目\SDC HACKATHON\03_交接与提交包\C04_low_price_evidence_2026-10-30_r4`
证据包：`evidence/`，逐文件哈希见 `evidence/SHA256.txt`；包级清单见 `PACK_SHA256.txt`。`evidence/` 自带 `.gitattributes`（`* -text`）保持字节。

## 0. 口径

C04 是 Gate A 要求项，只比 C01 多一个分支：**低价 → 送老板**。跑完的产出不是“老板批准”，而是一条稳定的 **PENDING** 审批，供 C06 直接沿用。

- 样例：`DRF_AFC94FC488144FC6932FA4800D73B0EC` v2 / `APR_7A1382B29D5C44FFB6242D15477A60B7`
- 客户：Kedai Rasa（`CUS_RASA`，Tier B）
- 金额：tier 19.00 → 成交 17.00；小计/总额 RM 34.00
- 升级原因：`PRICE_OVERRIDE_BELOW_TIER`（detail 19.00 → 17.00）
- 提交：`USR_T1_CLERK`，2026-10-30 16:57 MYT（08:57:07Z）

## 0.1 r2 修订（2026-10-30 21:5x，回复 Zhan ZR-20261030-02）

1. **PENDING 现值**：21:5x 复核 `GET /approvals/APR_7A1382B29D5C44FFB6242D15477A60B7`，仍为 `PENDING`，`decided_by/decided_at` 为空，C06 未消费；`c06_ready=true` 不变。
2. **PRICE condition 字段**：已补进 `sample.json.condition`，来源 `GET /orders/drafts/DRF_AFC94FC488144FC6932FA4800D73B0EC → conditions[0]`；含 `condition_kind/span/resolved/resolution/confirmed_unit_price`，第 5 条证据闭环。
3. **ENV-01 时间**：README §5 的 `Z` 后缀是笔误，已改为 UTC+8 + 显式 UTC（16:42:21+08 / 08:42:21Z；16:54:32+08 / 08:54:32Z）；`environment.json` 的 `08:54:32Z` 本来就对。
4. **Pages 口径**：前端源码 `f8ff1d7` / Pages 部署 `12ff95f` / Pages HEAD `94f0a6e`（仅记录 index hash，不是部署）。Gate E 决议里的 `94f0a6e` 应按此改写。

## 0.2 r3 修订（2026-10-30 23:09，回复 ZR-20261030-02-r2）

1. **复检时间戳**：`sample.json.rechecked_at=2026-10-30T23:09:16+08:00`，`recheck.status=PENDING`，`decided_at=null`；`acceptance.json.sample.rechecked_at` 同步。
2. **README** 增加“复检时点”一行：capture 17:09:36 / recheck 23:09:16，两次都是 PENDING。
3. **未改动**：4 张截图、`C06_reuse.txt`、condition 字段、Pages 口径；仅重算 `SHA256.txt` / `PACK_SHA256.txt`。

## 0.3 r4 修订（2026-10-30 23:2x，Zhou 复核通过）

1. **独立复核**：Zhou Jingxi 2026-10-30 23:21（UTC+8）复核通过（数据/流程）；UI-01 接受为 P3。记录：`evidence/reviews/01-Zhou-review-r3-2026-10-30.md`。
2. **Zhou 复核的两份哈希与 r3 实际文件一致**：`evidence/SHA256.txt` = `BB289829...A7D9E`；`PACK_SHA256.txt` = `3A2DD4B3...061C07`。
3. **状态**：`acceptance.json` 改为 `PASS_SIGNED_OFF` / `SIGNED_OFF` / `APPROVED`；`repo_status=PENDING_COMMIT` 等 PR 合并后再改。
4. **未改动**：condition、approval、line、4 张截图、matrix、environment、C06_reuse；仅重算哈希。
5. **改动清单**：新增 `evidence/reviews/01-Zhou-review-r3-2026-10-30.md`；修改 `sample.json`（review 元数据）、`acceptance.json`、`README.md`、`HANDOFF_C04.md`、`SHA256.txt`、`PACK_SHA256.txt`。condition/approval/line/4 张截图/matrix/environment/C06_reuse 未动。

## 1. 产物

| 文件 | 说明 |
|---|---|
| `evidence/README.md` | 范围、结果、方法、证据、已知问题、复现 |
| `evidence/acceptance.json` | 机器可读：`PASS_SIGNED_OFF` / `SIGNED_OFF` / `APPROVED` |
| `evidence/sample.json` | 样例事实：ID、tier/effective、condition、field_diffs、stock |
| `evidence/environment.json` | 时间、URL、v1.4.0/f8ff1d7、555f0fa、AI READY |
| `evidence/matrix.md` | 12 条检查逐条期望/实际 |
| `evidence/screenshots/` | `c04_01` ~ `c04_04` |
| `evidence/reviews/01-Zhou-review-r3-2026-10-30.md` | Zhou 独立复核记录（2026-10-30 23:21，通过；UI-01 P3） |
| `evidence/SHA256.txt` | 证据目录逐文件哈希 |
| `C06_reuse.txt` | 给 C06 的交接副本（截图路径已改成本包相对路径） |
| `PACK_SHA256.txt` | 包级清单 |

## 2. 复核结论（Zhou，2026-10-30 23:21：通过；UI-01 P3 接受）

以下清单保留为复核记录，全部已核对。

- [x] `acceptance.json`：`result=PASS_SAMPLE_PENDING_REVIEW`，`numbers.checks_passed=12`，`checks_failed=0`；
- [x] `sample.json`：`approval.status=PENDING`，`tier_unit_price=19.00`，`effective_unit_price=17.00`，`total_rm=34.00`；
- [x] `sample.json.condition`：`condition_kind=PRICE`、`span=kalau RM17`、`resolved=true`、`resolution=ACCEPT_REQUESTED_PRICE`；
- [x] `matrix.md`：12/12 PASS，第 9 条“无 DO”成立；
- [x] 截图 4 张：地址栏含 `DRF_...` / `APR_...`，OWNER 页为 `Awaiting decision`；
- [x] `c04_02` 商品表 19.00 / 34.00，`c04_04` Changes 表 19.00→17.00、38.00→34.00；
- [x] UI-01 已记录（0.00 为显示 bug，不影响数据）；
- [x] 样例仍为 PENDING（未被 C06 提前消费）；
- [x] 无 token / 手机号 / Authorization 落盘。

复核已通过：`acceptance.json` 已改为 `PASS_SIGNED_OFF` / `SIGNED_OFF` / `APPROVED`，并已重算 `SHA256.txt` 与 `PACK_SHA256.txt`。

## 3. 入库（Draft PR，别写“全通过”）

```powershell
$src  = "C:\Users\n_bom\Desktop\小项目\SDC HACKATHON\03_交接与提交包\C04_low_price_evidence_2026-10-30_r4"
$repo = "<sdc-2026-team-project 本地路径>"
git -C $repo switch -c c04/low-price-evidence

New-Item -ItemType Directory -Force "$repo\evidence\e2e\c04\2026-10-30" | Out-Null
Copy-Item "$src\evidence\*" "$repo\evidence\e2e\c04\2026-10-30\" -Recurse
Copy-Item "$src\HANDOFF_C04.md" "$repo\evidence\e2e\c04\2026-10-30\"
Copy-Item "$src\C06_reuse.txt" "$repo\evidence\e2e\c04\2026-10-30\"

git -C $repo add evidence/e2e/c04/2026-10-30
git -C $repo commit -m "evidence(c04): add low-price exception sample (signed off, pending repo)"
git -C $repo push -u origin c04/low-price-evidence
```

Draft PR 建议：

- 标题：`evidence(c04): low-price exception sample (signed off, pending repo)`
- 正文：
  - 低价条件 → `ACCEPT_REQUESTED_PRICE` → `unit_price_override=17.00`（tier 19.00）；
  - `PRICE_OVERRIDE_BELOW_TIER` → `SUBMIT_FOR_OWNER`，审批 PENDING，RM 34.00；
  - 12/12 检查、4 张截图；
  - 状态 `PASS_SIGNED_OFF` / `SIGNED_OFF`；
  - Zhou 2026-10-30 23:21 独立复核通过（数据/流程）；UI-01 接受为 P3；复核记录见 `evidence/reviews/01-Zhou-review-r3-2026-10-30.md`。

## 4. 注意事项

1. **不要 reset_demo**：会删掉这条 PENDING，也会删掉 C08 锚定的 `DO_20261029_453C4BC2`。
2. **不要重新部署/改前端版本**：C08 钉在 f8ff1d7（v1.4.0）/ 后端 555f0fa；C04 不需要发版。
3. **UI-01 是显示 bug**：`ui.tsx:273` 字段名不匹配；真实值看商品表、Changes 表、`sample.json`。Zhou 已接受为 P3；决赛前修或演示避开；C08 签字前不要改/重新部署。
4. **ENV-01**：`c04_01` 的 “AI offline” 是前端不轮询的过期显示；服务端 16:42:21 / 16:54:32（UTC+8，即 08:42:21Z / 08:54:32Z）均 READY，`c04_03` 也显示 AI ready。
5. **C06 消费前保持 PENDING**：C06 批准后才会生成 DO；C06 证据落盘前不要清理。
6. **不要提交令牌**：本包不含 token / 手机号 / Authorization。

## 5. 与 C08 的关系

C04 与 C08 相互独立：C08 只读、锚定 C01 的 DO；C04 新增一条 draft/approval，不改变 C08 的 41 条断言。两者可以并行复核/取证，唯一共享约束是：**不 reset、不重新部署、不改 T1 规则开关**。

C08 的状态仍是 `PASS_API_LAYER_PENDING_REPO` / `NOT_SIGNED_OFF`，不阻塞 C04 的复核；C04 也不阻塞 C08。两者都完成后，Gate A 才能签字。
