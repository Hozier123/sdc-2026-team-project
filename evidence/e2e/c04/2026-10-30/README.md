# C04 低价例外：PASS（已签字；待入库）

执行人：He；执行时间：2026-10-30 16:55–17:00（UTC+8）；环境：生产 API `https://kiraorder-api.replit.app/api/v1`；前端 `https://hozier123.github.io/sdc-2026-team-project/`（v1.4.0 / f8ff1d7）。
对象：T1 / Kedai Rasa（`CUS_RASA`，Tier B）。

**结论：低价分支跑通，已产出唯一一条 PENDING 审批 `APR_7A1382B29D5C44FFB6242D15477A60B7`，金额 RM 34.00，tier 19.00 → 成交 17.00。Zhou Jingxi 于 2026-10-30 23:21（UTC+8）复核通过（数据/流程），UI-01 接受为 P3；整体状态 `PASS_SIGNED_OFF`（`SIGNED_OFF`），等待入库/PR。**

> **r2（2026-10-30 21:5x，回复 Zhan ZR-20261030-02）**：补 `sample.json` 的 PRICE condition 字段；修 ENV-01 时间后缀；补 Pages 部署/HEAD 唯一口径。哈希已重算；r1 原件不动。

> **r3（2026-10-30 23:09，回复 ZR-20261030-02-r2）**：补 `rechecked_at=2026-10-30T23:09:16+08:00` / `recheck_status=PENDING` / `decided_at=null`。包内 `captured_at=17:09:36` 是取证时点，23:09 是最近复检；4 张截图与 `C06_reuse.txt` 字节未动。

> **r4（2026-10-30 23:2x，Zhou 复核通过）**：加入 `reviews/01-Zhou-review-r3-2026-10-30.md`；`acceptance.json` 改为 `PASS_SIGNED_OFF` / `SIGNED_OFF` / `APPROVED`。改动文件：`sample.json`（review 元数据）、`acceptance.json`、`README.md`、`HANDOFF_C04.md`、`SHA256.txt`、`PACK_SHA256.txt` + 新增 review 文件；condition/approval/line/4 张截图/matrix/environment/C06_reuse 字节未动。

## 1. 本次补的是什么

C04 的任务口径：Gate A 要求项；只比 C01 多一个分支（低价 → 送老板）；跑完产出“待老板批”的稳定样例（固定输入 + 步骤），C06 直接沿用。

本包不重复 C01 的基础流程，只补三块：

1. 低价条件 → `ACCEPT_REQUESTED_PRICE` → 行级 `unit_price_override=17.00`（tier 19.00）；
2. 保存后 `PRICE_OVERRIDE_BELOW_TIER` escalation → `SUBMIT_FOR_OWNER`；
3. 一条 PENDING 审批的固定样例：draft/approval ID、金额、时间、4 张截图。

## 2. 结果

| 检查 | 结果 |
|---|---|
| 低价条件识别 | PASS（“kalau RM17”，见 `sample.json.condition`） |
| 成交价低于 tier | PASS（17.00 < 19.00） |
| escalation | PASS `PRICE_OVERRIDE_BELOW_TIER` |
| 送老板而非直接生成 DO | PASS `SUBMIT_FOR_OWNER` |
| 草稿状态 | PASS `PENDING_OWNER_APPROVAL`，v2 |
| 审批 | PASS `PENDING`，RM 34.00，1 行 |
| 阈值干扰 | 无（34.00 < T1 阈值 1500.00，只有低价一条原因） |
| 截图 | 4 张（CLERK 2 + OWNER 2） |

关键证据：

- [sample.json](sample.json)：机器可读样例事实（ID、金额、tier/effective、condition、field_diffs、stock）。
- [matrix.md](matrix.md)：12 条检查逐条期望/实际。
- [screenshots/](screenshots/)：4 张，含地址栏与 draft/approval ID。

## 3. 方法：为什么这个结果可信

1. **全程 UI + 生产 API**：不连数据库、不跑迁移、不 reset；写入只发生在 C04 本身的建单/保存/送审。
2. **令牌不落盘**：只从本地私有 `demo_tokens.json` 读入浏览器内存；本包不含 token、手机号、Authorization。
3. **双重核对**：UI 商品表/Changes 表 + `GET /api/v1/approvals/{id}` 返回值一致（19.00 → 17.00，34.00）。
4. **字节级存证**：4 张原图逐张 SHA-256，见 [SHA256.txt](SHA256.txt)；本目录带 `.gitattributes`（`* -text`），避免 CRLF 归一化后哈希对不上。
5. **时间窗口内 AI READY**：服务端 16:42 与 16:54（UTC+8）两次核到 `READY`；CLERK 截图的 “AI offline” 是前端不自动轮询的过期显示，详见 §5。

### 3.1 版本唯一口径（回复 ZR-20261030-02 第 4 条）

| 名称 | 提交 | 说明 |
|---|---|---|
| 前端源码 | `f8ff1d7` | Gate E 版本；Pages 构建来源 |
| Pages 部署 | `12ff95f` | “Deploy B01 frontend from f8ff1d7”，2026-10-29T11:51:25Z |
| Pages HEAD | `94f0a6e` | “Record the published LF index hash”，2026-10-29T12:02:52Z；**部署后索引记录，不是部署本身** |

现场/PPT 统一写法：**前端 `f8ff1d7` / Pages 部署 `12ff95f`**。`94f0a6e` 只能写成“Pages HEAD/索引记录”，不能写成部署提交。

## 4. 证据清单

