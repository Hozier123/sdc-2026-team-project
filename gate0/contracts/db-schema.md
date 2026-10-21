# KiraOrder v1.3 物理数据库契约

> 状态：`GATE0_DRAFT`。P0 采用 PostgreSQL、v2.1 表名和 JSONB 聚合快照。这里定义事务真相；不得再建 `drafts/skus/draft_lines/issues/conditions/delivery_order_lines/approval_decisions` 作为第二套可写真相。

## 1. 全局不变量

- 所有业务查询和写入先由 Bearer 会话确定 `tenant_id`；跨租户资源对外按 404 处理。
- 标识符为稳定字符串；时间为 `timestamptz`，服务端按 UTC 存储。
- 租户展示时区固定记录于 `tenants.timezone`（P0 默认 `Asia/Kuala_Lumpur`），金额币种记录于 `tenants.currency`（P0 仅 `MYR`）。
- 金额数据库类型固定 `numeric(12,2)`；API 使用 decimal string。数量为正整数，库存允许 0。
- `orders` 是当前可变草稿聚合；`draft_versions.snapshot`、`delivery_orders.lines` 是不可变事实。
- `activity_log`、`audit_logs`、`field_diffs` 只追加。数据库触发器拒绝 UPDATE/DELETE。
- JSONB 列须保持约定顶层类型：集合为 array、开关/快照为 object；更细字段由 `fields.md` 和 OpenAPI 约束。
- 物理名映射：`skus→products`、`drafts→orders`、`customer_aliases→alias_cache`、`activity_logs→activity_log`。

## 2. 表清单

| 表 | 作用 | 主键/关键唯一性 |
|---|---|---|
| `tenants` | 租户规则与阈值 | `tenant_id` |
| `users` | 身份和角色 | `user_id`；角色仅 `CLERK/OWNER/WAREHOUSE` |
| `customers` | 客户主档 | `customer_id`；同租户 `phone_e164` 唯一（非空时） |
| `product_families` | 商品族闭集 | `family_id`；`(tenant_id,family_id)` 可供复合外键 |
| `family_aliases` | 商品族多语别名 | 同租户 `phrase_norm` 不跨族重复 |
| `products` | SKU 真相 | `product_id`；同租户 `sku_code` 唯一 |
| `uom_aliases` | 单位精确别名 | 同租户 `alias_norm` 唯一；P0 不隐式换算 |
| `customer_tier_prices` | SKU×Tier 等级价 | `(tenant_id,product_id,tier)` |
| `inventory` | 可用库存 | `(tenant_id,product_id)`；`available_qty>=0` |
| `alias_cache` | 已确认客户/租户别名 | 活跃记录的 `(tenant_id,coalesce(customer_id,''),phrase_norm)` 唯一 |
| `inbound_messages` | 脱敏入站消息 | `(tenant_id,message_id)`；只存 masked text |
| `orders` | 草稿聚合根 | `(tenant_id,draft_id)`；当前 `version` |
| `draft_versions` | 不可变版本快照 | `(tenant_id,draft_id,version)` |
| `approval_requests` | 老板审批 | `approval_id`；每租户/草稿最多一个 PENDING |
| `delivery_orders` | 已批准 DO | `do_number`；`(tenant_id,draft_id)` 唯一 |
| `activity_log` | UI 时间线 | identity；append-only |
| `audit_logs` | 审计头 | `audit_id`；append-only |
| `field_diffs` | 字段级差异 | identity；append-only |

## 3. 主数据与配置

### `tenants`

| 列 | 类型 | 空 | 默认/约束 | 语义 |
|---|---|---:|---|---|
| `tenant_id` | text | 否 | PK | 租户 ID |
| `name` | text | 否 | — | 显示名 |
| `timezone` | text | 否 | `Asia/Kuala_Lumpur` | 租户展示时区；数据库时间仍存 UTC |
| `currency` | text | 否 | `MYR` | P0 唯一结算币种 |
| `amount_threshold_rm` | numeric(12,2) | 否 | `>=0` | 金额升级阈值 |
| `checks_enabled` | jsonb object | 否 | `{}` | 检查开关 |
| `below_tier_price_override_requires_owner` | boolean | 否 | true | 低于等级价是否升级 |
| `credit_flag_requires_owner` | boolean | 否 | true | 信用标记是否升级 |
| `created_at/updated_at` | timestamptz | 否 | `now()` | 审计时间 |

