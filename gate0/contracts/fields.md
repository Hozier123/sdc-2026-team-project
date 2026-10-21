# KiraOrder v1.3 字段与状态契约

> 状态：`GATE0_DRAFT`。本文件是前端、AI、数据和后端的公共词典；OpenAPI 是 wire-level 机器真相，本文给出语义与不变量。

## 1. 公共枚举

```text
Role = CLERK | OWNER | WAREHOUSE

DraftStatus =
  DISAMBIGUATION_REQUIRED | READY_FOR_APPROVAL |
  PENDING_OWNER_APPROVAL | DO_GENERATED | REJECTED

TerminationReason = OWNER_REJECTED | CLERK_DISCARDED | SYSTEM_TERMINATED

IssueCode =
  MULTIPLE_PACK_SIZES | MULTIPLE_GRADES | MISSING_UOM |
  LOW_CONFIDENCE_MATCH | INSUFFICIENT_STOCK | CUSTOMER_CONDITION |
  SAME_DAY_ORDER | UNUSUAL_QTY

IssueReasonCode =
  INVALID_QUANTITY | FIELD_NOT_EVIDENCED | FAMILY_NOT_EVIDENCED |
  DUPLICATE_SPAN | OVERLAPPING_SPAN | SOURCE_EVIDENCE_INVALID |
  UNKNOWN_PRODUCT | NO_CANDIDATE | LOW_SCORE | SMALL_SCORE_GAP | AMBIGUOUS_QUANTITY

ConditionKind = STOCK | PRICE | TIME | OTHER
ConditionScope = SINGLE_LINE | MULTI_LINE | ORDER_LEVEL | UNKNOWN
AskWho = CUSTOMER | OWNER | CLERK | SYSTEM

ResolutionChoice =
  CONFIRMED_WITH_CUSTOMER | ACCEPT_REQUESTED_PRICE | NOT_A_CONDITION |
  SEPARATE_ADD_ON | DUPLICATE | CHANGE_EXISTING

EscalationCode =
  PRICE_OVERRIDE_BELOW_TIER | AMOUNT_OVER_THRESHOLD | CUSTOMER_CREDIT_FLAG

MatchSource =
  SUGGESTED_DEFAULT | LLM_EXTRACTED | RAPIDFUZZ_FALLBACK | MANUAL_SELECTED

AiMode = LLM | FALLBACK | ALIAS_ONLY | MIXED
PriceBasis = UNIT | TOTAL | UNKNOWN
ApprovalStatus = PENDING | APPROVED | REJECTED
ApprovalDecision = APPROVE | REJECT
CreditFlag = NONE | OVERDUE_NOTICE
AliasScope = CUSTOMER | TENANT
AiState = OFFLINE | WARMING | READY | DEGRADED

AllowedAction =
  EDIT_DRAFT | RESOLVE_ISSUE | COPY_CLARIFICATION |
  APPROVE_AND_GENERATE_DO | SUBMIT_FOR_OWNER |
  OWNER_APPROVE | OWNER_REJECT | CANCEL_DRAFT |
  VIEW_ACTIVITY | WAKE_AI

EscalationReason = {
  code: EscalationCode,
  line_id: string|null,
  detail: object
}
```

禁止重新公开旧状态 `DRAFT/NEEDS_REVIEW/APPROVED/CANCELLED`。`REJECTED` 的来源由 `termination_reason` 区分。`IssueResolutionAction` 整体删除；行级修改和消息级处理不得混成第二套动作枚举。

## 2. 状态机与角色

| 当前状态 | 事件 | 下一状态/结果 | 必要条件 |
|---|---|---|---|
| — | parse | `DISAMBIGUATION_REQUIRED` 或 `READY_FOR_APPROVAL` | 创建 v1 快照 |
| `DISAMBIGUATION_REQUIRED` | PUT lines | 同状态或 `READY_FOR_APPROVAL` | 无未解决阻断疑点才能 ready |
| `READY_FOR_APPROVAL` | PUT lines | 重算后的任一可编辑状态 | `expected_version` 最新 |
| `READY_FOR_APPROVAL` | CLERK approve | `DO_GENERATED` 或 `PENDING_OWNER_APPROVAL` | 六项批准硬复核通过 |
| `READY_FOR_APPROVAL` | OWNER approve | `DO_GENERATED` | 若仅命中升级规则，记录 `OWNER_SELF_APPROVED` |
| `PENDING_OWNER_APPROVAL` | OWNER decide APPROVE | `DO_GENERATED` | 绑定版本仍是当前版本；锁内库存复核 |
| `PENDING_OWNER_APPROVAL` | OWNER decide REJECT | `REJECTED` | note 必填；`OWNER_REJECTED` |
| 可编辑状态 | P1 discard | `REJECTED` | `expected_version`；note 必填；`CLERK_DISCARDED` |