| 文件 | 说明 |
|---|---|
| [acceptance.json](acceptance.json) | 机器可读结论与边界 |
| [sample.json](sample.json) | 样例事实：draft/approval、tier/effective、condition、field_diffs、stock |
| [environment.json](environment.json) | 时间、URL、前后端版本、租户/角色、AI 状态 |
| [matrix.md](matrix.md) | 12 条检查的期望/实际/证据 |
| [screenshots/](screenshots/) | 4 张截图（CLERK 2 + OWNER 2） |
| [screenshots/README.md](screenshots/README.md) | 每张图证明什么 |
| [reviews/01-Zhou-review-r3-2026-10-30.md](reviews/01-Zhou-review-r3-2026-10-30.md) | Zhou Jingxi 独立复核记录（2026-10-30 23:21，通过；UI-01 P3） |
| [SHA256.txt](SHA256.txt) | 本目录文件哈希（不含自身） |
| [.gitattributes](.gitattributes) | `* -text`，保证提交后字节不被归一化 |

## 5. 已知问题

### UI-01（P3，仅显示）

CLERK 草稿页的 “Owner review” 卡片、OWNER 审批页的 “Approval reasons” 卡片显示：

```text
Tier price RM 0.00 → requested RM 0.00
```

原因：`ui.tsx:273` 读的是 `detail.tier_price` / `detail.applied_price`，后端返回的是 `detail.tier_unit_price` / `detail.effective_unit_price`，取不到就回退成 `"0"`。

真实数据（接口与页面双重核对）：

```text
GET /api/v1/approvals/APR_7A1382B29D5C44FFB6242D15477A60B7
reasons[0].code   = PRICE_OVERRIDE_BELOW_TIER
reasons[0].detail = {"tier_unit_price":"19.00","effective_unit_price":"17.00"}
total_rm          = 34.00
snapshot.lines[0] = SKU_MILO_1KG, 2 bag, tier 19.00, effective 17.00, subtotal 34.00
```

处理：记录为 P3 UI 显示缺陷；**不要在 C08 复核/入库前改前端或重新部署**（C08 仍钉在 f8ff1d7 / v1.4.0）。Zhou 2026-10-30 23:21 接受为 P3；决赛前建议修，或演示时避开该卡片；修复/重新部署要等 C08 签字后。

### ENV-01（P3，仅显示）

`c04_01` 顶部显示 “AI offline”，但它是前端只刷新一次状态、之后不轮询造成的过期显示。服务端在 **16:42:21（UTC+8，即 08:42:21Z）** 与 **16:54:32（UTC+8，即 08:54:32Z）** 均为 `READY`，OWNER 页 `c04_03` 也显示 “AI ready”。不是“AI 离线也能抽单”的矛盾。

> r2 修正：早期版本这里写成 “16:42:21Z / 16:54:32Z”，Z 后缀是笔误（数值是 UTC+8 钟点）；`environment.json` 的 `checked_at=2026-10-30T08:54:32Z` 本来就是正确的 UTC。

## 6. 复现

固定输入：

```text
客户：Kedai Rasa（CUS_RASA，Tier B）
原文：Milo 1kg 2 bag, kalau RM17 boleh?
商品：Milo 美禄 1kg（SKU_MILO_1KG）
数量：2 bag
tier：19.00；成交：17.00；小计/总额：34.00
override 原因：Customer asked RM17 per 1kg bag; below tier price, owner approval required.
```

步骤：

1. CLERK 令牌连接 API；
2. New order → Kedai Rasa → 输入原文 → Create order draft；
3. Price condition → **Accept a requested discount**（Owner decides）→ 勾选 Milo → Confirmed price `17.00` → 填原因 → **Record decision**；
4. **Save changes**（v2）；
5. 出现 `PRICE_OVERRIDE_BELOW_TIER` → **Send to owner**；
6. 草稿变 `PENDING_OWNER_APPROVAL`，approval 变 `PENDING`；
7. OWNER 令牌 → Owner approvals → 核对 19.00 → 17.00、34.00（**不要批准**，留给 C06）。

## 7. 边界与未签字项

- **独立复核**：Zhou Jingxi 于 2026-10-30 23:21（UTC+8）复核通过（数据/流程）；UI-01 接受为 P3；记录见 [reviews/01-Zhou-review-r3-2026-10-30.md](reviews/01-Zhou-review-r3-2026-10-30.md)。
- **入库**：`repo_status=PENDING_COMMIT`；建议按 `evidence/e2e/c04/2026-10-30/` 入库。
- **C06 依赖**：样例必须保持 `PENDING` 直到 C06 消费；C06 之前不要 reset。
- **C08 依赖**：C08 锚定 `DO_20261029_453C4BC2`；C08 签字前 reset 会毁掉 C08 的可复现性。
- **复检时点**：`captured_at=2026-10-30 17:09:36+08`；`rechecked_at=2026-10-30 23:09:16+08`；两次均 `PENDING`、`decided_at=null`（见 `sample.json.recheck`）。
- 不在 C04 范围：C06 的批准/拒绝、DO 生成、库存扣减。

## 8. 结论

- C04 的低价分支与“待老板批”样例**已完成**，Zhou 2026-10-30 23:21 复核通过；状态 `PASS_SIGNED_OFF`（`SIGNED_OFF`）。
- 剩余：入库/PR；C06 可直接用 `APR_7A1382B29D5C44FFB6242D15477A60B7`。
- 入库前保持 `repo_status=PENDING_COMMIT`；PR 合并后再改 `COMMITTED`。
