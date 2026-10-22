# KiraOrder 后端基础、身份、seed 与 parse 骨架

当前实现 FastAPI 进程、数据库探针、Gate 0 迁移执行器、Bearer `/api/v1/me`、版本钉住的 seed loader，以及 PII + parse-draft 骨架。草稿编辑、审批和 DO 仍未实现。开发依据为 `gate0-baseline-v1`（内部 `gate0-v4 / draft revision 5`），原始 SQL 位于仓库 `gate0/migrations/0001_baseline.sql`。

## 安装和启动（Windows）

需要 Python 3.13 和可连接的 PostgreSQL 17；验收使用 PostgreSQL 17.10。以下从仓库根目录执行，保持整个仓库结构，并采用 editable 安装（单独安装 wheel 不携带 Gate 0）：

```powershell
py -3.13 -m venv backend/.venv
backend/.venv/Scripts/python -m pip install -c backend/requirements.lock -e './backend[test]'
```

在根目录 `.env` 设置 `DATABASE_URL=postgresql://用户名:密码@主机:5432/数据库名`。空值仍可启动存活探针，就绪探针返回 503。进程环境变量优先于 `.env`；读取 `.env` 的位置不依赖启动目录。密码中的 URL 特殊字符应按 URI 规则编码。

迁移是显式管理命令，不在 Web 服务启动时自动执行。迁移身份需具备创建 schema/table/function/trigger 的权限，复验时使用该对象所有者身份。部署应先运行迁移命令成功后再启动服务。

```powershell
backend/.venv/Scripts/python -m app.migrations
backend/.venv/Scripts/python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

| 路径 | 条件 | 响应 |
|---|---|---|
| `/healthz` | 进程可处理请求 | 200 `{"status":"ok"}` |
| `/readyz` | 数据库可查询且 Gate 0 迁移版本和哈希登记正确 | 200 `{"status":"ready"}` |
| `/readyz` | 未配置、不可连接、未迁移或登记哈希不一致 | 503 `{"status":"not_ready"}` |

这两个路径为运维探针，记录于后端运行说明及运行时 OpenAPI；不写回冻结业务 OpenAPI。探针不返回连接串或底层异常。连接超时 3 秒、普通查询和锁等待超时 5 秒；迁移事务中语句超时 30 秒；seed 导入事务中语句超时 60 秒、租户锁等待 10 秒。就绪探针检查连接和迁移登记，不声称每次都做完整 schema 漂移审计。

## Bearer 与 `/api/v1/me`

本阶段实现身份读取；seed 使用显式命令，parse-draft 目前只是 PII + 骨架。

```http
GET /api/v1/me
Authorization: Bearer <demo-token>
```

`demo-token` 的数据库存储值为：

```text
SHA-256(token UTF-8) 的小写 hex
```

`/me` 从 `users.demo_token_hash` 查找活跃用户，并返回 OpenAPI `MeResponse`：
`user_id`、`tenant:{id,name}`、`display_name`、`role`、`permissions`、`permission_summary`。
角色和租户只来自 token 对应的用户记录，不接受请求体或 query 覆盖。

失败统一返回 401 `INVALID_TOKEN`，带 `WWW-Authenticate: Bearer`；成功和失败响应都带
`X-Request-ID`。数据库或其它未知服务端错误走统一 500，不映射成业务错误，也不返回连接串。
在正式 seed 导入前，真实环境没有用户，`/me` 返回 401 是预期行为；
测试使用临时数据库和 fixture 用户，不提交 canonical seed。

## Seed loader

数据负责人提供 **data-only SQL** 文件后，用显式命令导入；Web 服务启动时不会自动 seed：

```powershell
backend/.venv/Scripts/python -m app.seed `
  --tenant T1 `
  --seed-sql ..\data\seed\seed_T1.sql `
  --seed-version T1-0.1 `
  --expect-sha256 <sql-sha256> `
  --expect-products 40 `
  --expect-inventory 795
