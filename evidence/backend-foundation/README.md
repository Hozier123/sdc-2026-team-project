# 后端基础验收记录

记录日期：2026-10-22。范围：P0-A 第一个后端 PR；不包含 seed、鉴权、parse、订单批准、业务 KPI 或平台部署证明。

## 本地环境与结果

- Windows，Python 3.13.5，PostgreSQL 17.10；依赖版本见 `backend/requirements.lock`。
- 数据库是本次验证单独初始化的本机临时实例，仅监听 `127.0.0.1:55432`；没有连接现有业务库。每项集成测试独立创建随机测试库，结束后删除自己的测试库。
- 命令：在 `backend/` 执行 `.venv/Scripts/python -m pytest -q`，测试连接通过 `TEST_DATABASE_ADMIN_URL` 提供。
- 实测结果：**17 passed，0 failed，0 skipped**。
- 另有 1 条第三方弃用提示：Starlette TestClient 提示今后应从 httpx 迁移至 httpx2。当前锁定版本的测试通过，未关闭或掩盖此提示；后续升级测试依赖时需重新验收。
- Ruff 静态检查、格式检查和 `pip check` 分别执行；依赖兼容性检查无错误。
- Gate 0 原验证入口 `gate0/scripts/bootstrap_gate0.ps1 -SkipInstall`：42 passed、73 项受控文件校验通过；`git diff gate0-baseline-v1 -- gate0/` 无差异。

## 已验证内容

1. 实际 Uvicorn 子进程可启动，HTTP `/healthz` 返回 200。
2. 未配置/未迁移/连接失败时 `/readyz` 返回 503；迁移登记正确后返回 200。
3. 真实 CLI 首次迁移 `applied`，重复运行 `already_applied`，已插入的合成数据保留。
4. `public` 恰有 18 张基础表、6 个非内部触发器对象、12 条 UPDATE/DELETE 事件记录；迁移账本独立位于 `kiraorder_meta`。
5. 两路并发只应用一次；提交前故意制造数据库错误时，DDL 与账本一起回滚，之后可重试成功。
6. SQL/清单哈希错误在连接数据库前拒绝；账本冲突、已有无账本表、禁用触发器均被拒绝，不静默修复。
7. 审批快照的非法 UPDATE/DELETE 被真实数据库阻止，合法 PENDING → APPROVED 转移可执行。
8. 探针和迁移 CLI 不输出连接密码或数据库原始异常。

## 可复验与限制

完整复验命令及数据库权限见 [后端说明](../../backend/README.md)。CI 定义在 `.github/workflows/backend-foundation.yml`，使用 PostgreSQL 17.10 服务；远端运行状态以对应 PR 的 Actions 记录为准，本文件不预先宣称 CI 成功。

数据库计数不能混用：`pg_trigger` 统计对象为 6，`information_schema.triggers` 按事件展开为 12。以上检查不是全面 schema 漂移审计，也不是业务端到端验收。

冻结基线为 `gate0-baseline-v1`，SQL SHA-256 为 `6DDFD6160A2416237A73ADC16A3B26F4DDE0657FD42BDB2A7C355682711FE471`，受控清单 SHA-256 为 `6A44089C623C1B4AE8F444660DBD89422C663E7EBDD141EA6FDA549DDD833770`。本 PR 不修改 `gate0/`，不移动标签，不更新冻结的签字状态；正式确认仍见 `evidence/gate0/`。
