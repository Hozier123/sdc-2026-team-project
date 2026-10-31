# C11 候选确认与记忆：已签收（SIGNED_OFF；7 PASS / 1 NOT_A_DEFECT / 2 LIMITATION）

> **当前状态 `SIGNED_OFF`。** Zhou Jingxi 2026-10-31 签收 `PASS_CANDIDATE_MEMORY_PENDING_REVIEW`；Zhan Zhengrong 形式 PASS，索引 `ZR-C11-20261031-01`。生产 API 主线 8 组 raw + 9 张截图：第 1/2/3/4/5/7/10 条 PASS，第 6 条 NOT_A_DEFECT，第 8/9 条 LIMITATION。

执行人：He（脚本 DSH）；口径 v1.1（Zhou 2026-10-31 02:45 批复）；执行：2026-10-31 10:42:57–10:45:08 UTC+8；截图补齐 11:16 UTC+8。

环境：**生产 API** `https://kiraorder-api.replit.app/api/v1`；前端 `f8ff1d7`（gh-pages `12ff95f`，v1.4.0）；后端 `9cff61ed`（源 `9dfee33`）。未 reset、未发版、未写 C04/C08 对象。按 Zhou 10:25 口径，插桩补丁只作本地补充，本包未打补丁。

## 1. 本次补的是什么

C02 是 **“待补证/参考”，不是“已证明”**；C02 目前需补证、未独立签收。C11 不重复 C02 的完整批准/DO 链，只补：

1. **LLM 模式**下的候选确认（C02 是 FALLBACK，`LLM_inference=NOT_ESTABLISHED`；C11 第 2 条自带最小候选证据）；
2. `CUSTOMER` 级**记忆写入 + 同句复用**；
3. **无候选 / 零行**死路的限制记录。

不在范围：UOM 7 缺口、D02/#91/#92/#93、TENANT 管理/撤销、Gate A、TEST32、真实受试者。

## 2. 判定标准与 Zhou 追加证据（10 条）

| # | 检查 | 期望 | 必须留的证据 |
|---|---|---|---|
| 1 | 种子别名读路径 | `CUS_RASA` + `老规矩辣椒酱 2`（不带 btl，uom 不作断言）→ `ALIAS_ONLY` / `SKU_CILI_1KG` / `ALS_CACHE_RASA_001` | 原始响应、request ID、environment ID、source commit、alias 行数 |
| 2 | LLM 候选 + 绑定 | `CUS_ALI` + `Milo 2 bag` → `LLM`、2 候选、`MULTIPLE_PACK_SIZES` | provider/model、`X-Request-ID`、**原始模型输出**、latency |
| 3 | 未保存保护 | 选 1kg 未保存 → approval disabled | 截图 |
| 4 | 保存 + 记忆 | 勾 remember → v2、`saved_alias` CUSTOMER、RM36.00 | 原始响应、**alias_cache 写前/写后行数（+1）**、截图 |
| 5 | 同句复用 + 不调模型 | 同句 → `ALIAS_ONLY`、同 alias_id、candidates=[] | **provider 调用计数=0** 或等价无模型日志、截图 |
| 6 | 数量边界 | `Milo 3 bag` 不命中 | 原始响应；若写 alias 则记录 |
| 7 | TENANT 负例（**必做**） | CLERK 传 TENANT → 403 | 原始响应、alias 行数不变 |
| 8 | 无候选死路 | `Milo 5kg` → `NO_CANDIDATE`、无选择器 | 原始响应、截图 |
| 9 | 零行死路 | `ok thanks` → 0 行、无补行入口 | 原始响应、截图 |
| 10 | 证据完整性 | raw + raw model output + 图 + 行数 + 哈希 + 无密钥 | `SHA256.txt` 等 |

**汇总规则**：第 7 条必做；1–5、7、10 全 PASS 才 `PASS_CANDIDATE_MEMORY_PENDING_REVIEW`。第 7 条未跑，或第 2/5 条缺规定证据 → `PARTIAL_PENDING_REVIEW`，不得 PASS。第 6 条 `NOT_A_DEFECT`，第 8/9 条 `LIMITATION_RECORDED`。始终 `NOT_SIGNED_OFF`，直到 Zhou 签字。

## 3. 方法：为什么这个结果可信

1. **隔离**：B05 环境 `b05-env-ea709a8e70d0` 的 firstuse 侧；两侧独立 PG cluster；不连生产 C04/C08。
2. **LLM 绑定**：本地 API 用 `runpod_adapter` 接真实 RunPod；插桩记录 `provider/model`、`X-Request-ID`、`choices[0].message.content` 原始输出；抽取逻辑不变，补丁 diff/hash 入证据。
3. **不调模型**：插桩有 provider 调用计数器；第 5 条前后计数不变（0 次），不是只写“冷态”。
4. **记忆范围**：只写 CUSTOMER；每次写入前后查 `alias_cache` 行数；TENANT 负例 403 且行数不变。
5. **原始字节**：raw 响应、raw model output、计数日志、截图、哈希全部落盘；不落 token。
6. **限制不美化**：第 8/9 条只记 `LIMITATION_RECORDED`。