### `users` / `customers`

| 表 | 必要列 | 约束 |
|---|---|---|
| `users` | `user_id,tenant_id,display_name,demo_token_hash,role,active,created_at` | `role∈{CLERK,OWNER,WAREHOUSE}`；只存演示 token 哈希，不存明文 token |
| `customers` | `customer_id,tenant_id,name,phone_e164,tier,credit_flag,active,created_at,updated_at` | `credit_flag∈{NONE,OVERDUE_NOTICE}`；E.164 由应用校验；同租户非空电话唯一 |

### 商品、价格、库存与别名

| 表 | 必要列 | 约束 |
|---|---|---|
| `product_families` | `family_id,tenant_id,family_name,family_version,active` | `family_version>0` |
| `family_aliases` | `alias_id,tenant_id,family_id,language,phrase,phrase_norm` | 复合 FK 保证同租户；`(tenant_id,phrase_norm)` unique |
| `products` | `product_id,tenant_id,family_id,sku_code,name,pack_size,grade,base_unit,active` | 同租户 SKU unique；family 同租户 |
| `uom_aliases` | `alias_id,tenant_id,canonical_unit,language,alias,alias_norm` | exact normalized match；同租户 alias unique |
| `customer_tier_prices` | `tenant_id,product_id,tier,unit_price_rm,updated_at` | `unit_price_rm>0`；复合 PK/FK |
| `inventory` | `tenant_id,product_id,available_qty,updated_at` | `available_qty>=0`；批准时按 product_id 稳定顺序锁定 |
| `alias_cache` | `alias_id,tenant_id,customer_id,phrase,phrase_norm,target_type,family_id,product_id,active,revoked_at,confirmed_by,created_at` | `target_type∈{FAMILY,SKU}` 且只允许对应一个目标；customer 可空表示租户级；仅活跃别名参与唯一索引；撤销记录保留审计轨迹 |

`uom_aliases` 是**租户可扩展真相**，P0 loader 必须读取；Gate 0 `field-evidence.md` 的 5 个单位只是最小 seed。seed 的 `btl/can/papan/pkt/tin/box/roll/unit` 通过 `uom_aliases` 登记（`pkt→pack`、`unit→pc` 仅在对应 SKU `base_unit=pc` 时）。P0 不做隐式换算。

## 4. 消息与草稿

### `inbound_messages`

| 列 | 类型 | 空 | 约束/说明 |
|---|---|---:|---|
| `tenant_id,message_id` | text | 否 | 复合 PK |
| `customer_id` | text | 否 | 同租户 FK |
| `source` | text | 否 | `PASTE/DEMO/WHATSAPP_SIM` |
| `masked_text` | text | 否 | 只允许脱敏文本；原始 PII 禁止入库 |
| `language` | text | 是 | `ms/en/zh/...` |
| `received_at` | timestamptz | 否 | 默认 now() |

`masked_text` 的 PII token 只允许 `[REDACTED_PHONE]`、`[REDACTED_MYKAD]`、`[REDACTED_EMAIL]`；应用层在 INSERT 前完成掩码并校验，数据库不得接收原始 `message_text`。

### `orders`

| 列 | 类型 | 空 | 默认/约束 | 说明 |
|---|---|---:|---|---|
| `tenant_id,draft_id` | text | 否 | 复合 PK | 草稿身份 |
| `customer_id` | text | 否 | 同租户 FK | 客户 |
| `message_id` | text | 是 | 同租户 FK | 入站消息 |
| `status` | text | 否 | 五状态 CHECK | 见 `fields.md` |
| `version` | integer | 否 | 1，`>0` | 乐观锁版本 |
| `ai_mode` | text | 否 | 四值 CHECK | `LLM/FALLBACK/ALIAS_ONLY/MIXED` |
| `ai_initial_snapshot` | jsonb object | 是 | — | 原始 AI 只读快照 |
| `working_lines` | jsonb array | 否 | `[]` | 当前行 |
| `issues` | jsonb array | 否 | `[]` | 当前疑点与条件 |
| `clarification` | jsonb object | 是 | — | 当前澄清对象 |
| `escalation_preview` | jsonb array | 否 | `[]` | 升级预演 |
| `termination_reason` | text | 是 | 三值 CHECK | 仅 `REJECTED` 非空 |
| `terminated_by_user_id` | text | 是 | user FK | 人工终止必须有 |
| `termination_note` | text | 是 | `<=500` | OWNER/CLERK 终止必填 |
| `created_at/updated_at` | timestamptz | 否 | `now()` | 时间 |

