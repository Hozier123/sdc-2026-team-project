# C11 候选确认与记忆：已结项（SIGNED_OFF / MERGED）

> **最终状态：`PASS_CANDIDATE_MEMORY_PENDING_REVIEW` / `SIGNED_OFF` / `MERGED`。**
> Zhou Jingxi 2026-10-31 技术签收；Zhan Zhengrong 形式 `PASS`，索引 `ZR-C11-20261031-01`。
> 证据 PR #111（merge `8365c92`）；结项记录 PR #112（merge `42919b4`）；目录 `evidence/e2e/c11/2026-10-31/`。

执行人：He（脚本 DSH）；口径 v1.1（Zhou 2026-10-31 02:45 批复，10:25 修订）；执行：2026-10-31 10:42:57–10:45:08 UTC+8；截图补齐 11:16 UTC+8。

环境：**生产 API** `https://kiraorder-api.replit.app/api/v1`；前端 `f8ff1d7`（gh-pages `12ff95f`，v1.4.0）；后端 `9cff61ed`（源 `9dfee33`）。未 reset、未发版、未写 C04/C08 对象。

## 1. 本次补的是什么

C02 是 **“待补证/参考”，不是“已证明”**；C02 目前需补证、未独立签收。C11 不重复 C02 的完整批准/DO 链，只补：

1. **LLM 模式**下的候选确认（C02 是 FALLBACK；C11 第 2 条自带最小候选证据）；
2. `CUSTOMER` 级**记忆写入 + 同句复用**；
3. **无候选 / 零行**死路的限制记录。

不在范围：UOM 7 缺口、D02/#91/#92/#93、TENANT 管理/撤销、Gate A、TEST32、真实受试者。

## 2. 10 条检查与结果

| # | 检查 | 结果 | 证据 |
|---|---|---|---|
| 1 | 种子别名读路径（`CUS_RASA` + `老规矩辣椒酱 2`，uom 不作断言） | **PASS** | `ALIAS_ONLY` / `SKU_CILI_1KG` / `ALS_CACHE_RASA_001`；`raw/01_*` |
| 2 | LLM 候选（`CUS_ALI` + `Milo 2 bag`） | **PASS** | 3/3 LLM；2 候选（1kg 18.00 / 2kg 34.00）；`MULTIPLE_PACK_SIZES`；`raw/02a–02c_*` |
| 3 | 未保存保护 | **PASS** | 选中 1kg 未保存 → Unsaved changes、Approve 置灰；`c11_02_unsaved.jpg` |
| 4 | 保存 + 记忆写入 | **PASS** | v2、`ALI_398DB0744E6F44B985643D81979F4456`、CUSTOMER、RM36.00；键级 alias 0→1；`raw/04_*`、`c11_03_*` |
| 5 | 同句冷态复用 | **PASS** | 10:44:37 `DEGRADED` → `ALIAS_ONLY`、同 alias、0 候选；`raw/05_*`、`c11_04_*` |
| 6 | 数量边界（`Milo 3 bag`） | **NOT_A_DEFECT** | 不命中、2 候选重新出现；phrase 含数量；`raw/06_*` |
| 7 | TENANT 负例（必做） | **PASS** | 403 `FORBIDDEN_ACTION`；draft 仍 v2、alias 未变；`raw/07_*` |
| 8 | 无候选死路（`Sos tiram 2 btl`） | **LIMITATION_RECORDED** | 1 行、0 候选、`NO_CANDIDATE`；无 SKU 选择器；`raw/08c_*`、`c11_05_*` |
| 9 | 零行死路（`ok thanks`） | **LIMITATION_RECORDED** | 0 行、`LOW_CONFIDENCE_MATCH`、无补行入口；`raw/09_*`、`c11_06_*` |
| 10 | 证据完整性 | **PASS** | 8 组 raw、9 张截图、哈希重算；电话脱敏、无响应 Cookie 头、无绝对路径/令牌 |

汇总：**7 PASS / 1 NOT_A_DEFECT / 2 LIMITATION**。第 6 条不参与 PASS 分母；第 8/9 条按限制记录。

