# C07 隔离执行与复核

本操作仅限防重、并发和批准事务回滚。每次运行使用新建 PostgreSQL cluster、独立端口及合成租户，不需要线上角色令牌或模型服务。

## 从当前源码执行

使用项目的 Python 3.13 测试环境和已有 PostgreSQL Windows bin 目录。在 `backend/` 中执行：

```powershell
.venv/Scripts/python -m tools.verify_c07_local `
  --postgres-bin '<PostgreSQL bin 绝对路径，含 initdb.exe/pg_ctl.exe/postgres.exe>' `
  --output '<C07 证据父目录绝对路径>'
```

脚本会：

1. 复制并绑定应用源码、冻结迁移、所需契约、原有并发测试和执行器；运行时使用副本。
2. 在独立 cluster 中建立 UTF8 业务库、迁移 schema，创建 C07 合成数据及本地临时身份。
3. 启动正常 API 和专供故障注入的 API，全部仅监听 127.0.0.1。
4. 执行 6 个预先登记的场景，保存 33 个请求/响应及业务表前后快照。
5. 对并发请求使用 Barrier；先持有测试行锁，观察所有 API 事务同时等待 PostgreSQL 锁，再释放并记录结果。
6. 运行原有 3 项并发/回滚集成测试及 4 项老板终态回归；每个测试创建独立随机数据库。终态回归覆盖批准/拒绝后重发相同或相反决定，要求正确错误码、409、无额外写入。
7. 校验运行时源码未变化，停止本次拥有的 API 和 PostgreSQL，并保存最终状态。

为兼容当前中文 Windows，cluster 使用 EUC_CN，业务库显式使用 UTF8；实际值记录在 `summary.json`。临时 cluster 保留在工作区 `.tmp/c07-*`，不装入交接 ZIP。脚本不会删除或复位既有数据库。

输出退出码 0 才表示本次执行通过；失败先读 `summary.json`、`runner.log` 和对应场景 `exception.json`。不要把失败批次覆盖成成功；修改后另开新批次。

## 离线复核交接包

解压本次 ZIP，进入其批次目录，用任意可用 Python 运行：

```powershell
python audit_c07_evidence.py
```

该脚本只用标准库，读取本地文件，不连接 API/数据库，重算源码大小/哈希、请求编号、响应 JSON、库存差值、DO/审计数量、重试前后相等、真实锁等待与 JUnit 结果。输出 `offline-review.json`；这仍是证据核对工具，不能替代独立复核人的判断。

需要独立重跑时，使用包内 `source/`，按 `requirements.lock` 准备独立 Python 3.13 环境，然后从 `source/backend/` 执行上述命令。每次生成新的批次，不改原包。

## 本次核对重点

| 材料 | 核对内容 |
| --- | --- |
| `test-plan.json` | 6 个预期在执行前登记 |
| `source-manifest.json`、`source/` | 原包 74 项、新修复包 75 项实际运行文件，含未提交源码；不能只看 Git HEAD |
| `cases/*/http/*.json` | 请求体、角色、原始响应文本、业务错误码、回传 X-Request-ID |
| `cases/*/db/*.json` | 8 类业务表原始行；确认库存、DO、审批、审计无重复 |
| `cases/*/*-overlap.json` | 4/4、4/4、2/2 API 事务同时处于锁等待；观察时间在请求起止内 |
| `cases/C07-06/fault-injection.json` | 仅专属故障 API 的运行时注入；DO 插入后失败，整笔回滚 |
| `existing-concurrency-tests.xml` | 3 个原有测试，无失败/跳过 |
| `terminal-decision-regression.xml` | 新修复包的 4 个终态回归，无失败/跳过 |
| `application-fix.patch`、`source-delta.json` | 新修复包相对原签收源码的补丁与差异；应用仅审批模块改变 |
| `ZHOU_REVIEW_ORIGINAL.md` | 用户转交的原批签收，安全目标通过、附 P2；不代表新修复已复签 |
| 工作区 `output/c07-closeout-2026-10-30/C07_REVIEW_v2.md` | Zhou 23:06 对新修复包的补签，本地 P2 关闭；原字节归档，不回写原交接包 |
| `summary.json` | 执行结果、实际环境、源码未变化及服务停止 |

复核结论应区分 He 侧执行通过、Zhou 独立验收、公开部署/浏览器行为。原批安全目标已签收，P2 修复包也已于 2026-10-30 23:06（UTC+8）补签，本地源码/证据层关闭。公开部署/浏览器仍不在本批范围。

## 线上 C07 执行与复核

2026-10-31 已在 `9cff61ed` 完成公开 HTTPS/Neon 执行；6 场景、验收映射 34 请求、194 项离线核对通过，独立线上复核待 Zhou。台账和重试取证说明见工作区 `output/c07-online-2026-10-30/ONLINE_REPORT_2026-10-31.md`，公开版本登记见 [c07-release.md](c07-release.md)。

交接包可执行 `python audit_online_c07.py review`，按台账读取五项首轮 PASS 和单独补测 C07-05 的原始文件。原整体 FAIL 和初始化失败均保留说明，不覆盖原证据。该离线命令不连接数据库或服务。

若决赛使用线上环境，应将已复核的审批修复合入目标发布版本，再在部署后核对实际线上版本。只读健康检查或旧版本号不能替代本次变更的版本绑定。

线上复核应使用获准的合成订单与执行窗口，保留请求/响应、X-Request-ID、实际错误码/文案和 DB 前后数据，重点包括：

- 已批准审批的顺序重试及同一审批的并发失败分支：409 / ALREADY_APPROVED，文案不再称 waiting。
- 已拒绝审批再次决定：409 / DRAFT_REJECTED；真正待批的送审重试仍为 PENDING_OWNER_APPROVAL。
- 无重复 DO、扣库存或审批审计；库存差值与实际订单数量相符。

发布若包含其他审批、库存或事务改动，应按新版本重跑受影响的 C07 安全场景，再交独立复核。本次线上证据已到位，状态为 He 执行通过、待独立线上复核；不沿用旧本地补签替代新签收。
