# PR #3 前端审核要点指引

> 审核对象：`docs/rules/02_KiraOrder_v1.3_后端与前端对接规则.md`  
> 适用 PR：<https://github.com/Hozier123/sdc-2026-team-project/pull/3>  
> 基线：`gate0-baseline-v1` / Gate 0 v4 / draft revision 5  
> 基线哈希：`6A44089C623C1B4AE8F444660DBD89422C663E7EBDD141EA6FDA549DDD833770`  
> Canonical：`gate0/`；本文只是审核指引，不是契约。

---

## 0. 审核前

先打开 PR #3，点：

```text
Update branch
```

PR #3 基于旧 main 创建；当前 main 已包含签字说明小 PR。更新后再看 diff。

审核目标只有一个：

> **这份前端文档会不会让前端写出与 Gate 0 不一致的实现？**

会 → 阻断。  
不会 → 确认或提非阻断建议。

---

## 1. 端点与响应

逐项对照 `gate0/contracts/openapi.yaml`：

- [ ] 16 个端点的方法、路径是否一致
- [ ] 每个端点的角色是否一致
- [ ] 成功模型是否一致：
  - parse/get draft/PUT lines → `OrderDraft`
  - list drafts → `DraftListResponse`
  - approve 200 → `DeliveryOrder`
  - approve 202 → `ApprovalRequest`
  - approvals → `ApprovalListResponse` / `ApprovalDetail`
  - decide → `DeliveryOrder` / `ApprovalDecisionResult`
- [ ] 是否错误地写成 `{data: ...}` 包装
- [ ] 是否声明所有响应带 `X-Request-ID`
- [ ] `approve` 的 200 和 202 是否都写成正常分支

### 阻断例子

```text
文档把 202 写成失败
文档把 approve 200 写成 ApprovalRequest
文档说成功响应包在 data 里
```

---

## 2. `DraftStatus` 必须精确

以 OpenAPI 为准，闭集只有：

```text
DISAMBIGUATION_REQUIRED
READY_FOR_APPROVAL
PENDING_OWNER_APPROVAL
DO_GENERATED
REJECTED
```

重点核对：

- [ ] 是否写了不存在的 `DRAFT_READY`
- [ ] 是否写了不存在的 `APPROVED`
- [ ] 是否写了不存在的 `CANCELLED`
- [ ] `DO_GENERATED` 是否用于“已生成 DO”
- [ ] `REJECTED` 是否用于终止只读页

### 阻断例子

```text
文档写 DRAFT_READY / APPROVED / CANCELLED
```

前端如果按这些值写状态机，会直接对不上后端。

---

## 3. 库存与候选

- [ ] `WorkingLine.available_qty` 是否定义为“当前已选 SKU 的库存”
- [ ] `candidate_skus[].available_qty` 是否定义为“候选 SKU 的库存”
- [ ] 是否明确两者不能混用
- [ ] 已确定行 `candidate_skus=[]` 是否写清楚
- [ ] 未解析行才显示候选控件是否写清楚
- [ ] 未选 SKU 时 `available_qty=null` 是否写清楚

### 阻断例子

```text
文档让前端用 candidate_skus[].available_qty 当当前行库存
文档说已确定行仍有候选
```

---

## 4. 状态、按钮与保存

- [ ] `blocking_issues[]` 是否作为批准按钮的真相
- [ ] `allowed_actions[]` 是否只渲染服务端允许的动作
- [ ] `version` 变化是否使旧编辑器失效
- [ ] `PUT lines` 缺货是否是 HTTP 200 + version+1 + `INSUFFICIENT_STOCK`
- [ ] `approve` 缺货是否是 HTTP 400
- [ ] `STALE_VERSION` 409 是否有恢复动作
- [ ] `ALREADY_APPROVED` 409 是否导航到已有 DO
- [ ] `PENDING_OWNER_APPROVAL` 是否只读

### 阻断例子

```text
文档把缺货保存写成 400
文档允许忽略 blocking_issues 直接批准
文档把 409 当普通错误弹窗
```

---

## 5. 澄清、审批快照与错误码

- [ ] `ClarificationDraft.language=ms` 时正文是否要求马来语
- [ ] `COPY_CLARIFICATION` 是否只在 clarification 非空时可用
- [ ] `ApprovalDetail.snapshot.lines[].span_end` 是否要求按 `masked_customer_text` 切片
- [ ] 审批快照是否只读
- [ ] 错误码是否覆盖 `errors.md` 的关键项：
  - `DISAMBIGUATION_UNRESOLVED`
  - `INSUFFICIENT_STOCK`
  - `TARGET_LINE_REQUIRED`
  - `STALE_VERSION`
  - `ALREADY_APPROVED`
  - `STOCK_CHANGED`
  - `REQUEST_VALIDATION_FAILED`
  - `AI_AND_FALLBACK_UNAVAILABLE`
- [ ] 是否只依赖 `error_code` + HTTP，不依赖 message 文案

### 阻断例子

```text
文档允许 ms 语言配英文正文
文档允许 COPY 按钮在没有澄清草稿时出现
文档按 message 文本分支
```

---

## 6. 联调 fixture

至少核对这些样例是否覆盖：

```text
parse_draft.json
parse_draft_ambiguous.json
save_lines_ready.json
save_lines_insufficient_stock_200.json
save_lines_price_mismatch_422.json
approval_detail.json
approve_200.json
approve_202.json
approve_stock_changed_409.json
delivery_order.json
```

- [ ] 已确定行候选为空
- [ ] 未解析行有候选
- [ ] 缺货 Issue 能定位行
- [ ] 澄清草稿可复制
- [ ] 审批快照 span 切片正确
- [ ] 200/202 都有样例

---

## 7. 审核结论

### 无阻断

在 PR 的 `Files changed` 对应文件下评论：

```text
02 前端对接已核对：
- 16 端点与 OpenAPI v4 一致
- DraftStatus / available_qty / candidate_skus 已确认
- 200/202、缺货 200、409/422 已确认
- 错误码和 fixtures 满足联调
无阻断异议。
```

或：

```text
Review changes → Approve
```

### 有阻断

```text
Request changes

阻断项：
文件/行：
Gate 0 依据：
期望：
实际：
影响：
```

### 只是建议

用普通 comment，并标注：

```text
非阻断建议：
```

不要把文案偏好标成阻断。

---

## 8. 前端通过标准

```text
[ ] 16 端点无偏差
[ ] DraftStatus 是 OpenAPI 闭集
[ ] available_qty / candidate_skus 语义正确
[ ] 已确定行候选为空
[ ] 200/202、缺货 200 正确
[ ] 关键错误码可分支
[ ] 澄清语言和审批快照无歧义
[ ] 无阻断评论
```
