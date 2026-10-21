# KiraOrder Gate 0 复审报告（Revision 2）

> **复审对象**：`C:\Users\n_bom\Desktop\Gate 0`（48 个受哈希产物）
> **唯一基线**：v2.1，SHA-256 `5D02EBF84413B7FE617C32B64E707AFF476EBD963E6638091C875EE0D1B8A55D`
> **执行提案**：Revision 2，SHA-256 `40DA19F4FE5CA0282B7127F66E934872B91A2BD920F8D833B79BEAB0684DF12B`
> **上一轮审查**：`Gate0_审查报告与修改建议_2026-10-21.md`，SHA-256 `F477633979D0C10BDEC27611D870094E4B6FF28E2855350C16D6AC910BE75840`
> **复审时间**：2026-10-21 20:30（UTC+8）
> **结论**：**95/100。P0-1—P0-13 全部闭合；再补 3 个“一句话契约”即可签字。** 这已经是一份可信的公共施工图，不是上一轮的“骨架稿”。

---

## 0. 一页结论

### 0.1 与上一轮相比的变化

| 项 | 上一轮 | 本轮 | 判断 |
|---|---|---|---|
| 受哈希产物 | 35 | **48** | 新增 tests/scripts/requirements/package/lock/review-resolution/log |
| P0 阻断项 | 13 个未闭合 | **13 个全部闭合** | 见 §2 |
| 前端字段完整性 | OrderDraft/DraftSummary/Me/Approval/DO 缺字段 | **已补齐并有机器测试** | `test_openapi_completeness.py` |
| H1/H5 验证 | 只查 JSON 行数 | **确定性 oracle 实际执行 9+11 例** | `test_h1_behavior.py`、`test_h5_behavior.py` |
| DDL 验证 | grep 表名 | **PGlite 空库执行 18 表/12 trigger 事件** | `test_migration_smoke.py` + log |
| 可重现 | 无 requirements | **Python requirements + pnpm lock + verify 脚本 + 日志** | 仍有“未预装”问题，见 §3.2 |
| 签字 | 后端待确认 | **后端待最终哈希确认；前端/AI/数据未签** | 未 tag，正确 |

### 0.2 评分

| 维度 | 分数 | 判断 |
|---|---:|---|
| 版本/哈希纪律 | 5.0 | 48/48 产物、6 个外部输入、4 个受保护文件全部哈希一致 |
| 物理 schema | 4.8 | 18 表、JSONB 聚合、不可变/append-only、身份/信用/别名撤销/审计字段都补了 |
| OpenAPI 结构 | 5.0 | 13 路径、23 错误码、官方 3.1 校验、`X-Request-ID`、本地 ref 全解析 |
| OpenAPI 语义完整性 | 4.8 | 上一轮缺的前端字段已补；只剩少量 P1/P2 |
| H1/H5 规格与验证 | 4.8 | 规则、词表、真值表、oracle、负例都齐；H5 的 UNIT 正向用例可再加 |
| 测试/可重现 | 4.3 | 29 passed / 0 skip 的日志与脚本齐；当前 shell 未预装依赖，需 bootstrap/CI |
| 治理/签字 | 4.8 | manifest/review-resolution/validation/signoff 分层很好；四方签名未完成 |
| **综合** | **4.75（95/100）** | **可进入签字评审；先补 3 个契约歧义** |

### 0.3 签字前只剩 3 个“一句话契约”

1. **`condition_id` 未定义**：`fields.md` 说库存疑点稳定派生键是 `(draft_id,line_id,issue_code,condition_id|null)`，但 `Issue`/OpenAPI 没有 `condition_id` 字段。要么加字段，要么把键改成 `(draft_id,line_id,issue_code,condition_kind,span_start)`。否则 H3/H5 的“重算”实现会各写一套。
2. **`GET /approvals` 与 `GET /approvals/{id}` 仍写 “OWNER only”**：02 §4.3/§13.4 要求 CLERK 能看“自己提交的审批状态”。要么加 `?mine=true`/CLERK 只读过滤，要么明确把 02 的入口删掉；不能让前端按 02 做、后端按 OpenAPI 403。
3. **PII 掩码 token 格式没写死**：fixture 用 `[PHONE]`，v2.1/01 用 `[REDACTED_*]`，03 没规定。Gate 0 应固定 `[REDACTED_PHONE]`/`[REDACTED_MYKAD]`/`[REDACTED_EMAIL]`（或统一 `[PHONE]`），并让 fixture、PII 测试、span 示例一致。这是安全边界和展示一致性的最后一厘米。