### `draft_versions`

| 列 | 类型 | 空 | 约束/说明 |
|---|---|---:|---|
| `tenant_id,draft_id,version` | text,text,int | 否 | 复合 PK；FK orders；`version>0` |
| `snapshot` | jsonb object | 否 | lines/issues/conditions/totals/clarification 完整快照 |
| `created_by` | text | 否 | user FK |
| `created_at` | timestamptz | 否 | 默认 now() |

该表 INSERT 后不可 UPDATE/DELETE。保存事务必须原子更新 `orders`、新增 `draft_versions`、追加 activity/audit。

## 5. 审批与 DO

### `approval_requests`

| 列 | 类型 | 空 | 约束/说明 |
|---|---|---:|---|
| `approval_id` | text | 否 | PK |
| `tenant_id,draft_id,draft_version` | text,text,int | 否 | FK 到不可变 `draft_versions` |
| `status` | text | 否 | `PENDING/APPROVED/REJECTED` |
| `reasons` | jsonb array | 否 | 升级原因快照 |
| `snapshot` | jsonb object | 否 | lines/totals/reasons/customer spans 完整快照 |
| `requested_by/requested_at` | text/timestamptz | 否 | 提交人/时间 |
| `decided_by/decided_at/decision_note` | text/timestamptz/text | 是 | 仅决定后填写；驳回 note 必填 |

唯一部分索引保证同一草稿至多一个 `PENDING`。触发器禁止 DELETE，禁止更改租户、草稿、版本、reasons、snapshot 与请求人，只允许从 `PENDING` 合法决定为 `APPROVED/REJECTED`。

### `delivery_orders`

| 列 | 类型 | 空 | 约束/说明 |
|---|---|---:|---|
| `do_number` | text | 否 | PK |
| `tenant_id,draft_id` | text | 否 | 同租户 FK；一草稿一 DO |
| `customer_id` | text | 否 | 同租户 FK |
| `draft_version` | integer | 否 | FK 到被批准快照 |
| `lines` | jsonb array | 否 | 不可变最终行 |
| `final_total_rm` | numeric(12,2) | 否 | `>=0` |
| `prepared_by/approved_by` | text | 否 | user FK；OWNER 自批可同人 |
| `escalation_reasons` | jsonb array | 否 | 默认 `[]` |
| `reply_draft` | jsonb object | 否 | 回复模板快照 |
| `related_do_number` | text | 是 | 同表 FK |
| `approved_at` | timestamptz | 否 | 默认 now() |

整行 INSERT 后不可 UPDATE/DELETE。重复批准通过 `(tenant_id,draft_id)` 唯一性恢复已有 `do_number/approved_at`。

## 6. 活动与审计

| 表 | 必要列 | 约束 |
|---|---|---|
| `activity_log` | `activity_id,tenant_id,draft_id,do_number,event_type,payload,actor_user_id,actor_role,created_at` | append-only；payload 仅安全摘要；`actor_role` 记录事件发生时角色 |
| `audit_logs` | `audit_id,tenant_id,draft_id,draft_version,do_number,actor_user_id,actor_role,action,payload,created_at` | append-only；角色为历史快照 |
| `field_diffs` | `field_diff_id,audit_id,draft_version,line_id,field_path,before_value,after_value,source,reason_code,created_at` | append-only；audit FK；版本和原因码必填 |

## 7. 迁移与验收

- 权威 DDL：`migrations/0001_baseline.sql`；应可在空 PostgreSQL schema 一次执行。
- seed 不属于本迁移；进入 P0 前必须校验 SKU×Tier 价格矩阵、合成电话、族与单位词表。
- 验收必须确认 18 张表、三个部分/表达式唯一索引、审批 UPDATE/DELETE 保护触发器和 append-only 触发器存在。
- Gate 0 不包含仓储业务 SQL、扣库存过程或 FastAPI 实现。