- `CLERK`：解析、查看/编辑本租户草稿、提交批准；可只读查看自己提交的审批状态，但不能决定老板审批，也不能看到其他人的审批。
- `OWNER`：拥有 CLERK 的 P0 能力，可查看/决定审批、查看审计；自己的常规单可直接批准。
- `WAREHOUSE`：P0 只读获准 DO 所需视图；不编辑草稿、不决定审批。
- `PENDING_OWNER_APPROVAL`、`DO_GENERATED`、`REJECTED` 不允许 PUT lines。跨租户一律不可见。

## 3. 基础值对象

### `SpanView`

| 字段 | 类型 | 空 | 规则 |
|---|---|---:|---|
| `text` | string | 否 | 必须来自 masked text |
| `start` | integer | 否 | Unicode code point 半开区间起点，`>=0` |
| `end` | integer | 否 | 半开区间终点，`end>start` |
| `normalizer_version` | string | 否 | 产生规范值的版本 |

### `FieldEvidence`

| 字段 | 类型 | 空 | 规则 |
|---|---|---:|---|
| `field` | string | 否 | `qty/uom/family/pack_size/grade/...` |
| `raw_text` | string | 否 | 脱敏证据文本 |
| `start/end` | integer | 否 | 指向同一 masked text |
| `normalizer_version` | string | 否 | 可回放版本 |

字段证据用于审计/内部标准行；常规日志不得打印原始未脱敏内容。

## 4. `Issue`

| 字段 | 类型 | 空 | 值/语义 |
|---|---|---:|---|
| `issue_id` | string | 否 | 稳定 `ISS_...` |
| `code` | `IssueCode` | 否 | 8 个公共码 |
| `condition_id` | string | 是 | `CUSTOMER_CONDITION` 必填；其他 Issue 为 null；格式 `CND_` + 24 位大写十六进制 |
| `line_id` | string | 是 | 单行疑点 |
| `span` | string | 是 | 规范脱敏原文；前端直接显示 |
| `span_start/span_end` | integer | 是 | 相对 `masked_message` 的 Unicode code point 半开区间 |
| `source_span` | string | 是 | deprecated，只读兼容别名，由 `span` 派生 |
| `condition_kind` | `ConditionKind` | 是 | 仅条件类必填 |
| `condition_scope` | `ConditionScope` | 是 | PRICE/跨行条件必填 |
| `candidate_line_ids` | string[] | 否 | 默认 `[]` |
| `target_line_ids` | unique string[] | 否 | 默认 `[]`；人工确认目标行 |
| `requested_unit_price` | decimal string | 是 | 只可由确定性规则提取，不自动应用 |
| `price_basis` | `PriceBasis` | 是 | PRICE 必填；P0 只执行 UNIT |
| `reason_code` | `IssueReasonCode` | 是 | 细分原因，不是公共 IssueCode |
| `ask` | `AskWho` | 否 | 下一责任方 |
| `data_used` | object | 否 | 安全的规则输入摘要 |
| `blocking` | boolean | 否 | 是否阻断保存后批准 |
| `resolved` | boolean | 否 | 当前版本派生结果 |
| `resolution` | `ResolutionChoice` | 是 | 已采用的消息级处理 |
| `resolution_note` | string≤500 | 是 | 必要说明 |
| `auto_resolved_by` | `STOCK_CHECK` | 是 | 仅确定性库存重算 |

`condition_id` 固定为 `CND_ + first24(UPPER_HEX(SHA-256(UTF-8(draft_id|condition_kind|span_start|span_end))))`；不包含可变的目标行或解决结果，因此同一原始条件在保存重算后保持稳定。Issue 稳定派生键为 `(draft_id,line_id,issue_code,condition_id|null)`。每次保存与批准重新派生；旧 `resolved=true` 没有放行权。

