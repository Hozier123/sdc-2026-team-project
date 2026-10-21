# KiraOrder v1.3 后端与前端对接规则

> 状态：`HANDOFF_DRAFT`（2026-10-22）  
> 适用基线：`gate0-baseline-v1` / Gate 0 v4 / draft revision 5  
> 基线哈希：`6A44089C623C1B4AE8F444660DBD89422C663E7EBDD141EA6FDA549DDD833770`  
> Canonical：`gate0/`（冻结，不可修改）  
> 本文性质：从 Gate 0 v4 派生的前端对接说明；与 `gate0/` 冲突时，**以 `gate0/` 为准**。

---

## 0. 先读这一节

### 0.1 本文不能替代的契约

以下文件是唯一机器可读真相：

```text
gate0/contracts/openapi.yaml
gate0/contracts/fields.md
gate0/contracts/errors.md
gate0/contracts/fixtures/
gate0/docs/gate0-test-data-map.md
```

本文只做三件事：

1. 把前端最常用的端点、字段、状态和错误集中到一页；
2. 标出 v1.2 → v1.3 的前端行为变化；
3. 给出联调验收清单。

### 0.2 不得修改 Gate 0

- 不修改 `gate0/` 内任何文件；
- 不修改 `gate0/contracts/openapi.yaml` 来“适配前端”；
- 前端类型以 OpenAPI v4 为准，不以旧 02 v1.2 为准；
- 发现契约缺口：记录问题，开 `gate0-v5` 流程，不要热修。

### 0.3 当前版本

```text
OpenAPI info.version = 1.3.0-gate0-v4
契约端点 = 16
受控文件 = 73
测试 = 42 passed
H1 = field-evidence-v2（35 例）
H5 = condition-triggers-v3（16 行真值表）
PII = pii-mask-tokens-v1
```

---

## 1. v1.2 → v1.3 的前端变化

| 变化 | 前端要做什么 |
|---|---|
| `WorkingLine.available_qty` 新增，必填只读 | 当前已选 SKU 的库存列直接读它；未选 SKU 时为 `null` |
| `candidate_skus` 在已确定行为 `[]` | 已确定行不显示候选控件；未解析行才显示候选 |
| 新增 `parse_draft_ambiguous.json` | 用未解析候选样例做 UI 状态测试 |
| `ClarificationDraft.language` 与正文必须一致 | `ms` 必须显示马来语正文；不能出现 `ms` + 英文正文 |
| `Issue.reason_code` 新增 `AMBIGUOUS_QUANTITY` | 数量多候选时显示“需人工确认数量”，不要自动选第一个 |
| `pack_size` 成为独立字段 | 规格（`500g`、`2kg`、`12 x 1L`）单独显示，不参与 qty |
| 审批详情快照 `span_end` 修正 | 高亮按 `masked_customer_text` 切片，不许多选逗号 |
| 缺货 fixture 绑定实际行 | `INSUFFICIENT_STOCK` 的 `line_id` 必须能定位行；`clarification_draft` 非空 |
| `H5` 16 行真值表 | 条件卡片按 PRICE/STOCK/OTHER 展示；STOCK 条件本身不阻断 |
| `IssueReasonCode` 闭集扩展 | 前端遇到未知 reason_code 时走通用 fallback，不能崩溃 |

---

## 2. 端点总表

所有业务成功响应直接返回模型，不使用 `{data: ...}` 包装；所有响应返回 `X-Request-ID`。

| # | 方法 | 路径 | 角色 | 成功 | 主要错误 |
|---:|---|---|---|---|---|
| 1 | POST | `/api/v1/orders/parse-draft` | CLERK / OWNER | 200 `OrderDraft` | 401/403/422/429/503 |
| 2 | GET | `/api/v1/orders/drafts` | CLERK / OWNER | 200 `DraftListResponse` | 401/403/422 |
| 3 | GET | `/api/v1/orders/drafts/{draft_id}` | CLERK / OWNER | 200 `OrderDraft` | 401/403/404 |
| 4 | PUT | `/api/v1/orders/drafts/{draft_id}/lines` | CLERK / OWNER | 200 `OrderDraft` | 400/401/403/404/409/422 |
| 5 | POST | `/api/v1/orders/{draft_id}/approve` | CLERK / OWNER | 200 `DeliveryOrder` 或 202 `ApprovalRequest` | 400/401/403/404/409/422 |
| 6 | GET | `/api/v1/approvals` | OWNER；CLERK 仅本人 | 200 `ApprovalListResponse` | 401/403/422 |
| 7 | GET | `/api/v1/approvals/{approval_id}` | OWNER / 相关 CLERK | 200 `ApprovalDetail` | 401/403/404 |
| 8 | POST | `/api/v1/approvals/{approval_id}/decide` | OWNER | 200 `DeliveryOrder` 或 `ApprovalDecisionResult` | 400/401/403/404/409/422 |
| 9 | GET | `/api/v1/orders/{do_number}/audit-detail` | CLERK / OWNER | 200 `AuditDetail` | 401/403/404 |
| 10 | GET | `/api/v1/activity` | CLERK / OWNER | 200 `ActivityListResponse` | 401/403/422 |
| 11 | GET | `/api/v1/me` | 已登录 | 200 `MeResponse` | 401 |
| 12 | GET | `/api/v1/ai/status` | CLERK / OWNER | 200 `AiStatus` | 401/403 |
| 13 | POST | `/api/v1/ai/wake` | CLERK / OWNER | 200 `AiWakeResult` | 401/403/429/503 |
| 14 | GET | `/api/v1/customers` | CLERK / OWNER | 200 `CustomerListResponse` | 401/403/422 |
| 15 | GET | `/api/v1/delivery-orders/{do_number}` | CLERK / OWNER | 200 `DeliveryOrder` | 401/403/404 |
| 16 | GET | `/api/v1/warehouse/delivery-orders/{do_number}` | WAREHOUSE（P1 视图绑定） | 200 `WarehouseDeliveryOrder` | 401/403/404 |

