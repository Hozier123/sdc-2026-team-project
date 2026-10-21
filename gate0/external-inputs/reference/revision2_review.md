# KiraOrder v1.3 Revision 2 复审与 Gate 0 批准建议

> **复审对象**：`KiraOrder_v1.2_评审复核与v1.3拟议解决方案_待批准_2026-10-21.md` **Revision 2**
> **提案 SHA-256**：`40DA19F4FE5CA0282B7127F66E934872B91A2BD920F8D833B79BEAB0684DF12B`（738 行 / 55,453 bytes）
> **唯一基线**：v2.1，SHA-256 `5D02EBF84413B7FE617C32B64E707AFF476EBD963E6638091C875EE0D1B8A55D`（1475 行）
> **前一版复审**：`KiraOrder_v1.3_拟议方案评审与批准建议_2026-10-21.md`，SHA-256 `87F5776B8554914274CB3196737603E39979FA738ACF75AE175EE1136FE4E9A4`（425 行）
> **Orbyte 参考**：SHA-256 `EE3FEB8C4C533A5104DAF3F3CC4AA144326A3CB675F48A4E73F3FF8D0F11CE00`（127 行）
> **复审时间**：2026-10-21 19:06（UTC+8）
> **结论**：**93/100，建议批准 Gate 0；暂不批准全量执行。** Revision 2 已经从“方向稿”升级为“可评审执行稿”，但仍有 7 个 Gate 0 细节需要闭合。

---

## 0. 一页结论

| 上一版 Gate 0 条件 | Revision 2 是否闭合 | 证据 | 剩余工作 |
|---|---|---|---|
| 物理数据模型/表名映射 | ✅ 已裁决 | §7.7 选择 v2.1 表名 + 聚合 JSONB；给出旧名→物理名映射 | 列级 DDL/约束/触发器留给 Gate 0-B |
| 字段字典/新语义 | ✅ 已给关键字段 | §7.8 覆盖 termination、reason_code、price_basis、deleted_line_ids、match_source、ignored、phone、threshold、checks | 完整 Issue/WorkingLine/DO/Approval schema 留给 OpenAPI |
| H1 确定性证据 | ✅ 规则已可执行 | §7.11 定位、数字词、单位/族证据、失败策略、数字字符串兼容 | 词表/版本/测试负责人留给 Gate 0 |
| H5 价格触发真值表 | ✅ 已给真值表 | §7.12 覆盖历史陈述、询价、复合、英文 available、总价歧义 | 词表正负例/测试留给 Gate 0 |
| OWNER/P0 范围 | ✅ 明确不降级 | §1.3、§8.4 P0-C：OWNER 全能力、审计、回复保持 P0 | 排期风险；若时间不够只能显式范围收缩 |
| v2.1 errata vs v1.3 | ✅ 已分层 | §8.1 三层表：erratum / v1.3 文档 / 实现验证 | 需要实际产出 `v2.1-erratum-1.md` |
| clause-to-section 矩阵 | ✅ 已补 | §8.5 覆盖 C/H/Orbyte 组 | 个别条目仍可细化 |
| 错误/成功体 | ✅ 已补，但未完全统一 | §7.10 错误表/成功表/`X-Request-ID` | 错误码命名与缺失码需补 |
| 显式删除 | ✅ 已补 | §7.9 `deleted_line_ids` + 校验 | 列级/事务测试 |
| `IssueResolutionAction` | ✅ 已删除 | §7.8 明确整体删除 | 02 需同步删除 |
| TEST-01—24 数据 | ✅ 已指定来源 | §5.1 C36、§8.3 04、§9.2 #26 | 数据负责人补录/哈希 |

**总评**：Revision 2 不再是“原则稿”；它已经能作为 Gate 0 的评审对象。**批准 Gate 0 是合理的；批准全量执行还差 7 个细节，主要集中在错误码、完整 schema、DDL 和 H1/H5 数据资产。**

---

## 1. Revision 2 相对 Revision 1 的关键改进

### 1.1 物理模型终于做了“单真相”裁决

§7.7 明确选择 **v2.1 表名 + 聚合 JSONB**，不再同时建 `orders`/`drafts`、`products`/`skus` 两套。它给出了 17 张 P0 物理表，包括：