## 5. `WorkingLine` 与写入投影

### `WorkingLine`（响应模型）

| 字段 | 类型 | 空 | 写权限/语义 |
|---|---|---:|---|
| `line_id` | string | 否 | 服务端稳定 ID；只读 |
| `client_line_ref` | string | 是 | 人工新增时的客户端关联 ID |
| `sku_id` | string | 是 | 可写；批准前必须非空且属当前租户 |
| `family_id` | string | 否 | `UNKNOWN` 表示未知；不得用 null |
| `description` | string | 是 | 显示文本 |
| `requested_qty` | positive integer | 否 | 初始解析量；只读 |
| `confirmed_qty` | positive integer | 是 | 人工确认量；可写 |
| `effective_qty` | positive integer | 否 | `confirmed_qty ?? requested_qty`；只读 |
| `uom` | string | 是 | 规范单位；可写但必须命中租户 `uom_aliases`（含 `btl/can/papan/pkt/tin/box/roll/unit` 扩展） |
| `pack_size` | string | 是 | 可写；精确规格 |
| `grade` | string | 是 | 可写；精确等级 |
| `tier_unit_price` | decimal string | 是 | 服务端价；只读 |
| `unit_price_override` | decimal string | 是 | 行级成交价写入；必须有 `override_reason` |
| `override_reason` | string≤500 | 是 | 改价时必填；统一 v2.1 命名 |
| `effective_unit_price` | decimal string | 是 | override 或 tier；只读 |
| `subtotal_rm` | decimal string | 是 | `effective_qty × effective_unit_price`；只读 |
| `match_source` | `MatchSource` | 否 | 当前 SKU 来源的唯一持久化字段 |
| `source_span` | string | 是 | 脱敏来源文本 |
| `span_start/span_end` | integer | 是 | Unicode code point 半开区间，只读 |
| `field_evidence` | `FieldEvidence[]` | 否 | 默认 `[]`；只读 |
| `candidate_skus` | `SkuCandidate[]` | 否 | 只读；未解析/低置信行返回候选，已确定行返回 `[]`；响应必带，空数组表示无候选 |
| `available_qty` | integer | 是 | 只读；当前已选 `sku_id` 的可用库存；未选 SKU 时为 null。与 `candidate_skus[].available_qty` 区分 |
| `saved_alias` | `AliasRecord` | 是 | 只读；上次保存已写入的客户级别名；无则 null |

### `SkuCandidate`

| 字段 | 类型 | 必填 | 说明 |
|---|---|---:|---|
| `sku_id` | string | 是 | 候选 SKU |
| `family_id` | string | 是 | 所属商品族 |
| `display_name` | string | 是 | 展示名 |
| `pack_size` | string | 否 | 规格 |
| `grade` | string | 否 | 等级 |
| `base_unit` | string | 是 | SKU 基本单位 |
| `tier_unit_price` | decimal string | 是 | 当前客户 Tier 的等级价 |
| `available_qty` | integer | 是 | 当前可用库存；只读 |

### `AliasRecord`

| 字段 | 类型 | 必填 | 说明 |
|---|---|---:|---|
| `alias_id` | string | 是 | `ALS_...` |
| `phrase` | string | 是 | 客户原话 |
| `target_type` | `FAMILY\|SKU` | 是 | 目标类型 |
| `family_id` | string | 否 | target=FAMILY 时 |
| `product_id` | string | 否 | target=SKU 时 |
| `scope` | `AliasScope` | 是 | `CUSTOMER/TENANT` |
| `active` | boolean | 是 | 是否生效 |
| `created_at` | date-time | 是 | 写入时间 |


`WorkingLineInput` 是可写投影，仅含 `line_id/client_line_ref/sku_id/family_id/confirmed_qty/uom/pack_size/grade/unit_price_override/override_reason/match_source/save_to_alias_cache/alias_scope`。`family_id` 在写请求中可空，由已选 SKU 推导；响应仍必须返回正式 family ID 或 `UNKNOWN`。客户端提交 `requested_qty/effective_qty/tier_unit_price/effective_unit_price/subtotal_rm/status` 必须以 422 拒绝，不能静默接受。

