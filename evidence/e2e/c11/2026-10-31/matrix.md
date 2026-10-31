# C11 检查矩阵（v1.3，生产 API 主线，已补截图）

- 口径：v1.1（Zhou 2026-10-31 02:45 批复）+ 10:25 说明：C11 主线在生产 API，补丁只作本地补充
- 环境：生产 API `https://kiraorder-api.replit.app/api/v1`；前端 `f8ff1d7`（gh-pages `12ff95f`）；后端 `9cff61ed`（源 `9dfee33`）
- 执行：He（脚本 DSH），2026-10-31 10:42:57–10:45:08 UTC+8；截图补齐 11:16 UTC+8
- 结论：**7 PASS / 1 NOT_A_DEFECT / 2 LIMITATION → `PASS_CANDIDATE_MEMORY_PENDING_REVIEW` / `SIGNED_OFF`（Zhou 2026-10-31；Zhan `ZR-C11-20261031-01`）**

| # | 检查 | 期望 | 实际 | 证据 | 结果 |
|---|---|---|---|---|---|
| 1 | 种子别名读路径 | `CUS_RASA` + `老规矩辣椒酱 2`（uom 不作断言）→ `ALIAS_ONLY` / `SKU_CILI_1KG` / `ALS_CACHE_RASA_001` / 0 候选 | 200，`ALIAS_ONLY`，`SKU_CILI_1KG`，`ALS_CACHE_RASA_001`，0 候选 | `raw/01_alias_preflight.*`；req `ebb3cb6d…` | **PASS** |
| 2 | LLM 候选 | `CUS_ALI` + `Milo 2 bag` → `ai_mode=LLM`、2 候选、`MULTIPLE_PACK_SIZES` | 3/3 次 LLM，2 候选（1kg 18.00 / 2kg 34.00），`MULTIPLE_PACK_SIZES` | `raw/02a…02c_llm_candidate.*`；req `b21f824a…` / `159cc5ae…` / `7d22dfc1…`；截图 `c11_01_candidates.jpg` + `_context` | **PASS** |
| 3 | 未保存保护 | 选 1kg 未保存 → approval disabled、Unsaved changes、数量仍 2 | 选中 1kg 后 **Unsaved changes**、`Approve & generate DO` 置灰、数量 2 | 截图 `c11_02_unsaved.jpg` | **PASS** |
| 4 | 保存 + 记忆写入 | 勾 remember → v2、`saved_alias` CUSTOMER、18.00×2=36.00；alias 写前/写后 | 200，v2，`READY_FOR_APPROVAL`，无 blocking，`ALI_398DB0744E6F44B985643D81979F4456`，CUSTOMER，36.00；键级 0→1 | `raw/04_save_alias.*`；截图 `c11_03_memory_saved.jpg` + `_context`；req `8204ce31…` | **PASS** |
| 5 | 同句冷态复用 | 新草稿同句 → `ALIAS_ONLY`、同 alias、0 候选；冷态 | `/ai/status` 10:44:37 DEGRADED；重放 200 `ALIAS_ONLY`，同 alias，0 候选 | `raw/05_alias_replay.*`、`raw/05_cold_state.txt`；截图 `c11_04_alias_only.jpg` + `_context`；req `38b607fe…` | **PASS** |
| 6 | 数量变化边界 | `Milo 3 bag` → 非 `ALIAS_ONLY`；phrase 含数量 | 200，`LLM`，2 候选重新出现，span `Milo 3 bag` | `raw/06_qty_boundary.*`；req `16b6f3f4…` | **NOT_A_DEFECT** |
| 7 | TENANT 负例（必做） | CLERK 传 TENANT → 403，不落库 | 403 `FORBIDDEN_ACTION`（TENANT alias scope requires OWNER）；draft 仍 v2，alias 未变 | `raw/07_tenant_forbidden.*`、`raw/07b_*`；req `190af066…` | **PASS** |
| 8 | 无候选死路 | 1 行、`candidate_skus=[]`、`NO_CANDIDATE`、无 SKU 选择器 | `Sos tiram 2 btl`：1 行、`FAMILY_NOT_EVIDENCED` + `NO_CANDIDATE`、0 候选；`Milo 5kg`/`Milo 3kg` 均 0 行 | `raw/08c_no_candidate.*`；截图 `c11_05_no_candidate.jpg`；req `5c212af9…` | **LIMITATION_RECORDED** |
| 9 | 零行死路 | 0 行、`LOW_CONFIDENCE_MATCH`、泛化澄清、无补行入口 | `ok thanks`：0 行，`DISAMBIGUATION_REQUIRED`，`LOW_CONFIDENCE_MATCH`，clarification 存在 | `raw/09_zero_rows.*`；截图 `c11_06_zero_rows.jpg`；req `3f9a078f…` | **LIMITATION_RECORDED** |
| 10 | 证据完整性 | 脱敏 raw + 图 + alias 键级行数 + 哈希 + 无敏感信息 | 8 组脱敏 raw、9 张截图、哈希已重算；无电话 / 响应 Cookie 头 / 绝对路径 | `raw/`（phone→[REDACTED_PHONE]）、`screenshots/`、`SHA256.txt` | **PASS** |

