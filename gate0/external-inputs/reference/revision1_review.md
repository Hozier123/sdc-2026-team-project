# KiraOrder v1.3 拟议方案评审与批准建议

> **评审对象**：`KiraOrder_v1.2_评审复核与v1.3拟议解决方案_待批准_2026-10-21.md`
> **提案 SHA-256**：`72C11ABF05C4E7431019223F5DAD83F8598E5A584E2F5839B24D94920A09609F`（445 行 / 30,758 bytes）
> **唯一基线**：`KiraOrder_终版执行方案_v2.1`（文件名仍为 `..._v2_...`，正文 v2.1）
> **基线 SHA-256**：`5D02EBF84413B7FE617C32B64E707AFF476EBD963E6638091C875EE0D1B8A55D`（1475 行）
> **Orbyte 参考**：`Orbyte-前后端参考说明.md`，SHA-256 `EE3FEB8C4C533A5104DAF3F3CC4AA144326A3CB675F48A4E73F3FF8D0F11CE00`（127 行）
> **前序评审报告**：`KiraOrder_v1.2_后端规则体系评审报告_2026-10-21.md`，SHA-256 `DB9A335B6A84E2DE2A3E120D10C07ED4661DBE07F3F68060F232D13ED6C446E9`（1103 行）
> **评审时间**：2026-10-21 18:37（UTC+8）
> **结论**：**条件性批准（85/100）。方向可以批准；不要批准“立即执行全部 C1—C21 + H1—H16”。**

---

## 0. 一页结论

| 问题 | 结论 |
|---|---|
| 方向是否正确 | **是。** 它比我的评审报告更严格地服从 v2.1，纠正了我报告最大的问题。 |
| 能否直接批准执行 | **不能。** 6 个执行条件还没闭合：物理数据模型、字段字典、H1 证据规范、H5 触发真值表、OWNER/P0 范围、v2.1 errata 与 v1.3 的分层。 |
| 能否批准为 v1.3 修订方向 | **可以。** 建议分两段批准：先批 Gate 0，再批全量执行。 |
| 最大优点 | 恢复 v2.1 唯一基线；拒绝我的折中命名；H4 直接删危险动作；Orbyte 边界克制；OpenAPI 单一真相源。 |
| 最大缺口 | **物理数据模型/表名没有对齐**；新字段没有定义；P0 范围过大；审计/回复被降级但 v2.1 把它们放在 P0。 |
| 评分 | **85/100**；补齐 6 个条件后可到 95。 |

**三句话**：

1. **它纠正了我报告最大的问题**：我为了让四份文档“内部自洽”，在 C1、C3、C6、C7、C9、C11、C13、C14、C16、C18、C19、C21 上建议保留 01/02 的旧命名或折中命名；在 v2.1 已确认唯一基线后，这些建议会制造第二套契约。提案拒绝它们是对的。
2. **它是一份“决策/方向”文档，不是“可执行的变更计划”**：它没有 clause-to-section 矩阵、字段字典、物理 schema 映射、每项改动的负责人/时间/验收 fixture。直接拿去改 01—04，仍会出现“每个人理解不同”的漂移。
3. **建议批准 Gate 0，不要批准全量执行**：先把 baseline manifest、schema 映射、字段字典、H1/H5 规范、P0 时间盒定下来；这些是 1—2 小时的工作，但能避免后面 2—3 天的返工。

---

## 1. 评审基线与方法

### 1.1 哈希核对

| 材料 | 提案引用 | 当前实测 | 结论 |
|---|---|---|---|
| v2.1 基线 | `5D02EBF84413...A55D` | `5D02EBF84413...A55D`，1475 行 | ✅ 一致 |
| 前序评审报告 | `DB9A335B6A84...C446E9` | `DB9A335B6A84...C446E9`，1103 行 | ✅ 一致 |
| Orbyte 参考 | `EE3FEB8C4C53...11CE00` | `EE3FEB8C4C53...11CE00`，127 行 | ✅ 一致 |
| 提案自身 | 未在文内记录自身哈希 | `72C11ABF05C4...09609F`，445 行 | ⚠️ 建议补进 baseline manifest |

> 提案引用的三个哈希都是当前值，说明它不是拿旧材料写的；这一点比很多“评审稿”可靠。

### 1.2 评审方法

- 逐条对照 v2.1 的 §4.8/§4.10/§4.11/§4.13、§9.1/§9.2，以及四份文件的 §5/§6/§8/§9/§13/§15。
- 对提案的 C1—C21、H1—H16、M1—M12 做“是否恢复 v2.1”与“是否可执行”两重检查。
- 对四份文件做覆盖度检查：提案说“要改”的，是否覆盖到具体章节、字段、fixture、测试。
- 对 Orbyte 参考做边界检查：是否把“页面实测”误写成“官方 API/SSO/Wallet”。

---

## 2. 总评分