当 `save_to_alias_cache=true` 时，必须是本次人工选定 SKU/FAMILY，`phrase_norm` 来自当前 masked span，`confirmed_by` 来自会话；`alias_scope=TENANT` 仅 OWNER 可用。默认 `false/CUSTOMER`。保存成功后响应行返回 `saved_alias`；`save_to_alias_cache` 本身不是持久行状态，后续保存未勾选**不会**静默撤销已有别名，撤销必须是显式 P1 动作。

删除必须放进 `deleted_line_ids`，不得用 `confirmed_qty=0` 或只从 `lines` 中省略来表示。

## 6. `IssueResolution` 与 `SaveLinesRequest`

### `IssueResolution`

| 字段 | 类型 | 空 | 规则 |
|---|---|---:|---|
| `issue_id` | string | 否 | 当前版本中的消息级疑点 |
| `choice` | `ResolutionChoice` | 否 | 仅 6 个动作 |
| `target_line_ids` | unique string[] | 否 | 默认 `[]`；PRICE 接受时必填 |
| `confirmed_unit_price` | decimal string | 是 | `ACCEPT_REQUESTED_PRICE` 输入；后端映射到目标行；与目标行 `unit_price_override` 同时出现时必须一致，否则 422 `REQUEST_VALIDATION_FAILED` |
| `price_basis` | `PriceBasis` | 是 | 接受价格必须为 UNIT |
| `note` | string≤500 | 是 | `NOT_A_CONDITION` 等规则要求时必填 |

> 唯一价格来源规则：`confirmed_unit_price` 只用于消息级价格条件；目标行最终成交价以 `unit_price_override` 为准。两者同时出现且不等时，不猜测优先级，直接 422。

### `SaveLinesRequest`

| 字段 | 类型 | 必填 | 语义 |
|---|---|---:|---|
| `expected_version` | positive integer | 是 | 必须等于当前版本 |
| `lines` | `WorkingLineInput[]` | 是 | 保存后的完整剩余行集合 |
| `deleted_line_ids` | unique string[] | 否 | 默认 `[]`；本次显式删除的旧行 |
| `resolutions` | `IssueResolution[]` | 否 | 默认 `[]`；只处理消息级疑点 |

验证顺序：

1. 每个当前旧 `line_id` 恰好出现于 `lines` 或 `deleted_line_ids`；不能两处同时出现，未知删除 ID 拒绝。
2. `lines` 至少一行，否则 `EMPTY_ORDER`。
3. `client_line_ref` 只用于新人工行且请求内唯一；服务端生成正式 `line_id`。
4. 重算 effective qty、匹配、库存疑点、价格、条件目标、澄清、升级预演和状态。
5. 原子写当前聚合、新版本快照、活动与审计；任一步失败全部回滚。

## 7. `OrderDraft`

| 字段 | 类型 | 空 | 说明 |
|---|---|---:|---|
| `draft_id` | string | 否 | 草稿 ID |
| `version` | positive integer | 否 | 当前乐观锁版本 |
| `status` | `DraftStatus` | 否 | 五状态 |
| `do_number` | string | 是 | 仅 `DO_GENERATED` 非空；用 `GET /delivery-orders/{do_number}` 读取 DO |
| `customer_id` | string | 否 | 当前租户客户 |
| `customer` | `CustomerSummary` | 否 | ID、名称、Tier、信用枚举；电话按角色裁剪 |
| `masked_message` | string | 否 | 后端本地掩码后的展示文本；原始请求不持久化 |
| `ai_mode` | `AiMode` | 否 | 行级来源汇总 |
| `lines` | `WorkingLine[]` | 否 | 当前完整行 |
| `issues` | `Issue[]` | 否 | 当前完整疑点 |
| `conditions` | `Issue[]` | 否 | `CUSTOMER_CONDITION` 的只读派生子集 |
| `blocking_issues` | `IssueCode[]` | 否 | 未解决阻断码去重列表 |
| `escalation_preview` | `EscalationReason[]` | 否 | 当前升级原因预演；对象数组，不是字符串数组 |
| `totals` | `OrderTotals` | 否 | `order_total/currency=MYR/is_complete`；金额由后端计算 |
| `allowed_actions` | `AllowedAction[]` | 否 | 前端按钮唯一依据 |
| `blocked_actions` | map[action,reason[]] | 否 | 被阻断动作及机器原因 |
| `clarification_draft` | `ClarificationDraft` | 是 | 可发送澄清草稿 |
| `clarification_lang` | string | 是 | 模板语言 |
| `ignored_spans` | `SpanView[]` | 否 | raw AI `ignored` 定位后的字段 |
| `disambiguations` | `Issue[]` | 是 | deprecated，只读派生兼容字段 |
| `termination_reason` | `TerminationReason` | 是 | 仅 REJECTED |
| `terminated_by_user_id` | string | 是 | 人工终止者 |
| `termination_note` | string | 是 | 人工终止原因 |
| `created_at/updated_at` | date-time | 否 | RFC 3339 |

