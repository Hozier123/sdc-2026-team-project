# PR #3 数据审核要点指引

> 审核对象：`docs/rules/04_KiraOrder_v1.3_后端与数据对接规则.md`  
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

审核目标：

> **这份数据文档会不会让数据/后端建出与 Gate 0 不一致的库或 seed？**

会 → 阻断。  
不会 → 确认或提非阻断建议。

---

## 1. 18 张 public 表

逐项对照 `gate0/contracts/db-schema.md`：

```text
tenants
users
customers
product_families
family_aliases
products
uom_aliases
customer_tier_prices
inventory
alias_cache
inbound_messages
orders
draft_versions
approval_requests
delivery_orders
activity_log
audit_logs
field_diffs
```

- [ ] 是否明确 18 张
- [ ] 表名是否与 DDL 一致
- [ ] 是否所有业务表都有 `tenant_id`
- [ ] 是否没有把迁移账本算进 public 18 表

### 阻断例子

```text
文档写 19 张（把 kiraorder_meta 算进去）
文档改了表名
文档允许在 public 加表
```

---

## 2. 约束与角色

- [ ] `users.role` 是否只允许 `CLERK/OWNER/WAREHOUSE`
- [ ] `customers.credit_flag` 是否只允许 `NONE/OVERDUE_NOTICE`
- [ ] `inventory.available_qty >= 0` 是否存在
- [ ] `orders.version` 是否是乐观锁
- [ ] `draft_versions` / `delivery_orders` 是否不可变
- [ ] `activity_log` / `audit_logs` / `field_diffs` 是否 append-only
- [ ] `approval_requests` 每租户/草稿最多一个 PENDING
- [ ] `delivery_orders` 每草稿唯一
- [ ] token 是否只存哈希
- [ ] `inbound_messages` 是否只存 masked text

### 阻断例子

```text
文档允许删除 draft_versions
文档允许修改 delivery_orders
文档允许 plaintext token
文档没有 tenant 隔离
```

---

## 3. Trigger 数量：6 个对象 / 12 条事件

这是最容易写错的点。

Gate 0 定义 6 个 trigger 对象：

```text
draft_versions_immutable
delivery_orders_immutable
activity_log_append_only
audit_logs_append_only
field_diffs_append_only
approval_request_snapshot_guard
```

每个都是：

```sql
BEFORE UPDATE OR DELETE
```

所以：

```text
pg_trigger 非内部对象 = 6
information_schema.triggers 事件行 = 12
approval_request_snapshot_guard = UPDATE + DELETE
```

审核时确认：

- [ ] 是否写 6 个对象
- [ ] 是否写 12 条事件
- [ ] 是否没有用 `pg_trigger` 期待 12
- [ ] 是否明确 approval guard 两个事件
- [ ] 是否明确六个 trigger 都覆盖 UPDATE 和 DELETE

### 阻断例子

```text
文档说 pg_trigger 有 12 个
文档说 information_schema 有 6 行
文档漏掉 approval guard 的 DELETE
```

---

## 4. 迁移机制

`0001_baseline.sql` 使用普通 `CREATE TABLE`，没有 `IF NOT EXISTS`：

- [ ] 文档是否明确原始 SQL 不能执行两次
- [ ] 是否禁止修改 Gate 0 SQL 加 `IF NOT EXISTS`
- [ ] 是否要求迁移执行器校验 SQL 哈希
- [ ] 是否要求 advisory lock
- [ ] 是否要求 `kiraorder_meta.schema_migrations` 账本
- [ ] 是否同 version + hash 跳过
- [ ] 是否同 version 不同 hash 立即失败
- [ ] 执行 Gate 0 SQL 前是否 `SET search_path = public`
- [ ] `kiraorder_meta` 是否不计入 public 18 表

### 阻断例子

```text
文档说直接重复执行 0001_baseline.sql 即可
文档建议加 IF NOT EXISTS
文档没有 hash 校验
文档把账本放 public
文档没有设置 search_path
```

---

## 5. Seed 数据

- [ ] T1/T2 是否有明确边界
- [ ] 每个租户是否覆盖 `CLERK/OWNER/WAREHOUSE`
- [ ] 是否覆盖正常客户/OVERDUE_NOTICE/等级价客户
- [ ] 是否覆盖商品族/SKU/等级价/库存
- [ ] 是否覆盖规格歧义（1kg / 5kg）
- [ ] 是否覆盖多语别名
- [ ] 是否覆盖客户级 alias 与租户级 alias 冲突
- [ ] 是否覆盖 H5 16 行条件消息
- [ ] seed 是否幂等
- [ ] 演示重置是否只重置演示租户
- [ ] 是否禁止真实客户/PII/密钥
- [ ] 金额是否 decimal string
- [ ] qty 是否正整数

### 阻断例子

```text
seed 重复插入
seed 使用真实电话
seed 只覆盖一个租户
seed 没有库存不足/边界
```

---

## 6. TEST / DEV / 答案键

- [ ] `dev_41` 是否是开发集 canonical
- [ ] `frozen_eval_32` 是否只放 TEST-01—32
- [ ] 两者是否不重叠
- [ ] `DEV-33—41` 是否不进入冻结集
- [ ] `TEST-01—32` 是否归数据岗独占
- [ ] `H5-CT-01—03` 是否没有占用 TEST 编号
- [ ] 答案键是否只在 `tests/answers/*`
- [ ] 运行时/API/AI 是否不能读答案键
- [ ] `FROZEN_SHA256.txt` 是否由封存生成
- [ ] 冻结集修改是否有新版本

### 阻断例子

```text
文档允许应用读 answers
文档把 H5-CT 写成 TEST-29/30
文档静默覆盖冻结集
```

---

## 7. 数据验收

```text
[ ] public 基础表 = 18
[ ] pg_trigger 非内部对象 = 6
[ ] information_schema.triggers = 12
[ ] approval_request_snapshot_guard = UPDATE + DELETE
[ ] 迁移第一次成功
[ ] 迁移第二次安全跳过
[ ] SQL 哈希异常拒绝迁移
[ ] seed 幂等
[ ] TEST/DEV 不重叠
[ ] 答案键隔离
[ ] gate0/ 无 diff
```

### 阻断例子

```text
文档没有 18/6/12 验收
文档没有迁移幂等
文档允许修改 gate0/migrations
```

---

## 8. 审核结论

### 无阻断

```text
04 数据对接已核对：
- 18 张 public 表 / 6 trigger 对象 / 12 事件
- approval guard UPDATE + DELETE
- 迁移执行器幂等与 hash 校验
- seed T1/T2、TEST-01—32、答案键隔离
无阻断异议。
```

或 `Review changes → Approve`。

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

### 非阻断

```text
非阻断建议：
```

例如建议补一个 seed 边界样例，但不要因此阻塞合并。

---

## 9. 数据通过标准

```text
[ ] 18 表 / 6 trigger 对象 / 12 事件
[ ] approval guard UPDATE + DELETE
[ ] 原始 SQL 不重复执行
[ ] 迁移执行器幂等且校验 hash
[ ] kiraorder_meta 不污染 public
[ ] seed 覆盖 T1/T2/三角色/歧义
[ ] TEST/DEV/答案键正确隔离
[ ] 无阻断评论
```
