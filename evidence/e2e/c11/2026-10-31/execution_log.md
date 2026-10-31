# C11 执行记录（生产 API 主线，2026-10-31 10:42–10:45 UTC+8）

- 环境：生产 API `https://kiraorder-api.replit.app/api/v1`
- 前端：`f8ff1d7`（gh-pages `12ff95f`，v1.4.0）；后端：`9cff61ed`（源 `9dfee33`）
- 执行人：He（脚本：DSH）
- 依据：`HANDOFF_C11.md` v1.1 / `evidence/matrix.md` v1.1；Zhou 2026-10-31 02:45 批复
- 原始响应：`evidence/raw/`（每条含 `.body.json`、`.headers.txt`、部分 `.req.json`）

## 1. 检查结果

| # | 检查 | HTTP | 模式 | request ID | draft | 结果 |
|---|---|---|---|---|---|---|
| 1 | 种子别名读路径（`老规矩辣椒酱 2`） | 200 | ALIAS_ONLY | `ebb3cb6d-6bfc-48ba-86de-361bee5d96a3` | `DRF_880B83679D994BBE943FA913E7D99287` | **PASS**：`SKU_CILI_1KG`、`ALS_CACHE_RASA_001`、0 候选 |
| 2a | LLM 候选 | 200 | LLM | `b21f824a-916c-44aa-8167-cf56b44da0d6` | `DRF_220516E8AC554F49AC2B45775AA69AA0` | PASS：2 候选 |
| 2b | LLM 候选 | 200 | LLM | `159cc5ae-ea66-4d3c-971e-9be117ed7986` | `DRF_90F128495E5842D0A95ADF09FB63D8C7` | PASS：2 候选 |
| 2c | LLM 候选 | 200 | LLM | `7d22dfc1-72d6-4b2a-aa44-44fb6fc1506d` | `DRF_448F5FF1388841458BF6D6B9BE0B53FC` | PASS：2 候选 |
| 3 | 未保存保护 | — | — | — | — | **PENDING：UI 截图** |
| 4 | 保存 + 记忆写入 | 200 | LLM（保存） | `8204ce31-e506-45b6-814c-860ac3daabb1` | `DRF_448F5FF1388841458BF6D6B9BE0B53FC` v2 | **PASS（API）**：`ALI_398DB0744E6F44B985643D81979F4456` / CUSTOMER / 36.00；截图待补 |
| 5 | 同句冷态复用 | 200 | ALIAS_ONLY | `38b607fe-e99e-4bab-ad04-d3fcfbb7f82b` | `DRF_9651CF71B1954C0D9BE00BB77F8CCA62` | **PASS（API）**：同 alias、0 候选；冷态 10:44:37 DEGRADED；截图待补 |
| 6 | 数量边界（`Milo 3 bag`） | 200 | LLM | `16b6f3f4-094e-4263-9cba-13c02a08e021` | `DRF_D23633252AD0471BB5E441F7E44FDAEC` | `NOT_A_DEFECT`：2 候选重新出现 |
| 7 | TENANT 负例 | 403 | — | `190af066-6e52-4f9d-bea7-986b22cff62d` | `DRF_448F5FF…` 仍 v2 | **PASS**：`FORBIDDEN_ACTION`，draft/alias 未变 |
| 8 | 无候选死路 | 200 | LLM | `5c212af9-9278-4d8d-acd4-e4d9c440250c` | `DRF_E47E0444470D407285C59C5663DC9340` | **LIMITATION**：1 行、0 候选、`NO_CANDIDATE`；截图待补 |
| 9 | 零行死路 | 200 | LLM | `3f9a078f-5d40-431d-aefe-be26b2a9639f` | `DRF_EF74C92677A34036894846F725612725` | **LIMITATION**：0 行、`LOW_CONFIDENCE_MATCH`；截图待补 |
| 10 | 证据完整性 | — | — | — | — | **PARTIAL**：raw 齐，截图与全表 alias 计数缺 |

## 2. 第 2 条 LLM 绑定

- 3/3 次 `ai_mode=LLM`，候选均为 `SKU_MILO_1KG 1kg 18.00` + `SKU_MILO_2KG 2kg 34.00`，`MULTIPLE_PACK_SIZES`。
- 请求 ID 见上表；响应头 `X-Request-ID` 已保存在各 `.headers.txt`。
- provider/model：部署配置 `AI_PROVIDER=runpod_adapter`，模型 `Qwen/Qwen2.5-7B-Instruct-AWQ`（部署侧配置，API 不返回模型名）。
- 原始模型输出：部署 API 不暴露；按 Zhou 10:25 口径，矩阵不要求，**未打补丁**。

## 3. 第 4/5 条记忆

