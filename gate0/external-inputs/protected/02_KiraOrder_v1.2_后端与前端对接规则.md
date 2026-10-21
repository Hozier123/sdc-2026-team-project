# KiraOrder v1.2 后端与前端对接规则

> 契约状态：`FROZEN_v1.2`  
> 后端负责人：He Minghao  
> 前端负责人：Ye Lianghui  
> 前置真相源：`01_KiraOrder_v1.2_后端完整规则框架.md`

## 0. 目的

本文规定前端可以依赖的后端对象、状态、动作、接口、错误码和角色视图。前端负责展示与采集人工操作，后端负责所有业务判断。

核心边界：

> 前端不得计算金额、库存或审批路由，不得自行修改状态，不得依靠隐藏按钮代替后端权限。

---

## 1. 前端可做与不可做

### 1.1 前端负责

- 展示掩码后的原始消息；
- 高亮订单行、条件和疑点的原文片段；
- 展示商品候选、等级价、库存和后端解释；
- 收集SKU选择、数量修正、成交价人工确认和备注；
- 展示后端返回的状态、金额、升级原因和`allowed_actions`；
- 处理版本冲突和业务错误；
- 复制澄清/回复草稿；
- 显示AI来源与运行状态；
- 按角色显示导航和后端已裁剪的数据。

### 1.2 前端禁止

- 使用JavaScript乘法计算行金额或总额；
- 根据总额、客户或价格自行判断是否找老板；
- 根据页面缓存判断库存足够；
- 向后端提交`status`、`requires_owner`或最终总额；
- 在批准请求中同时提交修改后的明细；
- 收到409后自动重试批准；
- 将FALLBACK或ALIAS_ONLY显示成AI；
- 把“复制模板”显示成“消息已发送”；
- 依靠CSS隐藏仓库无权看到的数据。

---

## 2. 统一前端类型

前端应从OpenAPI生成TypeScript类型，或至少与以下枚举保持完全一致。

### 2.1 角色

```ts
type Role = "CLERK" | "OWNER" | "WAREHOUSE";
```

### 2.2 草稿状态

```ts
type DraftStatus =
  | "DRAFT"
  | "NEEDS_REVIEW"
  | "READY_FOR_APPROVAL"
  | "PENDING_OWNER_APPROVAL"
  | "APPROVED"
  | "REJECTED"
  | "CANCELLED"; // P1
```

### 2.3 疑点状态和路由

```ts
type IssueStatus = "OPEN" | "RESOLVED" | "VOIDED";
type AskTarget = "CUSTOMER" | "OWNER" | "CLERK" | "SYSTEM";

type IssueCode =
  | "UNKNOWN_PRODUCT"
  | "MISSING_SPEC"
  | "MISSING_GRADE"
  | "MISSING_UNIT"
  | "INVALID_QUANTITY"
  | "AMBIGUOUS_MATCH"
  | "INSUFFICIENT_STOCK"
  | "PRICE_CONDITION_UNRESOLVED"
  | "OTHER_CONDITION_UNCONFIRMED"
  | "SOURCE_EVIDENCE_INVALID"
  | "SAME_DAY_ORDER_CHECK"; // P1

type IssueResolutionAction =
  | "SELECT_PRODUCT_FAMILY"
  | "SELECT_SKU"
  | "SET_QUANTITY"
  | "REDUCE_TO_AVAILABLE_STOCK"
  | "ASK_CUSTOMER_AT_TIER_PRICE"
  | "ACCEPT_REQUESTED_PRICE"
  | "CONFIRM_OTHER_CONDITION"
  | "USE_FALLBACK_RESULT"
  | "MARK_UNRESOLVED";
```

### 2.4 条件

```ts
type ConditionType =
  | "STOCK_IF_AVAILABLE"
  | "PRICE_REQUEST"
  | "OTHER_CONDITION";

type ConditionStatus =
  | "DETECTED"
  | "SATISFIED"
  | "NOT_SATISFIED"
  | "RESOLVED_BY_CLERK";
```

### 2.5 抽取来源与AI状态