| 维度 | 分数 | 判断 | 主要依据 |
|---|---:|---|---|
| 基线纪律 | 5.0 | 严格服从 v2.1，拒绝折中命名 | §2 全表；§7.1 枚举直接采用 v2.1 |
| 对评审报告的纠偏 | 4.8 | 正确识别我报告的“第二套契约”风险 | §1.2、§1.3、§2 的 C1/C3/C6/C7/C9/C11/C13/C14/C16/C18/C19/C21 |
| 技术正确性 | 4.0 | 方向对；H1/H5/H15 仍缺可执行规则 | §3 H1/H5/H15；§7.4/§7.5 |
| 可执行性 | 3.0 | 缺 clause-to-section 矩阵、字段字典、schema 映射 | §8.3 只有文件级 bullet；§7 只有核心枚举 |
| 范围/时间现实性 | 3.0 | P0-A/B/C 过大；OWNER 编辑；审计/回复降级 | §8.4；§9.2 #13；v2.1 §3.5 |
| 治理设计 | 5.0 | baseline manifest、OpenAPI 单一真相源、fixture、四方确认 | §8.1、§8.2、§9.1、§9.3 |
| Orbyte 边界 | 5.0 | Organization 只做 UI/适配；不虚构 SSO/Wallet/API | §6；参考说明的“限制”段 |
| **综合** | **4.25（85/100）** | **方向批准，执行附条件** |  |

**为什么不是更高**：它不是“改哪一段”的清单，而是“应该怎么改”的原则；真正落地时，四个文件仍有大量空白。
**为什么不是更低**：它把最危险的方向性错误（回到 01 旧命名、保留危险动作、把 Orbyte 页面当官方契约）都挡住了。

---

## 3. 它比我的评审报告更强的地方

### 3.1 它正确拒绝了我的“折中命名”

我的报告在 C1、C3、C6、C7、C9、C11、C13、C14、C16、C18、C19、C21 上，为了照顾 01/02 的既有写法，建议采用 `NEEDS_REVIEW`、`ask_target`、`draft_version`、`/drafts/...`、`{data,meta}`、`null`、布尔信用标记等。**在 v2.1 已确认唯一基线后，这些建议是错的**；它们会让四份文档继续形成第二套契约。提案逐条拒绝，这是对的。

这也说明我前一份报告的一个方法问题：我把“四份文档内部一致”放在了“与唯一基线一致”之前。提案的 §1.3 自我反思第 2 条说得很准：局部顺手的命名，不应凌驾于已确认的唯一基线。

### 3.2 它直接删除危险动作，而不是加守卫

我的 H4 建议给 `MARK_UNRESOLVED`、`ASK_CUSTOMER_AT_TIER_PRICE`、`USE_FALLBACK_RESULT` 加前置条件。提案更干净：**从公共 `ResolutionChoice` 删除这三个动作**，用 v2.1 的 `CONFIRMED_WITH_CUSTOMER`、`NOT_A_CONDITION`、人工选 SKU、删除行来替代。少三个动作，就少三个绕过口。

### 3.3 它把 H1 从“字符串子串”改成“确定性证据等价”

我的 H1 要求 `qty/uom/size/grade` 必须是 `span` 的规范化子串。这会误伤 `five → 5`、`两箱 → 2`、`ctn → 箱` 等语义等价。提案改成“先从 span 生成确定性候选，再校验模型字段与候选语义等价”，方向更好；但**“语义等价”必须写成确定性规则**，否则会退化成模糊匹配。

### 3.4 它发现了我没有充分展开的 v2.1 自身问题

- v2.1 SQL 的 `delivery_orders` 漏了 `escalation_reasons`，而 §4.11 的模型有；
- `AiMode` 没有 `MIXED`，但 §4.2 允许单行 fallback；
- 裸 `RM\d+` 会误报 `Last order was RM95`；
- 没有定义金额的 UNIT/TOTAL 口径；
- `price_override_requires_owner` 的命名与“只对低于等级价升级”不一致；
- 审批快照没有数据库级不可变保证；
- 成功响应没有逐端点固定；
- 文件名仍是 v2。

这些是真实缺口，且比“命名冲突”更接近业务风险。提案把它们单列在 §5，很好。

### 3.5 Orbyte 参考的采纳边界非常克制

提案只采纳：Organization 作为 UI/适配层术语、访问角色与项目分工分离、Submit/Review/Approve 与业务状态分离、权限由服务端判断、Wallet/Credit 标 Mock、整体表述为独立原型/模拟集成。它明确不采纳：全局 `tenant_id → organization_id`、完整 membership/多 Approver 模型、网页内部 `/api/...` 当官方契约、Wallet/Credit 账本、`workspace_id` 租户层级。

这与参考说明的“不能证明”“未获得 OpenAPI”“页面请求不是公开契约”完全一致，是四份文档最需要的边界。

### 3.6 它把 OpenAPI 作为唯一机器真相源，而不是再加 `enums.yaml`

我的报告建议 `contracts/enums.yaml` + OpenAPI + 生成 TS；提案指出这会变成“第五份手写契约”，改为 **OpenAPI + JSON Schema + fixtures + 生成/校验 TS/Pydantic**。这个判断更好，减少了新的漂移点。

### 3.7 它纠正了人员分工

我的报告 §8.2 直接抄了 v2.1 §12 的“Xiong 后端、He 数据”。如果 He 是后端负责人，这份提案的纠正是对的；技术基线不受影响，但 RACI 必须改，否则派工会错。

---

## 4. 批准前必须补的 6 个条件

> 这 6 条不是“建议”，是“批准全量执行前的 Gate 0”。每条都应产出可检查的文件，而不是口头共识。

### 条件 1（最高优先）：物理数据模型/表名映射

这是提案最大的缺口。它说“补 `escalation_reasons`、完整 DO 字段”，但没有处理 v2.1 SQL 与 01/04 的**物理表名/结构差异**：

