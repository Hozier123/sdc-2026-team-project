# B02 最小商品目录接口

B02 交付只读目录接口、独立前端调用层和只读目录页，并完成其测试与正式发布。B03/F03 的商品选择、补行和保存流程不属于本任务。

## 接口

`GET /api/v1/catalog/products`

- 使用现有 Bearer 会话；身份与租户只取自服务端验证结果。
- CLERK、OWNER 返回 200；WAREHOUSE 返回 403 / FORBIDDEN_ACTION。
- 缺失、错误、未知或已停用的令牌返回 401 / INVALID_TOKEN。
- 无查询参数。客户端传入的 tenant_id、role、limit 或 q 不改变结果；没有服务端搜索或分页。
- 只读本租户 `products.active=true` 的商品，按 sku_id 升序稳定返回。
- 固定最多 100 项。当前冻结目录 T1 为 40 项、T2 为 16 项，均完整返回。
- 若将来超过 100 项，返回前 100 项并设置 `truncated=true`；调用方必须提示目录不完整，不能宣称可选择全部商品。扩大目录或分页另行实施。
- `pack_size` 和 `grade` 共同表达规格，允许 null；`base_unit` 为商品基本单位。
- 不返回价格、库存、客户或等级上下文。选中商品不代表已经核价或确认库存。
- 成功与错误响应沿用 `X-Request-ID` 和 `Cache-Control: no-store`。

```json
{
  "items": [
    {
      "sku_id": "SKU_MILO_1KG",
      "display_name": "Milo 美禄",
      "pack_size": "1kg",
      "grade": null,
      "base_unit": "bag"
    }
  ],
  "limit": 100,
  "truncated": false
}
```

上例只展示响应形状，不代表 T1 只有一项。

## 前端交接

前端的独立 `src/lib/catalog.ts` 声明上述响应；`Service.catalogProducts()` 与 `HttpService.catalogProducts()` 公开读取完整对象，不使用会丢弃元信息的通用 list()。

v1.5.1 的 `#/catalog` 页面显示只读目录及完整性状态；nullable 规格显示为破折号，`truncated=true` 有明确的不完整提示，空目录有独立状态。401/403 沿用可见错误及请求编号。仓库不显示目录菜单，直接访问该 URL 时由真实后端返回 403。目录页不会自动预热 AI，也没有选择 SKU、补行或保存按钮。Demo 目录明确标为本地样本。

`gate0/`、`frontend/contracts/` 和冻结生成类型保持不变。已有保存接口仍负责客户等级价、库存和升级原因的校验；人工恢复留给 B03/F03。

## 验证

集成测试使用临时 PostgreSQL 数据库加载原始 T1/T2 种子，仅在测试库替换合成令牌哈希。

```powershell
cd backend
python -m pytest -q tests/test_catalog.py tests/test_health.py
```

数据库集成测试需 `TEST_DATABASE_ADMIN_URL` 指向专用测试实例。覆盖两个租户的两种允许角色、仓库拒绝、认证失败、租户伪造、有效商品过滤、空目录、100/101 项边界，以及读取前后所有 public 业务表逐行不变。

实现不新增迁移、依赖、配置或 AI 调用，不修改解析、保存、审批和出单实现。发布采用新版本记录，现有 Gate E 与其他历史验收仍绑定各自原版本。