```ts
type ExtractionSource = "AI" | "FALLBACK" | "ALIAS_ONLY";
type AiStatus = "OFFLINE" | "WARMING" | "READY" | "DEGRADED";

type OwnerEscalationCode =
  | "BELOW_TIER_PRICE"
  | "ORDER_TOTAL_THRESHOLD"
  | "CREDIT_TERM_NOTICE";
```

### 2.6 允许动作

```ts
type AllowedAction =
  | "EDIT_DRAFT"
  | "RESOLVE_ISSUE"
  | "COPY_CLARIFICATION"
  | "APPROVE_AND_GENERATE_DO"
  | "SUBMIT_FOR_OWNER"
  | "OWNER_APPROVE"
  | "OWNER_REJECT"
  | "CANCEL_DRAFT"
  | "VIEW_ACTIVITY"
  | "WAKE_AI";
```

前端不能发明`WAITING_BOSS`、`CAN_APPROVE`等平行枚举。

---

## 3. 通用API格式

### 3.1 成功响应

```json
{
  "data": {},
  "meta": {
    "request_id": "REQ_001"
  }
}
```

列表：

```json
{
  "data": [],
  "meta": {
    "count": 8,
    "request_id": "REQ_002"
  }
}
```

### 3.2 错误响应

```json
{
  "error": {
    "code": "DRAFT_VERSION_CONFLICT",
    "message": "Draft has changed. Reload the latest version.",
    "details": {
      "submitted_version": 3,
      "current_version": 4
    },
    "request_id": "REQ_003"
  }
}
```

前端逻辑只依据`error.code`，不要解析英文`message`决定行为。

### 3.3 金额和时间

- 所有金额均为字符串，如`"95.00"`；
- 前端只格式化成`RM 95.00`；
- 所有API时间为UTC ISO 8601；
- 展示时转换为UTC+8；
- 不在客户端修改审计时间。

---

## 4. `/me`与导航

### 4.1 请求

```http
GET /api/v1/me
Authorization: Bearer <demo-token>
```

### 4.2 响应

```json
{
  "data": {
    "user_id": "USR_SITI",
    "display_name": "Siti",
    "tenant": {
      "id": "T1",
      "name": "Sinaran Food Supply"
    },
    "role": "CLERK",
    "permissions": [
      "EDIT_DRAFT",
      "RESOLVE_ISSUE",
      "APPROVE_AND_GENERATE_DO",
      "SUBMIT_FOR_OWNER",
      "WAKE_AI"
    ],
    "permission_summary": "Can review drafts and approve standard orders."
  },
  "meta": {"request_id": "REQ_001"}
}
```

### 4.3 导航规则

| 角色 | P0入口 |
|---|---|
| CLERK | Workbench、自己提交的审批状态、Activity |
| OWNER | Approvals、Activity、只读草稿详情 |
| WAREHOUSE | 已批准DO裁剪视图；独立页面P1 |

OWNER在P0不能创建或编辑草稿。

---

## 5. 草稿列表契约

### 5.1 请求

```http
GET /api/v1/drafts?status=NEEDS_REVIEW&limit=50
```

规则：

- 默认`limit=50`；
- 最大`limit=100`；
- 默认`updated_at desc`；
- P0无复杂游标分页；
- 返回`count`。

### 5.2 列表项

```json
{
  "id": "DRF_001",
  "draft_version": 3,
  "customer_name": "Restoran Ali",
  "message_preview": "Boss, Milo 5 pack...",
  "status": "NEEDS_REVIEW",
  "open_blocking_issue_count": 1,
  "owner_escalation_count": 0,
  "extraction_sources": ["AI"],
  "updated_at": "2026-10-21T06:30:00Z",
  "allowed_actions": ["EDIT_DRAFT", "RESOLVE_ISSUE"]
}
```

### 5.3 分组建议

工作台可按以下顺序分组：

1. `NEEDS_REVIEW`
2. `READY_FOR_APPROVAL`
3. `PENDING_OWNER_APPROVAL`
4. `APPROVED`
5. `REJECTED`

分组只是展示方式，不改变状态。

---

## 6. 创建/解析草稿

### 6.1 请求

```http
POST /api/v1/drafts/parse
```