| v2.1 SQL | 01/04 文档 | 冲突/风险 | 建议 |
|---|---|---|---|
| `products` | `skus` + `product_families` | 表名/粒度不同；v2.1 只在 `products` 上加 `family_id/pack_size/grade` | 定一个物理模型；另一个做视图/迁移，不能两套都建 |
| `orders`（草稿表） | `drafts` | 表名不同；v2.1 用 `working_lines/issues JSONB`，01 用 `draft_lines/issues` 表 | 选 JSONB 或归一化；在 `contracts/db-schema.md` 固定 |
| `alias_cache` | `customer_aliases` | 表名不同；v2.1 有 `phrase_norm` 唯一索引，01 没有 | 统一表名/字段；保留唯一索引 |
| `activity_log` | `activity_logs` | 单复数不同 | 统一；迁移脚本 |
| `audit_logs` | `field_diffs` | v2.1 用审计表，01 用字段差异表 | 明确两者关系：审计事件 + 字段差异，不是二选一 |
| `delivery_orders.lines` JSONB | `delivery_order_lines` | JSONB vs 行表；影响查询/审计 | 选一个；若要行表，v2.1 SQL 必须改 |
| `orders.working_lines` JSONB | `draft_lines` | 同上 | 同上 |
| `orders.issues` JSONB | `issues` 表 | 同上 | 同上 |
| 没有 `inventory` 表 | 01/04 有 `inventory` | v2.1 的 `available_qty` 存在哪里？ | 必须补 `inventory` 或明确 `products.available_qty` |
| 没有 `customer_tier_prices` 表 | 01/04 有 | 等级价矩阵无法落地 | 必须补表或明确 `products` 内的价格结构 |
| 没有 `product_families` 表 | 01/04 有 | AI 闭集/族别名无存储 | 必须补表或 `products.family_id` + 族字典 |
| 没有 `draft_versions`/`conditions`/`inbound_messages` | 01 有 | 版本快照/条件/入站消息无表 | 按 H14/C 需求补 |
| `customers.phone_e164` | `synthetic_phone` | 字段名不同 | 统一；合成号段约束保留 |
| `tenants.amount_threshold_rm` | `owner_approval_threshold` | 字段名不同 | 统一；数据/前端映射 |
| `tenants.checks_enabled`/规则开关 | 01 没有 | 无法按租户开关检查 | 补字段；04 seed |

**Gateway 0 产出**：`contracts/db-schema.md`（表/字段/关系/迁移/兼容视图）+ `migrations/0001_baseline.sql`。**没有这个，P0-A 的 OpenAPI 对齐只是表面一致。**

### 条件 2：字段字典/新语义

提案提了很多“要补”，但没有给出字段级定义。至少需要：

| 字段/概念 | 为什么要 | 建议定义 |
|---|---|---|
| `termination_reason` | 提案 C1 不公开 `CANCELLED`，但 01 用它区分作废；`REJECTED` 会混淆老板驳回与跟单员作废 | `OWNER_REJECTED / CLERK_DISCARDED / SYSTEM`；配 `terminated_by`、`termination_note`；两种都必须 note |
| `reason_code` | C2 把 `INVALID_QUANTITY`/`SOURCE_EVIDENCE_INVALID` 折进 `LOW_CONFIDENCE_MATCH`，但没有区分原因 | `INVALID_QUANTITY / FIELD_NOT_IN_SPAN / FAMILY_NOT_EVIDENCED / DUPLICATE_SPAN / SOURCE_EVIDENCE_INVALID / UNKNOWN_PRODUCT`；作为 `Issue.reason_code` 闭集 |
| `price_basis` | H15 的 UNIT/TOTAL/UNKNOWN 没有字段 | 放在 `Issue`；`UNIT/TOTAL/UNKNOWN`；P0 只自动执行 UNIT |
| `deleted_line_ids` | §7.3 说“删除必须显式”，但 `SaveLinesRequest` 没有删除字段；省略行会被误判为删除 | `deleted_line_ids: []` 或 `line_ops: KEEP/UPDATE/DELETE`；至少保留 1 行；删空返回 `EMPTY_ORDER` |
| `match_source` vs `extraction_source` | 提案说“保留 match_source、UI 派生、快照存原始来源”，但没有说哪个是持久化真相 | 建议：行级持久化 `extraction_source`（AI/FALLBACK/ALIAS_ONLY）+ `manual_selected` 布尔；`match_source` 由后端派生给 UI；`ai_initial_snapshot` 存原始来源。或者反过来，但要只留一个 |
| `ignored` vs `ignored_spans` | v2.1 `LlmExtraction.ignored`，03 用 `ignored_spans` | 统一为 `ignored_spans` 或 `ignored`；Adapter 映射；加 C22 |
| `disambiguations` | v2.1 §4.11 保留兼容字段，01/02 没有 | 明确是 `issues` 的派生别名还是废弃；前端不能同时依赖两个 |
| `phone_e164` vs `synthetic_phone` | v2.1 与 01/04 字段名不同 | 统一；合成号段校验不变 |
| `amount_threshold_rm` vs `owner_approval_threshold` | 同上 | 统一；数据/前端映射 |
| `checks_enabled`/flags | v2.1 `tenants` 有，01 没有 | 补 `checks_enabled`、`price_override_requires_owner`、`credit_flag_requires_owner`；04 seed |
| `X-Request-ID` | 提案 C13 把 request_id 放响应头 | OpenAPI 声明 header；前端错误处理读 header；错误体不再带 request_id |
| `IssueResolutionAction` | 01/02 有 9 个动作，v2.1 `ResolutionChoice` 只有 6 个 | 删除 `IssueResolutionAction`；行级用 `WorkingLine.sku_id/confirmed_qty`；消息级用 `ResolutionChoice` |
| 错误表 | 提案只零散提 `STOCK_CHANGED`/`ALREADY_APPROVED` | 补 `TARGET_LINE_REQUIRED/OVERRIDE_REQUIRED/NOTE_REQUIRED/EMPTY_ORDER/PENDING_OWNER_APPROVAL/DRAFT_REJECTED/TENANT_MISMATCH` 的 HTTP/code/前端行为 |

