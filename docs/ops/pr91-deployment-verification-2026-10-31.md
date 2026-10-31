# PR #91 部署核实与账号来源查证

核实日期：2026-10-31（UTC+8）。本记录是两项独立收尾，不重开已结项的 B/C，不启动 B05 实测。

## 部署核实：完成

Replit 核实前的 Live 为 `6d6bafd8`，应用绑定 `99ee169ef01527587312c82beaba41858f47b9e4`。Replit 源码为 `b156e6a`（上一个发布后提交），`backend/app`、锁定依赖与该应用基线无差异。该发布早于 [PR #91](https://github.com/Hozier123/sdc-2026-team-project/pull/91) 的合入，相关五个应用文件也未包含修复，因此执行了限定补发。

发布源以 `99ee169` 为基线，仅 cherry-pick 已审核修复 `436eec684eb25a0ef1c9286e21917ff2adba2821`，干净应用，无冲突、无手工重写。GitHub 固定应用源为 [`520556cd64a7e6e6a17dfe84d0cdd386d0fef94e`](https://github.com/Hozier123/sdc-2026-team-project/commit/520556cd64a7e6e6a17dfe84d0cdd386d0fef94e)。相对旧基线共 9 个文件：5 个应用文件、3 个测试文件、1 份原有修复说明。没有将最新 main 的其他改动一起部署。

| 版本证据 | 值 |
| --- | --- |
| 当前 Replit Live | `5cae3434`；Publishing 显示 Live，当前 deploy logs 的五阶段均成功 |
| Replit 发布源提交 | `7ebf8e7f611de9eba5dbefb4196090f6eda6b531` |
| Replit 发布后提交 | `26c9450`，Published your App |
| 应用完整树 | `675d4c8bcaee22c56ee1c940acec00fd08d9a6b4`（`backend/app` Git tree） |
| 绑定检查 | Replit 发布前后 `backend/app`、`backend/requirements.lock`、`backend/pyproject.toml` 与固定应用源无差异；工作区干净 |
| 部署配置 | `.replit` 与 `b156e6a` 无差异；沿用原 build/run、端口、区域及权限 |
| API | `https://kiraorder-api.replit.app/api/v1` |
| 可回退基线 | Replit `6d6bafd8`，应用 `99ee169`；回退会移除本次 UOM guard 修复，不作为当前建议动作 |

证据边界：这是 Replit Git/editor 的完整应用树比对、平台发布记录和线上行为复验的联合绑定；未直接读取已发布容器文件系统。构建启动期间出现过瞬时 healthcheck 500，之后 Uvicorn 启动完成、发布成功，发布后 `/readyz` 与下述检查通过。根路径 `/` 的 404 不代替 `/readyz` 的健康判定。

## 针对性复验

- 本地固定发布源：独立 loopback PostgreSQL，`test_d02_uom_blocking`、`test_resolver_missing_uom`、`test_uom_save_approve`、B03 两组回归和 `test_uom_pack_disambiguation` 合计 **67 passed**；测试后 PostgreSQL 正常停止。Ruff 和 diff 检查通过。
- 发布前线上只读检查：18 个 GET，**58/58 PASS**。
- 发布后线上 guard：唯一合成草稿 `DRF_BFADF855DB5A48B2947ECF5C22D8D4C2`，批次 `pr91-live-ab61d5f06c40`，**16/16 PASS**，完成于 2026-10-31 14:44:20 UTC+8。解析以 `FALLBACK` 返回 `sku_id=null`、`uom=null`、`MISSING_UOM` 阻断；手工选定 SKU 而不填单位仍阻断。普通批准和 `confirmed_items` 绕过尝试均返回 400 / `DISAMBIGUATION_UNRESOLVED`，版本不变。合成草稿通过正常 discard 接口撤销。
- 发布后线上只读检查：18 个 GET，**58/58 PASS**，完成于 2026-10-31 14:44:43 UTC+8；六个既有角色会话、T1/T2 目录、仓库角色拒绝、跨租户伪造被忽略、匿名/无效令牌拒绝均通过。
- 合成复验无成功批准、无 DO；T1/T2 的库存、别名、产品、UOM 别名和价格前后摘要一致。未直接写数据库、未 seed/migrate/reset、未新增或轮换会话、未改任何访问权限。

本次只证明后端 guard，不将它记为模型 UOM 修复或准确率重跑。原有 UOM 24/31、七项模型质量缺口及 #92/#93 的边界均不因本记录改变。

公开脱敏摘要及截图见 [`evidence/deployment-verification/2026-10-31-pr91/`](../../evidence/deployment-verification/2026-10-31-pr91/)。原始 HTTP、私密数据库摘要与账号原始聊天摘录只保存在本地交接包。

## 账号／豁免：用户确认无需添加，收尾完成

已追溯到 2026-10-25 He 的原始队内确认，以及据此更新清单的提交 `5db9552`。这证明现有“无需添加”记录的来源；该原始消息没有附主办方书面豁免、指定账号或权限要求，不能由此声称官方要求已经闭环。

2026-10-31，用户进一步明确确认此项不需要、无需再询问主办方。因此撤销此前等待 Zhou 对外确认的待办；He、Zhan、Zhou 不再需要为本项追加查证、询问或等待回执。本地未发送的询问稿已标记撤销。

状态更新为 **CLOSED_USER_CONFIRMED_NOT_REQUIRED**，依据为用户本次确认，不宣称取得了主办方书面豁免。没有新增账号或修改权限。本次两项收尾均无剩余待办；部署仍为 `5cae3434`，其他已结项任务的状态与历史证据保持原样，B05 实测仍未启动。
