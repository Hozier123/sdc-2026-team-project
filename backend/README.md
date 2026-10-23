# KiraOrder 后端：当前实现与验收边界

当前已实现身份/租户权限、显式迁移与 seed、PII 掩码、AI HTTP 边界、字段证据防护、目录解析与客户记忆、草稿整批保存、条件与澄清、三语回复、作废草稿、价格升级、老板审批、DO/库存事务、查询/审计/仓库读取、AI 状态/唤醒、`checks_enabled` 软检查、并发回滚和契约回归。开发依据为 `gate0-baseline-v1`（内部 `gate0-v4 / draft revision 5`），原始 SQL 位于仓库 `gate0/migrations/0001_baseline.sql`，本轮未修改。

2026-10-23 审查说明与后续状态见 `docs/audit/backend-audit-2026-10-23.md`。当前 main 完整测试为 **290 passed**。仍属外部验收边界：真实 AI endpoint/模型准确率、公开部署、前端/数据独立 UAT；未配置 AI 时仅提供人工录单占位路径，不应宣传为完成了真实模型抽取。

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

身份读取和业务路由已实现；seed 仍须显式运行，应用启动不会自动改库。

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
测试使用隔离临时库；仓库已有经过哈希校验的 T1/T2 canonical seed。

## Seed loader

数据负责人提供 **data-only SQL** 文件后，用显式命令导入；Web 服务启动时不会自动 seed：

```powershell
backend/.venv/Scripts/python -m app.seed `
  --tenant T1 `
  --seed-sql ..\data\seed\T1_seed.sql `
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

正式 T1/T2 SQL 与 SHA-256 见 `data/seed/SEED_MANIFEST.json`；测试同时覆盖 canonical seed 与临时 fixture。SQL 的 LF 字节由 `.gitattributes` 保持，禁止为绕过失败而重新签署哈希。

## PII 与 parse-draft 骨架

`POST /api/v1/orders/parse-draft` 已可调用。未配置 `AI_SERVICE_URL` 时使用确定性
`StubExtractor`，会生成一个 `DISAMBIGUATION_REQUIRED` 的 v1 草稿，不生成正式商品行。

配置 `AI_SERVICE_URL` 后使用 `HttpAiExtractor`：

```text
AI_SERVICE_URL=https://.../api/v1/extract
AI_HEALTH_URL=https://.../health
AI_WAKE_URL=https://.../wake
AI_API_KEY=...
AI_TIMEOUT_S=8.0
AI_WAKE_RATE_LIMIT_S=60
AI_WARMUP_GRACE_S=15
```

`GET /api/v1/ai/status` 会探测 health URL，返回 `OFFLINE/WARMING/READY/DEGRADED` 和固定
`available_modes`；`POST /api/v1/ai/wake` 会向 wake URL 发送 `{"wake": true}`，同一用户
默认 60 秒限流，超限返回 429 `RATE_LIMITED` 与 `Retry-After`。未配置 endpoint 时返回
`OFFLINE`，fallback 仅表示人工/别名路径，不伪造 LLM readiness。API key 只发往 AI
endpoint，不出现在任何响应。

流程：

```text
Bearer → customer tenant check → PII mask
→ ExtractionProvider.extract(masked_text)
→ AI-Contract-v1.3 schema 校验
→ generic FAM_* 到 canonical seed 的显式映射
→ conds / ignored_spans 转换
→ 基础 RawExtraction 校验
→ AI 行进入草稿（未选 SKU 时标记 NO_CANDIDATE）
→ inbound_messages / orders / draft_versions
→ OrderDraft
```

- AI 契约、样例和 H1/H5 映射在 `docs/ai_contract/`；
- AI 只返回 `rows` + `ignored_spans`，不得返回 `sku_id`、价格、库存、审批或 DO；
- `FAM_FLOUR`/`FAM_RICE`/`FAM_OIL`/`FAM_SUGAR` 目前显式映射到 canonical T1 的
  `FAM_TEPUNG`/`FAM_BERAS`/`FAM_MINYAK`/`FAM_GULA`；租户差异后续用 catalog 注入；