**Gate 0 产出**：`contracts/fields.md` + `contracts/errors.md` + OpenAPI components。

### 条件 3：H1 的“确定性证据”规范

提案的方向对，但“语义等价”必须写成可执行规则：

1. **qty**：`span` 中阿拉伯数字、中文数字（五/两/十）、马来数字词（satu/dua/…）、英文数字词（five/…）的**精确 token**；不做模糊匹配。
2. **uom/size/grade**：单位/规格/等级的 canonical alias 精确匹配；`ctn/箱/carton` 等别名表由 04 维护；不做模糊匹配。
3. **fam**：族名/族别名/客户级别名在 `span` 中精确出现；否则 `LOW_CONFIDENCE_MATCH(reason_code=FAMILY_NOT_EVIDENCED)`。
4. **失败处理**：字段无证据 → 丢弃该字段，保留 span；`qty` 缺失/非法 → 行级 `LOW_CONFIDENCE_MATCH(reason_code=INVALID_QUANTITY)`；`fam` 无证据 → 不自动映射。
5. **禁止**：用 `fam` 在闭集、`qty` 是正整数就认为字段来自原文；用 RapidFuzz 分数直接放行。
6. **回归**：DEV-39/40/41；再加中文数字、马来数字词、`ctn/箱` 别名各一条。

**Gate 0 产出**：`contracts/field-evidence.md` + 词表（04）+ 测试（03/04）。

### 条件 4：H5 的价格触发真值表

提案说“裸金额只作证据；PRICE 触发应为议价短语，或金额 + 条件/询价语气”，但没有真值表。建议至少：

| 输入 | 是否条件 | 类型 | 说明 |
|---|---|---|---|
| `Last order was RM95.` | 否 | — | 历史陈述；04 负例 |
| `kalau RM95 boleh` | 是 | PRICE | 条件标记 + 议价 |
| `RM95?` | 是 | PRICE | 询价语气；需确认是否过宽 |
| `boleh kurang sikit?` | 是 | PRICE | 议价短语 |
| `kalau ada, boleh kurang` | 是 | STOCK + PRICE | 同片段多标签 |
| `If available, send 5 ctn` | 是 | STOCK | 英文 `available` |
| `hantar esok` | 否 | — | 普通送货要求 |
| `Stock code A95` | 否 | — | 编码数字 |
| `RM95 for 5 ctn` | 是 | PRICE，`price_basis=UNKNOWN/TOTAL` | 总价歧义；P0 阻断并询问 |

**Gate 0 产出**：`contracts/condition-triggers.md` + 04 词表正负例 + TEST-29/30/32 回归。

### 条件 5：OWNER 范围与 P0 时间盒

v2.1 §4.9/§4.10 允许 OWNER 解析、编辑、批准常规单；01/02 是 OWNER 只读。提案选择回归 v2.1，方向正确；但这是一项**额外 P0 工作**：owner 工作台、权限、`OWNER_SELF_APPROVED`、测试 #13 都要做。建议在 v1.3 中明确二选一：

- **方案 A（推荐，省时）**：P0 OWNER 只审批/驳回；OWNER 创建/编辑、`OWNER_SELF_APPROVED` 放 P1。这是 v2.1 允许的“收缩范围”，要写进变更记录，不能静默降级。
- **方案 B（完全回归）**：P0 做 OWNER 创建/编辑/批常规单；需要额外 UI、权限、测试；给出时间估计。

同时，提案的 §8.4 P0-A/B/C 太大：C1—C21 全量 + H1—H7/H11—H15 + 批量/审批/幂等/快照，在 10/21 晚上做不完。建议拆成：

| 时段 | 只做 | 不做 |
|---|---|---|
| 今晚（Gate 0 + 最小 P0） | baseline manifest、schema 映射、字段字典、C1/C4/C6/C7/C9/C11/C13/C14 的命名/路径/错误体、H1/H2/H3/H4、批量 PUT、批准 6 项硬复核 | H5/H7/H8/H9/H10/H11/H15/H16、审计/回复/老板详情、同日/仓库 |
| 10/22 | H5/H7/H8/H9/H10/H11/H15/H16、审计/回复/审批详情、P1 同日/仓库 | Orbyte 正式适配 |
| 10/23 | 只修阻断/证据 | 新功能 |