```json
{
  "customer_id": "CUS_ALI",
  "message_text": "Boss, Milo 5 pack kalau ada"
}
```

前端不得提交`tenant_id`、角色或AI来源。后端将：

1. 验证消息不超过4000 Unicode字符；
2. PII掩码；
3. 只存掩码文本；
4. 执行Alias/AI/Fallback管线；
5. 运行条件、疑点、价格和库存规则；
6. 返回角色裁剪后的草稿详情。

AI不可用时本接口不得仅因此失败；应返回FALLBACK草稿。

---

## 7. 草稿详情契约

### 7.1 CLERK响应示例

```json
{
  "data": {
    "id": "DRF_001",
    "draft_version": 3,
    "status": "NEEDS_REVIEW",
    "customer": {
      "id": "CUS_ALI",
      "name": "Restoran Ali",
      "tier": "A",
      "credit_term_notice": false
    },
    "masked_message": "Boss, Milo 5 pack kalau ada",
    "lines": [
      {
        "line_id": "LIN_001",
        "source_span": "Milo 5 pack",
        "span_start": 6,
        "span_end": 17,
        "extraction_source": "AI",
        "family_id": "FAM_MILO",
        "sku_id": null,
        "quantity": 5,
        "raw_quantity": "5",
        "raw_unit": "pack",
        "spec_text": null,
        "grade_text": null,
        "tier_unit_price": null,
        "applied_unit_price": null,
        "line_total": null
      }
    ],
    "issues": [],
    "conditions": [],
    "owner_escalations": [],
    "totals": {
      "order_total": null,
      "currency": "MYR"
    },
    "allowed_actions": ["RESOLVE_ISSUE", "COPY_CLARIFICATION"],
    "blocked_actions": {
      "APPROVE_AND_GENERATE_DO": ["MISSING_SPEC"]
    },
    "clarification_drafts": [],
    "created_at": "2026-10-21T06:20:00Z",
    "updated_at": "2026-10-21T06:30:00Z"
  },
  "meta": {"request_id": "REQ_004"}
}
```

### 7.2 未识别商品行

```json
{
  "source_span": "生抽王 2 箱",
  "family_id": null,
  "sku_id": null,
  "quantity": 2,
  "raw_unit": "箱",
  "extraction_source": "AI"
}
```

前端必须渲染此行并显示`UNKNOWN_PRODUCT`疑点，不能因为`family_id=null`而隐藏。

### 7.3 原文高亮

- `span_start/span_end`是相对于`masked_message`的Unicode字符索引；
- 区间采用半开区间`[span_start, span_end)`；
- JavaScript原生字符串下标按UTF-16码元计数，不能直接假定等于Unicode码点；高亮时应先用`Array.from(masked_message)`按码点切片，或使用统一转换函数；
- 使用这两个值高亮；
- 若索引无效，不自行修正，显示span文本并记录前端诊断；
- 同一商品在两个不同位置出现时保留两条行。

---

## 8. 疑点卡片契约

```json
{
  "issue_id": "ISS_001",
  "code": "MISSING_SPEC",
  "status": "OPEN",
  "blocking": true,
  "ask_target": "CUSTOMER",
  "source_span": "5 pack Milo",
  "reason": "Milo has multiple pack sizes.",
  "used_data": {
    "candidate_sku_ids": ["SKU_MILO_1KG", "SKU_MILO_2KG"]
  },
  "candidates": [
    {
      "sku_id": "SKU_MILO_1KG",
      "label": "Milo 1kg",
      "tier_unit_price": "32.00",
      "available_stock": 18,
      "unit": "pack"
    }
  ],
  "allowed_resolutions": ["SELECT_SKU", "COPY_CLARIFICATION"]
}
```

P0所有疑点均阻断批准。前端应明确展示：

- 为什么停下来；
- 应该问谁；
- 用了什么数据；
- 可以采取哪些动作。

---

## 9. 解决疑点

### 9.1 选择SKU

```http
POST /api/v1/drafts/DRF_001/issues/ISS_001/resolve
```

