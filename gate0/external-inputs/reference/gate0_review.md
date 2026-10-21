# KiraOrder Gate 0 审查报告与修改建议

> **审查对象**：`C:\Users\n_bom\Desktop\Gate 0`（35 个受哈希产物）
> **唯一基线**：v2.1，SHA-256 `5D02EBF84413B7FE617C32B64E707AFF476EBD963E6638091C875EE0D1B8A55D`
> **执行提案**：Revision 2，SHA-256 `40DA19F4FE5CA0282B7127F66E934872B91A2BD920F8D833B79BEAB0684DF12B`
> **审查时间**：2026-10-21 19:37（UTC+8）
> **结论**：**82/100。技术骨架 A，语义契约 B-；当前不要签 Gate 0。** 先修 12 个 P0，再四方签字。不是重写，是补最后一公里。

---

## 0. 一页结论

### 0.1 如果今天就签，第一天会发生什么

| 场景 | 会发生什么 | 根因 |
|---|---|---|
| 前端打开工作台 | `OrderDraft` 没有 `masked_message`、`customer`、`totals`、`allowed_actions`，无法显示原文/客户/合计/按钮 | OpenAPI 缺少 02 §7.1/§11 必需字段 |
| 前端渲染列表 | `DraftSummary` 没有 `customer_name`、`message_preview`、阻断计数、`allowed_actions` | OpenAPI 缺少 02 §5.2 字段 |
| 顶栏 | `/me` 没有 `tenant` 对象和 `permission_summary` | OpenAPI 缺少 02 §4.2 字段 |
| 老板审批 | `ApprovalRequest` 没有客户名/总额，列表无法选择；`allowed_actions` 是 `APPROVE/REJECT`，不是 `OWNER_APPROVE/OWNER_REJECT` | OpenAPI 缺少 02 §13.1 字段 |
| H4 记忆 | `WorkingLineInput` 没有 `save_to_alias_cache/alias_scope`，别名无法写入 | v2.1 `WorkingLine` 字段丢失 |
| 登录/权限 | `users` 没有 `demo_token_hash`，无法从 Bearer token 找到用户 | DDL 漏关键列 |
| 仓库视图 | `DeliveryOrder` 没有仓库裁剪模型，价格字段会跟着返回 | 缺少 `WarehouseDeliveryOrder` |
| AI 状态灯 | `AiStatus` 用 `COLD/UNAVAILABLE`，前端期望 `OFFLINE/DEGRADED` | 枚举不一致 |
| 客户端解析 | `ParseDraftRequest` 要求 `masked_text`，不是原始 `message_text` | 把 PII 掩码责任推给客户端，安全边界反了 |

### 0.2 评分

| 维度 | 分数 | 判断 |
|---|---:|---|
| 版本/哈希纪律 | 5.0 | 35/35 哈希一致；外部/受保护文件也一致；非常强 |
| 物理 schema | 4.0 | 18 表、JSONB 聚合、不可变/append-only 触发器很好；缺 auth/credit/alias active 等 |
| OpenAPI 结构 | 4.5 | 13 路径、错误目录、`X-Request-ID`、本地 ref 都很好 |
| OpenAPI 语义完整性 | 2.5 | 缺少前端第一天就要用的字段；机器校验通过不等于契约完整 |
| H1/H5 规格 | 4.5 | 规则、词表、真值表写得很细 |
| H1/H5 可执行验证 | 2.5 | 目前只验证 JSON/行数，没有真正跑触发/证据逻辑 |
| 错误/成功体 | 5.0 | 23 个错误码、扁平错误、直接成功、旧码映射完整 |
| fixtures/tests | 3.5 | fixture 覆盖广；测试依赖未固化，部分只做 grep/JSON |
| 治理/签字 | 4.5 | manifest/signoff/validation 分层好；签字尚未完成，`approved_by` 写得偏早 |
| **综合** | **4.1（82/100）** | **骨架优秀，语义未闭合；修完 P0 可到 95** |

---

## 1. 已核验事实

