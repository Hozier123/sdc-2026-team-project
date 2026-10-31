# Evidence Archive & Evaluation Index

## Final-Round Status Addendum (2026-10-31)

- [D01 data versions and snapshot gap](../docs/handoff/d01-data-status-2026-10-31.md): PARTIAL / SNAPSHOT_PENDING; private answers and inputs are not published.
- [D02 scoped backend closeout](../docs/audit/d02-uom-blocking-2026-10-31.md): DONE_WITH_KNOWN_LIMITATIONS; UOM remains 24/31, not a new model-quality result.
- [D06 public citation index](../docs/audit/d06-public-citation-index-2026-10-31.md): CLOSEOUT_DRAFT / PENDING_ZHOU_REVIEW; new citations are not new signatures or experiments. Formal TEST32 and D05 remain NOT_RUN in the current review record.
- The historical hash convention below is not universal for later evidence: PR91 deployment JSON has distinct repository-LF and manifest-CRLF hashes. Use the object-specific values in the D06 addendum; do not silently normalize a raw-byte verification.

The historical run index below is retained unchanged.

> [!NOTE]
> **Hash Convention（哈希计算口径）**：  
> 所有 SHA-256 均按 git blob（LF 归一化后）计算：  
> `git cat-file blob <rev>:evidence/<file> | sha256sum`  
> Windows 工作区因 `core.autocrlf` 显示 CRLF，直接对文件哈希会得到不同值。校验清单见 `evidence/SHA256.txt`。

> [!WARNING]
> **历史基线与质量引用声明**：  
> 本索引中 code_base 为 657ad5d 及更早的所有结果均为 HISTORICAL。  
> 657ad5d 存在 11 处 UOM 错误（把 pack 单位当 uom），已由 PR #46（076ddf1 prefer quantity UOM over pack-size unit）修复。  
> 当前质量一律以 db6f0ce 上的 official 重跑为准；在 official 生成前，旧 23 条与旧 5/6 均不得作为当前质量或验收通过引用。

> [!NOTE]
> **Official UOM known gaps（7 处 / 31 行）**：db6f0ce official 是
> `CURRENT_WITH_KNOWN_UOM_GAPS`，不是“UOM 全通过”。
> - `KNOWN_UOM_INJECTION_GAP`（3 处）：DEV-07 `botol`、DEV-13/27 `pail`。
>   T1 seed 已有 botol/pail alias，但 H1 adapter 只读 H1 lexicon /
>   `tenant_uom_extensions`，不读 DB `uom_aliases`。
> - `BULK_KG_REGRESSION`（4 处）：DEV-01/05/11/33 的散装 `kg` 被 PR #46
>   的 pack-size 排除误伤，`kg→None`；这是本轮新回归，不是数据错误。
> 本期不改 seed、不升 Gate0；未来代码分两层修：
> 1) 注入 tenant `uom_aliases`（botol/pail）；
> 2) 区分 bulk product 的 `kg` 与 pack-size `kg`（4 处 bulk-kg）。
> 修完必须重跑 23 条并替换 official evidence。

This document tracks all AI extraction and evaluation runs against canonical inputs (`dev_41_draft.json`, `dev_41_parse_scope.json`, `dev_format_probe_5.json`).

---

## 1. Core Evaluation Runs

| Run Identifier | File | Code Base | Calls | Description / Status | Git Blob SHA-256 |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **standalone v1** | `dev41_ai_only_v1_2026-10-24.json` | `backend/ai@c66d6f5` | 46 次 (每案2次) | 原独立模块评测（含 extractor 探针 + adapter 校验）。已对外交付。 | `A0E72CA7EE03323AAC61D7119A3B866471B1BDE8ECE67CE1C7953917734B080D` |
| **v2 comparison** | `dev41_ai_only_v2_2026-10-24.json` | `standalone-only` | 46 次 | standalone-only，归档不进准确率。归档理由：未在生产代码 db6f0ce 复跑 + 答案键未完全对齐。DEV-21 拆两行→合并一行 = IMPROVEMENT_CANDIDATE；DEV-37 删除 'kalau ada' 商品行、保留 STOCK condition = IMPROVEMENT_CANDIDATE；DEV-37 的 '2kg 的' 仍单独成行 = STRUCTURAL_CHANGE_UNJUDGED。 | `1C161DD563689481035F71FEAFA3D8C96EB44ADDE77829878448ACF8A938A72E` |
| **v1_prod manual** | `dev41_ai_only_v1_prod_2026-10-24_manual.json` | `app/ai@657ad5d` | 23 次 (每案1次) | HISTORICAL（657ad5d，11 处 UOM 错误，已由 #46 修复），不得作为当前质量引用 | `97C40A701A5385B50C38A27795CF099FC1DA15FCB5E6792B7862D8F1C797823D` |
| **v1_prod official (raw)** | `dev41_ai_only_v1_prod_2026-10-24.json` | `app/ai@db6f0ce` | 23 次 (每案1次) | CURRENT_RAW_ARTIFACT（官方运行产出的原始评测结果，未追加顶层元数据字段；指标 23/23 LLM, fallback 0, >4.1s 0, UNKNOWN 9） | `17F44B9B83CF0039FA3C5FE6410AC2C68152D2D96C54CA9E849899F4061A87CD` |
| **v1_prod official (annotated)** | `dev41_ai_only_v1_prod_2026-10-24.annotated.json` | `app/ai@db6f0ce` | 23 次 (每案1次) | CURRENT_WITH_KNOWN_UOM_GAPS (7)（追加 5 项顶层元数据；UOM 24/31，含 7 处已知缺口：botol/pail 注入缺口 3 处 + bulk-kg 回归 4 处） | `05959A4EE85D01C6BBD17E0ABC65ACE893DECE9FD005294CF2B202471B961E87` |