> 这三条都是“一句话/一个字段”的修复，不是架构问题。修完重算哈希、四方签字，就可以 tag `gate0-v1`。

---

## 1. 已核验事实

- `docs/gate0-hashes.txt` 列出 **48** 个产物；逐文件重算 SHA-256，**0 个不匹配**。
- `baseline-manifest.json` 中 v2.1、Revision 2、前序复审、Revision 1 复审、Orbyte 参考、执行手册、上一轮 Gate 0 审查，以及 `01`—`04` 四个受保护文件，**全部哈希一致**。
- OpenAPI：**13 个 P0 路径**、**23 个错误码**、官方 `openapi-spec-validator` 校验通过、每个 response component 带 `X-Request-ID`。
- 迁移：**18 张表**、**12 个 trigger 事件**（5 个 append-only/immutable × UPDATE/DELETE + 审批 UPDATE/DELETE）；PGlite 空库执行通过。
- tests：`gate0-validation.log` 记录 **29 passed / 0 failed / 0 skipped**；`test_demo_path` 不再 skip，而是断言“无业务代码”。
- H1：9 个 required case（4 基础 + 类型 + DEV-39—41）由确定性 oracle 执行。
- H5：11 行真值表逐行执行；`RM95 for 5 ctn` 固定 `price_basis=UNKNOWN`、`amount_allocation=UNALLOCATED`，没有非法 `UNKNOWN_OR_TOTAL`。
- Gate 0 状态：`GATE0_DRAFT_AWAITING_CROSS_FUNCTIONAL_SIGNOFF`；`approved_by=null`；未创建 `gate0-v1` 标签。

**可重现性说明**：当前 Gate 0 目录有 `tests/contract/requirements.txt`、`package.json`、`pnpm-lock.yaml`、`scripts/verify_gate0.py`、`scripts/verify_migration_pglite.cjs`，验证日志也写了固定版本和命令。但当前 shell 没有预装 Python 依赖和 Node/PGlite（`py -3` 缺 `yaml`，`node` 不在 PATH），所以我不能在这个 shell 直接复跑 29 个测试。这不是契约错误，但建议加一个 `scripts/bootstrap_gate0.ps1` 或 CI，让“任何人拿到 Gate 0 都能一键复验”。

---

## 2. P0-1—P0-13 闭合情况

