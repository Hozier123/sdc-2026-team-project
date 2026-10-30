# B05 独立本机环境交付

用途：在独立环境中准备、复核和复现隔离／复位边界。**创建环境与合成技术验收不要求真实受试者。本轮实际独立受试继续为 NOT_RUN，不计受试／计时分母。**

工具只创建新的环回 PostgreSQL、模板、T1 库和 API；不接受现有 DATABASE_URL、管理员 DSN、任意目标库、远程 API 或 reset hook 参数。现有演示环境的 C04／C08 证据及其“不 reset”约束继续保留。

## 依赖与创建

在本仓库使用 Python 3.13、backend/requirements.lock 中的依赖，以及 PostgreSQL 17 的 initdb、pg_ctl、postgres 程序。当前交付在 Windows 本机验收；其他平台需在各自环境验证，不根据源码路径分支自动宣称已验收。不需要预先配置 PostgreSQL 服务或人工提供管理员连接串。

在 backend 目录运行（把示例 PG 路径替换为本机实际路径）：

```powershell
python -m pip install -c requirements.lock -e '.[test]'
python -m tools.b05_environment create --pg-bin 'C:\PostgreSQL\17\bin'
python -m tools.b05_environment start
python -m tools.b05_environment check
```

每次 create 生成新的 `.tmp/b05-environments/b05-env-<随机ID>/`；不覆盖已有实例。两侧拥有不同 PostgreSQL cluster／system_identifier、数据库、API 端口、管理员密码和三角色令牌。工具自动迁移、加载哈希校验过的 T1 种子并建立新模板；创建后 PG 停止，start 才启动 API／PG。

create 输出 state_file。省略 `--state` 使用此 checkout 最新创建的环境；需要固定目标时使用：

```powershell
python -m tools.b05_environment --state '完整路径\environment.json' status
python -m tools.b05_environment --state '完整路径\environment.json' start
```

environment-public.json 和 HANDOFF.md 给出本机实际库名、API／前端地址、绑定版本摘要及操作命令。角色令牌和管理员密码仅存 credentials.private.json／同目录私密文件，整个运行目录受 `.tmp/` 忽略规则保护。交接可分享脱敏清单；不要把私密运行目录提交 Git 或当作跨机器数据库快照。其他机器使用同一代码重新 create。

## 页面与角色

在 frontend 目录运行 `npm ci`、`npm run build`，然后在 backend 目录运行：

```powershell
python -m tools.b05_environment frontend
```

工具使用该环境分配的新端口启动本 checkout 的静态预览，已有站点不重新发布、不改配置。打开 HANDOFF.md 中的 frontend_url，将页面 API connection 设为该环境的 firstuse API。OWNER 与 CLERK 使用各自私密令牌和不同浏览器上下文；仅开同源标签页不作为会话隔离证明。

API 的 `/__b05_identity` 返回 environment_id、side、数据库身份、PID／instance 与 OFFLINE_FALLBACK 策略。每个 API 独立实例化 provider，别名缓存在各自数据库，无共享 Redis；移除继承的远程 AI 配置，不调用 RunPod。check 验证两侧身份、三角色、跨侧令牌拒绝和专用前端 CORS。

## 首用侧复位

```powershell
python -m tools.b05_environment reset-firstuse
python -m tools.b05_environment reset-firstuse --apply
```

第一条仅 dry-run 并保存快照。第二条要求两侧 API 已启动、源码与环境绑定匹配，再先留十二类业务表与检查点证据，仅停止首用 API，调用已有 reset_demo 的受控切换，再仅重启首用 API。保护 API／PG 保持运行，其表、检查点文件和 PID／instance 必须不变；首用侧恢复创建时的初态。旧库按已有工具语义保留为备份，不自动清理。

目标库和模板名由 environment_id 派生并与 owner 标记锁定；连接通过本环境生成的私密管理员凭据建立。数据库 system_identifier 和实际 data_directory 再核验。`--target`、`--admin-url`、`--side protected` 等外部复位目标参数不被接受。复位失败保留现场及证据，不自动重试不确定写入。

该入口仅用于合成环境验收或已结束试次之间的运维；不用于进行中的试次。现有演示库无需解除“不 reset”限制，也不在本工具的可接受目标范围内。

## 一次性合成技术验收

在新 create 的干净环境运行：

```powershell
python -m tools.verify_b05_environment
```

脚本自动产生受保护的合成待批／别名／检查点，在首用侧用 HTTP 生成合成 DO，执行 dry-run 与实际首用复位，逐项核保护侧十二类表与检查点不变，再续接原保护侧检查点。保存真实原始响应、快照与 reset 日志。此过程没有受试者、研究计时、正式 TEST32 或当前演示库访问。使用过的夹具不自动重放；重新验收须新 create。

结果在该环境的 technical-acceptance.json，私密原件保留在 technical-verification／reset-evidence。成功只证明该代码／数据／本机环境的技术验收；不代替独立复核、真实受试或其他部署验收。

## 停止与历史状态

```powershell
python -m tools.b05_environment stop
```

只停止本环境标记且核实归属的 API、前端与 PG，保留数据、备份和全部证据。操作锁防止本工具并发启动／复位；遇到遗留锁须核实原操作状态，不自动跳过。

历史本轮范围决定仍见 [B05 收口记录](b05-closeout.md)。此次补交独立环境能力不回填真实受试结果；原封存包不改，真实受试继续 NOT_RUN。