- `docs/gate0-hashes.txt` 列出 **35** 个产物；逐文件重算 SHA-256，**0 个不匹配**。
- `baseline-manifest.json` 中 v2.1、Revision 2、前序报告、Revision 2 复审、Orbyte 参考、执行手册，以及 `01`—`04` 四个受保护文件，**全部哈希一致**。
- 迁移 SQL：**18 张表**、6 个触发器（5 个 append-only/immutable + 1 个 approval snapshot guard），触发器事件数 11。
- OpenAPI：**13 个 P0 路径**、**23 个公开错误码**、本地 `$ref` 可解析、每个 response component 都带 `X-Request-ID`。
- H5：真值表 **11 行**；H1：三语数字词、单位别名、失败映射齐全。
- fixtures：12 个 endpoint fixture + `error_catalog.json` + README。
- Gate 0 状态：`GATE0_DRAFT_AWAITING_CROSS_FUNCTIONAL_SIGNOFF`；前端/AI/数据未签，未创建 `gate0-v1` 标签。

**验证环境问题**：Gate 0 目录没有 `requirements.txt`/`pyproject.toml`。我在当前 shell 的 Python 3.13 上无法 `import yaml`；`test_openapi_parses.py` 用了 `pytest.importorskip("yaml")`，依赖缺失时是 **skip** 而不是 fail。这意味着“机器校验通过”目前不可在干净环境复现。

---

## 2. 做得好的地方

1. **哈希纪律是满分。** 35 个产物、6 个外部输入、4 个受保护文件全部可复核；这是 Gate 0 最重要的可信基础。
2. **物理模型做了单真相裁决。** 18 张表、`orders` 聚合 JSONB + `draft_versions` 快照、`delivery_orders.lines` 不可变 JSONB，没有同时保留 `drafts/skus` 双真相。
3. **数据库约束有真东西。** 一草稿一 PENDING、一草稿一 DO、`inventory >=0`、`draft_versions`/`delivery_orders` 不可变、`activity_log`/`audit_logs`/`field_diffs` append-only。
4. **错误目录完整。** 23 个 code 覆盖 400—503，扁平错误体、直接成功体、`X-Request-ID`、旧码映射都写清楚了。
5. **H1/H5 不是口号。** 数字词/单位/族证据、八条规则、11 行真值表、负向上下文、`NOT_A_CONDITION` 都具体。
6. **fixtures 覆盖面好。** parse/save/approve 200/202/409/audit/approval/owner self-approved/reject 都有。
7. **治理结构对。** manifest、erratum、change record、validation report、signoff 分开；不签就不 tag。
8. **没有偷改四份文件。** `01`—`04` 哈希与 Gate 0 前一致，边界守住了。

---

## 3. P0 阻断项（签 Gate 0 前必须修）

> 这些不是“未来优化”，是四个模块第一天就会用到的契约。修完再签字；否则前端会自己造字段、后端会自己解释，Gate 0 的意义就没了。

### P0-1 解析接口要求客户端传 `masked_text`，安全边界反了

**证据**：

- `contracts/openapi.yaml` `ParseDraftRequest` 要求 `masked_text`（约 L912—926）。
- `contracts/fixtures/parse_draft.json` 请求也是 `masked_text`。
- v2.1 §4.2 第 2 步：**后端本地掩码**；02 §6：前端提交 `message_text`；01 §15：`POST /drafts/parse` 接收 `message_text`。

**风险**：客户端可以传未脱敏原文，后端只存它收到的“masked”文本；PII 掩码从后端保证退化成客户端承诺，违反 H3/PDPA。

**修改**：

```yaml
ParseDraftRequest:
  required: [customer_id, message_text]
  properties:
    customer_id: { type: string, minLength: 1 }
    message_text: { type: string, minLength: 1, maxLength: 4000 }
    language_hint: { type: [string, 'null'] }
```

- 后端收到 `message_text` 后本地 `mask_pii`，只持久化 masked；
- `OrderDraft` 增加 `masked_message: string` 供前端展示；
- `masked_text` 只作为内部字段，不出现在请求里；
- fixture 改为 `message_text`，响应加 `masked_message`。

