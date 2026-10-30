# C08 仓库权限：API 层 PASS（Zhou 已签 SIGNED_OFF；已入库）

执行人：He；API 矩阵：2026-10-30 16:28（UTC+8）；浏览器证据：2026-10-30 16:04（UTC+8）；Zhou 复签：2026-10-30 16:40（UTC+8）；合并：2026-10-30 `c69f4ba`（UTC+8）；环境：生产 API `https://kiraorder-api.replit.app/api/v1`。
对象：C01 已出的 DO `DO_20261029_453C4BC2`（Restoran Ali，面粉 4 bag + 食用油 2 btl，`approved_at 2026-10-29T07:16:58Z`，草稿 `DRF_39D4D66CACC440A594B1C1AEBEF151B9`）。

**结论：API 层 41/41 通过，字段扫描与投影对比均通过，无 P0；浏览器两张已补齐；`response_sha256` 口径已按 Zhou 的选项 1 修正并通过 v2 复核（v2 57/57、v4 58/58，多出的是 `reviews/03` 本身；41/41 response 文件哈希与 matrix 一致）。Zhou 已复签 `SIGNED_OFF`（16:40），PR #75 已 squash 合入 `c69f4ba1498c73bc1d1700c4723b5c8e39b171cc`。合并后只更新了 `repo_status=MERGED` 等元数据，证据文件未变。**

## 1. 本次补的是什么

C08 的任务口径：只读、不写库，直接用 C01 的 DO，重点找"多个接口越权、字段泄漏"的 P0，是 Gate A 要求项。

C01 的验收边界原文是：

> 仓库写接口禁止的口径采用页面无入口、`permissions=[]` 及无写请求的只读证明；**没有新增写接口 403 实测**。

所以本包不重复 C01 已经证明的拣货视图，而是补三块：

1. 全部 16 条契约路由 + 2 条契约外实现路由对 WAREHOUSE 的拒绝矩阵（读 + 写）；
2. 同一 DO 的 CLERK 全量投影 vs WAREHOUSE 裁剪投影的逐字段对比；
3. 跨租户、查询参数提权、HTTP 方法面。

### Zhou 2026-10-30 口径

- 允许引用 C01 同一 DO 的仓库页证据；因 C01 页面图不是 f8ff1d7 构建，浏览器补两张：当前 picking 页 + 403。
- 版本：前端 `f8ff1d7` / 后端 `555f0fa`；屏上要可见 **Ah Kow / Warehouse**。
- 403 必须是 `GET /api/v1/delivery-orders/DO_20261029_453C4BC2`，**不能用 audit-detail 代替**；要能看到 `FORBIDDEN_ACTION` 响应体，或完整 URL + 403，只截状态码不算。
- **C01 页面证据不是 f8ff1d7 构建**：C01 会话是 2026-10-29 17:13–17:16（UTC+8），Pages 部署 f8ff1d7 在 19:51，所以按 Zhou 第 7 条补了当前 picking 页截图。
- 两张截图已于 2026-10-30 16:04 补齐，见 [browser/](browser/)；入库前 API 层曾标“待入库”，16:40 Zhou 复签后才改 `SIGNED_OFF`，没有提前签全通过。

完整记录见 [reviews/01-Zhou-scope-2026-10-30.md](reviews/01-Zhou-scope-2026-10-30.md)，截图要求见 [browser/README.md](browser/README.md)。

## 2. 结果

| 类别 | 通过 | 覆盖内容 |
|---|---|---|
| identity | 5/5 | 三角色 `/me`；无令牌/坏令牌 401 |
| read | 13/13 | `/customers`、drafts、approvals、activity、audit-detail、DO 详情全部 403；仓库视图 200；不存在 DO 404；无批量列举路由 |
| write | 7/7 | parse-draft、save-lines、approve、decide、discard、clarification-copied、ai/wake 全部 403 |
| cross_role | 2/2 | CLERK/OWNER 打 `/warehouse/...` 均 403 |
| tenant | 4/4 | T2 令牌查 T1 DO 404；`?tenant_id=T1` 不生效；`X-Tenant-Id: T1` 不生效；T1 令牌带 `?tenant_id=T2` 仍返回本租户对象 |
| override | 2/2 | `/me?role=OWNER&user_id=USR_T1_OWNER&tenant_id=T2` 与 `X-Role/X-User-Id/X-Tenant-Id` 均不改变 T1/WAREHOUSE 身份 |
| method | 6/6 | 读路由上的 DELETE/POST/PATCH/PUT/GET 误用一律 405，无方法绕过 |
| auth | 2/2 | 未认证访问仓库视图/客户列表 401 + `WWW-Authenticate: Bearer` |