| 上一轮 P0 | 本轮落地 | 证据 | 状态 |
|---|---|---|---|
| P0-1 安全边界：parse 收 `masked_text` | 改为 `message_text`；响应 `masked_message`；后端负责掩码 | `ParseDraftRequest.required=[customer_id,message_text]`；fixture 带手机号、响应 `[PHONE]` | ✅ |
| P0-2 OrderDraft 缺前端字段 | 补 `customer/masked_message/conditions/totals/allowed_actions/blocked_actions` | OpenAPI `OrderDraft`；fixture `parse_draft` | ✅ |
| P0-3 DraftSummary 缺列表字段 | 补 `customer_name/message_preview/open_blocking_issue_count/owner_escalation_count/extraction_sources/allowed_actions` | OpenAPI `DraftSummary`；completeness test | ✅ |
| P0-4 MeResponse 缺租户/权限摘要 | 补 `tenant:{id,name}`、`permissions:AllowedAction[]`、`permission_summary` | OpenAPI `MeResponse`；completeness test | ✅ |
| P0-5 Approval 缺客户/总额/动作 | 补 `customer/total_rm/line_count`、`customer_name` snapshot、`stock_check`、`OWNER_APPROVE/OWNER_REJECT` | `ApprovalRequest/Detail/Snapshot`；fixtures | ✅ |
| P0-6 H4 别名写入口 | `WorkingLineInput` 加 `save_to_alias_cache/alias_scope` | OpenAPI + `save_lines_ready` fixture；fields §5 | ✅ |
| P0-7 DO/仓库模型 | 独立 `DeliveryOrderLine`（含 `applied_unit_price`）与 `WarehouseDeliveryOrder` | OpenAPI；`approve_200`/`audit_detail` fixtures | ✅ |
| P0-8 AI 状态枚举 | 统一 `AiState=OFFLINE/WARMING/READY/DEGRADED`；补 `fallback_available/last_checked_at/message` | OpenAPI；completeness test | ✅ |
| P0-9 用户认证 | `users.demo_token_hash NOT NULL UNIQUE`；不存明文 | migration L20；db-schema §3 | ✅ |
| P0-10 信用标记 | `credit_flag: NONE/OVERDUE_NOTICE`；UI 布尔派生 | migration L33—34；`CreditFlag` enum | ✅ |
| P0-11 span wire | `span` 字符串 + `span_start/span_end`；`source_span` deprecated 兼容 | `Issue`/`WorkingLine`；erratum E9 | ✅ |
| P0-12 DB/审计硬化 | alias `active/revoked_at/FAMILY/SKU`；`actor_role`；`field_diffs` 版本/原因；`price>0`；审批 DELETE guard；`tenants.timezone/currency`；`inbound.source` | migration + db-schema + PGlite | ✅ |
| P0-13 可重现验证 | requirements + pnpm lock + verify script + H1/H5/completeness/parity/migration tests + log | `gate0-validation.log` 29 passed/0 skip | ✅（本机未预装，见 §3.2） |

> 这一轮不是“补文档”，而是把上一轮的每个 P0 都变成了 schema、DDL、fixture、测试或日志。做得对。

---

## 3. 仍需处理的事项

### 3.1 签字前建议先补的 3 个契约歧义

#### A. `condition_id` 没有字段

- **现状**：`fields.md` §4 说库存疑点稳定派生键是 `(draft_id,line_id,issue_code,condition_id|null)`；`Issue` 和 OpenAPI 没有 `condition_id`。
- **影响**：H3 的“每次 PUT/approve 重建疑点”、H5 的“同一片段 STOCK+PRICE 两个条件”都需要稳定身份。实现者可能用 `issue_id`、`span` 或 `condition_kind`，三种都能自洽，但彼此不兼容。
- **修复（二选一）**：
  - 加 `condition_id: Optional[str]`，定义为 `hash(condition_kind, span_start, span_end, target_line_ids)`；或
  - 把稳定键改成 `(draft_id,line_id,issue_code,condition_kind,span_start,span_end)`，删掉 `condition_id`。
- **建议**：加字段更明确；如果不想扩 schema，改稳定键定义即可。两者都是一句话，但必须选一个。

#### B. CLERK 能否看“自己提交的审批状态”

- **现状**：OpenAPI `GET /approvals` 和 `GET /approvals/{approval_id}` 都写 **OWNER only**；02 §4.3/§13.4 说 CLERK 可以看自己提交的审批状态。
- **影响**：前端按 02 做“我的提交”页，后端按 OpenAPI 403；或者前端不做，02 的导航空着。
- **修复（二选一）**：
  - 允许 CLERK 只读，服务端强制过滤 `requested_by = 当前用户`；`allowed_actions` 对 CLERK 为空；
  - 或明确删除 02 的“CLERK 查看提交状态”入口，只保留 OWNER 待办。
- **建议**：前者更符合 01 §12.1；加一个 `mine=true` 参数或角色过滤，别让 CLERK 看到别人的审批。

#### C. PII 掩码 token 格式没有写死