### P0-2 `OrderDraft` 缺前端必需的四个字段

**证据**：`openapi.yaml` `OrderDraft`（约 L940—1015）、`fields.md` §7（L173—193）都没有：

- `masked_message`：工作台中栏要显示脱敏原文；
- `customer`：客户名、Tier、`credit_flag`、电话（CLERK/OWNER）；
- `totals`：订单合计、币种、是否完整；
- `allowed_actions`：02 §11 明确“按钮只根据 `allowed_actions`”。

**风险**：前端无法渲染工作台；要么自己算总额（违反“前端不计算金额”），要么自己推导按钮（违反“按钮只来自后端”）。

**修改**：在 `OrderDraft` 增加：

```yaml
masked_message: { type: string }
customer:
  type: object
  additionalProperties: false
  required: [customer_id, name, tier, credit_flag]
  properties:
    customer_id: { type: string }
    name: { type: string }
    tier: { type: string }
    credit_flag: { type: string, enum: [NONE, OVERDUE_NOTICE] }
    phone_e164: { type: [string, 'null'] }
totals:
  type: object
  additionalProperties: false
  required: [order_total, currency, is_complete]
  properties:
    order_total: { oneOf: [{ $ref: '#/components/schemas/DecimalString' }, { type: 'null' }] }
    currency: { type: string, const: MYR }
    is_complete: { type: boolean }
allowed_actions:
  type: array
  uniqueItems: true
  items: { $ref: '#/components/schemas/AllowedAction' }
blocked_actions:
  type: object
  additionalProperties: true
```

并新增 `AllowedAction`：

```yaml
AllowedAction:
  type: string
  enum: [EDIT_DRAFT, RESOLVE_ISSUE, COPY_CLARIFICATION, APPROVE_AND_GENERATE_DO, SUBMIT_FOR_OWNER, OWNER_APPROVE, OWNER_REJECT, CANCEL_DRAFT, VIEW_ACTIVITY, WAKE_AI]
```

### P0-3 `DraftSummary` 缺工作台队列字段

**证据**：`openapi.yaml` `DraftSummary`（约 L1016—1035）只有 `draft_id/version/status/customer_id/blocking_issues/updated_at`；02 §5.2 需要 `customer_name`、`message_preview`、`open_blocking_issue_count`、`owner_escalation_count`、`extraction_sources`、`allowed_actions`。

**修改**：至少加：

```yaml
customer_name: { type: string }
message_preview: { type: string }
open_blocking_issue_count: { type: integer, minimum: 0 }
owner_escalation_count: { type: integer, minimum: 0 }
extraction_sources:
  type: array
  items: { $ref: '#/components/schemas/MatchSource' }
allowed_actions:
  type: array
  items: { $ref: '#/components/schemas/AllowedAction' }
```

### P0-4 `MeResponse` 缺 `tenant` 对象和 `permission_summary`

**证据**：`openapi.yaml` `MeResponse`（约 L1379—1396）；02 §4.2 期望 `tenant: {id,name}` 和 `permission_summary`。

**修改**：

```yaml
MeResponse:
  required: [user_id, tenant, display_name, role, permissions, permission_summary]
  properties:
    tenant:
      type: object
      required: [id, name]
      properties:
        id: { type: string }
        name: { type: string }
    permission_summary: { type: string }
    permissions:
      type: array
      items: { $ref: '#/components/schemas/AllowedAction' }
```

### P0-5 审批列表/详情缺客户与总额，`allowed_actions` 枚举也不对

**证据**：`ApprovalRequest`（L1074—1116）没有 `customer`、`total_rm`；`allowed_actions` 是 `ApprovalDecision`（`APPROVE/REJECT`）。02 §13.1 需要客户、总额、明细、原因；按钮是 `OWNER_APPROVE/OWNER_REJECT`。

**修改**：

- `ApprovalRequest` 加 `customer`（同上 `CustomerSummary`）、`total_rm`、`line_count`；
- `ApprovalDetail` 加 `customer`；
- `allowed_actions` 改用 `AllowedAction`（`OWNER_APPROVE/OWNER_REJECT`），不要再复用 `ApprovalDecision`；
- `ApprovalSnapshot` 加 `customer_id/customer_name`（或详情对象里给）。