- `product_families`、`family_aliases`、`products`、`uom_aliases`、`customer_tier_prices`、`inventory`；
- `alias_cache`、`inbound_messages`、`orders`、`draft_versions`、`approval_requests`、`delivery_orders`；
- `activity_log`、`audit_logs`、`field_diffs`；
- `tenants`/`users`/`customers`。

并明确 **P0 不另建** `draft_lines/issues/conditions/delivery_order_lines/approval_decisions` 作为第二真相；草稿行/疑点/条件放在 `orders` 聚合 JSONB + `draft_versions` 快照，DO 行放在 `delivery_orders.lines` JSONB。这是一个可执行的取舍，比上一版“只修 SQL 漏字段”完整得多。

### 1.2 字段字典补上了上一版缺的“新语义”

§7.8 现在有：

- `termination_reason`（`OWNER_REJECTED/CLERK_DISCARDED/SYSTEM_TERMINATED`）+ `terminated_by_user_id` + `termination_note`；
- `Issue.reason_code`（`INVALID_QUANTITY/FIELD_NOT_EVIDENCED/FAMILY_NOT_EVIDENCED/DUPLICATE_SPAN/OVERLAPPING_SPAN/SOURCE_EVIDENCE_INVALID/UNKNOWN_PRODUCT/NO_CANDIDATE/LOW_SCORE/SMALL_SCORE_GAP`）；
- `price_basis`（`UNIT/TOTAL/UNKNOWN`）；
- `deleted_line_ids`；
- `match_source`（唯一持久化来源）+ `ai_mode`（草稿级摘要）+ `ignored/ignored_spans`；
- `disambiguations`（deprecated 派生字段）；
- `phone_e164`、`amount_threshold_rm`、`checks_enabled`、`below_tier_price_override_requires_owner`、`credit_flag_requires_owner`；
- `requested_qty/confirmed_qty/effective_qty`、`expected_version`、`X-Request-ID`；
- 明确 `IssueResolutionAction` 整体删除。

这基本覆盖了上一轮指出的“字段未定义”问题。

### 1.3 H1/H5 从“原则”变成“规则”

- §7.11 给出 8 步：定位 span → 数字词/单位/族证据 → 多候选不猜 → 数字字符串兼容 → 审计 raw_text/start/end/normalizer_version → 失败丢字段/单行 fallback。
- §7.12 给出真值表：历史陈述不触发、`RM95?` 询价触发、`kalau ada, boleh kurang` 双标签、`If available` STOCK、`RM95 for 5 ctn` 总价歧义阻断、`Can follow last price RM95?` 触发。
- 这已经足够让 AI/数据团队开始实现；剩下的是词表版本和测试数据，不是设计问题。

### 1.4 错误/成功体、保存语义、逐文件落点、clause-to-section 都补齐了

- §7.10 有错误表、成功表、`X-Request-ID`；§7.9 有 `deleted_line_ids`、行集合校验、`confirmed_items` 兼容事务；§8.3 有 01—04 的逐节落点；§8.5 有 clause-to-section 矩阵；§9.2 有 26 个回归场景；§9.3 有 16 个 fixture。
- 这说明 Revision 2 不是“再写一遍原则”，而是按上一轮 Gate 0 清单逐项补了执行层。

### 1.5 它拒绝了我上一轮的“静默降级”建议

上一轮我建议 P0 只做 OWNER 批/驳、把创建/编辑放 P1，以省时间。Revision 2 明确拒绝：**v2.1 是唯一基线，OWNER 全能力、审计、回复保持 P0；任何范围收缩必须用户明确批准。** 这个立场更正确；我上一轮的建议是“工期导向”，不是“基线导向”。Revision 2 的选择更符合“唯一基线”原则，代价是 P0 更重，需要真实排期。

---

## 2. 现在可以批准什么

### 2.1 建议：批准 Gate 0，不批准全量执行

**Gate 0 只做“定义和骨架”，不改 01—04、不改 v2.1、不写业务代码。** 这正是 Revision 2 §8.1/§10.1 的两段式设计。

建议批准语：