另外，提案 §8.4 把“审批详情、审计/回复”放 P1，但 v2.1 §3.5 把“回复草稿、AI/人工差异审计”放在 P0。若接受这个降级，必须写成“P0 范围收缩”，并同步改演示脚本；否则会与基线冲突。提案 §9.2 #13 又要测 OWNER 自建/自提交，和 P0 范围决定不一致；必须先定 OWNER 范围，再定测试。

### 条件 6：v2.1 errata 与 v1.3 分层

提案说“v2.1 本身需要小型正确性勘误”，也说“拟冻结的 v1.3 核心契约”，但没把两者拆开。建议：

| 类别 | 内容 | 产出 |
|---|---|---|
| **v2.1 errata（改基线）** | `AiMode` 加 `MIXED`；SQL 补 `escalation_reasons`；H1 字段证据规则；H5 价格触发真值表；`price_basis`；审批快照不可变；成功/错误体 + `X-Request-ID`；文件名/哈希 | `v2.1-erratum-1.md`，单独哈希/批准 |
| **v1.3（四份文档对齐）** | 状态/疑点/条件/升级/API/权限/数量模型/DO 字段/危险动作删除/Orbyte 边界 | `05_契约变更记录.md` + 01—04 修订 |
| **实现/测试** | OpenAPI、fixtures、DB schema、DEV/TEST | `contracts/` + `tests/` |

**不要把 errata 混进“四份文档修订”**；否则 v2.1 会被静默改写，下一次又不知道基线是什么。

---

## 5. 逐节评审（提案 §0—§10）

| 节 | 评分 | 评价 | 需要补 |
|---|---:|---|---|
| §0 材料与优先级 | 5.0 | 哈希正确；优先级“用户指令 > v2.1 > 变更记录 > 机器契约 > 四份文档 > 参考材料”很清楚 | 把自己的 SHA 也写进 manifest |
| §1 最终判断 | 5.0 | “问题真实，但不是措辞问题”；对我报告的批评准确；自我反思 7 条很到位 | 把“我报告的方法问题”转成一条流程规则：先锁哈希，再评审 |
| §2 C1—C21 | 4.5 | 全部恢复 v2.1；拒绝折中命名，方向正确 | C1 终止原因、C2 reason_code、C5 match_source、C7 “所有写请求”例外、C13 成功体/头部、C18 数字字符串 |
| §3 H1—H16 | 4.0 | H4 直接删动作、H1 语义等价、H15 price_basis 都很好 | H1 规则化、H5 真值表、H15 TOTAL 后续路径、H16 与 P0 范围一致、H4 删除 `IssueResolutionAction` |
| §4 M1—M12 | 4.0 | M2/M7/M12 的范围控制很好 | M3 confirmed_items 事务细节、M9 事件全集、M10 payload schema、M11 详情字段 |
| §5 遗漏 | 5.0 | SQL 漏字段、H1 不完整、裸金额、MIXED、UNIT/TOTAL、配置命名、快照、成功体、文件名，都是真问题 | 补“物理表名/表结构”这一条；补“TEST-01—24 逐条数据” |
| §6 Orbyte | 5.0 | 只做 UI/适配，不做全局改名/会员/钱包/内部 API；非常克制 | 明确 `action_type`/membership 是 P1/P2，不进 P0 |
| §7 核心契约 | 4.0 | 枚举/API 基本对齐 v2.1；`MIXED` 是必要勘误 | 字段字典、错误表、删除行、`IssueResolutionAction` 移除、`X-Request-ID`、`expected_version` 例外 |
| §8 实施方案 | 4.0 | Gate 0/manifest/OpenAPI/fixture 的设计很好 | clause-to-section 矩阵、schema 映射、P0 时间盒、owner/负责人、审计/回复的 P0/P1 裁决 |
| §9 验收 | 4.5 | 18 个回归场景+10 个 fixture 很实用 | 补错误码/状态码、成功体、`X-Request-ID`、`OWNER_SELF_APPROVED`、`confirmed_items`、`EMPTY_ORDER`、`TEST-01—24` |
| §10 结论 | 5.0 | “不重写，受控升级”；“v2.1 需要 errata”；“Orbyte 只采纳边界”；都对 | 把“批准方式”写成两段式，而不是一次性全量 |

---

## 6. C1—C21 复核（提案裁决 vs v2.1）

> 这里不重复每条的完整理由，只标“提案裁决是否正确/还缺什么”。

