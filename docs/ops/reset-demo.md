# 试次重置：库级重建（方案 A）

> 适用：Gate 0 v4 / `gate0-baseline-v1`，T1 隔离试次。
> 工具：`backend/tools/reset_demo.py`。
> 结论先行：**行级 DELETE 不可行**（6 张表有 immutable/append-only 触发器），所以每次试次前用模板库重建目标库。

## 1. 为什么不能行级删除

Gate 0 的 DDL 给 6 张表挂了 `BEFORE UPDATE OR DELETE` 触发器：

| 表 | 触发器 | DELETE 结果 |
|---|---|---|
| `draft_versions` | `draft_versions_immutable` | `55000` |
| `delivery_orders` | `delivery_orders_immutable` | `55000` |
| `activity_log` | `activity_log_append_only` | `55000` |
| `audit_logs` | `audit_logs_append_only` | `55000` |
| `field_diffs` | `field_diffs_append_only` | `55000` |
| `approval_requests` | `approval_request_snapshot_guard` | `55000`（UPDATE 仅允许 PENDING→APPROVED/REJECTED） |

8 张流水表里只有 `orders` 和 `inbound_messages` 可以删。所以“清空当日草稿/DO”无法用行级 SQL 实现；改 DDL 需要 `gate0-v5`、重算 73 哈希、四方重签，代价远大于收益。

## 2. 两个库

```text
kiraorder_t1_seed   模板库：迁移 + canonical T1 seed，流水表为空，带 seed 清单
kiraorder_trial     目标库：每次试次前从模板整库重建
```

模板库里的 `kiraorder_meta.seed_manifest` 钉住版本：

| 列 | 含义 |
|---|---|
| `seed_version` | 与 canonical T1 同版本，例如 `T1-0.1` |
| `seed_sha256` | seed 文件哈希 |
| `product_count` / `inventory_total` | 40 / 795 |
| `family_count` / `customer_count` | 25 / 8 |
| `price_count` / `price_total_a` / `price_total_b` | 80 / 1060.40 / 1150.50 |
| `applied_at` | 模板生成时间 |

Zhou 一旦重定稿（库存或价格变化），必须重建模板并升版本；否则不同受试者跑的不是同一套数据。

**manifest 只证明“文件没被改”，不能证明“数值对”**：回读的期望值来自 `products.csv` 快照（80 条价、A 1060.40 / B 1150.50、795 件），manifest 与快照比对是两道独立检查，不能互相替代。

## 3. 一次 reset 的顺序（计时边界）

```text
   … 本单结束
   停表
   ↓
   ① preflight   模板存在、版本/哈希匹配、18 表校验
   ② 证据导出    DO 原文 + audit_logs/field_diffs 摘要落盘
   ③ 重建        DROP/CREATE kiraorder_trial FROM kiraorder_t1_seed
   ④ 回读校验    18 表、账本哈希、库存 40/795、alias_cache 0、流水表 0
   ⑤ hook        重启 API + 清 AI 进程态 + 前端刷新
   ↓
   起表 → 展示下一题消息
```

**重建、冷启动、刷新全部发生在停表之后、起表之前**，否则会被算进某一单。

## 4. 命令

```powershell
# 只看计划，不改库
python -m tools.reset_demo --dry-run --expect-seed-version T1-0.1 --expect-seed-sha256 <sha>

# 正式执行；hook 里重启后端与 AI
python -m tools.reset_demo --apply `
  --expect-seed-version T1-0.1 --expect-seed-sha256 <sha> `
  --hook "powershell -ExecutionPolicy Bypass -File ../scripts/restart-demo.ps1"

# Zhou 重定稿后重建模板
python -m tools.reset_demo --init-template `
  --seed-sql ../data/seed/seed_T1.sql `
  --seed-version T1-0.2 --seed-sha256 <sha>
```

连接串用 `RESET_ADMIN_DATABASE_URL`（或 `--admin-url`），必须是具备 `CREATEDB` 的管理员账号；业务库连接串 `DATABASE_URL` 权限不够，也不应被重置工具使用。

## 5. 证据导出（A 方案的必要补偿）

库级重建会连审计一起清掉，所以重建前必须导出：

```text
evidence/reset/reset_<target>_<时间戳>.json   完整 JSON：DO 原文、审计行、字段差异
evidence/reset/reset_<target>_<时间戳>.md     人读摘要：行数、DO 列表、审计表
```

导出发生在 `DROP DATABASE` 之前；导出失败则整个 reset 中止，不会出现“证据没落盘但库已经清空”。

## 6. 验收映射（Zhan 第 1 条）

| 验收项 | 本工具的回读校验 |
|---|---|
| inventory 40 行 / 合计 795 | `seed_snapshot()`，不符即失败 |
| 等级价 80 条、A 合计 1060.40、B 合计 1150.50 | 同上；每个 SKU 必须恰好 A/B 两档 |
| 商品 40 / 族 25 / 客户 8 | 同上 |
| `alias_cache` 0 行 | 计数必须为 0 |
| 6 张流水表 0 行 | `inbound_messages/orders/draft_versions/delivery_orders/activity_log/audit_logs` 全 0 |
| `approval_requests` 恒 0 | 计数必须为 0 |
| 18 表 / 6 trigger / 12 事件 | 复用 `app.migrations.verify_schema()` |
| 迁移账本 | `version + sql_sha256 + baseline_hash_sha256` 与冻结常量一致 |

期望值从 `products.csv` 传入（默认 40/25/8/80/1060.40/1150.50/795），不从 manifest 取——否则等于自己验自己。`field_diffs` 没有 `tenant_id`，通过 `audit_logs.audit_id` 关联统计，同样要求为 0。

## 7. 失败语义

- 任何一步失败 → 非零退出码，`status=failed`，日志写 `logs/reset_T1_<时间戳>.log`。
- 不收尾、不“尽力修复”：`DROP` 成功但 `CREATE` 失败时，目标库处于缺失状态，错误信息会明确要求重跑。
- 连跑两次结果一致（幂等）。
- 日志不含连接串或密码。

## 8. 前置与限制

- 目标库必须是**专用演示库**：库级重建会清掉该库全部数据，不能与真实租户共库。
- 需要 `CREATEDB` 权限；建议单独管理员账号，不授予应用。
- 应用连接池在重建后失效：hook 必须重启 API；AI 进程内存态（缓存/预热/RunPod 会话）也要重启，否则“干净起点”不成立。
- 前端旧 `draft_id` 会 404：试次之间必须刷新/重新登录。
- 审计证据只保留在导出的文件里，数据库内不再有。

## 9. 关于固定 AI 模式

`ai_mode` 的契约值是 `LLM / FALLBACK / ALIAS_ONLY / MIXED`，但 `KIRAORDER_AI_FORCE_MODE` 是 P0-A 的测试专用开关，当前代码尚未实现。

若全程固定 `ALIAS_ONLY`，命中率取决于别名覆盖：当前 seed 只有 25 条族级别名、0 条 SKU 别名、`alias_cache` 为空，多数消息会落到 `LOW_CONFIDENCE_MATCH`，测到的是“别名表覆盖度”而不是产品能力。更稳的固定模式是 `FALLBACK`（RapidFuzz，本地、确定性、无预热）。这一点需要在工具组开始前由测试侧确认。