关键证据：

- **投影对比**（[projection-diff.json](projection-diff.json)）：同一 DO，CLERK 投影 14 个顶层字段，WAREHOUSE 只有 4 个（`do_number/customer_name/items/approved_at`）；CLERK 行 10 个字段，WAREHOUSE item 只有 5 个。被移除的 11 个顶层字段包括 `final_total_rm`、`reply_draft`、`tier_unit_price` 所在的 `lines`、`draft_id` 等；行级移除 `applied_unit_price`、`subtotal_rm`、`tier_unit_price`、`override_reason`、`line_id`。`final_total_rm=70.80` 的值在整个仓库响应原文里不存在。
- **字段扫描**（[field-scan.json](field-scan.json)）：对 WAREHOUSE 的全部 2xx 响应递归扫描键名与字符串值，命中 0 个价格/电话/金额/Tier/原消息类字段。
- **写端点**（`write.*`）：全部使用**契约合法 body + 不存在 ID**，因此即使某处漏了角色判断，最多走到 404，不可能写库；实际全部 403，且 `details={}` 不泄漏对象是否存在。
- **`/ai/status`**：WAREHOUSE 返回 200，但 OpenAPI 对该路径只声明 200/401，响应只有 `state/available_modes/fallback_available/last_checked_at/message`，不含业务字段。**这是契约允许的，不是越权，不要当 P0 报。**
- **`/ai/wake`**：403，未触发任何预热任务（守卫在 `wake()` 之前）。
- **无批量列举**：`GET /warehouse/delivery-orders` 返回 404，WAREHOUSE 只能按 DO 号单查，不能枚举。
- 所有 200/401/403 响应均带 `X-Request-ID` 与 `Cache-Control: no-store`。

逐条结果见 [matrix.md](matrix.md) / [matrix.json](matrix.json)，原始响应在 [responses/](responses/)，请求级摘要（已脱敏 Authorization）在 [api-requests.json](api-requests.json)。

## 3. 方法：为什么这个结果可信

1. **不写库**：脚本只用 HTTP，不连数据库、不跑迁移、不 reset。写形态请求全部指向不存在的 `DRF_C08_PROBE` / `APR_C08_PROBE` / `CUS_C08_PROBE`，body 按 schema 构造。
2. **避开 422 假象**：FastAPI 先校验 body、后进 handler，角色判断在 handler 里。用空 body 测会得到 422 而不是 403，看起来"没拦住"，其实没走到权限判断。本包所有写端点都用合法 body；这一点也是 C08 最容易做错的地方。
3. **令牌不落盘**：令牌从本地私有 `demo_tokens.json` 读入，输出只记录角色标签与 `/me` 身份，不写 `Authorization`，不写令牌字符串（已扫描确认）。
4. **字节级存证**：`responses/*.json` 保存的是 HTTP 原始响应字节（不 pretty-print、不加换行），因此文件的 SHA-256 等于 `matrix.json` 的 `response_sha256`，文件大小等于 `response_bytes`；脚本在每次运行末尾会逐条断言这一点。本目录带 [.gitattributes](.gitattributes)（`* -text`，与 C01 同口径），避免仓库根的 `* text=auto` 把 CRLF 归一化后哈希对不上；提交后 git blob 与工作区字节一致。

### 浏览器证据（已补，2026-10-30 16:04）