| 编号 | 提案裁决 | 与 v2.1 | 复核/需补 |
|---|---|---|---|
| C1 状态集 | 严格 v2.1 五状态，不公开 `CANCELLED` | ✅ | 需要 `termination_reason` 区分 OWNER_REJECTED / CLERK_DISCARDED；否则 `REJECTED` 语义混 |
| C2 疑点代码 | 严格 8 个；`INVALID_QUANTITY`/`SOURCE_EVIDENCE_INVALID` 变 reason | ✅ | 需要 `Issue.reason_code` 闭集；否则数据/前端丢精度 |
| C3 条件类型 | 统一 4 类 | ✅ | 04 词表要从 3 类迁到 4 类；给映射表 |
| C4 升级原因 | 采用 v2.1 三码 | ✅ | — |
| C5 来源字段 | 保留 `ai_mode`/`match_source`，快照存原始来源，不加 `display_source` | ✅/⚠️ | 必须定义哪个是持久化真相；`match_source` 是 UI 徽章还是持久字段，二选一 |
| C6 路由字段 | 统一 `ask` | ✅ | — |
| C7 版本字段 | 统一 `expected_version` | ✅ | “所有写请求”太宽：parse/wake 不需要；decide 是否要？写清楚 |
| C8 数量模型 | `requested/confirmed/effective` | ✅ | `effective_qty` 不得由客户端提交；加测试 |
| C9 解析路径 | `/orders/parse-draft` | ✅ | — |
| C10 保存路径 | `PUT /orders/drafts/{id}/lines` | ✅ | 需要 `deleted_line_ids`；否则“省略行”是隐式删除 |
| C11 批准路径 | `/orders/{id}/approve` + `expected_version` | ✅ | — |
| C12 老板决定 | 单一 `decide` | ✅ | — |
| C13 响应格式 | 扁平错误 + 直接成功 + `X-Request-ID` | ✅（v2.1 错误体） | 成功体是 v1.3 决定；02 所有示例/客户端要改；OpenAPI 要声明 header |
| C14 审计接口 | `/orders/{do_number}/audit-detail` | ✅ | 需要 fixture/schema |
| C15 回复草稿 | 含 DO/明细/总额，标未发送 | ✅ | 02/01 的“回复不含价格”必须改；演示脚本同步 |
| C16 澄清结构 | 单一 `clarification_draft` | ✅ | 02 的数组要删；对象内 `issue_ids/not_sent` 固定 |
| C17 DO 字段 | 补 v2.1 字段；SQL 补 `escalation_reasons` | ✅ | 还要补物理表名/行表 vs JSONB |
| C18 AI 数量类型 | 模型 wire 严格 int | ✅（v2.1） | Qwen 可能输出 `"5"`；Adapter 要定义“接受数字字符串并转 int”还是 fallback；加测试 |
| C19 未知族 | 严格 `"UNKNOWN"` | ✅ | 01 现在禁止；03 现在 null；都要改；prompt 要允许 UNKNOWN |
| C20 AI 模式 | 加 `MIXED` | ✅ 必要勘误 | 定义“所有行同一路径才 LLM/FALLBACK”的判定 |
| C21 信用标记 | `credit_flag: NONE/OVERDUE_NOTICE` | ✅ | 04 的 `credit_term_notice` 要改；UI 布尔派生 |

**结论**：C1—C21 的裁决方向全部正确；需要补的是 6 个字段/语义，不是重新讨论命名。

---

## 7. H1—H16 复核

| 编号 | 提案方案 | 评价 | 需补 |
|---|---|---|---|
| H1 字段证据 | 从 span 生成确定性候选，再校验语义等价 | ✅ 方向对 | 规则化 qty/uom/size/grade/fam；数字词/单位别名；失败 reason_code；DEV-39—41 |
| H2 价格目标行 | `condition_scope/candidate/target` 进数据/API/事务 | ✅ | 目标行删除/替换后重新要求选择 |
| H3 数量重算 | 每次 PUT/approve 用 effective_qty 重建疑点 | ✅ | 定义“稳定派生键”（code + line_id + condition_id）；历史写版本 |
| H4 危险动作 | 删除三个公共动作 | ✅ | 删除整个 `IssueResolutionAction`；行级用 lines；消息级用 ResolutionChoice |
| H5 条件误报 | 裸金额只作证据；议价短语/询价语气触发 | ✅ 方向对 | 真值表 + `NOT_A_CONDITION` + 英文 available + 同片段多标签 |
| H6 双重阻塞 | STOCK 派生 blocking=false | ✅ | 返回 `auto_resolved_by/data_used` |
| H7 零库存 | 删除行 + EMPTY_ORDER | ✅ | `deleted_line_ids`/`line_ops`；至少 1 行 |
| H8 高于等级价 | 允许 + 理由 + 审计；不触发价格升级 | ✅ | 配置名/租户开关语义；测试 |
| H9 别名污染 | phrase_norm 唯一；别名来自 span；不做固定长度 | ✅ | 04/01 加字段/索引；测试跨族/跨客户 |
| H10 证据失败 | 删除 SOURCE_EVIDENCE_INVALID 公共码 | ✅ | 折进 LOW_CONFIDENCE + reason_code；人工选 SKU/删除行 |
| H11 重复/重叠 span | 同区间去重；重叠不静默合并 | ✅ | 诊断 reason，不新增公共码；测试 |
| H12 库存变化 | 保存时业务校验；事务锁后 409 STOCK_CHANGED | ✅ | 审批保持 PENDING；前端区分 |
| H13 重复批准 | 409 + do_number/approved_at | ✅ | fixture/测试 |
| H14 快照不可变 | 版本不可变；审批存 lines/totals/reasons/原话 | ✅ | 物理表/JSONB 方案；DB 级约束；测试 |
| H15 单价/总价 | `price_basis: UNIT/TOTAL/UNKNOWN`；P0 只 UNIT | ✅ 方向对 | TOTAL 被阻断后“客户确认总价”怎么录入？P0 只能转人工按单价+备注，或 P2；不要留死路 |
| H16 OWNER 路径 | 回归 v2.1：OWNER 可编辑/批常规单 | ✅ 相对 v2.1 | 这是额外 P0 工作；建议 P0 只批/驳，创建/编辑放 P1，并写“范围收缩”；与测试 #13 对齐 |

---

## 8. 四份文件更改覆盖度（粗略）