- **现状**：`parse_draft` fixture 用 `[PHONE]`；v2.1/01 用 `[REDACTED_*]`；03 没有规定具体 token。
- **影响**：前端展示、span 示例、AI prompt 里的“非商品片段”判断、日志扫描测试可能各用一套；不影响业务逻辑，但影响 Gate 0 的“公共语言”。
- **修复**：在 `field-evidence.md` 或 `db-schema.md` 加一行：

```text
MASK_TOKENS = [REDACTED_PHONE] | [REDACTED_MYKAD] | [REDACTED_EMAIL]
```

并让 fixture、PII 测试、`masked_message` 示例统一。若坚持 `[PHONE]`，就写进 errata，别让三份材料各说各的。

### 3.2 P1/P2 清单

| # | 项 | 级别 | 建议 |
|---|---|---|---|
| P1-1 | 当前 shell 未预装 Python/Node 依赖；29 passed 只能看日志，不能直接复跑 | P1 | 加 `scripts/bootstrap_gate0.ps1` 或 CI；或把 `.gate0-python`/`node_modules` 的安装步骤写进 README 首行 |
| P1-2 | H5 没有 `price_basis=UNIT` 的正向行为用例 | P1 | 加一行 `kalau RM95 untuk 1 ctn`，断言 UNIT；否则 P0 只执行 UNIT 的路径没有机器证据 |
| P1-3 | `DeliveryOrder` 没有 `customer_name`；`AuditDetail.final_snapshot` 也继承 | P1 | 加 `customer_name` 或 `customer: CustomerSummary`；WAREHOUSE 已有 `customer_name` |
| P1-4 | `ApprovalRequest.requested_by` 只有 user_id；02 要显示提交人 | P2 | 加 `requested_by_name` 或 `requested_by: UserSummary`；不要前端另查 |
| P1-5 | `ActivityItem`/`AuditEvent` 只有 `actor_user_id/actor_role`，没有显示名 | P2 | 加 `actor_display_name`；或明确 UI 只显示角色+ID |
| P1-6 | `INVALID_QUANTITY` 在 errors.md 是 422；提案 M1 说客户端 PUT 非法 400 | P2 | 二选一并写进 02；不要让前端按 400 处理、后端返回 422 |
| P1-7 | `clarification_lang` 在 `OrderDraft` 有，但 `orders` 表只有 `clarification` JSONB | P2 | 明确语言在 `clarification.language`，或加列；不要两个真相 |
| P1-8 | `OrderDraft.conditions` 是 `issues` 的派生副本 | P2 | 保持 readOnly；加测试断言 `conditions == issues.filter(CUSTOMER_CONDITION)`，防止两套漂移 |
| P1-9 | `test_openapi_completeness` 的 WAREHOUSE 检查只看顶层属性名 | P2 | 递归检查 `WarehouseDeliveryOrder.items` 的 nested schema 无价格/电话/Tier |
| P1-10 | `gate0_version` 仍叫 `gate0-v1`，但状态是 draft | P2 | 改成 `gate0-v1-draft` 或加 `draft_revision:2`（已有）；避免误读为已冻结 |

> 这些不影响“骨架正确”，但会影响“极致”。P1-1/P1-2/P1-3 建议签字前处理；其余可列入 P0-A 的 P1 清单。

---

## 4. 逐文件快评

