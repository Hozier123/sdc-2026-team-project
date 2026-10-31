# C11 He 侧交接单（2026-10-31 11:16，v1.3 证据已齐）

## 状态

| 项 | 状态 |
|---|---|
| 口径 | **SCOPE_LOCKED v1.1**：Zhou 2026-10-31 02:45 同意 5 条边界；10:25 明确 C11 主线在生产 API、补丁只作本地补充 |
| 执行 | **PASS_CANDIDATE_MEMORY_PENDING_REVIEW / SIGNED_OFF**：8 组 raw + 9 张截图；7 PASS / 1 NOT_A_DEFECT / 2 LIMITATION |
| 环境 | **生产 API** `https://kiraorder-api.replit.app/api/v1`；前端 `f8ff1d7`（gh-pages `12ff95f`）；后端 `9cff61ed`（源 `9dfee33`）；未 reset、未写 C04/C08 对象 |
| 依赖-模型 | 3/3 次 `ai_mode=LLM`（2.1–2.3 s）；未打插桩补丁；provider/model 属部署配置 |
| 依赖-语义 | D02 PR #91 在途；本包不纳入 UOM 7 缺口 |
| 独立复核 | **Zhou Jingxi 2026-10-31 签收 `SIGNED_OFF`**；Zhan 形式 `PASS`，索引 `ZR-C11-20261031-01` |
| 入库 | `PENDING_COMMIT` → `evidence/e2e/c11/2026-10-31/`（只拷 `evidence/` + `HANDOFF_C11.md`） |
| Gate A | **无关**；C11 不是 Gate A v5（C01/C04/C05/C08）的项 |

受控目录：`03_交接与提交包\C11_candidate_memory_evidence_2026-10-31`（本地绝对路径不公开）

本版是**口径锁定版**：`SHA256.txt` / `PACK_SHA256.txt` 只证明骨架未被改动；执行后必须重算。

## 0. 口径（Zhou 2026-10-31 02:45 批复；10:25 修订）

**C02 是“待补证/参考”，不是“已证明”。** C02 目前需补证、未独立签收；C11 不写“C02 已证明”，只写“C02 待补证/参考”。若 C11 不重跑最小候选确认，则第 2 条必须自带证据，否则标“依赖 C02 待签”。

C11 只补三块，不重复 C02 的完整批准/DO 链：

1. **LLM 模式下的候选确认**（C02 是 FALLBACK，`LLM_inference=NOT_ESTABLISHED`）；
2. **CUSTOMER 级记忆写入 + 同句复用**；
3. **无候选 / 零行的死路记录**（只记录，不判 PASS，不开发）。

**不在范围**：UOM 7 缺口、D02/#91/#92/#93、TENANT 管理、别名撤销、Gate A、TEST32、真实受试者、浏览器完整点击流（Zhou 同意，不要求 revoke）。

**Zhou 2026-10-31 02:45 追加的 4 个证据点（10:25 已修订）：**

1. **LLM 绑定**：`ai_mode=LLM` + `X-Request-ID` + provider/model（部署配置）；**原始模型输出不再是 matrix 要求**。
2. **ALIAS_ONLY**：同句 `ALIAS_ONLY` + 同 alias + 0 候选，**必须在 DEGRADED/OFFLINE 冷态执行**；provider 调用计数不再是 matrix 要求。
3. **C02 依赖**：C02 待补证/参考，不得写成已证。
4. **隔离与记忆范围**：环境 ID、版本、无 C04/C08 写入/reset；alias 只写 CUSTOMER；键级行数 0→1 足够（Zhou 11:53）。

**结论上限**：`PASS_CANDIDATE_MEMORY_PENDING_REVIEW` / `NOT_SIGNED_OFF`；没有 raw output / provider 计数不再降级。

## 1. 判定标准（10 条，按 Zhou 条件修订）