| 文件 | 提案已覆盖 | 仍缺 | 覆盖度 |
|---|---|---|---:|
| `01` 后端规则 | 状态/疑点/条件/升级/权限/API、数量模型、价格目标行、批准硬复核、危险动作删除、DO 字段、`STOCK_CHANGED`/`ALREADY_APPROVED`、Orbyte 适配 | **物理 schema/表名**、`termination_reason`、`reason_code`、`deleted_line_ids`、`ignored`/`disambiguations`、`phone_e164`/阈值字段、`checks_enabled`、成功体/`X-Request-ID`、OWNER 范围 | 70% |
| `02` 前端对接 | 类型从 OpenAPI、路径、`expected_version`、单 PUT、审批详情/审计/DO/回复/幂等、`allowed_actions`、Organization 文案 | 成功体/头部、`IssueResolutionAction` 移除、`match_source` 徽章、单数澄清、终止原因、删除行、OWNER 编辑 UI | 75% |
| `03` AI 对接 | `qty:int`、`fam:"UNKNOWN"`、4 类 `conds`、字段证据、重复/重叠/空结果/上限、`MIXED`、prompt/model/schema 版本 | `ignored` vs `ignored_spans`、数字字符串适配、H1 规范、`detected_language`、响应大小/最大 token | 80% |
| `04` 数据对接 | v2.1 枚举、DEV-38/TEST-32、family/uom aliases、phrase_norm、跨族冲突、H1/H2/H3/H5/H11、price basis、快照、答案键隔离/SHA/冻结集纪律 | 3→4 条件映射、`credit_flag`/`phone_e164`/表名、requested/confirmed、`price_basis` 数据、TEST-01—24 逐条、`dev_38` 文件名、`reason_code` | 70% |

> 覆盖度是“提案文字是否点到”，不是“改完后的正确率”。真正落地还要 clause-to-section 矩阵。

---

## 9. 提案遗漏的 C22+ 清单

### 9.1 P0（批准全量执行前必须补）

| 编号 | 缺口 | 影响 | 建议 |
|---|---|---|---|
| C22 | **物理数据模型/表名**：`products`/`orders`/`alias_cache`/`activity_log`/`audit_logs` vs 01/04 的归一化表；缺 `inventory`/`customer_tier_prices`/`product_families`/`draft_versions`/`conditions`/`inbound_messages` | API 对齐但数据库对不上；seed 导入失败；库存/价格/族无法落地 | `contracts/db-schema.md` + 迁移；选一个物理模型，另一个做兼容视图 |
| C23 | `termination_reason` | `CANCELLED` 删除后，老板驳回与跟单员作废无法区分 | `OWNER_REJECTED/CLERK_DISCARDED/SYSTEM` + note |
| C24 | `reason_code` | `INVALID_QUANTITY`/`SOURCE_EVIDENCE_INVALID` 折进 `LOW_CONFIDENCE_MATCH` 后丢原因 | `Issue.reason_code` 闭集 |
| C25 | `deleted_line_ids` | “删除必须显式”没有载体；省略行=隐式删除 | `deleted_line_ids`/`line_ops`；空订单 422 |
| C26 | `match_source` 语义 | 提案一边说保留，一边说 UI 派生；可能又出现两个来源 | 定一个持久化真相 + 一个派生徽章；写字段表 |
| C27 | `IssueResolutionAction` 未删除 | 02 仍会有 9 个动作，和 v2.1 的 6 个 `ResolutionChoice` 两套 | 删除；行级用 lines，消息级用 ResolutionChoice |
| C28 | 成功体/`X-Request-ID` | 02 仍可能是 `{data}`；前端/错误处理不一致 | OpenAPI 固定每端点成功 schema；声明 header；fixture |
| C29 | 错误表不完整 | `TARGET_LINE_REQUIRED/OVERRIDE_REQUIRED/NOTE_REQUIRED/EMPTY_ORDER/PENDING_OWNER_APPROVAL/DRAFT_REJECTED/TENANT_MISMATCH` 没有统一表 | `contracts/errors.md` + 前端行为 |

### 9.2 P1（10/22 前补）

| 编号 | 缺口 | 建议 |
|---|---|---|
| C30 | `ignored` vs `ignored_spans` | 统一；Adapter 映射；测试 |
| C31 | `disambiguations` 兼容 | 明确是 `issues` 派生别名还是废弃 |
| C32 | `phone_e164` vs `synthetic_phone` | 统一字段；合成号段约束 |
| C33 | `amount_threshold_rm` vs `owner_approval_threshold` | 统一字段；数据/前端映射 |
| C34 | `tenants.checks_enabled`/规则开关 | 补字段；04 seed |
| C35 | `price_basis=TOTAL` 后续路径 | P0 只 UNIT；TOTAL 转人工按单价+备注，或 P2；不要死路 |
| C36 | `TEST-01—24` 逐条数据 | HE 从方案 B 补录；否则 TEST 只有组级断言 |
| C37 | `v2.1` 文件名/基线 manifest | 复制为 v2.1 文件名；manifest 记录 SHA/行数/批准人 |
| C38 | 人员分工 | 若 He 是后端，改 v2.1 §12/报告 §8.2；若不是，改提案 |
| C39 | 审计/回复的 P0/P1 | v2.1 把审计/回复放 P0；提案放 P1；要么保留 P0，要么写“范围收缩”并改演示 |

---

## 10. 批准建议与下一步

### 10.1 建议的批准方式：两段式