### P0-6 `WorkingLineInput` 没有别名保存字段，H4 记忆写不进去

**证据**：v2.1 §4.11 `WorkingLine` 有 `save_to_alias_cache`、`alias_scope`；02 §9.1 有 `remember_for_customer`；`fields.md` §5 的 `WorkingLineInput` 没有这两个字段；`openapi.yaml` `WorkingLineInput`（L687—722）也没有。`alias_cache` 表存在，但没有写入口。

**风险**：H4“同一客户第二次下单，人工点选从 2 次降到 0 次”无法实现；alias_cache 永远为空。

**修改**：`WorkingLineInput` 加：

```yaml
save_to_alias_cache: { type: boolean, default: false }
alias_scope: { type: string, enum: [CUSTOMER, TENANT], default: CUSTOMER }
```

保存事务中，若 `save_to_alias_cache=true` 且本次人工选择了 SKU，则写 `alias_cache`（`phrase_norm` 来自当前 span，`confirmed_by` 当前用户）；`alias_scope=TENANT` 仅 OWNER 可写。补 fixture 与测试。

### P0-7 `DeliveryOrder.lines` 复用 `WorkingLine`，缺 `applied_unit_price` 与仓库裁剪模型

**证据**：`DeliveryOrder`（L1257—1307）`lines` 是 `WorkingLine`；`WorkingLine` 用 `effective_unit_price`，没有 `applied_unit_price`。v2.1/01/02 的 DO 行要 `tier_unit_price` + `applied_unit_price`；02 §14.2 的 WAREHOUSE 响应不能有价格、电话、Tier。

**修改**：

```yaml
DeliveryOrderLine:
  type: object
  additionalProperties: false
  required: [line_id, sku_id, display_name, quantity, unit, tier_unit_price, applied_unit_price, subtotal_rm]
  properties:
    line_id: { type: string }
    sku_id: { type: string }
    display_name: { type: string }
    quantity: { type: integer, minimum: 1 }
    unit: { type: string }
    tier_unit_price: { $ref: '#/components/schemas/DecimalString' }
    applied_unit_price: { $ref: '#/components/schemas/DecimalString' }
    subtotal_rm: { $ref: '#/components/schemas/DecimalString' }
```

- `DeliveryOrder.lines` 改为 `DeliveryOrderLine[]`；
- 新增 `WarehouseDeliveryOrder`：只含 `do_number/customer_name/items/approved_at`，`items` 只含 `sku_id/display_name/quantity/unit/picking_note`；
- 不要用 `WorkingLine` 作为 DO 行；它会带 `requested_qty`、`field_evidence`、`match_source` 等草稿字段。

### P0-8 `AiStatus` 状态枚举与 v2.1/02/03 不一致

**证据**：`openapi.yaml` `AiStatus`/`AiWakeResult` 用 `READY/WARMING/COLD/UNAVAILABLE`（L1397—1424）；v2.1/02 §15.2/03 §12 用 `READY/WARMING/OFFLINE/DEGRADED`。

**修改**：

```yaml
AiState:
  type: string
  enum: [OFFLINE, WARMING, READY, DEGRADED]
```

- `AiStatus` 加 `fallback_available: boolean`、`last_checked_at: date-time`、`message: string`；
- `AiWakeResult` 用同一 `AiState`；
- 更新 fixtures/tests；如果保留 `COLD/UNAVAILABLE`，必须在 errata 里写明映射，不能静默。

### P0-9 `users` 表没有 `demo_token_hash`，无法认证

**证据**：`db-schema.md` §3（L52—57）`users` 必要列没有 token；`migrations/0001_baseline.sql`（L14—22）也没有。v2.1 SQL/01 §6.2 有 `demo_token_hash`。

**风险**：`Authorization: Bearer <demo_token>` 无法映射到 `user_id/tenant_id/role`；401/403/租户隔离都无法实现/测试。

**修改**：

