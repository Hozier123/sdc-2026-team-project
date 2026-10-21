# KiraOrder v1.3 后端与数据对接规则

> 状态：`HANDOFF_DRAFT`（2026-10-22）  
> 适用基线：`gate0-baseline-v1` / Gate 0 v4 / draft revision 5  
> 基线哈希：`6A44089C623C1B4AE8F444660DBD89422C663E7EBDD141EA6FDA549DDD833770`  
> Canonical：`gate0/`（冻结，不可修改）  
> 本文性质：从 Gate 0 v4 派生的数据对接说明；与 `gate0/` 冲突时，**以 `gate0/` 为准**。

---

## 0. 先读这一节

### 0.1 唯一机器可读真相

```text
gate0/contracts/db-schema.md
gate0/migrations/0001_baseline.sql
gate0/contracts/fields.md
gate0/contracts/errors.md
gate0/docs/gate0-test-data-map.md
gate0/contracts/fixtures/
```

本文只说明数据岗要交付什么、后端和数据岗的边界在哪里。

### 0.2 数据岗负责

```text
T1/T2 合成种子数据
商品族/SKU/等级价/库存
客户/用户/别名
dev_41 开发集
frozen_eval_32 冻结集
答案键隔离
冻结集哈希
导入/重置脚本的数据部分
```

### 0.3 数据岗不负责

```text
不改 gate0/ 的 18 张表 DDL
不改 gate0/ 的 trigger
不改 Gate 0 契约
不决定后端路由/审批逻辑
不把答案键放进应用运行时
```

### 0.4 不得修改 Gate 0

- 不修改 `gate0/migrations/0001_baseline.sql`；
- 不为了 seed 方便加表/改列/删约束；
- 需要改 schema：开 `gate0-v5`，重新哈希、重新签字；
- 日常 seed 只写 `data/` 和测试数据目录。

---

## 1. 数据库结构

### 1.1 `public` 18 张基础表

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

共 **18** 张。

### 1.2 关键约束

- 所有业务表带 `tenant_id`，跨租户不可见；
- `users.role` 闭集：`CLERK/OWNER/WAREHOUSE`；
- `customers.credit_flag`：`NONE/OVERDUE_NOTICE`；
- `inventory.available_qty >= 0`；
- `orders.version` 是乐观锁；
- `draft_versions`、`delivery_orders` 不可变；
- `activity_log`、`audit_logs`、`field_diffs` append-only；
- `approval_requests` 每租户/草稿最多一个 PENDING；
- `delivery_orders` 每草稿唯一；
- 密码/token 只存哈希，不存明文；
- `inbound_messages` 只存 masked text。

### 1.3 6 个 trigger 对象 / 12 条事件

Gate 0 的 DDL 定义 **6 个 trigger 对象**：

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

**不要把 6 和 12 混用。**

正确验收 SQL：

```sql
-- 6 个 trigger 对象
SELECT count(*)
FROM pg_trigger t
JOIN pg_class c ON c.oid = t.tgrelid
JOIN pg_namespace n ON n.oid = c.relnamespace
WHERE NOT t.tgisinternal
  AND n.nspname = 'public';

-- 12 条事件记录
SELECT count(*)
FROM information_schema.triggers
WHERE trigger_schema = 'public';

-- 审批 guard 两个事件
SELECT trigger_name, event_manipulation
FROM information_schema.triggers
WHERE trigger_schema = 'public'
  AND trigger_name = 'approval_request_snapshot_guard'
ORDER BY event_manipulation;
```

预期：

```text
6
12
DELETE
UPDATE
```

---

## 2. seed 数据

### 2.1 租户

至少：

```text
T1：正常租户
T2：跨租户隔离测试租户
```

要求：

- 同一份 seed 可重复导入；
- T1/T2 数据不共享；
- 所有业务样本为团队自建合成数据；
- 不使用真实客户、真实电话、真实 MyKad、真实邮箱。

### 2.2 用户与角色

每个租户至少覆盖：

```text
CLERK
OWNER
WAREHOUSE
```

要求：

- 演示 token 只存哈希；
- 不把明文 token 写进 seed 文件或仓库；
- 跨租户用户不能通过改 URL 访问另一租户资源；
- OWNER 的升级权限、CLERK 的本人范围、WAREHOUSE 的只读视图要能测试。

### 2.3 客户

至少覆盖：

- 正常客户；
- `credit_flag=OVERDUE_NOTICE` 客户；
- 有等级价客户；
- 跨租户同名/同电话边界（用于证明隔离）。

金额：

```text
decimal string，两位小数
不使用 binary float
```

### 2.4 商品族 / SKU / 别名

必须覆盖：

- 10 个左右商品族；
- T1 至少 16 个 SKU；
- 规格歧义：同族不同 `pack_size`（如 1kg / 5kg）；
- 等级价：同一 SKU 不同 tier；
- 库存：充足/不足/边界；
- 多语别名：马来语/英语/中文；
- 客户级 alias 与租户级 alias 冲突场景；
- `uom_aliases` 的租户扩展。

### 2.5 条件消息

至少覆盖 H5 v3 的 16 行真值表：

```text
历史金额不触发
裸金额/问号
马来语/英语/中文议价
STOCK
STOCK + PRICE 多标签
UNIT/TOTAL/UNKNOWN
否定/已付/编码
```