`approve` 的 200 与 202 都是正常成功：

- 200：直接生成 DO；
- 202：进入 OWNER 审批；
- 前端必须按 HTTP 分支，不能从 body 猜。

---

## 3. 核心对象

### 3.1 `OrderDraft`

前端最少需要读：

```text
draft_id
status
version
customer_id / customer
lines[]
issues[]
conditions[]
totals
clarification_draft
clarification_lang
blocking_issues[]
allowed_actions[]
blocked_actions{}
masked_message
created_at / updated_at
```

### 3.2 `WorkingLine`

| 字段 | 前端用法 |
|---|---|
| `line_id` | 行定位、Issue 绑定、保存 |
| `sku_id` | 已确定 SKU；未解析为 `null` |
| `description` | 展示描述；不要自行拼接成 SKU |
| `requested_qty` / `effective_qty` | 客户要求 / 当前生效 |
| `uom` | 展示单位；P0 不做自动换算 |
| `candidate_skus[]` | 未解析行候选；已确定行为 `[]` |
| `candidate_skus[].available_qty` | **候选 SKU** 的库存 |
| `available_qty` | **当前已选 SKU** 的库存；未选为 `null` |
| `tier_unit_price` / `effective_unit_price` | 等级价 / 当前生效价 |
| `subtotal_rm` | 只读展示 |
| `field_evidence[]` | 高亮原文证据 |
| `saved_alias` | 上次保存的别名；无则 `null` |

**不要混用**：

```text
candidate_skus[].available_qty  → 候选比较
WorkingLine.available_qty       → 当前行库存列
```

### 3.3 `SkuCandidate`

```text
sku_id
family_id
display_name
pack_size
grade
base_unit
tier_unit_price
available_qty
```

### 3.4 `Issue`

前端展示字段：

```text
issue_id
code
line_id
span / span_start / span_end
condition_kind / condition_scope
candidate_line_ids[]
target_line_ids[]
ask
blocking
resolved
reason_code
data_used
```

要求：

- `span_start/span_end` 是 Unicode code point 半开区间；
- 高亮只能按服务端给的 masked text 切；
- `reason_code=AMBIGUOUS_QUANTITY` 显示“数量需确认”，不要自动选第一个候选；
- `code=INSUFFICIENT_STOCK` 必须能通过 `line_id` 定位实际行；`clarification_draft` 可直接复制；
- `STOCK` 条件本身 `blocking=false`；缺货由行级 `INSUFFICIENT_STOCK` 阻断。

### 3.5 `ClarificationDraft`

```text
language: ms | en | zh
message: 对应语言的正文
unresolved_issue_ids[]
```

规则：

- `language=ms` 时 `message` 必须是马来语；
- `COPY_CLARIFICATION` 只在 `clarification_draft != null` 时可用；
- 不要在前端翻译服务端正文；按 `language` 选择显示模板。

### 3.6 审批与 DO

- `ApprovalDetail.snapshot.lines[].span_end` 必须与 `masked_customer_text` 切片一致；
- `approval_detail` 里的行只读；
- 审批决定成功后返回 DO 或 `ApprovalDecisionResult`；
- `ALREADY_APPROVED` 409 应导航到已有 `do_number`，不能重复创建。

---

## 4. 状态与按钮

`DraftStatus` 以 OpenAPI 闭集为准，只有：

```text
DISAMBIGUATION_REQUIRED
READY_FOR_APPROVAL
PENDING_OWNER_APPROVAL
DO_GENERATED
REJECTED
```

| 状态/字段 | 前端行为 |
|---|---|
| `DISAMBIGUATION_REQUIRED` | 显示疑点卡；批准按钮禁用 |
| `READY_FOR_APPROVAL` | 可保存/批准；按 `blocking_issues` 判断 |
| `PENDING_OWNER_APPROVAL` | 只读；显示“等待老板审批” |
| `DO_GENERATED` | 只读；显示 DO |
| `REJECTED` | 只读终止页 |
| `blocking_issues[]` 非空 | 批准禁用，显示对应 Issue |
| `allowed_actions[]` | 只渲染服务端允许的动作 |
| `blocked_actions{}` | 禁用原因按 code 映射 |
| `version` 变化 | 旧版本编辑器失效，重新拉取 |