```sql
ALTER TABLE users
  ADD COLUMN demo_token_hash text NOT NULL UNIQUE;
```

或单独 `user_tokens(token_hash, user_id, tenant_id, active, expires_at)`。种子只存哈希；演示 token 放 Secrets/受控登录，不放仓库。

### P0-10 `customers.credit_flag` 是 boolean，v2.1 是枚举

**证据**：`migrations` L30 `credit_flag boolean`；`fields.md` C21/`erratum` 要求 `credit_flag: NONE / OVERDUE_NOTICE`；v2.1 SQL 是 text check。

**修改**：

```sql
-- 新库直接建：
credit_flag text NOT NULL DEFAULT 'NONE'
  CHECK (credit_flag IN ('NONE','OVERDUE_NOTICE'))
```

API 若 UI 需要布尔值，由后端派生 `has_credit_notice`，不要保留第二个真相。同步 seed/answer keys/02。

### P0-11 `Issue.span` 是对象，v2.1/02 是字符串/`source_span`

**证据**：`fields.md` §4 `Issue.span: SpanView`；`openapi.yaml` `Issue.span` `SpanView`（L814—817）；v2.1 `Issue.span: Optional[str]`；02 疑点卡用 `source_span` 字符串。

**风险**：前端/测试按字符串取值会拿到对象；高亮逻辑/错误提示可能直接崩。

**修改（二选一，写进 errata）**：

- 方案 A：`Issue.span` 回到 `string`，另加 `span_start/span_end` 两个整数；
- 方案 B：保留 `SpanView`，同时加 `source_span: string` 兼容字段，02 先用 `source_span`，P1 再迁移到对象。

推荐 A，最少惊喜；如果选 B，必须改 fixtures/02 并说明弃用时间。

### P0-12 数据库/审计还有 5 个硬缺口

| # | 缺口 | 证据 | 修改 |
|---|---|---|---|
| 12a | `alias_cache` 没有 `active`，别名不可撤销 | `migrations` L112—129；01 `customer_aliases.active` | 加 `active boolean default true`、`revoked_at`；唯一索引加 `WHERE active` |
| 12b | `alias_cache` 只能指向 `product_id`，不能指向 family | `migrations` L118；01 `target_type FAMILY/SKU` | 加 `target_type text check`、`family_id nullable`；或明确“P0 只支持 SKU 别名”并写 errata |
| 12c | `activity_log`/`audit_logs` 没有 `actor_role` | `migrations` L260—293；v2.1 SQL `actor_role` | 加 `actor_role text`；审计时冻结当时角色 |
| 12d | `field_diffs` 没有 `reason_code`/`draft_version` | `migrations` L295—304；01 §14/02 审计页 | 加 `reason_code text`、`draft_version int`；或明确由 audit header 关联 |
| 12e | `customer_tier_prices` 允许 0 | `migrations` L95 `>=0`；01 §11.1/04 §7 要求 `>0` | 改为 `CHECK (unit_price_rm > 0)` |
| 12f | `approval_requests` 只防 UPDATE，不防 DELETE | `migrations` L366 `BEFORE UPDATE` | 加 `BEFORE DELETE` 触发器或撤销 DELETE 权限 |

### P0-13 测试/验证还不足以证明 Gate 0

**证据**：

- 没有 `requirements.txt`/`pyproject.toml`；当前 Python 3.13 缺 `yaml`。
- `test_openapi_parses.py` 用 `pytest.importorskip("yaml")`，缺依赖时 **skip**，不是 fail。
- `test_lexicons.py` 只检查“11 行/三语/单位存在”，没有把 11 行真值表跑过触发逻辑。
- `test_migration_contract.py` 只用正则 grep 表名/触发器名，没有执行 DDL；PGlite 验证在报告里，但不在测试里。
- `test_fixture_schemas.py` 用同一份 OpenAPI 验证 fixtures；两边同时缺字段时，测试仍通过（循环验证）。
- `gate0-validation-report.md` 没有命令、环境版本、退出码/日志路径。

**修改**：