> 批准 Revision 2 作为 v1.3 的修订执行方向；批准仅创建 Gate 0 产物，包括 baseline manifest、v2.1 erratum 草案、变更记录 v0.1、物理 schema、字段字典、错误表、H1/H5 规范、OpenAPI 骨架和 fixture 目录；暂不修改 01—04 和现有基线。全量执行待 Gate 0 审阅后另行批准。

### 2.2 Gate 0 必须产出（按 Revision 2 §8.1/§10.2）

| 产出 | 验收 |
|---|---|
| `baseline-manifest.json` | v2.1/评审/提案/参考的路径、字节、行数、SHA、批准人、时间 |
| `05_KiraOrder_v1.3_契约变更记录.md` v0.1 | 变更项、理由、影响文件、批准人 |
| `v2.1-erratum-1.md` | `MIXED`、H1、H5、price basis、快照、SQL 漏字段、成功体/头部、物理 schema 裁决 |
| `contracts/db-schema.md` + `migrations/0001_baseline.sql` | 列级 DDL、FK、唯一约束、append-only/immutability 触发器 |
| `contracts/fields.md` | 完整 Issue/WorkingLine/Draft/Approval/DO 字段 |
| `contracts/errors.md` | 错误码、HTTP、前端行为、旧码→新码映射 |
| `contracts/openapi.yaml` | 13 个 P0 端点、成功/错误模型、`X-Request-ID` |
| `contracts/condition-triggers.md` + `field-evidence.md` | H5/H1 词表、版本、正负例、测试负责人 |
| `contracts/fixtures/*.json` | parse/save/approve 200/202/409/audit/approval/reply/warehouse |
| 四方签字 | 后端、前端、AI、数据 |

---

## 3. 仍需在 Gate 0 闭合的 7 个细节

> 这些不是“方向错误”，而是“全量执行前必须钉死的执行细节”。不闭合，四份文档仍会在联调时出现“同名不同义”。

### 细节 1：错误码表还没有完全统一

§7.10 的错误表比上一版完整，但有几处需要裁决：

| 问题 | 现状 | 建议 |
|---|---|---|
| `MISSING_TIER_PRICE` 的 HTTP | §7.10 用 **500**；01 §15.4 用 **422**；v2.1 没有明确 HTTP | 二选一并写进 errata。若视为服务端配置错误，500 可接受；但前端应能显示“配置缺失”，而不是普通 500。 |
| 401/403/404 的 code | §7.10 用 `UNAUTHORIZED/FORBIDDEN/NOT_FOUND`；01/02 用 `INVALID_TOKEN/FORBIDDEN_ACTION/RESOURCE_NOT_FOUND` | 选一套 canonical，给旧码→新码映射；否则 02 的错误表要重写。 |
| 缺失 `MESSAGE_TOO_LONG` | v2.1/01 有 422 `MESSAGE_TOO_LONG`；§7.10 没有 | 补 422 + 前端提示 4000 字符。 |
| 缺失 `REJECTION_REASON_REQUIRED` | v2.1/01 有 422；§7.10 没有 | 补，或明确用 `NOTE_REQUIRED` 覆盖；老板驳回理由需要单独 code 更清楚。 |
| 缺失 `INVALID_QUANTITY` 客户端错误 | M1 说客户端 PUT 非法返回 400；§7.10 只有 `REQUEST_VALIDATION_FAILED` 422 | 明确 400/422 和 code；不要让 01 的 `INVALID_QUANTITY` 与 §7.10 的 `REQUEST_VALIDATION_FAILED` 两套并存。 |
| `AI_WAKE_RATE_LIMITED` vs `RATE_LIMITED` | §7.10 用 `RATE_LIMITED`；01/02 用 `AI_WAKE_RATE_LIMITED` | 选一套；如果统一 `RATE_LIMITED`，在 02 加映射。 |

**Gate 0 产出**：`contracts/errors.md` + 旧码→新码表 + 每个错误的 fixture。

### 细节 2：完整 schema 还没列全，§7.8 只是“关键字段”