特别规则：

```text
PUT lines 遇到缺货：HTTP 200，version 照常 +1，返回 INSUFFICIENT_STOCK Issue
approve 遇到缺货：HTTP 400 INSUFFICIENT_STOCK
```

保存成功不等于可批准；不要把缺货 200 当失败，也不要忽略 Issue。

---

## 5. 错误处理

只依赖 `error_code` + HTTP；`message` 只用于默认展示。

| HTTP | error_code | 前端动作 |
|---:|---|---|
| 400 | `DISAMBIGUATION_UNRESOLVED` | 聚焦未解决疑点 |
| 400 | `INSUFFICIENT_STOCK` | 聚焦缺货行，提供减量/删除 |
| 400 | `TARGET_LINE_REQUIRED` | 打开目标行选择 |
| 400 | `OVERRIDE_REQUIRED` | 聚焦目标行价格/原因 |
| 400 | `NOTE_REQUIRED` | 聚焦备注 |
| 400 | `EMPTY_ORDER` | 要求保留/新增一行 |
| 400 | `INVALID_LINE_OPERATION` | 刷新草稿，重建编辑集 |
| 401 | `INVALID_TOKEN` | 重新认证 |
| 403 | `FORBIDDEN_ACTION` | 隐藏/禁用动作 |
| 403 | `TENANT_MISMATCH` | 丢弃本地请求 |
| 404 | `RESOURCE_NOT_FOUND` | 返回列表，不区分越权 |
| 409 | `STALE_VERSION` | 拉最新草稿，提示重放修改 |
| 409 | `PENDING_OWNER_APPROVAL` | 切只读 |
| 409 | `ALREADY_APPROVED` | 打开 `details.do_number` |
| 409 | `DRAFT_REJECTED` | 终止只读页 |
| 409 | `STOCK_CHANGED` | 刷新库存，让 OWNER 重试 |
| 422 | `REQUEST_VALIDATION_FAILED` | 按 `details.fields` 标注 |
| 422 | `MESSAGE_TOO_LONG` | 显示 4000 code point 限制 |
| 422 | `INVALID_QUANTITY` | 聚焦数量 |
| 422 | `MISSING_TIER_PRICE` | 阻断并提示管理员修配置 |
| 429 | `RATE_LIMITED` | 按 `Retry-After` 延迟 |
| 503 | `AI_AND_FALLBACK_UNAVAILABLE` | 保留输入，稍后重试 |

---

## 6. 联调样例

必须用 Gate 0 fixtures 做契约测试：

```text
gate0/contracts/fixtures/parse_draft.json
gate0/contracts/fixtures/parse_draft_ambiguous.json
gate0/contracts/fixtures/save_lines_ready.json
gate0/contracts/fixtures/save_lines_insufficient_stock_200.json
gate0/contracts/fixtures/save_lines_price_mismatch_422.json
gate0/contracts/fixtures/approval_detail.json
gate0/contracts/fixtures/approve_200.json
gate0/contracts/fixtures/approve_202.json
gate0/contracts/fixtures/approve_stock_changed_409.json
gate0/contracts/fixtures/delivery_order.json
```

重点回归：

- [ ] `parse_draft` 已确定行 `candidate_skus=[]`
- [ ] `parse_draft_ambiguous` 未解析行有候选
- [ ] `WorkingLine.available_qty` 与候选库存分开显示
- [ ] `save_lines_insufficient_stock_200` 的 Issue 有 `line_id`
- [ ] 该 fixture 的 `clarification_draft` 非空，COPY 可用
- [ ] `approval_detail` 的 `span_end` 切片不含逗号
- [ ] `language=ms` 的正文是马来语
- [ ] 409/422/503 按 error_code 分支
- [ ] 所有请求/响应带 `X-Request-ID`

---

## 7. 前端交付验收

- [ ] 16 个端点路径与 OpenAPI v4 一致
- [ ] 不使用旧 `{data: ...}` 包装
- [ ] 不修改 Gate 0 的字段名
- [ ] 未解析行显示 `candidate_skus`，已确定行不显示
- [ ] 当前行库存读 `available_qty`
- [ ] `AMBIGUOUS_QUANTITY` 有独立 UI
- [ ] `pack_size` 与 `qty` 分开显示
- [ ] 审批快照高亮与 masked text 切片一致
- [ ] 缺货行可定位、澄清可复制
- [ ] 200/202 正常分支都实现
- [ ] 所有错误按 `error_code` 处理

---

## 8. 交接问题

前端发现不一致时，提交：

```text
端点/字段：
Gate 0 文件：
fixture：
期望：
实际：
是否阻断：
```

不要直接改 `gate0/`；如果确实需要变更，进入 `gate0-v5` 流程。