- 加 `tests/contract/requirements.txt`：`pytest`、`PyYAML`、`jsonschema`、`referencing`、`openapi-spec-validator`、`pglast`（或 PGlite 包装）；
- `test_openapi_parses` 去掉 `importorskip`，缺依赖直接 fail；
- 加 `scripts/verify_gate0.py`，一条命令跑：JSON 解析、OpenAPI 校验、schema/fixture 校验、DDL 空库执行、hash 复核；
- 加 `test_h1_behavior.py`：用词表解析 `dua ctn`/`three cartons`/`两箱`/`5 ctn`/`"5"`，断言 qty/uom/`MODEL_TYPE_COERCED`；
- 加 `test_h5_behavior.py`：把 11 行真值表逐行喂给触发函数，断言 `kinds`/`price_basis`/`blocking`；`RM95 for 5 ctn` 不要出现非法枚举 `UNKNOWN_OR_TOTAL`；
- 加 `test_contract_completeness.py`：断言 `OrderDraft` 有 `masked_message/customer/totals/allowed_actions`；`DraftSummary` 有列表字段；`MeResponse` 有 `tenant/permission_summary`；`WorkingLineInput` 有别名保存；`DeliveryOrder` 有 `applied_unit_price`；`AiState` 是 `OFFLINE/WARMING/READY/DEGRADED`；
- 加 `test_v21_parity.py`：从 v2.1 提取关键枚举/字段，和 OpenAPI 对比；不要求全文，至少 C1—C4/C8/C17/C18/C19/C21；
- 加 `test_migration_smoke.py`：真正在空库执行 `0001_baseline.sql`，断言 18 表/索引/触发器；
- 把命令、版本、退出码写进 `gate0-validation-report.md`，附日志路径。

---

## 4. P1/P2 建议

| # | 项 | 建议 |
|---|---|---|
| P1-1 | `SaveLinesRequest` 强制 `deleted_line_ids/resolutions` | v2.1 里是可选默认空；要么改成可选，要么更新 02/fixtures，明确客户端必须传空数组 |
| P1-2 | `WorkingLineInput.family_id` 必填 | 选 SKU 后 family 可由后端推导；建议改可选，后端补全；否则前端多点一次 |
| P1-3 | `price_override_reason` vs v2.1 `override_reason` | 统一命名；建议用 `override_reason`，或做映射并标 deprecated |
| P1-4 | `effective_unit_price` vs DO 的 `applied_unit_price` | 明确：草稿行用 `effective_unit_price`；DO 行必须 `applied_unit_price`；不要两个名字都表示同一列 |
| P1-5 | `OrderDraft` 缺 `conditions`/`blocked_actions` | 02 §7.1 有；可派生，但建议在 OpenAPI 明确，避免前端自己拼 |
| P1-6 | `AiStatus.checked_at` vs `last_checked_at` | 02/03 用 `last_checked_at`；统一 |
| P1-7 | `tenants` 缺 `timezone/currency` | P1 同日订单需要 MYT 业务日期；加 `timezone text default 'Asia/Kuala_Lumpur'` |
| P1-8 | `inbound_messages` 缺 `source` | P1 模拟入站 vs P0 粘贴；加 `source text check (PASTE/DEMO/WHATSAPP_SIM)` |
| P1-9 | `orders` 缺 `clarification_lang` | `OrderDraft` 有该字段；可放进 `clarification` 对象，或加列；明确一处 |
| P1-10 | `ApprovalDetail` 缺库存复核状态 | 02 §13.1 老板页要显示“库存复核”；加 `stock_check` 对象 |
| P1-11 | `ActivityItem` 缺 `actor_role` | 02 时间线要显示角色；加 |
| P1-12 | `DraftSummary` 缺 `allowed_actions` | 行操作需要；与 P0-3 一起补 |

---

## 5. 逐文件审查

