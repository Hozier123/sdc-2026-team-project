# C08 仓库权限结项记录（2026-10-30）

## 1. 结论

**C08 已完成。** API 层 41/41、无 P0；浏览器两张证据通过；Zhou Jingxi 于 2026-10-30 16:40（UTC+8）复签 `SIGNED_OFF`；证据已通过 PR #75 合入 `main`。

| 字段 | 值 |
|---|---|
| `status` | `PASS_API_LAYER` |
| `overall_status` | `SIGNED_OFF` |
| `independent_review_status` | `PASSED` |
| `repo_status` | `MERGED` |
| 证据 PR | #75，merge `c69f4ba1498c73bc1d1700c4723b5c8e39b171cc` |
| 元数据 PR | #78，merge `d98658f261c17ebbd5943286e389fe9567843fc2` |
| 最终清单 | `170E92024B8D7ED38C34AD3CCC541E942DB6C722BA3AF371C3D2CD6E204165EC`（58 文件） |
| 离线包 | `C08_API_evidence_2026-10-30.zip`，1,913,528 B，`11D9D98F751D7D4A59A4EA9A19C43551D58BF001D97AE5FD93473E9F37C919DA`（传输件，未入库） |
| 索引号 | `ZR-20261030-19`（Zhan 核包后分配） |

**未决外部字段**（不影响 C08 结论）：

- **Gate A 时间**：由 Zhou 确认后 Zhan 同步；C08 材料已入库。
- **索引号**：`ZR-20261030-19`（Zhan 2026-10-30 核包后分配）。

## 2. 范围与对象

- 任务口径：Warehouse 只读权限矩阵，重点查多接口越权与字段泄漏；Gate A 要求项。
- 对象：C01 的 DO `DO_20261029_453C4BC2`（Restoran Ali，面粉 4 bag + 食用油 2 btl，草稿 `DRF_39D4D66CACC440A594B1C1AEBEF151B9`）。
- 环境：生产 API `https://kiraorder-api.replit.app/api/v1`。
- 版本：前端 `f8ff1d7`（gh-pages `12ff95f` 明确记录）、后端 `555f0fa`（`0a255df` 未改 `backend/app/`；API 不暴露 commit，属仓库证据推断）。
- 数据：T1/T2 合成演示数据；未写库、未 reset、未触发 AI 预热。

## 3. 结果

### API 矩阵

- 41/41 通过，0 失败；16 条契约路由 + 2 条契约外实现路由。
- `write.*` 7 条全部 403（parse-draft、save-lines、approve、decide、discard、clarification-copied、ai/wake）。
- tenant：T2 令牌查 T1 DO 404；`?tenant_id`、`X-Tenant-Id` 提权无效。
- override：`?role/user_id/tenant_id` 与 `X-Role/X-User-Id` 不改变身份。
- method：读路由上的 DELETE/POST/PATCH/PUT 误用 405。
- 无批量列举：`GET /warehouse/delivery-orders` 404。
- `/ai/status` 对 WAREHOUSE 200 是契约允许；`/ai/wake` 403，未触发任务。

### 字段与投影

- 同一 DO：CLERK 14 个顶层字段 → WAREHOUSE 4 个；行 10 个字段 → item 5 个。
- `final_total_rm=70.80` 不在仓库响应原文；`reply_draft`、`applied_unit_price`、`subtotal_rm`、`tier_unit_price` 等被裁掉。
- field-scan：0 命中（无价格/电话/金额/Tier/原消息类字段）。

### 字节口径

- `responses/*.json` 保存 HTTP 原始响应字节，不 pretty-print、不加换行。
- 41/41 文件 SHA-256 等于 `matrix.response_sha256`，文件大小等于 `response_bytes`；脚本每次运行末尾断言。
- 指定样例：`read.warehouse_do` `ae663539…9c47c7` / 347 B；`read.clerk_do_full` `ea3662ed…0574c0` / 1147 B；`write.approve` `87dea780…ec6dfe` / 93 B。

### 浏览器

- `c08_01_picking_current.png`：f8ff1d7 构建（页脚 v1.4.0）；顶栏 **Ah Kow / Warehouse**；同一 DO 与明细；无价格/电话/原消息。
- `c08_02_forbidden_403.png`：Console 完整 URL + 403 + `FORBIDDEN_ACTION` 响应体；无令牌。
- 原始 JPEG 保留在 `browser/source/`，源 SHA-256 记在 `acceptance.json`。

## 4. 签署与入库