| 文件 | 校验 |
|---|---|
| [c08_01_picking_current.png](browser/c08_01_picking_current.png) | f8ff1d7 构建（页脚 `v1.4.0`）；顶栏 **Ah Kow / Warehouse**；同一 DO 与拣货明细；无价格/电话/原消息 |
| [c08_02_forbidden_403.png](browser/c08_02_forbidden_403.png) | Console 完整 URL + 403 + `FORBIDDEN_ACTION` 响应体；无令牌 |
| [source/](browser/source/) | 转换前的原始 JPEG 字节，源文件 SHA256 记在 `acceptance.json` |

说明：403 图与 picking 图是同一会话、同一 DO；身份和构建版本由 picking 图证明。两图均未出现 `Authorization` 或令牌明文。

### Zhou 独立复核与复签（2026-10-30）

| 轮次 | 结果 |
|---|---|
| v1（16:16） | API/浏览器通过；证据包因 `response_sha256` 与 response 文件字节不一致暂缓 |
| 修正 | 按选项 1：responses 改为原始响应字节；41/41 文件哈希与 matrix 一致（`read.warehouse_do` 均 `ae663539…`，347 B） |
| v2（16:40） | **复签通过：`SIGNED_OFF`**；v2 57/57、v4 58/58（多 `reviews/03` 本身）；41/41 response 哈希与大小一致、浏览器两张不变 |
| 记录 | [v1 复核](reviews/02-Zhou-review-2026-10-30.md) · [v2 复签](reviews/03-Zhou-signoff-2026-10-30.md) |

Zhou 已复签 `SIGNED_OFF`；PR #75 已 squash 合入 `c69f4ba`。合并后只把 `repo_status` 元数据改为 `MERGED`，证据文件未改。

## 4. 边界与入库记录

- **入库**：PR #75 squash merged at `c69f4ba1498c73bc1d1700c4723b5c8e39b171cc`；合并后仅把 `repo_status` 改为 `MERGED`、清空 `open_items`，41 条 response、matrix、浏览器图均未改。17:47 的 `not_covered`/README 修正与本次合并后更新都只改元数据，Zhou 已确认不需要重开复核。

- **部署版本不可见**：API 未暴露部署 commit。前端版本由 `gh-pages` 提交 `12ff95f`（“Deploy B01 frontend from f8ff1d7”）证明；后端 `0a255df` 未改 `backend/app/`，最后一个改 `backend/app/` 的是 `555f0fa`。本包结论对应 2026-10-30 16:28 的生产响应。
- **T2 无已批准 DO**：T2 的活动流为空，当前演示库没有 T2 DO，所以反向跨租户用“T1 真实 DO + T2 令牌”验证 404；要在 T2 侧造 DO 属于写入，超出 C08 只读范围。
- **独立复核**：Zhou 2026-10-30 16:40 复签 `SIGNED_OFF`（`independent_review_status=PASSED`）；签名记录见 [reviews/03-Zhou-signoff-2026-10-30.md](reviews/03-Zhou-signoff-2026-10-30.md)。
- 不在 C08 范围：CLERK/OWNER 之间的 IDOR、前端 Local Demo、T2 业务流程。

## 5. 复现

```powershell
py -3.13 c08_warehouse_audit.py `
  --tokens <私有 demo_tokens.json 路径> `
  --out evidence
```

- 仅需 Python 3.13 标准库与公网访问；默认打生产，`--base-url` 可切本地。
- `--skip-wake` 可跳过 `POST /ai/wake`（默认包含，403 时不会产生任务）。
- 期望输出：`41/41 passed, field_scan=True, projection_diff=True, status=PASS_API_LAYER`，退出码 0。
- 令牌文件格式同本地 `99_敏感资料_勿提交/demo_tokens.json`：`{"T1": {"USR_T1_CLERK": ..., ...}, "T2": {...}}`。

## 6. 文件清单