> [!NOTE]
> **耗时诊断特别标注**：  
> 旧 657ad5d v1_prod 的 DEV-37 = WALL_CLOCK_EXCEEDS_4.1，不是 timeout、不是 fallback。

---

## 2. Supporting Benchmarks & He's 6 Cases

> **Canonical six source of truth**：`docs/ai_contract/samples/`。
> 本仓库不复制第二份样例；6 个源文件 blob SHA 见
> `evidence/samples/canonical-6/SHA256.txt`，口径为
> `family_scored=false / GENERIC_CONTRACT_SAMPLE`。
>
> **Byte-level variant notice**：final 6-case 报告 header 记录的是运行时使用的
> byte-level 变体 SHA（normal=`7E479ABB…`），不是 canonical-6 的文件 SHA
> （normal=`FD4CD18E…`）。Xiong 已逐文件比对：6 个文件的
> `input.masked_text` 与 `expected_response` 全部 deep-equal，结果可复现；
> 审计时不是样例不一致。Canonical source 仍是 `docs/ai_contract/samples/`。

* **He's 6 Cases Acceptance (Final)**: `he_6cases_final_2026-10-24.txt` | `app/ai@db6f0ce` | 6 次真机  
  CURRENT_FINAL_6CASES；5 PASS / 1 KNOWN_LIMITATION (normal.json = MODEL_SPAN_TRUNCATED)  
  Git Blob SHA-256: `8223C89E15F12046CAFA1E13C0E66BB605E3053C4E1CEC30A6382519204EE2EE`
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

---

## 4. Blocker Evidence

| Run | File | Status | Known defect | Original SHA-256 |
| :--- | :--- | :--- | :--- | :--- |
| T1 E2E 23 (pre-PR55) | `e2e/blocker/t1_e2e_23_2026-10-24.json` | `BLOCKER_EVIDENCE`；不是 current E2E / READY / 通过 | DEV-01 `10kg Bawang` 误选 `SKU_BAWANG_10KG`（bag），10×32=320；应为 bulk KG，10×3.50=35。PR #55 `c93d6d0` 已阻断自动选 SKU。 | `97FEE66743809D748E4C571749777D69D0CF2B01F6AAA8770C16289AB8F390D8` |

> 该文件保留 Zhou 的原始 CRLF 字节；`git blob` 与工作区 SHA 一致，仅作 blocker 归档，不进入 current 结果。

---

## 5. E2E Evidence (separate from AI-only index)

| Run | File | Code Base | Result | Original SHA-256 |
| :--- | :--- | :--- | :--- | :--- |
| T1 E2E post-PR55 | `e2e/post55/t1_e2e_23_2026-10-24_post55.json` | `c93d6d0` | `E2E_POST55`；23/23 HTTP+LLM, fallback 0；7 READY / 16 DISAMBIGUATION_REQUIRED；DEV-01 已修复为 MISSING_UOM + 候选；UOM None 仍 9 处。不是 23/23 E2E 通过。 | `DCA16B6E5DBC54AB712C1FD1133DFA13CF5083A397B56CCA99CBE41363DAC4C0` |
| T2 E2E | `e2e/t2/t2-e2e-active-20261024.json` | `c93d6d0` | `T2_E2E_PASS`；/me 200 T2/CLERK；parse 200，ai_mode=LLM，request-id `t2-e2e-active-20261024`，lines=1，uom=ctn。 | `70A1BF9B9ACADECF8764C0CF1B748CB9D9B9DC85BE1444C3F92CA1E5E19ACDB8` |

> 该文件保留 Zhou 的原始 CRLF 字节；独立于 AI-only 索引，不覆盖旧 97FEE blocker。

---

## 6. RunPod Platform Proof

| Proof | Files | Status |
| :--- | :--- | :--- |
| RunPod 2026-10-24 | `runpod/2026-10-24/runpod-overview-2026-10-24.png`、`runpod-workers-zero-2026-10-24.png`、`runpod-logs-shutdown-2026-10-24.png` | Usage proof only；Active=0、0 running、$0.00000/s、balance $13.38、shutdown complete 20:25:10 +08:00；不是 AI 全量验收。 |
