# 试次证据导出（kiraorder_demo_b05_firstuse_ea709a8e70d0）

- 租户：`T1`
- 导出时间：2026-10-31T01:47:37.241041+08:00
- 目的：库级重建会连同审计一起清除，本文件是重建前的唯一证据

## 行数

| 表 | 行数 |
|---|---:|
| `inbound_messages` | 3 |
| `orders` | 3 |
| `draft_versions` | 5 |
| `delivery_orders` | 2 |
| `activity_log` | 7 |
| `audit_logs` | 7 |
| `field_diffs` | 10 |
| `approval_requests` | 1 |

## DO 原文（2 条）

见同名 `.json` 的 `delivery_orders` 数组（完整 JSONB，未裁剪）。

## 审计摘要（7 条）

| do_number | action | actor_role | 时间 |
|---|---|---|---|
| `-` | `SAVE_LINES` | CLERK | 2026-10-31T01:46:08.282333+08:00 |
| `DO_20261030_77EBD4F2` | `APPROVE` | CLERK | 2026-10-31T01:46:08.522509+08:00 |
| `DO_20261030_77EBD4F2` | `INVENTORY_DEDUCT` | CLERK | 2026-10-31T01:46:08.522509+08:00 |
| `-` | `SAVE_LINES` | CLERK | 2026-10-31T01:46:32.429198+08:00 |
| `-` | `SUBMIT_APPROVAL` | CLERK | 2026-10-31T01:46:32.658264+08:00 |
| `DO_20261030_6FC83E94` | `DECIDE_APPROVE` | OWNER | 2026-10-31T01:46:54.163765+08:00 |
| `DO_20261030_6FC83E94` | `INVENTORY_DEDUCT` | OWNER | 2026-10-31T01:46:54.163765+08:00 |

## 字段差异（10 条）

见同名 `.json` 的 `field_diffs` 数组。
