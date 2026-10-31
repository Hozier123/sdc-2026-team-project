# B06 运行说明与访问交接

核对日期：2026-10-31，UTC+8。适用范围：前后端版本、启动顺序、真实入口、角色会话取得方式、回滚基线、负责人。本说明已完成线上只读核对；不重新判定已结项任务，不替代业务回归或正式 TEST32。

## 1. 当前运行版本

| 对象 | 已核对版本 | 依据与含义 |
| --- | --- | --- |
| 本次文档采用的 main 快照 | `15f6138926d2090c00f405f419cf41fad93195cf` | 本次核对起点；不是线上部署号 |
| 线上前端 | `v1.5.1`；源提交 `befac4c33e723559f1f9a4d0ef05b66f0ba4f8ef` | Pages `release.json`、页面显示与资源实测 |
| 前端应用发布提交 | gh-pages `adc3cc2e27eb79e8b1e1235de886a6de997bcb47` | 实际发布 v1.5.1 应用资源的提交 |
| Pages 完整恢复快照 | gh-pages `ae5a0d7c7dc4cc663c96fee39fbf14dcb62e0fab` | 含应用、LF 哈希修订和 B02 结项材料；当前线上文件逐字节匹配 |
| 当前后端 Live | Replit `6d6bafd8` | 本次查看当前发布的 deploy logs，显示 published，五阶段 success；发布页显示 Live |
| 后端应用源码基线 | `99ee169ef01527587312c82beaba41858f47b9e4`，PR #104 | B03 已归档源码绑定；Replit 源提交 `9e9ae24`，发布后提交 `b156e6a` |
| 后端回退基线 | Replit `3e568d26`；应用 `f767e7b738613efe7872549757cdc00b3c64be6c`，PR #89 | 当前发布历史仍可见；B02 已验的上一个后端版本 |
| 数据库 | Neon PostgreSQL 17；沿用现有 T1/T2 | 不在日常启动或本次交接中迁移、重灌或 reset |
| AI 配置 | `runpod_adapter`；`Qwen/Qwen2.5-7B-Instruct-AWQ`；`LLM_TIMEOUT_S=4.1` | 本次只读查看 Replit `.replit`；配置存在不代表当前模型 READY |

**版本口径：** Pages `release.json` 的 `backend_deployment=3e568d26` 是 B02 发布时的后端绑定，不能用它覆盖当前后端 `6d6bafd8`。C11 环境记录里的前端 `f8ff1d7` / gh-pages `12ff95f`、后端 `9cff61ed` / `9dfee33` 也保留为其历史证据，不改写为当前版本。

本次 main 的 `backend/app` 与 `99ee169` 不相同，`frontend` 与 Pages 源 `befac4c3` 也不相同。后续 main 已含其他应用改动，不能直接声称已全部上线，也不能为了文档交接把最新 main 自动部署。当前源码绑定沿用 B03 的 Git/editor 比对和发布记录，本次没有逐字节回读已发布服务器文件系统。