## 4. 证据清单（执行后）

| 文件 | 说明 |
|---|---|
| `acceptance.json` | 10 条检查、Zhou 条件、环境计划、样本、限制、结论 |
| `sample.json` | 预检/候选/复用/边界/限制样本的期望与证据要求 |
| `environment.json` | B05 环境、源码 commit、插桩 patch hash、provider 计数、alias 行数 |
| `matrix.md` | 10 条逐条期望/证据/结果 |
| `raw/` | 原始 API 响应、原始模型输出、provider 计数 |
| `screenshots/` | 6 张（候选、未保存、记忆、ALIAS_ONLY、无候选、零行） |
| `SHA256.txt` | 证据目录逐文件哈希 |

## 5. 已知限制

- **C11-LIM-01**：`NO_CANDIDATE` 行无 SKU 选择器，未开发死路；只记录。
- **C11-LIM-02**：0 行草稿无补行入口；只记录。
- **C11-LIM-03**：别名 phrase 含数量，只有一字不差才命中；第 6 条是语义边界，不是缺陷。
- **C11-LIM-04**：无撤销接口，写入不可逆；第 4 条前确认 phrase/SKU。
- **C11-LIM-05**：预检草稿 3 条，未保存/未批准/未写别名；`DRF_124C` 无 raw output，不能当第 2 条证据。
- **C11-LIM-06**：若只能用生产 API 且无插桩/RunPod 日志，第 2/5 条只能记 LIMITATION，结论降为 `PARTIAL_PENDING_REVIEW`。

## 6. 边界与未签字项

- **独立复核**：`independent_review_status=NOT_REQUESTED`；跑完发 Zhou（技术）+ Zhan（形式）。
- **入库**：`repo_status=NOT_COMMITTED`；建议路径 `evidence/e2e/c11/2026-10-31/`，只拷 `evidence/` + `HANDOFF_C11.md`，不拷 `scripts/` 与插桩副本。
- **生产**：只用合成数据；不 reset（C04 PENDING、C08 DO 锚点）；不发版。
- **不含**：UOM 7 缺口结论、TENANT 管理、撤销、Gate A、TEST32、真实受试者。

## 7. 结论

**生产 API 主线已执行，当前 `PASS_CANDIDATE_MEMORY_PENDING_REVIEW` / `NOT_SIGNED_OFF`：**

- 第 1/2/3/4/5/7/10 条 PASS（第 2 条 3/3 LLM；第 4 条写入 `ALI_398DB0744E6F44B985643D81979F4456`；第 5 条在 DEGRADED 冷态 `ALIAS_ONLY`；第 7 条 403）；
- 第 6 条 `NOT_A_DEFECT`；第 8/9 条 `LIMITATION_RECORDED`；
- 8 组 raw + 9 张截图 + 哈希已齐；全表 `alias_cache` 行数仍缺生产只读 DSN（C11-LIM-07，当前只证明键级 0→1）。

Zhou 签字前始终 `NOT_SIGNED_OFF`；逐条证据见 `execution_log.md`、`raw/`、`screenshots/`。

## 8. 复核修订（2026-10-31 12:00）

- 生产 alias 写入已按 Zhou 10:25 口径正式记录并接受；acceptance 不再保留 B05/“不写生产”的旧 primary。
- 发布卫生：15 处电话 → `[REDACTED_PHONE]`；18 条响应 Cookie 头删除；绝对路径删除；`SHA256.txt` / `PACK_SHA256.txt` 重算。
- 键级 alias 0→1 足够，不需要全表 count（Zhou 11:53）。
- 别名不可逆：`CUS_ALI` + `Milo 2 bag` 永久 `ALIAS_ONLY`；演示 LLM 候选请用 `Milo 3 bag` 或别的客户。

## 9. 签收

- 技术：Zhou Jingxi，2026-10-31，`SIGNED_OFF`；签收的传输包 SHA-256 `DA9E606A84A73D78796289D89083DC03248C097EF7F1338D19335B497C08621F`（1,539,150 B）。
- 形式：Zhan Zhengrong，`PASS`，索引号 `ZR-C11-20261031-01`，入库路径 `evidence/e2e/c11/2026-10-31/`。
- 本目录的 `SHA256.txt` / `PACK_SHA256.txt` 在签收元数据更新后重算；业务证据（raw/screenshots）未改。

## 10. 入库

- PR #111 squash merged；merge commit `8365c928a00a3a0df59aebaed9a6c18e380fcb25`（2026-10-31T04:22:21Z）。
- 路径 `evidence/e2e/c11/2026-10-31/`；业务证据未改，本页仅补入库元数据。