| 文件 | 评分 | 评价 | 必改 |
|---|---:|---|---|
| `baseline-manifest.json` | 5.0 | 哈希/行数/字节/受保护文件都对；状态明确 | `approved_by` 在未签时先留空，避免“已批准”误读 |
| `contracts/db-schema.md` | 4.0 | 18 表/JSONB/约束清楚 | 补 users token、credit_flag 枚举、alias active、actor_role、field_diffs reason、tier>0 |
| `contracts/fields.md` | 3.5 | 字段语义细，枚举清楚 | 补 OrderDraft 的 customer/totals/allowed_actions/masked_message、Me/DraftSummary、AllowedAction、别名保存、DO 行 |
| `contracts/errors.md` | 5.0 | 23 码、扁平错误、旧码映射、`X-Request-ID` 完整 | 无；与 OpenAPI 保持一致即可 |
| `contracts/field-evidence.md` | 4.5 | H1 八条/词表/失败映射很强 | 把 `H1-TYPE`、`H1-TYPE-NEG`、DEV-39—41 加进 lexicon JSON 和测试 |
| `contracts/condition-triggers.md` | 4.0 | 真值表/词表/负例很好 | `UNKNOWN_OR_TOTAL` 不是合法 `PriceBasis`；`discount` 要加“问句/议价上下文”约束；补 `not asking for discount` |
| `contracts/openapi.yaml` | 3.5 | 13 路径/错误/X-Request-ID/本地 ref 很强 | P0-1—P0-8：解析请求、OrderDraft、DraftSummary、Me、Approval、别名保存、DO 行/仓库、AiState |
| `migrations/0001_baseline.sql` | 4.0 | 18 表/触发器/索引很好 | P0-9—P0-12：users token、credit_flag、alias active、actor_role、field_diffs、tier>0、approval delete guard |
| `contracts/fixtures/*` | 4.0 | 覆盖广、错误目录完整 | 跟随 OpenAPI 补字段；`save_lines_ready` 里 `blocking=true` 但 `resolved=true` 语义要改 |
| `tests/contract/*` | 3.0 | 结构清楚，有 13 路径/错误目录/JSON 校验 | 依赖固化、去 skip、H1/H5 行为测试、完整度测试、真实迁移测试 |
| `docs/05_...` | 4.5 | G0-01—07 分组清楚 | G0-02 “字段与枚举无漂移”目前不成立；改验收口径 |
| `docs/v2.1-erratum-1.md` | 5.0 | E1—E8 + 伴随裁决清楚 | 无；与 Gate 0 实际保持一致 |
| `docs/gate0-validation-report.md` | 4.0 | 技术校验范围写清楚 | 补命令/版本/退出码/日志；明确“机器校验≠语义完整” |
| `docs/gate0-signoff.md` | 4.5 | 未签就标未签，很好 | 技术清单 [x] 太宽；加“四端字段完整度”“无 skip 测试”“迁移真实执行” |

---

## 6. 测试与验证的具体缺口

### 6.1 当前测试覆盖了什么

- OpenAPI 可解析、13 路径、本地 ref、错误枚举与 catalog 一致；
- fixtures 是 JSON、有 wrapper/`X-Request-ID`、错误体扁平；
- fixture 请求/响应能匹配 OpenAPI；
- lexicon JSON 版本、H5 11 行、H1 三语/单位存在；
- migration SQL 含 18 表名和关键触发器名；
- demo path skip。

### 6.2 没覆盖什么

- `OrderDraft` 是否含前端必需字段；
- `DraftSummary`/`MeResponse`/`ApprovalRequest` 是否含列表/详情字段；
- `WorkingLineInput` 是否能保存别名；
- `DeliveryOrder` 是否有 `applied_unit_price`、WAREHOUSE 是否裁剪；
- `AiState` 是否与 02/03 一致；
- H5 11 行是否真的按词表触发；
- H1 词表是否真的解析 `dua ctn/three cartons/两箱`；
- migration 是否真的在空库执行（当前只是 grep）；
- 依赖是否可复现。

### 6.3 建议的最小测试集

```text
tests/contract/
├── requirements.txt
├── test_openapi_parses.py          # 去 importorskip
├── test_openapi_completeness.py    # 前端必需字段
├── test_v21_parity.py              # 关键枚举/字段
├── test_h1_behavior.py             # 词表解析
├── test_h5_behavior.py             # 11 行真值表
├── test_fixture_schemas.py         # 保留
├── test_fixtures_json.py           # 保留
├── test_migration_smoke.py         # 真执行 DDL
└── scripts/verify_gate0.py         # 一条命令跑全部
```