```

行为：

- 先校验 SQL 文件 SHA-256，再连接数据库；
- seed SQL 只允许 `INSERT`，不得包含 DDL 或 `BEGIN/COMMIT/ROLLBACK`；
- 在一个事务内执行数据 SQL、计数校验和 `kiraorder_meta.seed_manifest` 登记；
- 同一 tenant + version + hash 重复执行返回 `already_loaded`，不重复插入；
- 同一 tenant 已有数据但没有 manifest 时拒绝自动接管；
- 计数不符或 SQL 失败时回滚，不留下半成品；
- 不创建/修改 Gate 0 的 `public` 业务表结构。

正式的 T1/T2 seed、40/795 计数和 SHA-256 由数据负责人定稿；本仓库测试只使用临时 fixture。

## PII 与 parse-draft 骨架

`POST /api/v1/orders/parse-draft` 已可调用，但当前使用确定性 `StubExtractor`：
它会生成一个 `DISAMBIGUATION_REQUIRED` 的 v1 草稿，不生成正式商品行。

流程：

```text
Bearer → customer tenant check → PII mask
→ ExtractionProvider.extract(masked_text)
→ 基础 RawExtraction 校验
→ inbound_messages / orders / draft_versions
→ OrderDraft
```

- PII 只允许 `[REDACTED_PHONE]`、`[REDACTED_MYKAD]`、`[REDACTED_EMAIL]`；
- 仅 `CLERK` / `OWNER` 可调用；`WAREHOUSE` 返回 403 `FORBIDDEN_ACTION`；
- 原始 `message_text` 不写日志、不落库、不传给 provider；
- `masked_text` 超过 4000 code points 返回 422 `MESSAGE_TOO_LONG`；
- customer 不存在或跨租户返回 404 `RESOURCE_NOT_FOUND`；
- 真实 AI 到货后，用新的 `ExtractionProvider` 替换 `StubExtractor`，不改 API；
- 当前骨架不是最终 H1/H5 解析能力。

## 迁移执行规则

1. 在连接数据库前校验原始 SQL 字节 SHA-256 和受控哈希清单 SHA-256，预期值绑定已冻结标签。
2. PostgreSQL 解析器按 SQL 语句边界分割，只读原始语句文本，不用分号手工拆分函数体，不生成改写 SQL。
3. 执行原脚本的 `BEGIN`，取得事务级 advisory lock。在 `kiraorder_meta.schema_migrations` 建立迁移账本；业务对象仍在 `public`。
4. 未登记时，仅在没有业务基础表的 `public` 中顺序执行原始 DDL，再登记版本、SQL 哈希、基线清单哈希。已有无账本的表会被拒绝自动接管。
5. 登记匹配时跳过 DDL，但仍复查表名集合、触发器事件和启用状态、三项唯一索引存在且有效。
6. 验收通过后执行原脚本的 `COMMIT`。DDL、账本创建和登记都在同一事务中；任何中途错误都回滚。并发执行由锁串行化，锁超时可重试。

首次命令结果 `status=applied`；重复结果 `status=already_applied`。登记冲突或 schema 异常时退出码为 1，不尝试修补或删除已有数据。后续新增迁移需扩展版本序列管理，本 PR 仅支持 `0001_baseline`。

验收数字按 schema 区分：`public` **18 张基础表、6 个 trigger 对象、12 条 UPDATE/DELETE 事件记录**；`kiraorder_meta` 另有 1 张迁移账本。验证对象名称和作用表，不仅比较数量。完整字段/约束的持续漂移检测不属于本阶段。

## 测试

无需数据库的测试（明确排除集成测试）：

```powershell
Set-Location backend
.venv/Scripts/python -m pytest -q -m 'not integration'
```

完整验收需要测试实例管理员连接 `TEST_DATABASE_ADMIN_URL`，有 CREATEDB 权限。每项集成测试创建随机命名的 `kiraorder_test_<uuid>` 数据库，结束时仅删除它自己创建的数据库；不读取应用 `DATABASE_URL` 作为测试目标。没有测试连接时完整测试明确失败，不静默 skip。

```powershell
$env:TEST_DATABASE_ADMIN_URL = 'postgresql://测试用户:测试密码@127.0.0.1:5432/postgres'
.venv/Scripts/python -m pytest -q
.venv/Scripts/python -m ruff check app tests
.venv/Scripts/python -m ruff format --check app tests
.venv/Scripts/python -m pip check
```

覆盖：实际 Uvicorn 启动、HTTP 存活/就绪状态、迁移 CLI、空库安装、重复运行保留数据、并发互斥、提交前故障完整回滚、哈希错误、账本冲突、无账本既有表保护、禁用 trigger 检测、审批快照 UPDATE/DELETE 保护。

GitHub Actions 使用隔离 PostgreSQL 17.10 service 执行完整验收。Gate 0 自身的 42 项契约检查仍通过原 `gate0/scripts/bootstrap_gate0.ps1` 运行；不与新后端依赖环境混装。

## 后续衔接

后续提交依次接真实 AI/H1/H5、draft/PUT lines、approve/DO、approvals/decide，再补齐 OWNER、审计和回复主链路。01—04 的 v1.3 工作文档在 `docs/rules/` 以独立提交随对应实现更新，本次不修改冻结文件。

实现依据：[psycopg 事务管理](https://www.psycopg.org/psycopg3/docs/basic/transactions.html)、[pglast SQL 解析器](https://pglast.readthedocs.io/en/v7/parser.html)、[PostgreSQL advisory locks](https://www.postgresql.org/docs/17/explicit-locking.html#ADVISORY-LOCKS)。