```json
{
  "draft_version": 3,
  "resolution": {
    "action": "SELECT_SKU",
    "sku_id": "SKU_MILO_1KG",
    "remember_for_customer": true
  }
}
```

成功后后端创建版本4，并返回完整新草稿。前端不要在本地手动模拟状态变化。

### 9.2 接受客户价格

```json
{
  "draft_version": 4,
  "resolution": {
    "action": "ACCEPT_REQUESTED_PRICE",
    "line_id": "LIN_001",
    "applied_unit_price": "95.00"
  }
}
```

这是人工明确输入的成交价，不是AI价格。后端返回重算结果和老板升级原因。

P0成交价必须是两位小数字符串且严格大于`0.00`；前端可先做输入提示，但以后端校验为准。

### 9.3 数量修正

```json
{
  "draft_version": 4,
  "resolution": {
    "action": "SET_QUANTITY",
    "line_id": "LIN_001",
    "quantity": 5
  }
}
```

前端输入必须为正整数；后端仍做最终验证。小数不得自动四舍五入。

---

## 10. 条件展示

| 类型 | 前端表现 | 动作 |
|---|---|---|
| `STOCK_IF_AVAILABLE`满足 | 显示系统使用的库存事实 | 无需老板 |
| `STOCK_IF_AVAILABLE`不满足 | 显示缺货疑点和澄清模板 | 减量/询问客户 |
| `PRICE_REQUEST` | 显示原文条件 | 按等级价询问或接受客户价 |
| `OTHER_CONDITION` | 显示原文和备注输入 | 人工确认 |

价格条件中的RM数字不能预填成成交价后自动保存；必须让跟单员执行明确动作。

---

## 11. 按钮规则

前端只根据`allowed_actions`显示可操作按钮。

| 动作 | 推荐文案 |
|---|---|
| `APPROVE_AND_GENERATE_DO` | Approve & Generate DO |
| `SUBMIT_FOR_OWNER` | Send to Owner |
| `OWNER_APPROVE` | Approve Order |
| `OWNER_REJECT` | Reject Order |
| `COPY_CLARIFICATION` | Copy Question |
| `WAKE_AI` | Wake AI |

如果后端只返回`RESOLVE_ISSUE`，前端不能因自己认为金额很低而显示批准按钮。

`APPROVE_AND_GENERATE_DO`与`SUBMIT_FOR_OWNER`都调用`POST /api/v1/drafts/{id}/approve`并只提交`draft_version`。两种动作名称用于准确表达后端已经计算出的路由，不代表前端可以指定`requires_owner`。

---

## 12. 普通批准

```http
POST /api/v1/drafts/DRF_001/approve
```

```json
{
  "draft_version": 5
}
```

请求中不得携带：

```text
lines
prices
totals
requires_owner
status
```

可能结果：

- `200`：没有升级原因，返回`APPROVED`草稿与DO；
- `202`：存在升级原因，后端创建`ApprovalRequest`并返回`PENDING_OWNER_APPROVAL`草稿；前端打开/提示老板待办状态；
- 422 `BLOCKING_ISSUES_REMAIN`：定位疑点；
- 409 `DRAFT_VERSION_CONFLICT`：重新加载；
- 409 `INSUFFICIENT_STOCK`：重新加载库存和疑点；
- 409 `ALREADY_APPROVED`：转到已有DO。

前端不得先调用一次“普通批准”来试探是否需要老板，也不得把`202`当错误。按钮已经由`allowed_actions`告诉用户本次是直接批准还是送老板，但最终仍以后端事务内重算为准。

---

## 13. 老板审批

### 13.1 待办响应必须展示

- 客户；
- 固定`draft_version`；
- 所有订单行；
- 等级价、成交价和总额；
- 全部升级原因及具体数字；
- 客户原文片段；
- AI/人工字段差异；
- 提交人和时间；
- 允许动作。

### 13.2 批准

```http
POST /api/v1/approvals/APR_001/approve
```

```json
{
  "draft_version": 5
}
```

### 13.3 驳回

```http
POST /api/v1/approvals/APR_001/reject
```

```json
{
  "draft_version": 5,
  "reason": "Requested price is below the acceptable margin."
}
```