| 文件 | 说明 |
|---|---|
| [acceptance.json](acceptance.json) | 机器可读结论与边界 |
| [matrix.json](matrix.json) / [matrix.md](matrix.md) | 41 条用例的期望/实际/失败原因 |
| [environment.json](environment.json) | 时间、base URL、对象、三角色身份（无令牌） |
| [projection-diff.json](projection-diff.json) | CLERK vs WAREHOUSE 字段差集 |
| [field-scan.json](field-scan.json) | 禁用键/值扫描结果 |
| [api-requests.json](api-requests.json) | 请求级摘要（Authorization 仅记角色） |
| [responses/](responses/) | 每条用例的原始响应 JSON |
| [browser/README.md](browser/README.md) | 截图要求与已补记录 |
| [browser/c08_01_picking_current.png](browser/c08_01_picking_current.png) | 当前构建 picking 页（含 Ah Kow / Warehouse 身份） |
| [browser/c08_02_forbidden_403.png](browser/c08_02_forbidden_403.png) | 403 + `FORBIDDEN_ACTION` 响应体 |
| [browser/source/](browser/source/) | 原始 JPEG 源文件 |
| [reviews/01-Zhou-scope-2026-10-30.md](reviews/01-Zhou-scope-2026-10-30.md) | Zhou 口径与版本核对记录 |
| [reviews/02-Zhou-review-2026-10-30.md](reviews/02-Zhou-review-2026-10-30.md) | Zhou v1 复核（暂缓签字与修正要求） |
| [reviews/03-Zhou-signoff-2026-10-30.md](reviews/03-Zhou-signoff-2026-10-30.md) | Zhou v2 复签（SIGNED_OFF） |
| [SHA256.txt](SHA256.txt) | 本目录文件哈希（不自我哈希） |
| [.gitattributes](.gitattributes) | `* -text`，保证提交后字节不被归一化 |

脚本：本工作目录上一级 [c08_warehouse_audit.py](../c08_warehouse_audit.py)。入库建议：脚本放 `scripts/c08_warehouse_audit.py`，本目录整体放 `evidence/e2e/c08/2026-10-30/`（此时脚本引用改为 `scripts/c08_warehouse_audit.py`）。

## 7. 观察与建议（非 C08 缺陷）

1. **422 先于 403**：这是 FastAPI 的校验顺序。若希望"已认证但角色不符"始终稳定返回 403，可把角色检查提前到路由依赖层；当前不影响安全，只是测试口径要注意（P3）。
2. **`/ai/status` 对 WAREHOUSE 开放**：契约如此，且无业务字段；Gate A 口径里应写明，避免复核人误报。
3. **契约外路由**：`/orders/drafts/{id}/discard` 与 `/clarification-copied` 已在实现中，但不在 Gate 0 OpenAPI 的路径集合里；两者对 WAREHOUSE 均为 403，契约完整性问题另登记，不算 C08 权限缺陷。
4. **C01 的 DO 依赖**：本包所有读证据都指向该 DO。若演示库被 `reset_demo` 重建，DO 会消失，本包仍可作为历史证据，但无法复跑；API 与浏览器证据均已在 2026-10-30 完成。
5. **`picking_note` 是仓库可见的自由文本**：契约允许它出现在仓库视图里，本次该字段为 `null`。如果业务上允许跟单员把价格写进备注，就会形成一条绕过字段裁剪的旁路；建议在规则/前端层限制其内容（P3，不属于本次 API 权限缺陷）。

## 8. 结论

- Zhou 2026-10-30 16:40 复签 `SIGNED_OFF`；API、浏览器、证据包全部通过，41/41 response 文件哈希与 matrix 一致。
- 剩余：无；PR #75 已合入 `c69f4ba1498c73bc1d1700c4723b5c8e39b171cc`，C08 证据、复核、入库均已闭环。
- 状态：`status=PASS_API_LAYER`、`overall_status=SIGNED_OFF`、`independent_review_status=PASSED`、`repo_status=MERGED`、`merge_commit=c69f4ba1498c73bc1d1700c4723b5c8e39b171cc`。
- Gate A：时间由 Zhou 确认后由 Zhan 同步；C08 材料已入库，等 Zhan 挂索引。
- 本次 41 条请求累计约 14.3 秒（最长 5.3 秒），远低于任务表给的 20 分钟，时间可以留给 Gate A 的其他项。