§7.8 覆盖了新增字段，但没有完整列出 v2.1 `Issue`/`WorkingLine`/`Draft`/`ApprovalRequest`/`DeliveryOrder` 的所有字段。至少以下字段需要在 OpenAPI/`fields.md` 明确：

- `Issue`：`condition_kind`、`condition_scope`、`candidate_line_ids`、`target_line_ids`、`requested_unit_price`、`auto_resolved_by`、`data_used`、`blocking`、`resolved`、`resolution`、`resolution_note`、`price_basis`、`reason_code`；
- `WorkingLine`：`line_id`、`sku_id`、`confirmed_qty`、`unit_price_override`、`override_reason`、`save_to_alias_cache`、`alias_scope`、`client_line_ref`；
- `DeliveryOrder`：`do_number`、`tenant_id`、`draft_id`、`customer_id`、`lines`、`final_total`、`prepared_by`、`approved_by`、`escalation_reasons`、`related_do_number`、`approved_at`、`reply_draft`；
- `Draft`：`version`、`ai_mode`、`ignored_spans`、`issues`、`blocking_issues`、`escalation_preview`、`clarification_draft`、`clarification_lang`；
- `ApprovalRequest/Detail`：`approval_id`、`draft_id`、`draft_version`、`status`、`reasons`、`requested_by`、`requested_at`、`decided_by`、`decided_at`、`decision_note`、`snapshot`；
- `draft_versions`：版本号、行/疑点/条件/总额/澄清快照、创建人/时间、不可变标记。

**不影响 Gate 0 批准，但影响 Gate 0-C 的 OpenAPI 完成度。**

### 细节 3：物理 schema 只有表级裁决，还没有列级 DDL/约束

§7.7 的表级设计是对的，但全量执行前必须补：

- `draft_versions`/`approval_requests`/`delivery_orders` 的列、FK、唯一约束、JSONB schema；
- `draft_versions`、`approval_requests` 的 immutability trigger（或只允许 INSERT 的权限）；
- `activity_log`、`audit_logs`、`field_diffs` 的 append-only trigger；
- `inventory` 的 `(tenant_id, product_id)` 唯一 + `CHECK >= 0` + 固定顺序锁；
- `customer_tier_prices` 的 `(tenant_id, product_id, tier)` 唯一；
- `alias_cache`/`family_aliases` 的 `phrase_norm` 唯一 + 同租户不跨族；
- `orders` 的 `version` 乐观锁 + 当前版本指针；
- `delivery_orders.draft_id` 唯一（一草稿一 DO）；
- `approval_requests` 的 `one pending per draft` 部分唯一索引。

这些是 §8.1 `db-schema.md` 的内容；Gate 0-B 必须看到列级 DDL，不能只看到表名。

### 细节 4：H1/H5 的“数据资产”还没落地

§7.11/§7.12 规则已经可执行，但还需要：

- 中文/英文/马来数字词表（`satu/dua/...`、`five/...`、`五/两/十`）及版本号；
- `uom_aliases`（`ctn/箱/carton`、`pack/包` 等）及 canonical unit；
- `family_aliases` 与跨族冲突校验；
- 条件触发词表的正例/负例（`Last order was RM95`、`RM95?`、`hantar esok`、`If available`、`Stock code A95`、`Can follow last price RM95?`）；
- `normalizer_version` 的记录与回放；
- DEV-39—41、TEST-29/30/32 的具体输入/答案键。

**Gate 0 产出**：`field-evidence.md`、`condition-triggers.md`、词表版本、测试负责人。

### 细节 5：几个字段名还需要统一

| 问题 | 现状 | 建议 |
|---|---|---|
| `confirmed_unit_price` vs `unit_price_override` | H15 说“填写 `confirmed_unit_price`”；§7.8/§9 用 `unit_price_override` | 明确：`WorkingLine.unit_price_override` 是写路径；`IssueResolution.confirmed_unit_price` 是消息级解决路径；不要两套混用。 |
| `below_tier_price_override_requires_owner` vs v2.1 `price_override_requires_owner` | §7.8 用新名；v2.1 SQL 用旧名 | 写入 errata；04 seed/01 schema 同步；给旧名→新名映射。 |
| `MISSING_TIER_PRICE` 500 vs 422 | 见细节 1 | 二选一；写 errata。 |
| P1 `discard` 端点 | §7.2 的 expected_version 提到 discard，但 API 表没有 `POST /orders/drafts/{id}/discard` | 加到 P1 API 表；补 reason/`termination_reason`。 |