| 文件 | 评分 | 评价 |
|---|---:|---|
| `baseline-manifest.json` | 5.0 | 48 个产物/外部输入/受保护文件哈希全对；`approved_by=null` 正确；draft revision 2 清楚 |
| `contracts/db-schema.md` | 4.8 | 18 表、JSONB 聚合、身份/信用/别名撤销/审计字段都补了；只剩 `condition_id`/`clarification_lang` 的存储表述 |
| `contracts/fields.md` | 4.5 | 前端/审批/DO/AI 字段基本齐全；`condition_id` 仍是悬空引用 |
| `contracts/errors.md` | 5.0 | 23 码、扁平错误、旧码映射、`X-Request-ID` 完整 |
| `contracts/field-evidence.md` | 4.8 | 8 条规则 + 三语词表 + 失败映射 + 9 个用例；PII token 格式未写死 |
| `contracts/condition-triggers.md` | 4.8 | 11 行真值表、`UNALLOCATED`、`discount` 语境、否定近邻都补了；UNIT 正向用例可再加 |
| `contracts/openapi.yaml` | 4.8 | 1710 行、13 路径、完整前端/审批/DO/仓库/AI 模型；只剩 CLERK 审批只读和 `customer_name` 等 P1 |
| `migrations/0001_baseline.sql` | 4.8 | 18 表、12 trigger 事件、PGlite 通过；关键硬化都落地 |
| `contracts/fixtures/*` | 4.8 | parse/save/approve/approval/audit/owner 都更新到新模型；`[PHONE]` 待统一 |
| `tests/contract/*` | 4.5 | 29 passed/0 skip；H1/H5/完整度/parity/migration 都有；依赖未预装、H5 UNIT 缺正向 |
| `docs/gate0-review-resolution.md` | 5.0 | P0-1—P0-13 逐项对应，未执行项写明；很好 |
| `docs/gate0-validation-report.md` / `.log` | 4.8 | 工具版本、命令、结果、边界都写了；缺 bootstrap/CI 一键复跑 |
| `docs/gate0-signoff.md` | 4.8 | 未签就标未签；技术清单已加 H1/H5/完整度/DDL；四方签名仍是门禁 |

---

## 5. 签字建议

### 5.1 建议的签字顺序

1. **先补 3 个契约歧义**（§3.1 A/B/C）：`condition_id`、CLERK 审批只读、PII mask token。
2. **补 3 个 P1**：bootstrap/CI、H5 UNIT 正向、`DeliveryOrder.customer_name`。
3. **重跑** `py -3 scripts/verify_gate0.py` + `node scripts/verify_migration_pglite.cjs`；确认 0 failed/0 skipped。
4. **重算 48 个产物哈希**，更新 `docs/gate0-hashes.txt` 和 `baseline-manifest.json`；不要用旧哈希签新文件。
5. **四方签字**：后端、前端、AI、数据；如果采用“24 小时无异议”，附群消息时间和截图路径。
6. **打 `gate0-v1` 标签**；之后任何改动开 `gate0-v2`。

### 5.2 批准语（可直接用）

> 批准 Gate 0 draft revision 2 作为 KiraOrder v1.3 的公共机器契约；确认 P0-1—P0-13 已闭合；要求签字前补齐 `condition_id` 稳定键、CLERK 审批只读过滤、PII mask token 三个契约歧义，以及 bootstrap/CI、H5 UNIT 正向、`DeliveryOrder.customer_name` 三项 P1；重算 48 个产物哈希后，四方签字并创建 `gate0-v1` 标签。未签字前不进入 P0-A 业务代码。

### 5.3 不建议做的事

- 不要因为“文件很多、测试 29 个”就直接 tag；先补 3 个歧义。
- 不要把 `condition_id` 留给实现者“自己看着办”；H3/H5 会分叉。
- 不要让 CLERK 按 02 做审批页、后端按 OpenAPI 403；这是第一天的联调 bug。
- 不要用 `[PHONE]` 和 `[REDACTED_*]` 两套 mask token；Gate 0 要只留一套。
- 不要在未重算哈希的情况下签字；旧 `gate0-hashes.txt` 会立刻失效。

---

## 6. 最终结论

**这一版 Gate 0 已经从“技术骨架”变成“可签字执行稿”。** 上一轮 13 个 P0 全部有 schema/DDL/fixture/test/log 对应；48 个产物哈希一致；29 个测试 0 skip；PGlite 空库 18 表/12 trigger 事件；前端/审批/DO/仓库/AI 的字段都补齐了。**95/100，建议进入签字评审。**

但“极致”还差三步：**`condition_id` 稳定键、CLERK 审批只读、PII mask token**。这三条都是一句话/一个字段，修完再签；否则它们会在 P0-A 变成三处“各自解释”。

**一句话**：**Gate 0 已经可以签，但先把这三句话写死，再签。**
