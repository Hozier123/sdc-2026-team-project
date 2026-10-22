# Canonical seed（T1 / T2）

来源：`seed_he_2026-10-22.zip`  
包 SHA-256：`AC8FFEC030476CD1CB02020FC95577EAB9783E5A3A393EF3246EF95323AAE8D4`

## 文件

```text
T1_seed.sql
T2_seed.sql
SEED_MANIFEST.json
```

- `T1_seed.sql` / `T2_seed.sql`：data-only SQL，只含 `INSERT`，不含 DDL，不含事务控制。
- 原始包 SQL 带外层 `BEGIN/COMMIT`；本目录副本只移除了这两个外层事务语句，数据行未改。
- 原始 SQL 的 SHA-256 保留在 `SEED_MANIFEST.json` 的 `source_sql_sha256`。
- 明文 demo token 不在仓库；SQL 只含 `demo_token_hash`。

## 版本与计数

| Tenant | seed_version | products | inventory sum | users | customers | aliases |
|---|---|---|---:|---:|---:|---:|
| T1 | `KB-T1-20261022-r1` | 40 | 795 | 3 | 8 | 50 family / 26 uom |
| T2 | `KB-T2-20261022-r1` | 16 | 450 | 3 | 5 | 30 family / 30 uom |

T2 `alias_cache` 2 条；T1 `alias_cache` 0 条。

## 导入

先迁移，再按 tenant 分别导入：

```powershell
Set-Location backend

.venv\Scripts\python -m app.seed `
  --tenant T1 `
  --seed-sql ..\data\seed\T1_seed.sql `
  --seed-version KB-T1-20261022-r1 `
  --expect-sha256 <见 SEED_MANIFEST.json> `
  --expect-products 40 `
  --expect-inventory 795

.venv\Scripts\python -m app.seed `
  --tenant T2 `
  --seed-sql ..\data\seed\T2_seed.sql `
  --seed-version KB-T2-20261022-r1 `
  --expect-sha256 <见 SEED_MANIFEST.json> `
  --expect-products 16 `
  --expect-inventory 450
```

不要使用 `seed_all.sql` 做逐 tenant 导入；它会把 T1/T2 一起插入，但 manifest 只登记当前 tenant。

## 验收

```text
kiraorder_meta.seed_manifest 两行
T1 products=40, inventory=795
T2 products=16, inventory=450
重复导入返回 already_loaded
```

`/me` 200 需要私发的明文 token；本目录没有明文 token。