### 细节 6：OWNER 全能力 P0 是“正确但重”的选择

Revision 2 明确保留 OWNER 创建/编辑/批常规单、`OWNER_SELF_APPROVED`、审计、回复为 P0；这是对 v2.1 的忠实回归，不是错误。但它显著增加 P0-C 的工作量：

- OWNER 工作台/入口；
- OWNER 创建/编辑草稿的权限与 UI；
- `OWNER_SELF_APPROVED` 事件与直接 DO；
- 权限测试 #13/#25；
- 审计/回复页面。

**建议**：Gate 0 通过后，先做 P0-A/P0-B；如果 P0-C 出现时间风险，**只能由用户明确批准范围收缩**，并写入变更记录，不能静默降为 P1。Revision 2 已经这样要求；执行时守住即可。

### 细节 7：TEST-01—24 的原始数据还没有补录

Revision 2 已经把责任写进 §5.1 C36、§8.3 04、§9.2 #26、§10.2 清单。但数据仍未补；Gate 0 应确认：

- 谁从方案 B 原始数据补录 TEST-01—24 的逐条消息/答案键；
- 不能从组级断言反推答案；
- 补录后写入 `frozen_eval_32.json`/`frozen_answers.json` 并重算 SHA-256；
- 在 Gate 0 manifest 记录数据版本。

---

## 4. 逐节评分

| 节 | 分数 | 评价 | 仍需补 |
|---|---:|---|---|
| §0 材料与优先级 | 5.0 | 哈希正确；把前一版复审也纳入；明确自引用哈希由 manifest 记录 | 无 |
| §1 最终判断/两段式批准 | 5.0 | Gate 0 vs 全量执行分得很清楚；不静默降级 OWNER/审计/回复 | 排期风险 |
| §2 C1—C21 | 4.8 | 全部恢复 v2.1；C1 加 termination、C2 加 reason、C5 定 match_source、C7 限定写请求、C10 加 deleted_line_ids、C13 固定成功/头、C18 兼容数字字符串 | 错误码映射、full schema |
| §3 H1—H16 | 4.8 | H1/H5/H15 已规则化；H16 保留完整 OWNER | H1/H5 词表/测试；`confirmed_unit_price` 命名 |
| §4 M1—M12 | 4.5 | M2/M7/M12 范围控制好；M3 兼容事务清楚 | M9 事件全集、M10 payload schema |
| §5 遗漏/C22—C39 | 5.0 | C22 物理模型、C23—C29 字段/错误、C30—C39 全部有落点 | C36 数据补录 |
| §6 Orbyte | 5.0 | 只做 UI/适配，不碰 membership/wallet/内部 API | 无 |
| §7 核心契约 | 4.5 | 枚举/API/物理表/字段/保存/错误/成功/H1/H5 都已成形 | 列级 DDL、完整 schema、错误码映射 |
| §8 实施/矩阵 | 4.8 | 两段式、三层产物、clause-to-section、P0-A/B/C 很清楚 | 负责人/时间估计可再具体 |
| §9 验收 | 4.8 | 26 场景 + 16 fixture，覆盖很广 | 错误码/fixture 与 §7.10 对齐 |
| §10 结论 | 5.0 | 明确“可评审执行稿”+两段批准语+检查清单 | 无 |
| **综合** | **4.65（93/100）** | **Gate 0 可批准；全量执行前补 7 个细节** |  |

---

## 5. 四份文件的覆盖度（Revision 2 之后）