| # | 检查 | 期望 | 结果 |
|---|---|---|---|
| 1 | 种子别名读路径 | `CUS_RASA` + `老规矩辣椒酱 2`（**不带 btl；uom 不作断言**）→ `ALIAS_ONLY`、`SKU_CILI_1KG`、`ALS_CACHE_RASA_001`、`candidate_skus=[]` | PASS/FAIL |
| 2 | LLM 候选 + LLM 绑定 | `CUS_ALI` + `Milo 2 bag` → `ai_mode=LLM`、`X-Request-ID`、3 次复跑稳定；2 候选（1kg 18.00 / 2kg 34.00）、`MULTIPLE_PACK_SIZES`、澄清含 RM | PASS/FAIL |
| 3 | 未保存保护 | 选 1kg 未保存 → approval disabled、Unsaved changes、数量仍 2 | PASS/FAIL（UI） |
| 4 | 保存 + 记忆写入 | 勾 remember → 200 v2、blocking clear、`saved_alias` CUSTOMER、`MANUAL_SELECTED`、18.00×2=36.00；记录 **alias_cache 写前/写后行数（+1）**、environment ID、source commit | PASS/FAIL |
| 5 | 同句复用 + 不调模型 | 新草稿同句 → `ALIAS_ONLY`、同 `alias_id`、`candidates=[]`；必须在 `DEGRADED/OFFLINE` 冷态执行 | PASS/FAIL |
| 6 | 数量变化边界 | `Milo 3 bag` → 不命中（非 `ALIAS_ONLY`）；若此步新写 alias，记录 phrase/SKU/scope 与行数变化 | `NOT_A_DEFECT` |
| 7 | TENANT 负例（**必做**） | CLERK 对已选行 `alias_scope=TENANT` + 记忆勾选 → 403 `FORBIDDEN_ACTION`，不落库、`alias_cache` 行数不变 | PASS/FAIL |
| 8 | 无候选死路 | `Milo 5kg 2 bag` → `candidate_skus=[]` + `NO_CANDIDATE`；页面无 SKU 选择器 | `LIMITATION_RECORDED` |
| 9 | 零行死路 | `ok thanks` → 0 行、`LOW_CONFIDENCE_MATCH`、泛化澄清；无补行入口 | `LIMITATION_RECORDED` |
| 10 | 证据完整性 | 脱敏 raw（phone→[REDACTED_PHONE]）+ 无响应 Cookie 头 + 截图 + alias 键级行数 + environment/版本 + 哈希；无令牌/电话/本机绝对路径 | PASS/FAIL |

**汇总规则（Zhou 指定）**：第 7 条必做；1–5、7、10 全 PASS → `PASS_CANDIDATE_MEMORY_PENDING_REVIEW`。第 6 条 `NOT_A_DEFECT`，第 8/9 条 `LIMITATION_RECORDED`，均不参与 PASS 分母。按 Zhou 10:25 口径，raw model output / provider 计数不是 matrix 要求。

## 2. 环境方案（Zhou 2026-10-31 10:25 定稿）

**主线：生产 API。** C11 按 matrix 在生产 API 跑 8 条 raw + 6 张截图；补丁只作本地补充，不能替代主线。

- 环境：`https://kiraorder-api.replit.app/api/v1`；前端 `f8ff1d7`（gh-pages `12ff95f`）；后端 `9cff61ed`（源 `9dfee33`）。
- 写入范围：只写 `CUS_ALI` 的 CUSTOMER 别名；C04 的 PENDING 与 C08 的 DO 只读核对，未 reset。
- 第 2 条：生产响应 `ai_mode=LLM` 即可，不要求原始模型输出；补丁不是必需项（Zhou 10:25）。
- 第 5 条：必须在 `DEGRADED/OFFLINE` 冷态跑，补丁不能顶这一项。
- 截图：生产 Pages，用 CLERK 会话连生产 API；6 张清单见 `evidence/execution_log.md` §5。

**可选补充（本包未执行）**：如以后需要 raw model output / provider 计数，可在 B05 本地副本打只读日志补丁；须按 Zhou 的 8 条约束（只包 provider client 外层、默认关闭、计数分 LLM/fallback/失败、#2 跑 2–3 次、写全三个 SHA、raw 只留本地 private、标签 `LOCAL_B05_SUPPLEMENT`、#5 仍需冷态），且不替代主线。

## 3. 预检草稿（2026-10-31 02:03，助手预检创建）

| 草稿 | 客户 | 句子 | 模式 | 说明 |
|---|---|---|---|---|
| `DRF_124C222C32364B408CFC97A221EDD7B3` | CUS_ALI | `Milo 2 bag` | LLM，2 候选 | v1 未保存；**没有 raw output**，不能直接当第 2 条证据 |
| `DRF_231D314608ED4926B09929C5613D83B6` | CUS_RASA | `老规矩辣椒酱 2 btl` | ALIAS_ONLY | 仅 runbook 参考；第 1 条改用不带 btl 的句子重跑 |
| `DRF_D604F28837D1434AAC012585A42BDB57` | CUS_ALI | `Milo 2 bag` | FALLBACK，2 候选 | 仅降级参考，不计正式证据 |

三条均未保存、未批准、未扣库存、未写别名。

## 4. 版本与样本

- 主线：生产 API；前端 `f8ff1d7`（gh-pages `12ff95f`，v1.4.0）；后端 `9cff61ed`（源 `9dfee33`）。
- 可选补充（未执行）：B05 `b05-env-ea709a8e70d0`，源码 `c8848ef`；补丁只用日志，不替代主线。
- 模型：`Qwen/Qwen2.5-7B-Instruct-AWQ`，vLLM 0.32.0，`LLM_TIMEOUT_S=4.1`。
- 样本：`CUS_ALI`（Restoran Ali，Tier A，Milo 1kg 18.00）；`CUS_RASA`（Kedai Rasa，Tier B，种子别名）。

