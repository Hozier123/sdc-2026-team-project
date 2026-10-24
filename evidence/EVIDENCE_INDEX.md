# Evidence Archive & Evaluation Index

> [!NOTE]
> **Hash Convention（哈希计算口径）**：  
> 所有 SHA-256 均按 git blob（LF 归一化后）计算：  
> `git cat-file blob <rev>:evidence/<file> | sha256sum`  
> Windows 工作区因 `core.autocrlf` 显示 CRLF，直接对文件哈希会得到不同值。

> [!WARNING]
> **历史基线与质量引用声明**：  
> 本索引中 code_base 为 657ad5d 及更早的所有结果均为 HISTORICAL。  
> 657ad5d 存在 11 处 UOM 错误（把 pack 单位当 uom），已由 PR #46（076ddf1 prefer quantity UOM over pack-size unit）修复。  
> 当前质量一律以 db6f0ce 上的 official 重跑为准；在 official 生成前，旧 23 条与旧 5/6 均不得作为当前质量或验收通过引用。

> [!NOTE]
> **Official UOM known gap**：db6f0ce official 共 31 行，其中 1 行为
> `KNOWN_UOM_INJECTION_GAP`：`4 botol minyak 5kg` 的 `botol` 未识别为 UOM。
> T1 seed 已有 `ALS_UOM_007`（botol→btl），但 H1 adapter 只读
> `tenant_uom_extensions` / H1 lexicon，不读 DB `uom_aliases`。
> 这不是数据缺口，也不能写“UOM 全通过”；本期不改 seed、不升 Gate0。
> 未来清零方案：由代码侧把 tenant `uom_aliases` 注入 adapter，再重跑 23 条。

This document tracks all AI extraction and evaluation runs against canonical inputs (`dev_41_draft.json`, `dev_41_parse_scope.json`, `dev_format_probe_5.json`).

---

## 1. Core Evaluation Runs

| Run Identifier | File | Code Base | Calls | Description / Status | Git Blob SHA-256 |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **standalone v1** | `dev41_ai_only_v1_2026-10-24.json` | `backend/ai@c66d6f5` | 46 次 (每案2次) | 原独立模块评测（含 extractor 探针 + adapter 校验）。已对外交付。 | `A0E72CA7EE03323AAC61D7119A3B866471B1BDE8ECE67CE1C7953917734B080D` |
| **v2 comparison** | `dev41_ai_only_v2_2026-10-24.json` | `standalone-only` | 46 次 | standalone-only，归档不进准确率。归档理由：未在生产代码 db6f0ce 复跑 + 答案键未完全对齐。DEV-21 拆两行→合并一行 = IMPROVEMENT_CANDIDATE；DEV-37 删除 'kalau ada' 商品行、保留 STOCK condition = IMPROVEMENT_CANDIDATE；DEV-37 的 '2kg 的' 仍单独成行 = STRUCTURAL_CHANGE_UNJUDGED。 | `1C161DD563689481035F71FEAFA3D8C96EB44ADDE77829878448ACF8A938A72E` |
| **v1_prod manual** | `dev41_ai_only_v1_prod_2026-10-24_manual.json` | `app/ai@657ad5d` | 23 次 (每案1次) | HISTORICAL（657ad5d，11 处 UOM 错误，已由 #46 修复），不得作为当前质量引用 | `97C40A701A5385B50C38A27795CF099FC1DA15FCB5E6792B7862D8F1C797823D` |
| **v1_prod official** | `dev41_ai_only_v1_prod_2026-10-24.json` | `app/ai@db6f0ce` | 23 次 (每案1次) | CURRENT（23/23 LLM, fallback 0, >4.1s 0, UNKNOWN 9；UOM 30/31，1 处 KNOWN_UOM_INJECTION_GAP=`botol`） | `17F44B9B83CF0039FA3C5FE6410AC2C68152D2D96C54CA9E849899F4061A87CD` |

> [!NOTE]
> **耗时诊断特别标注**：  
> 旧 657ad5d v1_prod 的 DEV-37 = WALL_CLOCK_EXCEEDS_4.1，不是 timeout、不是 fallback。

---

## 2. Supporting Benchmarks & He's 6 Cases

* **He's 6 Cases Acceptance (v1)**: `he_6cases_2026-10-24.txt`  
  HISTORICAL：5 PASS / 1 KNOWN_LIMITATION，prompt 未改，不作为验收通过  
  Git Blob SHA-256: `E2CB3F57D4B81FD5A2691045211B8A54691EFB76D81403FAF67B1AD625B4D3D5`
* **He's 6 Cases Acceptance (v2)**: `he_6cases_v2_2026-10-24.txt`  
  HISTORICAL：5 PASS / 1 KNOWN_LIMITATION，prompt 未改，不作为验收通过  
  Git Blob SHA-256: `F0A5DA58F23BAB8B4C034A68402E39698D604F93EF026F06E38BFA58B74A7ACA`
* **RunPod Latency Benchmark**: `runpod_benchmark_2026-10-23.txt`  
  Git Blob SHA-256: `007BC0EFF020CB6F3F33D44D63399C1E60F900124AD853252BD2D203F278F8BC`
* **Smoke 6 Cases Acceptance**: `smoke_6cases_2026-10-23.txt`  
  Git Blob SHA-256: `B3DBEF00E09DE2AD79A6791E7970E99702A8EE95DDADF68A6399A37B657AF95C`
* **dev_probe5 Probe Run**: `dev_probe5_2026-10-24.json`  
  Git Blob SHA-256: `9989AE2416183A2880700DC8541C210BF6CD601F2B21E19DBBEAE3DD667B7EC7`
* **eval_dev Preliminary Run**: `eval_dev_2026-10-23.json`  
  Git Blob SHA-256: `806B77BAC3BBD68D919609914608E3CA4A6DDBC5FE58A0D9EA2067743ED92337`

---

## 3. Consistency Verification Rules

当官方窗口开启并由 `eval_dev41_v1_prod.py` 跑出正式 `dev41_ai_only_v1_prod_2026-10-24.json` 后，需与 `dev41_ai_only_v1_prod_2026-10-24_manual.json` 进行一致性比对：
1. UNKNOWN 行数完全一致；
2. Fallback 行数完全一致；
3. `>4.1s` 超时条数完全一致；
4. 各案 span 坐标与切分完全一致。
*注：若差异超过 1 条必须立即停下向负责人汇报，严禁直接覆盖。*
