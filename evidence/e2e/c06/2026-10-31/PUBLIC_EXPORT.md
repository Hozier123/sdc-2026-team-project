# C06 公开副本说明（r2-public）

## 1. 来源与签字原件

- 签字原件：`C06_stock_shortage_evidence_2026-10-31.zip`
- 大小：86,506 B
- SHA-256：`89AC444265CADB22DAEBF1659FFA01F7A6A3A0A86D5251F7FE271488CF2F58A6`
- 原件清单：`PACK_SHA256.txt` 59 项、`evidence/SHA256.txt` 46 项；Zhan 实算 **59/59、46/46** 全通过。
- 技术复核：Zhou **APPROVED**（He 转录）；形式复核：Zhan **PASS** + 索引号 `ZR-20261031-03`；公开副本另核 `ZR-20261031-04`（raw 19/19、db 11/11 与原件逐字节相同；`SHA256.txt` 51/51）。

本目录是公开仓库用的**脱敏派生副本**，不是另一个签字件。技术证据（`raw/`、`db/`）字节未改；只改了文档措辞、状态元数据，并脱敏本机路径/备份库名。

## 2. 相对原件改了什么

1. **本机路径脱敏**：`evidence/meta/b05_environment_public.json`、`evidence/meta/b05_technical_acceptance.json`、`evidence/reset/apply.txt`、`evidence/reset/apply_core_reset.json`、`evidence/reset/apply_reset_T1_….log`、`evidence/reset/dryrun.txt`、`HANDOFF_C06.md` 中的本机绝对路径已换成 `<local-path>` / `<b05-env-ea709a8e70d0>` 等占位符。
2. **备份库名脱敏**：`kiraorder_demo_b05_firstuse_ea709a8e70d0_backup_<id>`，保留“有备份库”这一事实，不公开随机后缀。
3. **矩阵第 3 条**：拆分 `raw/02`（`blocked_actions=[INSUFFICIENT_STOCK]`）与 `raw/04`（`blocked_actions=[BLOCKING_ISSUES]`、`blocking_issues=[INSUFFICIENT_STOCK]`），缺货事实以 issue code 为准。
4. **snapshot 说明**：`raw/13`、`raw/14` 的 `available_qty=30` 是送审 snapshot；409 实时值为 `1`，见 `raw/12` 与 `db/b5_manual_stock_down.json`。
5. **acceptance.json**：`gate_a_status=DEFERRED`；`result=PASS_TECHNICAL_SIGNED_OFF`、`overall_status=SIGNED_OFF`、`independent_review_status=PASSED`、`repo_status=PENDING_COMMIT`；补 `reviews` 与 `public_export` 字段。
6. **README / HANDOFF**：补复核结论、限制口径、索引号与公开副本说明；去掉本机绝对路径；标注 Zhou/Zhan 回执为 He 转录件。
7. **不含 `scripts/`**：本机复现脚本不进公开仓库；包内原有脚本只保留在签字原件中。

> 签字/报告统一引用仓库 `SHA256.txt` 的 51/51；公开 zip 的 `46A5…9DAD` 是本地分发副本的哈希，未随 PR 提供，Zhan 未核，不作为仓库签字依据。

## 3. 公开副本的哈希

- 本目录 `SHA256.txt`：覆盖本目录全部 51 个文件（含 HANDOFF、reviews、raw、db、reset），不含清单自身。
- 分发包另有 `PACK_SHA256.txt`；仓库副本以本目录 `SHA256.txt` 为准。

## 4. 口径提醒

- 本包是 **API + DB 技术验收**，不是浏览器/UI 通过；没有截图。
- 环境绑定源码 `c8848ef`，不是当前 main；换环境需重新 create。
- 本包不改变生产 C04/C08；C04 的 PENDING 样例未消费。
- C06 不是 Gate A 条目；`gate_a_status=DEFERRED`。