## 5. 产物清单

| 文件 | 说明 |
|---|---|
| `evidence/README.md` | 范围、判定、方法、边界（执行后补结果） |
| `evidence/acceptance.json` | 10 条检查、样本、环境、限制、Zhou 条件 |
| `evidence/matrix.md` | 10 条逐条期望/实际/证据 |
| `evidence/environment.json` | B05 环境 ID、源码 commit、插桩补丁 hash、AI 状态 |
| `evidence/sample.json` | 样本、alias 行数、provider 计数期望 |
| `evidence/raw/` | 脱敏后的原始 API 响应、请求 ID、截图索引 |
| `evidence/screenshots/` | 候选卡片、记忆勾选、saved_alias、复用 ALIAS_ONLY、两条限制 |
| `evidence/SHA256.txt` / `PACK_SHA256.txt` | 逐文件哈希 |
| `scripts/hash_pack.py` | 重算哈希 + 打包 |

## 6. 复现与执行记录

执行命令与逐请求记录见 `evidence/execution_log.md` 与 `evidence/raw/`；本文件不再嵌入带鉴权占位符的脚本。

## 7. 已知限制（先写死）

- **C11-LIM-01**：`NO_CANDIDATE` 行无 SKU 选择器，未开发死路；只记录。
- **C11-LIM-02**：0 行草稿无补行入口；只记录。
- **C11-LIM-03**：别名 phrase = 当前 masked span（含数量），同句才命中；第 6 条是语义边界，不是缺陷。
- **C11-LIM-04**：无撤销接口，写入不可逆；第 4 条前确认 phrase/SKU。
- **C11-LIM-05**：预检草稿 3 条，未保存/未批准/未写别名，不计正式检查。
- **C11-LIM-06**：10:25 口径已明确 raw model output / provider 计数不是 matrix 要求；本包未采，不影响 PASS。

## 8. 复核清单（给 Zhou / Zhan）

- [x] 环境：生产 API；前端 `f8ff1d7`、后端 `9cff61ed`/`9dfee33`；未 reset、未写 C04/C08 对象；
- [x] 第 1 条：`老规矩辣椒酱 2`（uom 未断言）→ `ALIAS_ONLY` / `ALS_CACHE_RASA_001`；
- [x] 第 2 条：3/3 `ai_mode=LLM` + `X-Request-ID` + 2 候选；未打补丁，原始模型输出不在矩阵要求内（Zhou 10:25）；
- [x] 第 4 条：`ALI_398DB0744E6F44B985643D81979F4456` CUSTOMER + 36.00；键级 0→1；
- [x] 第 5 条：10:44:37 DEGRADED 冷态 → `ALIAS_ONLY` + 同 alias + 0 候选；
- [x] 第 6 条：`Milo 3 bag` 不命中，2 候选重新出现；
- [x] 第 7 条：403 `FORBIDDEN_ACTION`，draft 仍 v2，alias 未变；
- [x] 第 8/9 条：`NO_CANDIDATE` / 0 行，只记 LIMITATION；
- [x] 第 3 条：选中 1kg 未保存 → Unsaved changes + Approve 置灰（`c11_02_unsaved.jpg`）；
- [x] 第 10 条：8 组 raw + 9 张截图 + 哈希已齐；全表 alias count 无 DSN（C11-LIM-07）；
- [x] 汇总：`PASS_CANDIDATE_MEMORY_PENDING_REVIEW`；始终 `NOT_SIGNED_OFF`，等 Zhou 签字。

## 9. 结论

生产 API 主线已执行并补齐截图：第 1/2/3/4/5/7/10 条 PASS，第 6 条 NOT_A_DEFECT，第 8/9 条 LIMITATION。**当前 `PASS_CANDIDATE_MEMORY_PENDING_REVIEW` / `SIGNED_OFF`（Zhou 2026-10-31；Zhan `ZR-C11-20261031-01`）。** 逐条证据见 `evidence/execution_log.md`、`evidence/raw/`、`evidence/screenshots/`；全表 alias count 仍缺生产只读 DSN（C11-LIM-07）。签收完成；下一步按 `evidence/e2e/c11/2026-10-31/` 开 Draft PR。

## 10. 发布卫生（2026-10-31 12:00）

- `raw/*.body.json`：`+60...` 电话值全部替换为 `[REDACTED_PHONE]`；
- `raw/*.headers.txt`：删除全部响应 Cookie 头；
- `environment.json`、本文件：删除本机绝对路径，只保留 environment ID / 相对路径；
- 无令牌、无鉴权头、无客户电话；`SHA256.txt` / `PACK_SHA256.txt` 已重算。