- Zhou v1（16:16）：API/浏览器通过；指出 `response_sha256` 与 response 文件字节不一致，暂缓签字。
- 修正（16:28）：按选项 1 保存原始响应字节；41/41 文件哈希与 matrix 一致。
- Zhou v2（16:40）：**复签 `SIGNED_OFF`**（[reviews/03](../../evidence/e2e/c08/2026-10-30/reviews/03-Zhou-signoff-2026-10-30.md)）。
- 元数据修正（17:47）：`not_covered` 删除已补截图、README 状态改 `PASS_API_LAYER`；Zhou v4 确认“证据未变，不需要重开复核”。
- 入库：PR #75 squash merged `c69f4ba1498c73bc1d1700c4723b5c8e39b171cc`。
- 合并后元数据：`repo_status` 改 `MERGED`、补 `merge_commit`、清空 `open_items`；PR #78 squash merged `d98658f261c17ebbd5943286e389fe9567843fc2`。
- 合并后未改：41 条 responses、matrix、两张浏览器图、`reviews/01–03`。

## 5. 变更历史

| 时间（UTC+8） | 事件 |
|---|---|
| 15:44 | API 矩阵首跑，41/41 |
| 16:04 | 浏览器两张补齐 |
| 16:16 | Zhou v1 复核；`response_sha256` 口径阻断 |
| 16:28 | 改为原始响应字节并重跑；41/41 哈希一致 |
| 16:40 | Zhou v2 复签 `SIGNED_OFF`；57 文件 |
| 17:47 | 元数据修正（`not_covered`/README）；Zhou v4 确认；58 文件 |
| 17:52 | PR #75 合入 `c69f4ba` |
| 23:10 | 合并后 `repo_status=MERGED`；PR #78 合入 `d98658f`；最终 58 文件，manifest `170E…` |
| 23:30 | Zhan 核包通过，分配索引号 `ZR-20261030-19`；Gate A 时间待定 |

## 6. 边界

- 本包是 API + 浏览器截图证据；不含浏览器 HAR（C01 已证页面无写请求）。
- API 不暴露部署 commit；版本归属是仓库证据，不是运行时自证。
- T2 当前无已批准 DO；跨租户用“T1 真实 DO + T2 令牌”验证 404。
- 不在 C08 范围：CLERK/OWNER 之间的 IDOR、前端 Local Demo、T2 业务流程。
- `/ai/status` 对 WAREHOUSE 200 是契约允许，不是 P0。
- 无效 body 会先 422；测试需用合法 body，避免把 422 误判为“未拦住”。
- `picking_note` 是仓库可见自由文本；若允许写价格会形成旁路（P3 建议）。

## 7. 给索引的条目（Zhan 可直接用）

| 字段 | 值 |
|---|---|
| 编号 | C08 |
| 名称 | 仓库权限（Warehouse RBAC / 字段裁剪） |
| 结论 | `PASS_API_LAYER` / `SIGNED_OFF` / `independent PASSED` |
| 证据 PR | #75，merge `c69f4ba1498c73bc1d1700c4723b5c8e39b171cc` |
| 证据目录 | `evidence/e2e/c08/2026-10-30/` |
| 清单 | `170E9202…4165EC`（58 文件） |
| 离线包 | `C08_API_evidence_2026-10-30.zip`，`11D9D98F…C919DA`，1,913,528 B |
| 复核 | Zhou Jingxi，2026-10-30 16:40，[reviews/03](../../evidence/e2e/c08/2026-10-30/reviews/03-Zhou-signoff-2026-10-30.md) |
| Gate A | 时间待 Zhou 确认、Zhan 同步 |
| 索引号 | `ZR-20261030-19` |

## 8. 复现

```powershell
py -3.13 c08_warehouse_audit.py `
  --tokens <私有 demo_tokens.json 路径> `
  --out evidence
```

期望 `41/41 passed, field_scan=True, projection_diff=True, status=PASS_API_LAYER`，退出码 0。

## 9. 链接

- PR #75：https://github.com/Hozier123/sdc-2026-team-project/pull/75
- PR #78：https://github.com/Hozier123/sdc-2026-team-project/pull/78
- 证据目录：https://github.com/Hozier123/sdc-2026-team-project/tree/main/evidence/e2e/c08/2026-10-30
- 复核记录：[reviews/02](../../evidence/e2e/c08/2026-10-30/reviews/02-Zhou-review-2026-10-30.md)、[reviews/03](../../evidence/e2e/c08/2026-10-30/reviews/03-Zhou-signoff-2026-10-30.md)