**第一段（现在就可以批）——Gate 0：**

- 批准“以 v2.1 为唯一基线、按提案方向做 v1.3 受控升级”；
- 批准建立 `baseline-manifest.json`、`05_契约变更记录.md`、`contracts/db-schema.md`、`contracts/fields.md`、`contracts/errors.md`；
- 批准修正人员分工/文件名；
- **不批准**立即改 01—04 的全部内容。

**第二段（Gate 0 评审后）——全量执行：**

- 批准 C1—C21 + H1—H16 的具体修订；
- 批准 v2.1 errata（`MIXED`、SQL 字段、H1/H5、price_basis、快照、成功体/头部）；
- 批准 P0/P1 范围收缩（OWNER、审计/回复、同日/仓库）。

### 10.2 Gate 0 产出清单

| 产出 | 内容 | 负责人 | 验收 |
|---|---|---|---|
| `baseline-manifest.json` | v2.1 路径/行数/SHA/批准人/时间；提案/参考哈希 | He | 与实测一致 |
| `05_契约变更记录.md` v0.1 | 变更项/理由/影响文件/批准人 | He | 四端确认 |
| `contracts/db-schema.md` | 物理表/字段/关系/迁移/兼容视图 | He + 数据 | 与 01/04/seed 对得上 |
| `contracts/fields.md` | `termination_reason/reason_code/price_basis/deleted_line_ids/match_source` 等 | He + 前端/AI/数据 | 每字段有类型/枚举/可空/示例 |
| `contracts/errors.md` | 全部错误码/HTTP/前端行为 | He + 前端 | 覆盖 C1—C21/H |
| `contracts/openapi.yaml` | 13 个 P0 端点 + schema + header | He | lint 通过；fixture 通过 |
| `contracts/fixtures/*.json` | parse/save/approve 200/202/409/audit/approval/warehouse | He + 前端 | 三端可跑 |
| `v2.1-erratum-1.md` | MIXED/SQL/H1/H5/price_basis/快照/成功体 | He | 单独哈希/批准 |

### 10.3 今晚最小 P0（建议）

| 时间 | 动作 | 产出 |
|---|---|---|
| 18:45—19:15 | Gate 0：baseline manifest、人员/文件名、errata 范围 | manifest + 变更记录 v0.1 |
| 19:15—20:00 | schema 映射 + 字段字典 + 错误表 | `db-schema.md`、`fields.md`、`errors.md` |
| 20:00—21:00 | 枚举/路径/错误体 + H1/H2/H3/H4 + 批量 PUT + 批准 6 项硬复核 | OpenAPI + fixtures + 单测 |
| 21:00—23:59 | 无 AI 闭环 + 关键 fixture；H5/H7/H8/H9/H10/H11/H15/H16 留到 10/22 | 闭环通过/失败记录 |

> 如果 18:45 的会决定“P0 收缩 OWNER/审计/回复”，把对应测试从今晚移出，写进变更记录；不要既说“全量 v2.1”又把它们降 P1。

### 10.4 批准检查清单

- [ ] 基线 manifest 已记录 v2.1 SHA/行数/批准人
- [ ] 文件名已改为 v2.1，或文件头有 `CANONICAL_BASELINE`
- [ ] 物理 schema 映射已定（表名/JSONB vs 行表/缺表）
- [ ] 字段字典已定（termination/reason/price_basis/deleted_lines/match_source）
- [ ] H1 确定性证据规范已定（数字词/单位/族）
- [ ] H5 价格触发真值表已定
- [ ] OWNER 范围已定（P0 只批/驳 vs 全量回归）
- [ ] 审计/回复的 P0/P1 已定，并同步演示脚本
- [ ] 错误表/成功体/`X-Request-ID` 已定
- [ ] `IssueResolutionAction` 已删除
- [ ] `TEST-01—24` 逐条数据负责人已定
- [ ] 四端（后端/前端/AI/数据）已确认

---

## 11. 最终结论

**这份提案是四份文档修订的合格“方向稿”，不是合格的“执行稿”。**

它最重要的贡献，是把讨论从“用 01 还是用 v2.1 的命名”拉回到“v2.1 是唯一基线”；它纠正了我报告里最危险的折中倾向。它的 Orbyte 边界、OpenAPI 单一真相源、baseline manifest、H4 删除危险动作、H1 语义等价，都是应该保留的。

但在批准全量执行前，必须补：

1. **物理数据模型/表名映射**（最大缺口）；
2. **字段字典/新语义**（termination/reason/price_basis/deleted_lines/match_source/ignored）；
3. **H1 确定性证据规范**；
4. **H5 价格触发真值表**；
5. **OWNER 范围与 P0 时间盒**；
6. **v2.1 errata 与 v1.3 分层**。

**建议的批准语**：

> 批准本提案作为 v1.3 的修订方向；批准立即执行 Gate 0（baseline manifest、schema 映射、字段字典、错误表、H1/H5 规范、P0 范围裁决）；全量 C1—C21 + H1—H16 的文档修订，待 Gate 0 产出评审后再批准。审计/回复/OWNER 等 P0/P1 降级，必须写成“范围收缩”，不得静默改变 v2.1。

**一句话**：**方向可以批准，执行先过 Gate 0；它已经比我的报告更接近正确答案，但还差一张“改哪一段、改成什么、怎么验”的矩阵。**