---

## 7. 90 分钟修订顺序

| 时间 | 动作 | 产出 |
|---|---|---|
| 0–15 | P0-1/P0-2/P0-3/P0-4：解析请求、OrderDraft、DraftSummary、Me | OpenAPI 字段+`AllowedAction` |
| 15–30 | P0-5/P0-6/P0-7/P0-8：Approval、别名保存、DO 行/仓库、AiState | OpenAPI + fixtures |
| 30–45 | P0-9/P0-10/P0-11/P0-12：users token、credit_flag、Issue.span、DB 硬化 | migration/schema/fields |
| 45–60 | 更新 fixtures 与 02 示例；修 `save_lines_ready` 的 blocking/resolved | fixtures |
| 60–75 | 加 requirements、行为测试、完整度测试、真实迁移测试 | tests/scripts |
| 75–90 | 重算哈希、更新 manifest/hashes、四方签字、`gate0-v1` | 新 Gate 0 |

> **重要**：改完任何文件后，旧 `gate0-hashes.txt` 和 `baseline-manifest.json` 的哈希都会失效。必须重算全部 35 个产物哈希，更新 manifest，再签字；不要用旧哈希签新文件。

---

## 8. 修订后的 Gate 0 完成定义

- [ ] `ParseDraftRequest` 接收 `message_text`，后端掩码；响应有 `masked_message`
- [ ] `OrderDraft` 有 `customer/totals/allowed_actions/masked_message`
- [ ] `DraftSummary` 有客户名/预览/计数/`allowed_actions`
- [ ] `MeResponse` 有 `tenant` 对象/`permission_summary`
- [ ] `ApprovalRequest/Detail` 有客户/总额/`OWNER_APPROVE|OWNER_REJECT`
- [ ] `WorkingLineInput` 有 `save_to_alias_cache/alias_scope`
- [ ] `DeliveryOrderLine` 有 `tier_unit_price/applied_unit_price`；`WarehouseDeliveryOrder` 无价格/电话/Tier
- [ ] `AiState = OFFLINE/WARMING/READY/DEGRADED`
- [ ] `users.demo_token_hash` 存在且 seed 只存哈希
- [ ] `customers.credit_flag = NONE/OVERDUE_NOTICE`
- [ ] `Issue.span` 与 02 的 `source_span` 二选一/兼容，并写 errata
- [ ] `alias_cache` 有 `active`；`activity_log/audit_logs` 有 `actor_role`；`field_diffs` 有 `reason_code/draft_version`
- [ ] `customer_tier_prices.unit_price_rm > 0`
- [ ] `approval_requests` 防 DELETE
- [ ] `tests/contract/requirements.txt` + `verify_gate0.py`；缺依赖 fail，不 skip
- [ ] H1/H5 行为测试 + 完整度测试 + 真实迁移测试全绿
- [ ] 35 个产物哈希重算；manifest 更新；四方签字；`gate0-v1` 标签
- [ ] `01`—`04` 与 v2.1 未被修改

---

## 9. 最终结论

**Gate 0 的技术骨架是优秀的，但语义契约还没闭合。** 它现在能通过“OpenAPI 语法/路径/fixture 形状”校验，却不能让前端渲染工作台、不能让后端认证、不能让 H4 保存别名、不能让老板列表显示客户与总额、不能让仓库安全裁剪价格。这些不是 P1，而是第一天就会卡住的 P0。

**建议**：**不要现在签 Gate 0。** 按 §3 的 P0-1—P0-13 修完，重算哈希，再四方签字。修完后这份 Gate 0 会非常强，可以作为后续所有板块的公共施工图；现在签，会把“字段缺口”带进 P0-A，后面返工更大。

**一句话**：**这份 Gate 0 不是“不行”，是“还差最后一公里”；把前端字段、认证、别名保存、DO 裁剪、AiState 和测试补齐，再签。**