- 保存前：3 次 `Milo 2 bag` 均返回 2 候选、无 `saved_alias` → 键 `(T1, CUS_ALI, phrase_norm=milo 2 bag)` 写前 **0 行**。
- 保存：v2、`READY_FOR_APPROVAL`、无 blocking、`ALI_398DB0744E6F44B985643D81979F4456`、scope CUSTOMER、`SKU_MILO_1KG`、18.00×2=36.00。
- 冷态：10:43:19–10:44:25 READY，10:44:37 **DEGRADED**；随后重放 → `ALIAS_ONLY`、同 alias、0 候选 → 键写后 **1 行**。
- **全表 `alias_cache` 行数**：无生产 DB DSN，无法查询；当前证据是“键级 0→1 + 同 alias 复用”。若 Zhou 要全表 count，需要提供 Neon 只读 DSN 后补。
- TENANT 负例 403 后 `GET` draft 仍 v2、alias 未变。

## 4. 锚点

| 锚点 | 执行前 | 执行后 |
|---|---|---|
| C04 `APR_7A1382B29D5C44FFB6242D15477A60B7` | 200，PENDING，34.00 | 200，PENDING，34.00 |
| C08 `DO_20261029_453C4BC2` | 200 | 200 |

未 reset、未发版、未写 C04/C08 对象。

## 5. 截图（已补，2026-10-31 11:16 UTC+8）

生产 Pages + CLERK 会话；9 张 JPEG（6 主图 + 3 上下文）：

| 文件 | 内容 | 草稿 |
|---|---|---|
| `c11_01_candidates.jpg` | 两张候选卡片（1kg / 2kg）+ Which pack size? | `DRF_220516…` |
| `c11_01_candidates_context.jpg` | 页头 LLM / Needs review | `DRF_220516…` |
| `c11_02_unsaved.jpg` | 选中 1kg、Unsaved changes、Approve 置灰 | `DRF_220516…` |
| `c11_03_memory_saved.jpg` | Remember 复选框 + “Customer phrase remembered · customer scope” + RM36.00 | `DRF_448F5F…` |
| `c11_03_memory_saved_context.jpg` | v2 / Ready to approve | `DRF_448F5F…` |
| `c11_04_alias_only.jpg` | 产品行直接命中、无候选、记忆提示 | `DRF_9651CF…` |
| `c11_04_alias_only_context.jpg` | 页头 “ALIAS_ONLY · non-AI” | `DRF_9651CF…` |
| `c11_05_no_candidate.jpg` | `Sos tiram 2 btl`、无候选、Confirm the product | `DRF_E47E04…` |
| `c11_06_zero_rows.jpg` | `Products & quantities 0`、无补行入口、Ask the customer | `DRF_EF74C9…` |

逐文件 SHA-256 见 `acceptance.json` 的 `screenshots` 与 `SHA256.txt`。

## 5.1 说明

- 全表 `alias_cache` 行数不需要（Zhou 2026-10-31 11:53）；键级 0→1 对 C11 够用。
- 浏览器 HAR / 完整点击流不在本包范围。

## 6. 未覆盖

- 浏览器点击流、HAR、TEST32、Gate A、UOM 7 缺口、TENANT 管理/撤销。
- 第 8 条尝试：`Milo 5kg 2 bag` 与 `Milo 3kg 2 bag` 均返回 0 行（零行），最终用 `Sos tiram 2 btl` 构造出 `NO_CANDIDATE`；原始响应分别保留在 `08_*`、`08b_*`、`08c_*`。

## 7. 复核修订（2026-10-31 12:00）

- 按 Zhou 10:25：生产 alias 写入正式接受；C04 PENDING / C08 DO 锚点前后未变。
- 发布卫生：15 处电话 → `[REDACTED_PHONE]`；18 条响应 Cookie 头删除；环境/交接单绝对路径删除；哈希重算。
- 别名不可逆：`CUS_ALI` + `Milo 2 bag` 永久 `ALIAS_ONLY`；演示改用 `Milo 3 bag` 或别的客户。

## 8. 签收（2026-10-31）

- Zhou Jingxi：`SIGNED_OFF`，结果 `PASS_CANDIDATE_MEMORY_PENDING_REVIEW`；签收传输包 SHA-256 `DA9E606A84A73D78796289D89083DC03248C097EF7F1338D19335B497C08621F`。
- Zhan Zhengrong：形式 `PASS`，索引 `ZR-C11-20261031-01`，入库路径 `evidence/e2e/c11/2026-10-31/`。
- 业务证据（raw/screenshots）未改；仅签收元数据与 P3 文案更新。

## 9. 入库（2026-10-31）

- PR #111 squash merged；merge commit `8365c928a00a3a0df59aebaed9a6c18e380fcb25`（2026-10-31T04:22:21Z）。
- 路径 `evidence/e2e/c11/2026-10-31/`；业务证据未改，仅补入库元数据。