| 文件 | 现在的覆盖 | 仍缺 | 覆盖度 |
|---|---|---|---:|
| `01` | 状态/疑点/条件/升级/权限/API、物理表、数量模型、价格目标行、批准 6 项硬复核、危险动作删除、DO 字段、错误/成功、审计/回复、Orbyte 边界 | 完整 Issue/WorkingLine/DO 列级 schema、错误码映射、`confirmed_unit_price`、P1 discard | 85% |
| `02` | 类型从 OpenAPI、路径、`expected_version`、单 PUT、`deleted_line_ids`、审批详情/审计/DO/回复、`allowed_actions`、OWNER 工作台、Organization 文案 | 错误码旧→新映射、完整响应 schema、P1 discard、`match_source` 徽章细节 | 85% |
| `03` | `qty:int`、`fam:"UNKNOWN"`、4 类 `conds`、`ignored`、字段证据、数字字符串兼容、重复/重叠、`MIXED`、版本记录 | 数字词/单位词表版本、`normalizer_version`、H1/H5 测试数据 | 90% |
| `04` | 物理名、family/uom aliases、phrase_norm、phone/credit/threshold/checks、`dev_38`、TEST-01—32、答案键、SHA/冻结纪律 | `below_tier...` 新名、TEST-01—24 逐条数据、`confirmed_unit_price`/price basis 数据 | 85% |

> 这四份文件已经从“需要重写”变成“按 §8.3 的落点改”；剩下的主要是 schema 细节和数据资产，不是架构分歧。

---

## 6. 批准建议

### 6.1 建议动作

1. **现在批准 Gate 0**：只创建 manifest、errata 草案、变更记录 v0.1、db-schema、fields、errors、H1/H5 规范、OpenAPI 骨架、fixture 目录。
2. **Gate 0 审阅后再批准全量执行**：修改 v2.1 erratum、01—04、OpenAPI/Schema/fixture/seed/test。
3. **Gate 0 的 7 个细节先闭合**：错误码、完整 schema、列级 DDL、H1/H5 数据资产、字段名、OWNER 排期风险、TEST-01—24 数据。
4. **守住“不静默降级”**：OWNER 全能力、审计、回复保持 P0；如果时间不够，必须由用户明确批准范围收缩并写变更记录。

### 6.2 不建议现在做的事

- 不建议现在批准“全量执行 C1—C21 + H1—H16”；7 个细节未闭合，改到一半会出现新的“同名不同义”。
- 不建议把 OWNER 创建/编辑、审计、回复静默移到 P1；Revision 2 已明确拒绝，这是对的。
- 不建议在 Gate 0 之前改 01—04 正文；否则 Gate 0 的 schema/字段结论会推翻已改内容。
- 不建议把 `MISSING_TIER_PRICE`、`UNAUTHORIZED/FORBIDDEN/NOT_FOUND`、`MESSAGE_TOO_LONG` 等错误码留到实现时再定；这些是前端/测试的硬依赖。

### 6.3 一句话

**Revision 2 已经从“方向稿”升级为“可评审执行稿”；现在可以批准 Gate 0，但还不能批准全量执行。** 它最大的进步不是字数，而是把“物理表、字段、H1/H5、错误/成功体、逐文件落点、clause-to-section”都写成了可检查的对象；剩下的 7 个细节，都是 Gate 0 能在 1—2 小时内钉死的。

---

## 7. 结论

- **评分**：93/100（Revision 1 是 85/100）。
- **Gate 0**：建议批准。
- **全量执行**：暂不批准；先闭合 7 个细节。
- **最大剩余风险**：不是设计，而是执行纪律——错误码/字段/DDL/词表/测试数据是否真的按 Gate 0 产物落地。
- **对上一版复审的修正**：我上一版建议“P0 只做 OWNER 批/驳、创建/编辑放 P1”，这是工期导向，不是基线导向；Revision 2 拒绝它是正确的。现在应坚持 v2.1 全能力 P0，若时间不够再走“显式范围收缩”。

**建议的批准语**：

> 批准 Revision 2 作为 v1.3 的修订执行方向；批准仅创建 Gate 0 产物，包括 baseline manifest、v2.1 erratum 草案、变更记录 v0.1、物理 schema、字段字典、错误表、H1/H5 规范、OpenAPI 骨架和 fixture 目录；暂不修改 01—04 和现有基线。全量执行待 Gate 0 审阅后另行批准；OWNER 全能力、审计、回复保持 v2.1 P0，不作静默范围收缩。

**一句话**：**这次可以批 Gate 0 了；全量执行再等 7 个细节闭合。**