### `ClarificationDraft`

`language`、`message`、`unresolved_issue_ids` 必填；文本只引用脱敏信息，不得声称已确认未知价格、SKU 或数量。

### 列表、身份与 AI 状态

- `DraftSummary` 必含 `customer_name/message_preview/open_blocking_issue_count/owner_escalation_count/extraction_sources/allowed_actions`；`do_number` 仅 `DO_GENERATED` 非空；预览必须来自 masked message。
- `MeResponse` 必含 `tenant:{id,name}`、`role`、`permissions:AllowedAction[]` 与 `permission_summary`；角色和权限只从 Bearer 会话获得。
- `AiStatus/AiWakeResult` 统一使用 `AiState=OFFLINE/WARMING/READY/DEGRADED`，并返回 `fallback_available/last_checked_at/message`。

## 8. 批准对象

### `ApproveRequest`

| 字段 | 类型 | 必填 | 规则 |
|---|---|---:|---|
| `expected_version` | positive integer | 是 | 批准当前已保存版本 |
| `confirmed_items` | `WorkingLineInput[]` | 否 | deprecated 兼容路径；若出现，必须同事务先保存为新版本再批准该新版本 |

常规新前端不得使用 `confirmed_items`。

### `ApprovalRequest` / `ApprovalDetail`

| 字段 | 类型 | 说明 |
|---|---|---|
| `approval_id` | string | 待办 ID |
| `draft_id/draft_version` | string/integer | 绑定不可变版本 |
| `status` | `ApprovalStatus` | 审批状态 |
| `customer` | `CustomerSummary` | 列表可显示客户；不得让前端另查后拼 |
| `total_rm/line_count` | decimal string/integer | 列表选择所需总额和行数 |
| `reasons` | `EscalationReason[]` | 升级原因快照；对象数组，含 `code/line_id/detail` |
| `requested_by/requested_at` | string/date-time | 请求信息 |
| `allowed_actions` | `AllowedAction[]` | **只针对当前调用者**；CLERK 为 `[]`，OWNER 才返回 `OWNER_APPROVE/OWNER_REJECT`；请求体 decision 仍用 `APPROVE/REJECT` |

`ApprovalDetail` 还必须包含 `snapshot`（客户 ID/名称、脱敏原话、最终 lines、total、reasons）、`field_diffs`、`stock_check` 和可空的 `decided_by/decided_at/decision_note`。列表可以省略完整 snapshot，但不得让前端自行猜测动作权限。

读取权限固定如下：OWNER 可读当前租户全部审批并可用 `mine=true` 过滤本人提交；CLERK 无论是否传 `mine` 都由服务端强制过滤为 `requested_by=current_user`，详情仅能读取本人提交项，越权统一返回 404，且 `allowed_actions=[]`；WAREHOUSE 返回 403。只有 OWNER 可调用 decide。

### `DecideRequest`

| 字段 | 类型 | 必填 | 规则 |
|---|---|---:|---|
| `decision` | `APPROVE/REJECT` | 是 | 仅 OWNER |
| `note` | string≤500 | 条件 | REJECT 必填且非空 |

客户端不重复提交 draft lines/version；服务端从 approval 绑定快照复核当前状态与版本。

## 9. `DeliveryOrder`、审计与回复