STOCK 条件本身不阻断；缺货由行级 `INSUFFICIENT_STOCK` 阻断。

### 2.6 seed 幂等

seed loader 必须：

- 可重复执行；
- 不产生重复租户/用户/SKU；
- 不覆盖人工修改的业务数据；
- 演示重置只重置演示租户；
- 失败时整体回滚或明确报告部分失败。

---

## 3. 测试数据与编号

### 3.1 文件

```text
tests/dev_41.json                 DEV-01—41
tests/dev_32.json                 旧版，deprecated
tests/frozen_eval_32.json         TEST-01—32
tests/FROZEN_SHA256.txt           冻结集哈希
tests/answers/dev_answers.json    仅离线评测
tests/answers/frozen_answers.json 仅离线评测
```

### 3.2 规则

- `dev_41` 是开发集 canonical；
- `frozen_eval_32` 只放 TEST-01—32，不放 DEV；
- 两个集合不重叠；
- `DEV-33—41` 是回归/新规则，不进入冻结集；
- 冻结集封存后只读；
- 需要修改：新建版本 + 重算 `FROZEN_SHA256.txt`，不能静默覆盖。

### 3.3 答案键隔离

- `tests/answers/*` 不得进入应用镜像；
- 运行时/API/AI 不得读取答案键；
- 答案键不得进入 prompt、公开 URL、日志；
- 只有离线 `run_eval.py` 可读；
- 冻结集尚未在 repo 分发时，只交哈希和审批记录。

### 3.4 H5 契约用例

Gate 0 的 H5 契约用例是：

```text
H5-CT-01
H5-CT-02
H5-CT-03
```

它们 **不是** `TEST-29/30/32`。  
`TEST-01—32` 是数据岗独占的冻结集编号。

---

## 4. 迁移机制

### 4.1 冻结 SQL 不可重复执行

`gate0/migrations/0001_baseline.sql` 使用普通：

```sql
CREATE TABLE ...
```

没有 `IF NOT EXISTS`，所以原始 SQL **不能执行两次**。

不要通过修改 Gate 0 SQL 来加 `IF NOT EXISTS`。

### 4.2 迁移执行器必须幂等

正确设计：

```text
1. 校验 SQL 文件 SHA-256
2. 获取 PostgreSQL advisory lock
3. 在 kiraorder_meta 建迁移账本
4. 第一次执行 Gate 0 SQL，登记 version + hash
5. 第二次相同 version + hash → 直接跳过
6. 同 version 不同 hash → 立即失败，禁止启动
```

### 4.3 schema 隔离

- Gate 0 的 18 张表全部在 `public`；
- 迁移账本放：

```text
kiraorder_meta.schema_migrations
```

- 执行 Gate 0 SQL 前必须：

```sql
SET search_path = public;
```

否则未限定的 `CREATE TABLE` 可能落到错误 schema。

### 4.4 验收

- 第一次迁移成功；
- 第二次迁移安全跳过；
- `public` 恰好 18 张表；
- `pg_trigger` 非内部对象 6 个；
- `information_schema.triggers` 12 条事件；
- approval guard 同时有 UPDATE/DELETE；
- SQL 哈希异常时拒绝迁移；
- `kiraorder_meta` 不计入 public 18 表。

---

## 5. 数据校验

### 5.1 结构

- 18 张表全部存在；
- 主键/唯一约束/外键生效；
- 6 个 trigger 对象存在；
- 审批 UPDATE/DELETE guard 存在；
- append-only 表的 UPDATE/DELETE 被拒。

### 5.2 数据

- 货币金额可精确还原；
- qty 为正整数；
- 库存非负；
- 租户隔离；
- 客户/商品/价格/SKU 外键完整；
- seed 重跑不重复；
- 跨租户 URL 返回 404/403。

### 5.3 冻结集

- `frozen_eval_32.json` 的 SHA-256 与 `FROZEN_SHA256.txt` 一致；
- 冻结集与 dev 集无重叠；
- 答案键不在应用可读路径；
- 冻结集修改有版本记录。

---

## 6. 交付清单

### 6.1 数据文件

- [ ] T1 seed
- [ ] T2 seed
- [ ] 商品族/SKU/等级价/库存
- [ ] 客户/用户/别名
- [ ] dev_41
- [ ] frozen_eval_32
- [ ] FROZEN_SHA256.txt
- [ ] 答案键（隔离存放）

### 6.2 脚本

- [ ] seed loader
- [ ] 演示重置
- [ ] schema 校验
- [ ] 冻结集哈希校验
- [ ] 导入顺序说明

### 6.3 验收

- [ ] 18 张 public 表
- [ ] 6 个非内部 trigger
- [ ] 12 条 trigger 事件
- [ ] approval guard UPDATE + DELETE
- [ ] seed 幂等
- [ ] TEST/DEV 不重叠
- [ ] 答案键不进运行时
- [ ] 不提交真实数据/密钥
- [ ] `gate0/` 无 diff

---

## 7. 交接问题格式

```text
数据文件：
Gate 0 契约：
期望：
实际：
影响：
是否阻断：
```

发现 schema 缺口时，不要直接改 Gate 0；进入 `gate0-v5` 流程。
