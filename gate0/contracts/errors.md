# KiraOrder v1.3 HTTP、错误与成功响应契约

> 状态：`GATE0_DRAFT`。所有成功和失败响应必须返回 `X-Request-ID`；业务成功体直接返回模型，不使用 `{data: ...}` 包装。

## 1. 固定错误体

```json
{
  "error_code": "STALE_VERSION",
  "message": "Draft version is stale.",
  "details": {
    "expected_version": 2,
    "current_version": 3
  }
}
```

- `error_code`：稳定机器码；前端分支只依赖此字段和 HTTP。
- `message`：安全、可显示的默认文案；不得泄露跨租户资源存在性、SQL、token 或未脱敏原文。
- `details`：对象，允许为空；只放结构化恢复信息。
- 请求 JSON 无法通过 schema 时使用 422 `REQUEST_VALIDATION_FAILED`，`details.fields[]` 可含 `path/reason`。
- 未知服务端错误不映射成下表的业务错误；按统一 500 处理并仍返回 `X-Request-ID`。

## 2. 错误目录

| HTTP | `error_code` | 精确触发 | 前端行为 | 契约 fixture |
|---:|---|---|---|---|
| 400 | `DISAMBIGUATION_UNRESOLVED` | approve 时仍有未解决阻断疑点 | 留在草稿，聚焦疑点卡 | `error_catalog.json#DISAMBIGUATION_UNRESOLVED` |
| 400 | `INSUFFICIENT_STOCK` | **approve** 时仍有缺货阻断；PUT lines 保存成功并返回 200 + `INSUFFICIENT_STOCK` Issue，版本照常 +1，不写半成品 | 批准被阻断；去减量/删除该行；保存成功不是错误 | `save_lines_insufficient_stock_200.json` + `error_catalog.json#INSUFFICIENT_STOCK` |
| 400 | `TARGET_LINE_REQUIRED` | PRICE 条件未确认目标行 | 打开目标行选择 | `save_lines_target_required.json` |
| 400 | `OVERRIDE_REQUIRED` | 目标行未写有效单位价或改价原因 | 聚焦目标行价格和理由 | `error_catalog.json#OVERRIDE_REQUIRED` |
| 400 | `NOTE_REQUIRED` | `NOT_A_CONDITION` 等动作缺必须备注 | 聚焦备注框 | `error_catalog.json#NOTE_REQUIRED` |
| 400 | `EMPTY_ORDER` | 显式删除后无剩余行 | 阻止保存并要求保留/新增一行 | `save_lines_empty_order_400.json` |
| 400 | `INVALID_LINE_OPERATION` | 旧行未覆盖、重复、同时保留/删除或删除未知 ID | 刷新草稿并重建编辑集 | `error_catalog.json#INVALID_LINE_OPERATION` |
| 401 | `INVALID_TOKEN` | Bearer 缺失、无效或过期 | 进入重新认证，不重试写操作 | `error_catalog.json#INVALID_TOKEN` |
| 403 | `FORBIDDEN_ACTION` | 当前角色不能执行动作 | 隐藏/禁用动作并提示权限 | `error_catalog.json#FORBIDDEN_ACTION` |
| 403 | `TENANT_MISMATCH` | 兼容请求体租户与会话租户不一致 | 丢弃本地请求，报告安全错误 | `error_catalog.json#TENANT_MISMATCH` |
| 404 | `RESOURCE_NOT_FOUND` | 当前租户不存在或不可见；跨租户也返回同码 | 返回列表/上一页，不区分不存在与越权 | `error_catalog.json#RESOURCE_NOT_FOUND` |
| 409 | `STALE_VERSION` | `expected_version != current_version` | 获取最新草稿，提示用户重新应用修改 | `error_catalog.json#STALE_VERSION` |
| 409 | `PENDING_OWNER_APPROVAL` | 待批期间编辑、重复提交或作废 | 切到只读审批状态 | `error_catalog.json#PENDING_OWNER_APPROVAL` |
| 409 | `ALREADY_APPROVED` | 草稿已生成 DO | 按幂等成功打开 `details.do_number` | `already_approved_409.json` |
| 409 | `DRAFT_REJECTED` | 对已终止草稿继续写/批 | 切到终止只读页 | `error_catalog.json#DRAFT_REJECTED` |
| 409 | `STOCK_CHANGED` | 锁内库存与提交前不同且不再满足 | 保持审批 PENDING，刷新库存后让 OWNER 重试 | `approve_stock_changed_409.json` |
| 422 | `REQUEST_VALIDATION_FAILED` | JSON 类型、闭集、格式或只读字段非法；含 `confirmed_unit_price` 与目标行 `unit_price_override` 不一致 | 按 `details.fields` 标记输入 | `error_catalog.json#REQUEST_VALIDATION_FAILED` |
| 422 | `MESSAGE_TOO_LONG` | 请求 `message_text` 超过 4000 Unicode code points | 显示长度限制，不记录原文、不发起 AI | `error_catalog.json#MESSAGE_TOO_LONG` |
| 422 | `REJECTION_REASON_REQUIRED` | OWNER REJECT 未给非空 note | 聚焦拒绝原因 | `error_catalog.json#REJECTION_REASON_REQUIRED` |
| 422 | `INVALID_QUANTITY` | 客户端提交 0、负数、非整数或超限数量 | 聚焦数量字段 | `error_catalog.json#INVALID_QUANTITY` |
| 422 | `MISSING_TIER_PRICE` | 当前客户 tier 与 SKU 无配置价格 | 阻断流程并提示管理员修配置，不显示为可解决 Issue | `error_catalog.json#MISSING_TIER_PRICE` |
| 429 | `RATE_LIMITED` | parse 或 AI wake 超配额 | 按 `Retry-After` 延迟；读取 `details.scope` | `error_catalog.json#RATE_LIMITED` |
| 503 | `AI_AND_FALLBACK_UNAVAILABLE` | AI 与本地 fallback 均不可用，不能形成安全草稿 | 保留输入，允许稍后重试 | `error_catalog.json#AI_AND_FALLBACK_UNAVAILABLE` |