来源：[B03 发布与绑定](../../evidence/b03/2026-10-31/release.json)、[B02 线上结项记录](https://hozier123.github.io/sdc-2026-team-project/b02-closeout.json)、[C11 结项](c11-closeout.md)、[本次版本观察](../../evidence/b06/2026-10-31/source-observations.json)。

## 2. 真实入口与最短操作

| 用途 | 入口 | 操作 |
| --- | --- | --- |
| 正式前端 | <https://hozier123.github.io/sdc-2026-team-project/> | 首页介绍后进入工作台 |
| 直接进入工作台 | <https://hozier123.github.io/sdc-2026-team-project/#/workspace> | 默认是 LOCAL DEMO；不会自动连接生产 API |
| 商品目录 | <https://hozier123.github.io/sdc-2026-team-project/#/catalog> | 真实连接后的 CLERK / OWNER 可访问；WAREHOUSE 403 为预期 |
| 真实 API base | `https://kiraorder-api.replit.app/api/v1` | 供 Connect API 使用；不是前端网页 |
| 数据库就绪探针 | <https://kiraorder-api.replit.app/readyz> | 预期 200 / `status=ready`；不证明模型或整单业务就绪 |
| 当前后端发布控制台 | <https://replit.com/@dsc2509046/kiraorder-api> | He 使用现有授权账号；Publishing / deploy logs 查看版本 |
| 历史前端 | <https://kiraorder-web.replit.app> | 旧 UI，运行交接统一使用上面的 Pages |

真实会话操作：打开 Pages 工作台 → 左侧 **Connect API** → **API base URL** 填上述完整 `/api/v1` 地址 → **Session token** 输入私下取得的对应角色令牌 → **Connect API**。先核 `/me` 返回的租户、用户、角色，再操作合成业务数据。本次已检查线上连接对话框的字段、默认 API 地址与内存会话提示。

切换角色或租户必须重新连接对应会话；Local Demo 的角色切换不能获得真实 API 权限。刷新后需要重连；退出可用连接对话框的 **Return to demo**。CLERK / OWNER 连接后页面可能自动触发 AI 预热，安排真实浏览器演示前应先与 Xiong 确认资源窗口；本次没有输入令牌连接浏览器，也没有触发预热。

**C11 结项后的样例状态：** 生产 `CUS_ALI` + `Milo 2 bag` 已写入 CUSTOMER 记忆，现在同句会走 `ALIAS_ONLY`，不能再承诺出现原来的 LLM 候选。需要展示候选时使用 `Milo 3 bag` 或另一个事先核过的客户，并在实际演示时检查返回模式。现有别名没有撤销接口，不为重复演示删除别名或 reset 数据。无候选、零行在已发布页面仍按 C11 的限制说明，不把 B03 后端能力当成 F03 页面已上线。

## 3. 启动顺序

### 已部署环境：日常演示与恢复

1. **Zhou / Zhan 确定演示租户、样例和实际访问时段。** 默认对外入口为 Local Demo；真实 API 采用预约或现场团队驱动，不能只凭本说明承诺全天候模型服务。
2. **He 确认现有 Neon 与 Replit。** 沿用原 Secrets、端口和数据库；GET `/readyz` 为 200，再检查当前 Live 部署号。已发布环境无需重新运行 migration 或 seed。公开 `/healthz` 是已知边缘保留路径，不把其 404 当成业务故障。
3. **He 核身份和 CORS。** 本机执行第 7 节只读检查，六个 `/me` 均应返回 200 和对应 T1/T2、CLERK/OWNER/WAREHOUSE。页面来源是 `https://hozier123.github.io`，不含项目路径。
4. **Xiong 准备 AI，He / Ye 核实际模式。** 需要真实 LLM 时在约定资源窗口预热，检查 AI 状态并通过计划内的最小推理确认。`READY`、`WARMING`、`DEGRADED`、`OFFLINE` 照实显示；解析响应的 `ai_mode` 逐次实填，不能以 `/readyz=200` 代替。降级时仍按实际 FALLBACK / ALIAS_ONLY / MIXED 说明。
5. **Ye 打开 Pages 并连接相应角色。** 核浏览器显示的租户/角色，再由操作者执行约定样例。老板会话与仓库会话单独保管；不要靠同一浏览器切 demo role 演示真实鉴权。
6. **Zhan 记录交接与服务结束。** 记录前后端版本、样例、实际模式、时间、异常 request_id、支持人。He 负责会话收回或失效处理；Xiong 按已约定资源计划收尾。本说明没有新增全天候值班承诺或自动停机任务。

### 新建本机副本：与生产分开

Python 3.13、Node.js 22、PostgreSQL 17。先使用完整仓库安装锁定依赖，再创建隔离数据库、迁移和加载经哈希核验的合成种子，之后启动 API，最后启动前端。数据库 URL 和令牌不进入命令记录或 VITE 变量。

```powershell
# 仓库根目录；DATABASE_URL 只配置到本机新建的私密 .env。
py -3.13 -m venv backend/.venv
backend/.venv/Scripts/python -m pip install -c backend/requirements.lock -e './backend[test]'

# 仅对新建隔离数据库执行，不能指向现有 Neon 演示库。
backend/.venv/Scripts/python -m app.migrations
# 按 backend/README.md 的 seed loader 使用真实 seed version/hash/计数。
# seed 完成后：
backend/.venv/Scripts/python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

另开终端在 `frontend` 运行 `npm ci`、`npm run dev`，打开终端显示的地址，Connect API 指向 `http://127.0.0.1:8000/api/v1`。保留完整仓库结构，不能把 backend wheel 当成独立包含 Gate 0 的部署包。

需要可复现隔离/复位环境时优先使用已交付的 [B05 环境工具](b05-environment.md)，由它新建 PG/凭据/端口并输出 `HANDOFF.md`；只使用该环境自己的会话。B05 本机端口与令牌不作为生产入口。C04 / C08 已有业务对象和检查点继续保留，不 reset。

Replit 当前实际命令如下，发布恢复时保留，不为 B06 修改：

```text
build: cd backend && python3.13 -I -m venv .venv313 && PIP_CONFIG_FILE=/dev/null .venv313/bin/python -m pip install -c requirements.lock -e '.[test]'
run:   cd backend && .venv313/bin/python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
port:  local 8000 -> external 80; autoscale
```

前端重新构建时须保留 `/sdc-2026-team-project/` base：`npm run build -- --base=/sdc-2026-team-project/`。`VITE_API_BASE_URL` 只放公开 API 地址，**所有 VITE 变量都会进入构建产物，不能放角色令牌或模型 key**。B06 没有重新发布前端或后端。

## 4. 角色会话取得与保管

| 租户 | 角色 | 服务端用户 | 私密取得方式 | 本次实测 |
| --- | --- | --- | --- | --- |
| T1 | CLERK | `USR_T1_CLERK` | He 私下提供对应合成角色会话 | `/me` 200；目录 40 项 |
| T1 | OWNER | `USR_T1_OWNER` | He 保管；按约定单独交给指定操作者 | `/me` 200；目录 40 项 |
| T1 | WAREHOUSE | `USR_T1_WAREHOUSE` | He 私下提供对应仓库会话 | `/me` 200；目录 403 |
| T2 | CLERK | `USR_T2_CLERK` | He 私下提供对应合成角色会话 | `/me` 200；目录 16 项 |
| T2 | OWNER | `USR_T2_OWNER` | He 保管；按约定单独交给指定操作者 | `/me` 200；目录 16 项 |
| T2 | WAREHOUSE | `USR_T2_WAREHOUSE` | He 私下提供对应仓库会话 | `/me` 200；目录 403 |

评委需要操作真实 API 时：通过现有比赛团队联系渠道联系队长 Zhou，由 He 按实际用途提供租户、角色、私密会话、约定访问时段和支持联系人。默认团队驱动；需要评委交互时按约定交指定角色，不公开 OWNER 令牌。不在公开 issue、README、URL、PPT、浏览器持久存储或构建文件中传会话。

现有鉴权使用 `SHA-256(token)` 对照启用的用户记录，身份/租户来自服务端；没有自动一次性 TTL 的承诺。到期处理由 He 负责：先结束受影响角色的演示窗口，再对明确指定的用户停用或轮换数据库中的会话 hash，验证旧令牌 401、新令牌 `/me` 正确，然后私下更新指定接收者。该操作影响共用该角色会话的人，须协调已有使用者；**不修改冻结 seed SQL / manifest / TEST32 哈希**。本次没有轮换、停用或重新生成任何会话。

缺失、错误或停用会话应 401 `INVALID_TOKEN`；权限不足应 403。令牌只能私下重新取得，不能从公开种子 hash 反推。浏览器退出连接只清除当前页会话，并不撤销服务端令牌。

## 5. 回滚基线与执行方法

| 组件 | 恢复目标 | 负责人 | 恢复后的影响 |
| --- | --- | --- | --- |
| Pages | 完整 gh-pages 快照 `ae5a0d7c7dc4cc663c96fee39fbf14dcb62e0fab`，v1.5.1 | Ye；He 协助访问 | 恢复本次实测的静态文件，保留 B02 目录 |
| 后端上一版 | Replit `3e568d26`；GitHub 应用 `f767e7b738613efe7872549757cdc00b3c64be6c` | He | 回到 B02 已验后端；B03 新增人工恢复/价格重绑定不再作为可用承诺 |
| 后端当前已验源码恢复点 | Replit `6d6bafd8`；应用 `99ee169ef01527587312c82beaba41858f47b9e4` | He | 后续坏版本上线时可恢复到本次登记的 B03 基线 |
| Neon 数据 | 沿用当前数据库；不随应用回滚 | He；Zhou 核数据 | 应用回滚不撤销库存/批准/别名；不借恢复重置 C04/C08 |
| AI 配置 | 原 provider/model/timeout；私密 key 保留原位置 | Xiong；He 核部署 | 不随 Git 回滚假定 GPU 或凭据恢复；需要另核实际模式 |

发生版本回归时，由支持人先暂停新的写入和演示，记录故障版本、时间及 request_id。保留当前证据，再恢复指定组件。**本次只核目标与操作说明，没有执行线上回滚或故障注入。**

Pages：在干净的新工作副本创建恢复提交，不 force-push，不回退 main。以下 PowerShell 从仓库根目录执行，恢复目录名须尚不存在：

```powershell
git fetch origin gh-pages
git worktree add -b codex/b06-pages-recovery ../b06-pages-recovery origin/gh-pages
git -C ../b06-pages-recovery restore --source=ae5a0d7c7dc4cc663c96fee39fbf14dcb62e0fab --staged --worktree -- .
git -C ../b06-pages-recovery diff --cached --stat
# 目标已是相同快照时没有 diff，无需提交/发布。
# 确认 diff 后：
git -C ../b06-pages-recovery commit -m "Restore verified B06 Pages v1.5.1 snapshot"
git -C ../b06-pages-recovery push origin HEAD:gh-pages
```

后端：He 在 Replit 发布历史先核 `3e568d26`（上一个后端）或 `6d6bafd8`（当前恢复点）。如果平台提供保留构建的恢复入口，选择明确的目标；本次未验证该入口实际执行。否则在干净的发布工作副本，从上表对应的 **GitHub 应用完整 SHA** 恢复 `backend/app`、`backend/requirements.lock`、`backend/pyproject.toml`，核对 diff 后使用现有 `.replit` 的 build/run 重新发布。不能将源码 hash 与 Replit 发布号混用；重新发布会生成新发布号，必须重新登记。保留原 `.replit`、Secrets、Neon、CORS 和端口，不执行 seed/migration/reset。

恢复后先验证 `/readyz`、六角色 `/me`、CORS 和 Pages 全部文件；再对受影响的保存/审批/库存分支复验。应用版本改变时，不把旧 B03/C07 签字直接移到新版本；记录恢复后承诺的功能边界。数据库事故另按备份恢复流程处置，不通过清空业务表伪造应用恢复成功。

## 6. 负责人、服务窗口与异常分工

| 工作 | 主负责人 | 协作/接收 |
| --- | --- | --- |
| B06 运行说明、后端发布/恢复、Secrets、六角色会话、Neon | He Minghao | Ye 核真实入口；Zhan 收技术事实 |
| Pages 源码/静态发布、前端回滚、浏览器连接与录屏 | Ye Lianghui | He 核 API/CORS；Zhan 收入口和操作步骤 |
| RunPod、模型预热、资源窗口与预算 | Xiong Peicheng | He 核实际 provider；Zhou 核样例 |
| 样例、租户数据、业务与证据复核、团队访问协调 | Zhou Jingxi | He / Ye 执行；Zhan 收复核结论 |
| 材料收录、评委/主办方渠道与实际访问时段记录 | Zhan Zhengrong | Zhou 确认对外事项；技术三人给事实 |

服务窗口采用“约定时段 + 现场支持人”方式：真实访问前由 Zhou / Zhan 记录实际起止时间，He / Ye 确认 API/角色/页面，Xiong 确认是否提供真实 LLM。没有约定窗口时评委仍可使用 Local Demo；本说明的通过不等于持续 GPU 可用或新增人员值班确认。本次未发送团队消息、发放评委会话或登记新的对外时段。

| 故障 | 第一处理人 | 当场动作 |
| --- | --- | --- |
| 页面空白、旧资源或 base 路径错误 | Ye | 核 release / 资源哈希，按 Pages 恢复点处理 |
| `/readyz` 非 200、5xx | He | 停止新业务写入，查当前发布及 DB；保留 request_id |
| 401 / 403 / 租户不符 | He | 重新核正确会话；不改角色绕过权限 |
| AI WARMING / DEGRADED / OFFLINE | Xiong + He | 核资源窗口；按实际降级模式演示，不伪报 LLM |
| 重复批准、库存或数据异常 | He + Zhou | 停止受影响流程并留证，按受影响版本复验 |

组委会指定 GitHub 账号或书面豁免、最终门户提交属于 Zhan / Zhou 对外事项。本次没有找到新的官方依据，不从“仓库公开”推断豁免，也不把运行说明完成写成官方提交完成；这些不改变本次六项运行交接的技术结果。

## 7. 只读复核与验收

在本仓库根目录运行，令牌文件由 He 私下提供；公开命令只写占位路径：

```powershell
git fetch origin gh-pages
py -3.13 scripts/b06_preflight.py --tokens-file '<private-role-token.json>' --output '<new-output-directory>/preflight.json'
```

工具仅发送 GET / OPTIONS：固定生产 API 的 `/readyz`、`/me`、目录与 CORS 预检，以及 Pages release/index/assets。拒绝跟随重定向，不把 Authorization、Cookie、原始个人资料或私密文件路径写进报告，不调用 parse、AI status/wake、批准、迁移或 reset。没有私密令牌时不能报告六角色通过。输出文件已存在时拒绝覆盖历史证据。

本次结果：**19/19 检查通过**；六角色身份全部正确；CLERK/OWNER 目录 T1=40、T2=16，WAREHOUSE 403；缺失/错误令牌 401；Pages CORS 通过；index 与全部受检构建资产和固定 gh-pages 快照逐字节一致。详见 [preflight.json](../../evidence/b06/2026-10-31/preflight.json) 的资产列表与 request_id。

本次未重跑完整业务 E2E、正式 TEST32、浏览器六角色业务操作或 LLM 推理；没有重开 B01–B05、C04/C06/C07/C08/C11 的既有结项。本机初版检查器读取错误码时误用了嵌套字段，修正为正式顶层 `error_code` 后重新通过；初次记录保留在本机 output，不能把检查器错误写成线上鉴权缺陷。

六项交付映射和限制见 [acceptance.json](../../evidence/b06/2026-10-31/acceptance.json)。这是本次运行说明交付与 He 侧验证，不冒充 Ye/Zhou/Zhan 的新增独立签字。