- 真实 endpoint/key 不在仓库；未配置时不会伪造 AI 调用；
- PII 只允许 `[REDACTED_PHONE]`、`[REDACTED_MYKAD]`、`[REDACTED_EMAIL]`；
- 仅 `CLERK` / `OWNER` 可调用；`WAREHOUSE` 返回 403 `FORBIDDEN_ACTION`；
- 原始 `message_text` 不写日志、不落库、不传给 provider；
- `masked_text` 超过 4000 code points 返回 422 `MESSAGE_TOO_LONG`；
- customer 不存在或跨租户返回 404 `RESOURCE_NOT_FOUND`；
- 真实 H1/H5 准确率仍需 AI endpoint/评测集；当前 adapter 不伪造这些。

## Clarification、CORS 与 AI 失败

`clarification_draft` 由后端根据未解决 issues/conditions 生成：

```text
language
message
unresolved_issue_ids
```

只在 `clarification_draft` 非空时返回 `COPY_CLARIFICATION`。支持 `ms` / `en` / `zh`，
不包含原始 PII，不声称价格、SKU 或数量已确认。

CORS 默认允许本地前端：

```text
http://127.0.0.1:5173
http://localhost:5173
http://127.0.0.1:4173
http://localhost:4173
```

可用 `CORS_ALLOW_ORIGINS` 覆盖；不使用 `*`。

AI 服务超时、5xx、非法 JSON 或非法 payload 返回：

```text
503 AI_AND_FALLBACK_UNAVAILABLE
```

## 草稿行、批准与 DO

已实现：

```text
PUT  /api/v1/orders/drafts/{draft_id}/lines
POST /api/v1/orders/drafts/{draft_id}/discard
POST /api/v1/orders/drafts/{draft_id}/clarification-copied
POST /api/v1/orders/{draft_id}/approve
POST /api/v1/approvals/{approval_id}/decide
GET  /api/v1/delivery-orders/{do_number}
GET  /api/v1/approvals
GET  /api/v1/approvals/{approval_id}
```

`discard` 是 P1 的 CLERK/OWNER 终止动作：要求 `expected_version` 和非空
`note`，仅允许 `DISAMBIGUATION_REQUIRED` / `READY_FOR_APPROVAL` 使用；成功后
`status=REJECTED`、`termination_reason=CLERK_DISCARDED`，写入 `CANCEL_DRAFT`
审计和 `DRAFT_DISCARDED` 活动记录。pending 或已出单的草稿不能作废。

`clarification-copied` 只追加 `COPY_CLARIFICATION` 审计和
`CLARIFICATION_COPIED` 活动；绑定 draft/version、clarification 的 issue_ids、
对应 line_ids、语言和消息 SHA-256，不保存完整消息，不修改草稿或版本。

同日订单检查只查客户当天已有 DO。`SEPARATE_ADD_ON` 必须在保存 resolutions 时
显式给出 `related_do_number`；新 DO 会写 `related_do_number`，原 DO 不变。
`DUPLICATE` / `CHANGE_EXISTING` 走 P1-02 discard，关闭当前草稿并记录理由，
不自动修改原单。`SEPARATE_ADD_ON` 的决定会跨后续保存保留，除非当天 DO 集合变化。

**`confirmed_items` 是 deprecated 兼容路径。** 新前端仍必须先：

```text
PUT /api/v1/orders/drafts/{draft_id}/lines
→ POST /api/v1/orders/{draft_id}/approve
```

如果旧客户端携带 `confirmed_items`，后端在同一个事务里：

```text
1. 按 PUT lines 规则保存新版本
2. 重新校验库存/升级/条件
3. 批准这个新版本
4. 任一步失败则整个事务回滚
```

响应返回实际批准的版本；不会静默批准未保存明细。该兼容路径不再返回 422，OpenAPI 仍标记为 deprecated。

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

## 当前验收边界

内部后端主链路已完成并有自动测试；当前 main 为 **290 passed**。仍需外部材料或现场验收的部分：真实 AI endpoint 的模型质量与独立准确率、公开部署、前端/数据独立 UAT、真人试用记录。01—04 的 v1.3 工作文档在 `docs/rules/` 以独立提交随对应实现更新；不回写冻结文件。

实现依据：[psycopg 事务管理](https://www.psycopg.org/psycopg3/docs/basic/transactions.html)、[pglast SQL 解析器](https://pglast.readthedocs.io/en/v7/parser.html)、[PostgreSQL advisory locks](https://www.postgresql.org/docs/17/explicit-locking.html#ADVISORY-LOCKS)。