## 3. 关键 `details` 形状

| 错误 | 必需 details |
|---|---|
| `STALE_VERSION` | `expected_version:int,current_version:int` |
| `ALREADY_APPROVED` | `do_number:string,approved_at:date-time` |
| `STOCK_CHANGED` | `lines:[{line_id,sku_id,requested_qty,effective_qty,available_qty}]` |
| `REQUEST_VALIDATION_FAILED` | `fields:[{path,reason}]`；价格冲突示例：`path=resolutions[0].confirmed_unit_price,reason=must equal target line unit_price_override` |
| `RATE_LIMITED` | `scope:PARSE|AI_WAKE,retry_after_seconds:int`；同时返回 `Retry-After` |
| `TARGET_LINE_REQUIRED` | `issue_id,candidate_line_ids[]` |
| `INVALID_LINE_OPERATION` | `missing_line_ids[],duplicate_line_ids[],unknown_deleted_line_ids[]` |
| `REQUEST_VALIDATION_FAILED` | `fields:[{path,reason}]` |
| `MISSING_TIER_PRICE` | `customer_id,sku_id,tier`；不得包含内部 SQL |

## 4. 旧码映射

| 旧码 | 新码 | HTTP/规则 |
|---|---|---|
| `DRAFT_VERSION_CONFLICT` | `STALE_VERSION` | 409 |
| `UNAUTHORIZED` | `INVALID_TOKEN` | 401 |
| `FORBIDDEN` | `FORBIDDEN_ACTION` | 403 |
| `NOT_FOUND` | `RESOURCE_NOT_FOUND` | 404 |
| `AI_WAKE_RATE_LIMITED` | `RATE_LIMITED` | 429，`details.scope=AI_WAKE` |

旧码只用于迁移说明，不得由 v1.3 API 新产生。

## 5. 成功响应

| 端点组 | HTTP | 直接模型 |
|---|---:|---|
| parse / get draft / PUT lines | 200 | `OrderDraft` |
| list drafts | 200 | `DraftListResponse` |
| approve 无升级 | 200 | `DeliveryOrder`（含 `reply_draft`） |
| approve 有升级 | 202 | `ApprovalRequest` |
| approval list/detail | 200 | `ApprovalListResponse` / `ApprovalDetail` |
| decide APPROVE | 200 | `DeliveryOrder` |
| decide REJECT | 200 | `ApprovalDecisionResult(status=REJECTED)` |
| audit/activity/me | 200 | 各自直接模型 |
| AI status/wake | 200 | `AiStatus` / `AiWakeResult` |

`approve` 的 200 与 202 是两个正常成功分支。客户端不得把 202 当失败，也不得从响应结构猜测 HTTP。

## 6. 请求 ID 与缓存

- 入站已有合法 `X-Request-ID` 时可沿用，否则服务端生成；响应始终返回最终值。
- 错误正文不再重复 request ID；日志以该值关联，但不记录原始 PII。
- 鉴权、审批、草稿与审计响应建议 `Cache-Control: no-store`。
- `ALREADY_APPROVED` 是可恢复的 409：前端必须导航到已有 DO，不能重复创建。