## 汇总规则（Zhou 指定）

- 1–5、7、10 全 PASS → **`PASS_CANDIDATE_MEMORY_PENDING_REVIEW`**。
- 第 6 条 `NOT_A_DEFECT`；第 8/9 条 `LIMITATION_RECORDED`，不参与 PASS 分母。
- `SIGNED_OFF`（Zhou 2026-10-31）；Zhan 形式 `PASS`，索引 `ZR-C11-20261031-01`。

## 备注

- C02 是“待补证/参考”，不是“已证明”；本矩阵不引用 C02 作为已签收事实。
- 第 2 条 3/3 LLM，候选稳定；provider/model = `runpod_adapter` / `Qwen/Qwen2.5-7B-Instruct-AWQ`；API 不返回模型名，属部署侧配置。
- 原始模型输出未采集：部署 API 不暴露；按 Zhou 10:25 口径，矩阵不要求，未打补丁。
- 第 4 条写入 `ALI_398DB0744E6F44B985643D81979F4456`；键级写前 0 / 写后 1；键级足够，不需要全表 count（Zhou 11:53）。
- 锚点：C04 `APR_7A13…` 前后均 PENDING 34.00；C08 `DO_20261029_453C4BC2` 前后均 200。
- 未 reset、未发版、未写 C04/C08 对象。
- 截图 9 张：6 张主图 + 3 张上下文（`c11_01`、`c11_03`、`c11_04` 的 `_context`）；哈希见 `acceptance.json` 与 `SHA256.txt`。
- 哈希已重算。

## 复核修订（2026-10-31 12:00）

- **10:25 口径已写入 acceptance**：C11 主线为生产 API；对 `CUS_ALI` 的这一次 CUSTOMER alias 写入已由 Zhou 接受；C04/C08 锚点前后未变、未 reset。
- **发布卫生**：`raw/*.body.json` 15 处电话 → `[REDACTED_PHONE]`；`raw/*.headers.txt` 18 条响应 Cookie 头删除；`environment.json` / `HANDOFF` 绝对路径删除；哈希重算。
- **别名不可逆**：`CUS_ALI` + `Milo 2 bag` 永久 `ALIAS_ONLY`；演示 LLM 候选请用 `Milo 3 bag` 或别的客户，写进演示脚本。

## 签收

- Zhou Jingxi 2026-10-31 签收；Zhan Zhengrong 形式 PASS，索引 `ZR-C11-20261031-01`；入库路径 `evidence/e2e/c11/2026-10-31/`。

## 入库

- PR #111 squash merged；merge commit `8365c928a00a3a0df59aebaed9a6c18e380fcb25`（2026-10-31T04:22:21Z）。
