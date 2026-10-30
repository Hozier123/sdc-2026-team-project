# B02 最小商品目录接口

B02 只交付只读目录查询及其测试。本聊天不接管 B03/F03、AI 质量、正式 TEST32 或其他任务的验收。

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

前端可在独立的 `src/lib/catalog.ts` 中声明上述响应并做本地筛选；此次 B02 不改页面或调用流程。
不要修改 `gate0/`、`frontend/contracts/` 或冻结生成类型。已有保存接口仍负责客户等级价、库存和升级原因的校验；人工恢复留给 B03/F03。

## 验证

集成测试使用临时 PostgreSQL 数据库加载原始 T1/T2 种子，仅在测试库替换合成令牌哈希。

```powershell
cd backend
python -m pytest -q tests/test_catalog.py tests/test_health.py
```

数据库集成测试需 `TEST_DATABASE_ADMIN_URL` 指向专用测试实例。覆盖两个租户的两种允许角色、仓库拒绝、认证失败、租户伪造、有效商品过滤、空目录、100/101 项边界，以及读取前后所有 public 业务表逐行不变。

实现不新增迁移、依赖、配置或 AI 调用，不修改解析、保存、审批和出单实现。发布采用新版本记录，现有 Gate E 与其他历史验收仍绑定各自原版本。