理由必须非空。`REJECTED`是终态。前端不得提供“修改后再次批准原草稿”的按钮。

### 13.4 等待老板期间

CLERK可以查看自己提交的审批状态，但不能编辑、批准或驳回。

---

## 14. DO详情与仓库视图

### 14.1 CLERK/OWNER DO

可包含价格、金额、审批和审计信息。

### 14.2 WAREHOUSE DO

只包含：

```json
{
  "do_number": "DO-20261021-001",
  "customer_name": "Restoran Ali",
  "items": [
    {
      "sku_id": "SKU_MILO_1KG",
      "display_name": "Milo 1kg",
      "quantity": 5,
      "unit": "pack",
      "picking_note": null
    }
  ],
  "approved_at": "2026-10-21T07:00:00Z"
}
```

响应中不能出现价格、总额、客户电话、Tier、账期提醒、原消息或AI差异。前端不需要再隐藏这些字段。

---

## 15. AI状态与Wake AI

### 15.1 页面打开

工作台打开后：

1. 请求`GET /api/v1/ai/status`；
2. 后端可异步触发一次预热；
3. 不阻塞页面和离线闭环。

### 15.2 状态显示

| 状态 | 显示 |
|---|---|
| `READY` | AI ready |
| `WARMING` | AI warming up |
| `OFFLINE` | Offline match · non-AI |
| `DEGRADED` | AI degraded · using fallback |

### 15.3 Wake AI

按钮调用`POST /api/v1/ai/wake`。点击后：

- 显示正在预热；
- 不连续重复调用；
- 429时显示稍后再试；
- 不将RunPod密钥暴露给浏览器。

---

## 16. 错误处理表

| 错误码 | 前端行为 |
|---|---|
| `INVALID_TOKEN` | 返回角色入口/提示令牌失效 |
| `FORBIDDEN_ACTION` | 禁止操作，显示权限摘要 |
| `RESOURCE_NOT_FOUND` | 显示不存在，不猜是否跨租户 |
| `DRAFT_VERSION_CONFLICT` | 停止操作，重新加载，不自动重试 |
| `ALREADY_APPROVED` | 打开已有DO |
| `INVALID_STATE_TRANSITION` | 重新加载最新状态 |
| `INSUFFICIENT_STOCK` | 刷新草稿和库存解释 |
| `BLOCKING_ISSUES_REMAIN` | 滚动到开放疑点 |
| `REJECTION_REASON_REQUIRED` | 聚焦理由输入框 |
| `MISSING_TIER_PRICE` | 显示配置错误，不允许手填猜价 |
| `INVALID_QUANTITY` | 显示只支持正整数 |
| `MESSAGE_TOO_LONG` | 显示4000字符限制 |
| `AI_WAKE_RATE_LIMITED` | 禁用按钮并稍后恢复 |
| `AI_AND_FALLBACK_UNAVAILABLE` | 显示需人工录入/稍后重试 |

---

## 17. 澄清和回复模板

- 后端返回最终模板文本；
- 前端只复制；
- 复制成功只提示“Copied”，不能写“Sent”；
- P0回复草稿不包含价格；
- 模板语言由后端根据消息语言和客户偏好决定；
- 前端不得调用模型自行生成客户文案。

---

## 18. 前端联调验收

- [ ] OpenAPI生成的类型与前端枚举一致。
- [ ] 前端不计算任何金额。
- [ ] 按钮完全来自`allowed_actions`。
- [ ] 未识别商品行能够正常显示。
- [ ] P0所有疑点都阻断批准。
- [ ] 解决疑点后使用后端返回的新版本。
- [ ] 409冲突会重新加载且不自动批准。
- [ ] AI关闭时仍可完成订单闭环。
- [ ] FALLBACK明确标注non-AI。
- [ ] Copy Question不显示已发送。
- [ ] CLERK只能查看已提交审批状态，不能操作老板动作。
- [ ] OWNER不能编辑草稿。
- [ ] WAREHOUSE响应中不存在价格和电话。
- [ ] APPROVED页面一定能打开DO。
- [ ] REJECTED页面没有继续编辑入口。