## 3. 方法

1. **生产主线**：按 Zhou 10:25 口径，C11 在生产 API 执行；仅写入 `CUS_ALI` 一条 CUSTOMER alias。
2. **LLM 绑定**：第 2 条 3/3 次 `ai_mode=LLM`（2.1–2.3 s），`X-Request-ID` 已存；provider/model 属部署配置（`runpod_adapter` / `Qwen/Qwen2.5-7B-Instruct-AWQ`）。
3. **不调模型**：第 5 条在 `/ai/status=DEGRADED` 冷态执行，响应 `ALIAS_ONLY`、同 alias、0 候选。
4. **记忆范围**：仅 CUSTOMER；键级 alias 行数 0→1；TENANT 负例 403 且不落库。
5. **原始字节**：raw 响应/请求 ID/截图/哈希落盘；电话已脱敏、响应 Cookie 头已删除。
6. **限制不美化**：第 8/9 条只记 `LIMITATION_RECORDED`。

## 4. 证据清单

| 文件 | 说明 |
|---|---|
| `acceptance.json` | 10 条检查、签收、环境、样本、限制、边界 |
| `sample.json` | 样本与期望值 |
| `environment.json` | 生产环境、版本、运行时间、alias 键级行数 |
| `matrix.md` | 10 条逐条期望/实际/证据 |
| `execution_log.md` | 逐请求记录、request ID、冷态轮询、锚点 |
| `raw/` | 49 个原始文件（8 组检查 + 锚点 + 重试 + 请求体；已脱敏） |
| `screenshots/` | 9 张 JPG（6 主 + 3 上下文） |
| `SHA256.txt` | 证据目录逐文件哈希 |

## 5. 已知限制

- **C11-LIM-01**：`NO_CANDIDATE` 行无 SKU 选择器，未开发死路；只记录。
- **C11-LIM-02**：0 行草稿无补行入口；只记录。
- **C11-LIM-03**：别名 phrase 含数量，只有一字不差才命中；第 6 条是语义边界，不是缺陷。
- **C11-LIM-04**：无撤销接口，写入不可逆；`CUS_ALI` + `Milo 2 bag` 已永久 `ALIAS_ONLY`。
- **C11-LIM-05**：预检草稿 3 条，未保存/未批准/未写别名，不计正式证据。

## 6. 边界

- 签收与入库已完成；本包不替代 TEST32 / Gate A / UAT，不改变 UOM 24/31。
- 生产写入仅 `CUS_ALI` 一条 CUSTOMER alias；C04 的 PENDING、C08 的 DO 只读核对前后未变；未 reset、未发版。
- 无 raw model output、无 provider 调用计数（Zhou 10:25 豁免）；全表 alias 计数不需要，键级 0→1 足够。
- TENANT 管理、撤销、D02/#91/#92/#93 不在范围。

## 7. 结论

**`PASS_CANDIDATE_MEMORY_PENDING_REVIEW` / `SIGNED_OFF` / `MERGED`。** 第 1/2/3/4/5/7/10 条 PASS；第 6 条 `NOT_A_DEFECT`；第 8/9 条 `LIMITATION_RECORDED`。逐条证据见 `execution_log.md`、`raw/`、`screenshots/`。

## 8. 演示口径

- `CUS_ALI` + `Milo 2 bag` 现在永久 `ALIAS_ONLY`，不会再出 LLM 候选。
- 展示 LLM 候选请用 `Milo 3 bag` 或另一个客户；不要承诺该客户/该句还能重新学一次。

## 9. 签收与入库

- 技术：Zhou Jingxi，2026-10-31，`SIGNED_OFF`；签收的传输包 SHA-256 `DA9E606A84A73D78796289D89083DC03248C097EF7F1338D19335B497C08621F`（1,539,150 B）。
- 形式：Zhan Zhengrong，`PASS`，索引 `ZR-C11-20261031-01`。
- PR #111 squash merged（`8365c92`）；结项记录 PR #112（`42919b4`）。
