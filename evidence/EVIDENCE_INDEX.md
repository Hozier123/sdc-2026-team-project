# Evidence Archive & Evaluation Index

> [!WARNING]
> **历史基线与质量引用声明**：  
> 本索引中 code_base 为 657ad5d 及更早的所有结果均为 HISTORICAL。  
> 657ad5d 存在 11 处 UOM 错误（把 pack 单位当 uom），已由 PR #46（076ddf1 prefer quantity UOM over pack-size unit）修复。  
> 当前质量一律以 db6f0ce 上的 official 重跑为准；在 official 生成前，旧 23 条与旧 5/6 均不得作为当前质量或验收通过引用。

This document tracks all AI extraction and evaluation runs against canonical inputs (`dev_41_draft.json`, `dev_41_parse_scope.json`, `dev_format_probe_5.json`).

---

## 1. Core Evaluation Runs

| Run Identifier | File | Code Base | Calls | Description / Status | SHA-256 |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **standalone v1** | `dev41_ai_only_v1_2026-10-24.json` | `backend/ai@c66d6f5` | 46 次 (每案2次) | 原独立模块评测（含 extractor 探针 + adapter 校验）。已对外交付。 | `6B1400090CE23D47834A2E849E988012BBC0AD58DBE8CE645737DFDE3C839FC6` |
| **v2 comparison** | `dev41_ai_only_v2_2026-10-24.json` | `standalone-only` | 46 次 | standalone-only，归档不进准确率。归档理由：未在生产代码 db6f0ce 复跑 + 答案键未完全对齐。DEV-21 拆两行→合并一行 = IMPROVEMENT_CANDIDATE；DEV-37 删除 'kalau ada' 商品行、保留 STOCK condition = IMPROVEMENT_CANDIDATE；DEV-37 的 '2kg 的' 仍单独成行 = STRUCTURAL_CHANGE_UNJUDGED。 | `A6529A4D3403649D0E55ABCC785CC636BFDCD7E3E2AF609D06A08958E2BBD119` |
| **v1_prod manual** | `dev41_ai_only_v1_prod_2026-10-24_manual.json` | `app/ai@657ad5d` | 23 次 (每案1次) | HISTORICAL（657ad5d，11 处 UOM 错误，已由 #46 修复），不得作为当前质量引用 | `60A28A7CDC3D5E90F0BCFD584F79136BBEB4347942B105187548ECD717350B46` |
| **v1_prod official** | `dev41_ai_only_v1_prod_2026-10-24.json` | `app/ai@db6f0ce` | 23 次 (每案1次) | CURRENT（23/23 LLM, fallback 0, >4.1s 0, UNKNOWN 9, UOM 11→1） | `BDC444DB8D753311D751EF0FC03151496BE16E4C2BC5746E908C8FF33947942E` |

> [!NOTE]
> **耗时诊断特别标注**：  
> 旧 657ad5d v1_prod 的 DEV-37 = WALL_CLOCK_EXCEEDS_4.1，不是 timeout、不是 fallback。

---

## 2. Supporting Benchmarks & He's 6 Cases

* **He's 6 Cases Acceptance (v1)**: `he_6cases_2026-10-24.txt`  
  HISTORICAL：5 PASS / 1 KNOWN_LIMITATION，prompt 未改，不作为验收通过  
  SHA-256: `645E568F80B9156DF3CEB6BFB83BCBCEBEED128AF06F4EE3967882FEBE002FFB`
* **He's 6 Cases Acceptance (v2)**: `he_6cases_v2_2026-10-24.txt`  
  HISTORICAL：5 PASS / 1 KNOWN_LIMITATION，prompt 未改，不作为验收通过  
  SHA-256: `81B09112AAA9855B2CDEE82BE7787C126512C81250606A636365D7F8B3B92DA6`
* **RunPod Latency Benchmark**: `runpod_benchmark_2026-10-23.txt`  
  SHA-256: `7F6E726D68EC53215D39FEA6DC76B55146D89FF1E6F364E9DAA34A60E21AE69C`
* **Smoke 6 Cases Acceptance**: `smoke_6cases_2026-10-23.txt`  
  SHA-256: `044D2551A07E442FE39F241DC1E83F992E3FA7114A53AC7768A78FBF294DA6D7`

---

## 3. Consistency Verification Rules

当官方窗口开启并由 `eval_dev41_v1_prod.py` 跑出正式 `dev41_ai_only_v1_prod_2026-10-24.json` 后，需与 `dev41_ai_only_v1_prod_2026-10-24_manual.json` 进行一致性比对：
1. UNKNOWN 行数完全一致；
2. Fallback 行数完全一致；
3. `>4.1s` 超时条数完全一致；
4. 各案 span 坐标与切分完全一致。
*注：若差异超过 1 条必须立即停下向负责人汇报，严禁直接覆盖。*