| 字段 | 类型 | 空 | 说明 |
|---|---|---:|---|
| `do_number` | string | 否 | 稳定 DO 号 |
| `draft_id/draft_version` | string/integer | 否 | 被批准版本 |
| `customer_id` | string | 否 | 客户 |
| `customer_name` | string | 否 | 批准时客户显示名快照；DO 与审计无需另查客户主档 |
| `lines` | `DeliveryOrderLine[]` | 否 | 不可变终稿；不复用草稿 WorkingLine |
| `final_total_rm` | decimal string | 否 | 最终总额 |
| `prepared_by/approved_by` | string | 否 | 制单/批准用户 |
| `escalation_reasons` | `EscalationReason[]` | 否 | 默认 `[]`；OWNER 自批亦记录；对象数组 |
| `approval_mode` | `DIRECT/OWNER_APPROVED/OWNER_SELF_APPROVED` | 否 | 批准路径 |
| `reply_draft` | `ReplyDraft` | 否 | 供人工发送的回复草稿 |
| `related_do_number` | string | 是 | 同日/关联单 |
| `approved_at` | date-time | 否 | 批准时间 |

`ReplyDraft` 必含 `language/message/do_number`，可含 `warnings[]`；它是模板草稿，不代表系统已向客户发送。

`DeliveryOrderLine` 固定为 `line_id/sku_id/display_name/quantity/unit/tier_unit_price/applied_unit_price/subtotal_rm/override_reason?/picking_note?`。草稿行用 `effective_unit_price`，DO 行只用 `applied_unit_price`，两者不得混用。

`WarehouseDeliveryOrder` 只含 `do_number/customer_name/items/approved_at`；item 只含 `sku_id/display_name/quantity/unit/picking_note`。价格、总额、客户电话/Tier/信用提醒、原消息和 AI 差异必须由后端裁剪，不能依赖前端隐藏。

`AuditDetail` 必含 DO、AI 初始快照摘要、最终快照、字段差异、操作者和时间线。敏感原文不得出现；跨租户同样 404。

### DO 读取与刷新

- `OrderDraft.do_number` / `DraftSummary.do_number` 在 `DO_GENERATED` 时非空；前端刷新用 `GET /delivery-orders/{do_number}`（CLERK/OWNER）恢复完成页。
- 仓库视图用 `GET /warehouse/delivery-orders/{do_number}`（P1，WAREHOUSE）；响应只含 `do_number/customer_name/items/approved_at`，服务端已裁剪价格、电话、Tier、原消息。
- `GET /delivery-orders/{do_number}` 对 WAREHOUSE 返回 403；`GET /warehouse/...` 对 CLERK/OWNER 返回 403。

### `FieldDiff` 路径

- `field_path` 是**相对 `line_id` 的字段路径**（如 `unit_price_override`、`sku_id`）；`line_id` 为空时相对 draft/DO 根（如 `status`）。
- 不使用 `lines[0].unit_price` 这类数组下标；行通过稳定 `line_id` 关联，避免数组重排后错位。

### `StockCheckSummary`

- `lines[]` 必含 `line_id/sku_id/requested_qty/effective_qty/available_qty/sufficient`。
- `requested_qty` 是原始解析量；`effective_qty` 是本次实际复核量（`confirmed_qty ?? requested_qty`）。减量后前端展示 `effective_qty`，不要拿 `requested_qty` 当当前量。
- `STOCK_CHANGED.details.lines[]` 同样包含 `effective_qty`，并保留 `requested_qty` 供审计。

## 10. 终止字段约束

- 非 `REJECTED`：`termination_reason/terminated_by_user_id/termination_note` 全部为空。
- `OWNER_REJECTED`：决定者与非空 note 必填。
- `CLERK_DISCARDED`：作废者与非空 note 必填；端点属于 P1。
- `SYSTEM_TERMINATED`：`terminated_by_user_id` 可空，必须有可审计原因；不能伪装成人工驳回。

## 11. 租户配置字段

`amount_threshold_rm` 是唯一金额阈值；`checks_enabled` 给出各检查布尔开关；`below_tier_price_override_requires_owner` 只控制低于等级价；`credit_flag_requires_owner` 只控制信用标记。旧名 `owner_approval_threshold/price_override_requires_owner` 仅可出现在迁移映射，不得进入新 wire 或新 seed。
