# B03 人工恢复与 F03 接入契约

B03 复用现有保存与批准接口，负责已有行改选 SKU、零有效行补录、删除后补正，以及保存后的业务校验。页面入口、目录选择器、未保存离开保护及浏览器交互由 F03 接入；本文件不将后端测试登记为 F03 页面验收。

## 调用顺序

1. 用现有角色会话读取草稿及 `GET /api/v1/catalog/products`。只有 CLERK / OWNER 可以编辑；以草稿 `allowed_actions` 决定页面是否开放编辑，服务端同时独立校验角色、租户、状态及版本。
2. 已有行改选时保留服务端 `line_id`，提交目录的 `sku_id`、`base_unit`、规格及已确认整数数量，使用 `match_source=MANUAL_SELECTED`。原文、offset、field_evidence 由服务端保留，不能由客户端改写。
3. 新行使用唯一、非空白 `client_line_ref`，不填 `line_id`，必须选择 SKU、确认正整数数量，并使用 `MANUAL_SELECTED`。不能把补录标为 LLM 或 FALLBACK 识别。
4. 使用 `PUT /api/v1/orders/drafts/{draft_id}/lines` 一次提交全部保留行及新增行；删除的旧行 ID 放入 `deleted_line_ids`。每条当前旧行必须恰好保留或删除，不能静默漏行。空订单不能保存。
5. 保存返回成功后，用**完整保存响应**更新页面和版本号，再显示金额、库存、阻断项与审批原因；选中目录商品本身不表示已核价或有库存。保存不批准、不扣库存、不生成 DO。
6. 没有未保存输入且保存结果允许批准时，发送 `POST /api/v1/orders/{draft_id}/approve`，仅带最新 `expected_version`。批准会再次核价格及库存；202 表示等待老板，200 才表示生成 DO。

新增行示例（SKU / unit 必须来自本租户实际目录，下列为测试值）：

```json
{
  "expected_version": 1,
  "lines": [{
    "client_line_ref": "manual-1",
    "sku_id": "SKU_MILO_1KG",
    "confirmed_qty": 2,
    "uom": "ctn",
    "match_source": "MANUAL_SELECTED"
  }],
  "deleted_line_ids": [],
  "resolutions": []
}
```

`line_id` 与 `client_line_ref` 二选一。新增行成功后，响应同时含 `client_line_ref` 和新分配的 `line_id`，前端用前者对齐本地输入，下一次保存改用后者。数量不能传字符串、小数、布尔值、零或负数。没有选择 SKU 的旧行可以继续保持待澄清；新增人工行必须选 SKU。

**已有行保存也应显式提交 `sku_id`**：未改商品时回传当前 SKU，改选时传新 SKU，仍未选择时传 `null`。该批量保存接口当前不具有“省略 sku_id 就保持原值”的 PATCH 语义；省略会被解析为 `null`，对原来已选的行可能触发改选来源检查而返回 422，或者在 `MANUAL_SELECTED` 时清空选择并产生待澄清项。前端和 B04 driver 已显式带该字段；其他调用方应遵守同一约定。此处澄清当前 `99ee169` 的行为，不变更已复核的应用实现。

目录字段不含 family / 价格 / 库存；`family_id` 可以省略，由后端根据 SKU 确定。切换 SKU 时应清空旧规格、单位、价格 override、override_reason、alias 勾选和本地价格 resolution，重新取所选商品的单位/规格；不把旧商品的价格决策自动带到新商品。即使有意保留 override，也须显式重新确认关联的价格条件。

## 价格条件与删行补正

`unit_price_override` 和 `override_reason` 是允许的输入，前者为正数十进制字符串，后者必填。禁止提交派生的等级价、最终价、行金额、库存或审批结果。后端按草稿的 customer_id 查询客户当前 tier，不接受客户端自报 tier。

价格条件不因删除原行而消失。删除目标行、切换目标 SKU 或更改接受价后，旧接受记录失效，必须重新明确确认当前目标。原始条件文字及历史版本保留；当前条件不再保留失效的接受价/备注或已删除的行引用。

新行 ID 由服务端分配，因此涉及新增行的价格绑定按两次保存执行：

1. 先保存补正行，保留未解决的价格条件；读取响应新 `line_id` 和 `version`。这一步仍可为 `DISAMBIGUATION_REQUIRED`。
2. 用新版本和返回的行 ID 重新保存全部当前行，并提交该条件的 `issue_id`、`choice=ACCEPT_REQUESTED_PRICE`、`target_line_ids`、`confirmed_unit_price`、`price_basis=UNIT` 和明确备注。

`target_line_ids` 只接受实际服务端行 ID，不能传 `client_line_ref` 或猜测 ID。接受低于 tier 的价格仍进入老板审批，不因人工恢复绕过审批。

## 恢复与错误处理

- 409 / `STALE_VERSION`：保留本地输入，读取最新草稿，用户确认差异后再保存；不要盲目自动重试。版本冲突不会写入任何业务行。
- 超时或网络中断：结果可能已写入，先 GET 草稿核版本、行及 client_line_ref；不能无条件再次新增。client_line_ref 是响应对齐字段，不是跨版本幂等键。
- 409 / `PENDING_OWNER_APPROVAL`、`ALREADY_APPROVED`、`DRAFT_REJECTED`：停止编辑并显示当前状态；不能在待批或终态补录。
- 422：显示具体字段或条件错误及 request_id，保留输入；不要将保存失败的本地金额显示为已核金额。
- 库存不足可以以 blocking issue 返回 200；必须检查 `blocking_issues` / `allowed_actions`。相同 SKU 多行合并核库存，不能用拆行绕过。
- 401 / 403 / 404：分别处理会话失效、角色禁止、资源不在当前租户或不存在；不要更改 token 中的租户归属。

## 验证

在专用测试 PostgreSQL 实例配置 `TEST_DATABASE_ADMIN_URL` 后，从 backend 执行：

```powershell
python -m pytest -q tests/test_b03_manual_recovery.py tests/test_b03_canonical_recovery.py
```

测试每例创建独立数据库并最终删除该测试数据库，覆盖无候选改选、零行补录、来源证据、非法人工行、删行补正与价格重绑定、客户等级价变化、低价老板审批、重复 SKU 总库存、批准时库存变化、错误版本、角色/租户及终态。另以原始 T1/T2 种子覆盖两租户 CLERK/OWNER 的“目录→零行补录→保存→批准→DO→仓库”及跨租户拒绝。拒绝路径比较所有 public 业务表的完整行，成功路径核实际 DO 和库存。使用合成 provider，不调用 GPU，不连接或复位正式演示库，不替代正式 TEST32 或独立业务签收。

## 独立复核与保留项

Zhou 已通过用户转交的回复确认 B03 后端复核通过，核对 PR #104 的 head / merge、Git 与 Windows CRLF 两种源码哈希及 CI，并确认人工恢复、价格重绑定、低价老板审批成立。其未独立重跑 151 项本地 PG 测试、未独立验证 Replit 部署；F03 页面和正式 TEST32 不在该复核范围。回执与结项状态见 [B03 记录](../../evidence/b03/2026-10-31/README.md)。

保留一项非阻塞 P3：失效条件的 `price_basis=UNIT`、`SEPARATE_ADD_ON` 的 `data_used.related_do_number` 仍可能残留。Zhou 已说明无审批绕过；本轮记录为后续元数据清理建议，不修改运行逻辑或扩大本次复核结论。
