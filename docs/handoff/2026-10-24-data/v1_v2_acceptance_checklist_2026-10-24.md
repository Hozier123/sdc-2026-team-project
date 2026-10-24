# v1 → v2 Prompt 对照验收清单（2026-10-24）

## 1. 固定输入

- `dev_41_draft.json` SHA-256：`5529443897C7B718DF1D8064A3C668AFEAA0755E9DD032B4596AF96180F8AD40`
- `dev_41_parse_scope.json` SHA-256：`6AE86B6B4CE58EB546A27EBDAE2E9C3F2608040A332836E47B802F0659F128F0`
- AI-only：23 条；resolver-only：DEV-02/08/23，另行验收。
- 统一 `adapter_mode=RUNPOD_REAL`、`timeout_s=4.1`；预热 180s 单独记录，不混入 warm latency。
- 每组 evidence 必须记录：`prompt_version`、数据 SHA、scope SHA、case_ids、模型 ID、`fallback_count`、每条 latency、`exceeds_production_timeout`。

## 2. 顺序

1. **v1 基线**：23 条 AI-only，先跑；保存 evidence v1，不覆盖。
2. **v2 对照**：同一 23 条 + He 6 条；prompt 只加通用 exact-whitelist 规则；示例从当前租户 whitelist 动态生成。
3. v2 不得覆盖 v1；两套结果同时保留。

## 3. 计分

### AI-only 23 条

- family：exact tenant ID 才算对；`FAM_EGG`、`FAM_CHILI` 等近似 ID 记 `UNKNOWN` + `KNOWN_MODEL_LIMITATION`，不算对。
- span：必须 verbatim、可定位、不越界。
- qty：正整数或 null；非法小数/金额误入 qty 记错。
- uom / pack_size：原样命中；pack_size 缺失或截断记错。
- conditions：PRICE/STOCK/OTHER 的类型和原文 span 必须对。
- 状态与 issue：按 `dev_answers_partial_ai23.json` 的 `DRAFT_PARTIAL` 口径比较；未填字段不强行判分。

### He 6 条 generic samples

- `family_scored=false` / `GENERIC_CONTRACT_SAMPLE`。
- 只评 span / qty / uom / pack_size / conditions；不评 family。
- `normal.json` 的 span 漏 `1kg` 仍是 pack_size 失败，不因 B 变 PASS。
- `empty.json` 的 ignored_spans 按 normalized coverage 判：verbatim、不重叠、覆盖差集为空、不吞业务 token；否则 REVIEW。

### resolver-only 3 条

- DEV-02 / DEV-08 / DEV-23 不计 AI-only 分母。
- 按 `dev_answers_resolver_only_3.json` 的 exact alias / SKU / qty / uom / status 验收。
- 若 resolver 仍走 AI 并产生 `FAM_CHILI` 等近似 ID，记 resolver 路由问题，不记数据问题。

## 4. v2 采用规则（预先登记）

只有同时满足以下条件才采用 v2：

1. AI-only 23 条的 family exact 命中数 **增加**；
2. span / qty / uom / pack_size 没有新增回归；
3. He 6 条除 family 外的维度没有新增回归；
4. `normal.json` 的 pack_size 失败没有被“隐藏”或改判 PASS；
5. v2 evidence 可复现，prompt 版本和 whitelist 注入方式可查。

任一条件不满足：保留 v1 进材料，v2 只作为实验记录。

## 5. 产物

- `evidence/v1_ai23_*.json`
- `evidence/v2_ai23_he6_*.json`
- `evidence/dev_probe5_*`（如重跑）
- 对照摘要：每案 `v1/v2` 的 family、span、qty、uom、pack_size、conditions、latency、fallback 差异。
- 最终材料只引用被选中的版本，同时保留另一版作为附录。
