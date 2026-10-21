# KiraOrder v1.3 后端与 AI 对接规则

> 状态：`HANDOFF_DRAFT`（2026-10-22）  
> 适用基线：`gate0-baseline-v1` / Gate 0 v4 / draft revision 5  
> 基线哈希：`6A44089C623C1B4AE8F444660DBD89422C663E7EBDD141EA6FDA549DDD833770`  
> Canonical：`gate0/`（冻结，不可修改）  
> 本文性质：从 Gate 0 v4 派生的 AI 对接说明；与 `gate0/` 冲突时，**以 `gate0/` 为准**。

---

## 0. 先读这一节

### 0.1 唯一机器可读真相

```text
gate0/contracts/field-evidence.md
gate0/contracts/lexicons/field-evidence-v2.json
gate0/contracts/condition-triggers.md
gate0/contracts/lexicons/condition-triggers-v3.json
gate0/contracts/errors.md
gate0/contracts/fixtures/
gate0/tests/contract/contract_oracles.py
```

本文是派生说明，不替代上述文件。

### 0.2 AI 的边界

AI **不决定**：

```text
价格是否成立
库存是否足够
是否升级给 OWNER
目标行是谁
是否批准
最终 DO
```

AI 只输出：

```text
原文 span
qty / uom / family / pack_size 证据
条件候选
被忽略的片段
```

价格、库存、审批、目标行的最终决定都在后端确定性规则和人工动作里。

### 0.3 禁止修改 Gate 0

- 不修改 `gate0/` 内任何文件；
- 不把 H1/H5 词表复制成第二套硬编码；
- 不修改 `condition-triggers-v3.json` 来“适配 prompt”；
- 发现契约缺口：记录问题，开 `gate0-v5` 流程。

---

## 1. 端到端位置

```text
原始 message_text
  → 后端 PII 掩码
  → masked_text
  → AI / RunPod
  → 原始 rows / conds
  → Adapter 校验
  → 确定性 Resolver
  → OrderDraft
```

AI 永远不接收原始未脱敏消息；Adapter 永远不把 AI 的“猜测”直接写入正式字段。

### 1.1 输入上限

- `masked_text` 最多 **4000 Unicode code points**；
- 超过直接 422 `MESSAGE_TOO_LONG`，不调用 AI；
- 偏移口径固定为 **Unicode code point**，不是 UTF-8 byte，也不是 UTF-16 code unit。

### 1.2 PII

固定三个 token：

```text
[REDACTED_PHONE]
[REDACTED_MYKAD]
[REDACTED_EMAIL]
```

- 只有这三个 token，不使用 `[PHONE]`、`[EMAIL]` 等第二套；
- token 作为完整占位符参与偏移；
- 原始 `message_text` 只在请求作用域内存活；
- 日志、prompt、fixture、DB 的 masked 字段都不得出现原始 PII。

---

## 2. AI 原始输出契约

AI 返回的是**候选**，不是最终订单。

### 2.1 行级字段

```json
{
  "rows": [
    {
      "span": "Tepung 5 ctn",
      "qty": 5,
      "uom": "ctn",
      "fam": "FAM_FLOUR",
      "pack_size": "5kg",
      "conds": []
    }
  ],
  "ignored_spans": []
}
```

要求：

- `span` 必须是 `masked_text` 中的精确子串；
- 同一行只表达一个商品意图；
- 不返回 `sku_id`、价格、库存、审批、DO、目标行；
- 多余字段由 Adapter 丢弃并记录；
- `qty` 允许 integer 或 ASCII 数字字符串（Adapter 可转），其他字符串拒绝；
- `conds` 只表达条件候选，不表达最终价格。

### 2.2 禁止字段

AI 不得返回或决定：

```text
sku_id
unit_price
available_qty
target_line_ids
approval_required
do_number
blocking
resolved
```

这些是后端/人工字段。

---

## 3. H1 v2：字段证据

### 3.1 目标

证明每个业务字段确实来自对应 masked span：

```text
qty
uom
family
pack_size
```

“值合法”不等于“有原文证据”。

### 3.2 定位规则

1. 在 `masked_text` 中唯一定位 `span`；
2. 排除已消费区间；
3. 必须唯一命中，否则当前行 fallback；
4. 归一化只允许 NFKC + casefold + 空白折叠；
5. 匹配在归一化空间执行，但 `start/end` 必须映射回原 masked text 的 code point；
6. 重复文本按行顺序、出现顺序、非重叠约束定位；
7. 无法唯一定位：仅当前行 fallback，不跨行借值。

### 3.3 qty 解析

正式 qty 是正整数，范围 `1..999999`（业务上限可配置）。

支持的语法：

```text
阿拉伯数字：1—999999
马来语：satu/dua/.../sebelas
马来语复合：dua belas、dua puluh、tiga puluh lima
英语：one—twenty、twenty-five、twenty five
中文：一/二/两/.../十、十五、三十五
```

必须：

- 最长匹配优先；
- 不猜拼写；
- 不使用编辑距离；
- 不跨 span 借值；
- 0、负数、小数、非法格式 → `INVALID_QUANTITY`；
- 两个以上互不重叠的不同 qty 候选 → `AMBIGUOUS_QUANTITY`，不选最早值。

### 3.4 金额、编码、单价限定词

必须先做**保长掩码**，再做候选：

```text
RM95 / RM 2.50        → 金额，不是 qty
A95 / stock code A95  → 编码，不是 qty
RM2.50 satu           → satu 是单价限定词，不是 qty=1
RM95 untuk 1 ctn      → 1 是单位价表达式，不是订单 qty
```

示例：

| 输入 | qty |
|---|---:|
| `kalau RM95 boleh 3 ctn` | 3 |
| `RM95 for 5 ctn` | 5 |
| `Milo RM2.50 satu, 10 ctn` | 10 |
| `RM95 untuk 1 ctn, ambil 5` | 5 |
| `Milo satu 10 ctn` | `AMBIGUOUS_QUANTITY` |

### 3.5 小数守卫

- 点号小数：`1.5kg`、`0.5 ctn` → 无 qty + `INVALID_QUANTITY`；
- 逗号只有在后接单位时才是小数：`1,5kg` 阻断；
- `12, 3 pack` 的逗号是列表分隔，不是小数；
- 不能因为金额 `RM12.50` 把合法的 `4 pack` 一起杀掉。

### 3.6 pack_size

规格数字不是订货数量：

```text
500g
2kg
5kg x 2
12 x 1L
```

示例：

| 输入 | qty | pack_size |
|---|---:|---|
| `美禄 500g 装, 3 包` | 3 | 500g |
| `Minyak 12 x 1L, 5 ctn` | 5 | 12 x 1L |
| `Tepung 5kg x 2` | 2 | 5kg |
| `Milo 2kg, 4 ctn` | 4 | 2kg |
| `10kg bawang` | 10 | null |

`10kg bawang` 只有一个数量候选，按 qty 处理；只有出现另一个 qty 候选或 `x/装` 规格形态时才把 spec 掩掉。

### 3.7 uom

- 匹配必须在 NFKC + casefold 后进行；
- `5 CTN`、`10KG` 必须命中；
- 只接受版本化 aliases / tenant extensions；
- 不得使用私有硬编码补充表；
- P0 不自动做单位换算。

### 3.8 family

- 只接受当前租户正式族名、`family_aliases`、当前客户已确认别名；
- 必须精确命中 span；
- 多 exact 命中无法唯一归属 → `FAMILY_NOT_EVIDENCED` / `UNKNOWN`。

### 3.9 H1 错误映射

| 情况 | reason_code |
|---|---|
| 无 qty、0/负数、小数、非法格式 | `INVALID_QUANTITY` |
| 多个不同 qty 候选 | `AMBIGUOUS_QUANTITY` |
| 模型值无证据 | `FIELD_NOT_EVIDENCED` |
| 商品族无证据 | `FAMILY_NOT_EVIDENCED` |
| 重叠 span | `OVERLAPPING_SPAN` |
| 重复完全一致项 | `DUPLICATE_SPAN` |

失败只降级当前行；不能静默形成确定 SKU+数量。

### 3.10 实现注记（很重要）

Gate 0 v4 的 `field-evidence.md` 第 39 行仍保留旧 pipeline 描述：

```text
EXCLUDE_AMOUNT → EXCLUDE_CODE → DECIMAL_GUARD → CANDIDATES
```

实际可执行顺序在 `contract_oracles.py` / `field-evidence-v2.json` 中，按下面实现：

```text
1. 单价限定词掩码（RM...satu/each/per/untuk 1）
2. 金额掩码
3. 编码掩码
4. pack_size 条件掩码
5. 小数守卫
6. qty 候选 + 多候选判定
```

这是 Gate 0 v4 的**文字与 oracle 不一致**，不改变冻结基线；实现以 oracle 为准，文档差异记录给 `gate0-v5` 修正。不要修改 `gate0/`。

---

## 4. H5 v3：条件触发

### 4.1 触发原则

1. PRICE 必须是明确议价短语，或“金额 + 条件/询价语气”；
2. 裸 `RM95` 不单独触发；
3. STOCK 必须命中库存条件短语；
4. 同一片段允许多标签，例如 `kalau ada, boleh kurang` → STOCK + PRICE；
5. 历史词不永久抑制；显式询价可以覆盖：
   `Can follow last price RM95?` 仍触发 PRICE；
6. PRICE 必须记录 `condition_scope / target_line_ids / requested_unit_price / price_basis`；
7. P0 只执行 `price_basis=UNIT`；`TOTAL/UNKNOWN` 必须澄清，不能自行除法；
8. `NOT_A_CONDITION` 必须带非空 note，并写 `CONDITION_DISMISSED` 活动。

### 4.2 16 行真值表

| # | 输入 | 结果 |
|---:|---|---|
| 1 | `Last order was RM95.` | 不生成 |
| 2 | `Total last time RM95.` | 不生成 |
| 3 | `kalau RM95 boleh` | PRICE，默认 UNKNOWN |
| 4 | `RM95?` | PRICE |
| 5 | `boleh kurang sikit?` | PRICE |
| 6 | `kalau ada, boleh kurang` | STOCK + PRICE |
| 7 | `If available, send 5 ctn` | STOCK，不阻断 |
| 8 | `hantar esok` | 不生成 |
| 9 | `Stock code A95` | 不生成 |
| 10 | `RM95 for 5 ctn` | PRICE，UNKNOWN，阻断 |
| 11 | `Can follow last price RM95?` | PRICE |
| 12 | `kalau RM95 untuk 1 ctn` | PRICE，UNIT，阻断直到接受 |
| 13 | `can less?` | PRICE |
| 14 | `老价钱?` | PRICE |
| 15 | `harga lama?` | PRICE |
| 16 | `boleh diskaun?` | PRICE |

### 4.3 阻断规则

- **STOCK 条件本身 `blocking=false`**；
- 缺货由行级 `INSUFFICIENT_STOCK(blocking=true)` 单独阻断；
- PRICE 默认 `blocking=true`，直到 target、UNIT basis、有效目标行成交价与理由满足；
- `condition_scope=UNKNOWN` 且 `target_line_ids=[]` → `TARGET_LINE_REQUIRED`；
- 接受价格只修改 `target_line_ids`，不能改非目标行。

### 4.4 词表与上下文

- 触发正则在 NFKC + casefold + 空白折叠后执行；
- `negative_contexts` / `context_markers` 从 `condition-triggers-v3.json` 读取；
- 不允许在 prompt 或代码里再写第二套否定词；
- `requires_context=true` 的 trigger 必须在 context marker 命中、negative context 未命中时触发。

### 4.5 价格字段

- 金额用 decimal string，不用 binary float；
- 只有明确单位价才填 `requested_unit_price`；
- `price_basis=UNKNOWN` 时 `requested_unit_price=null`；
- `RM95 for 5 ctn` 不能自动算 19.00；
- `RM95 untuk 1 ctn` 才是 UNIT；
- `price_basis` 闭集只有 `UNIT/TOTAL/UNKNOWN`。

---

## 5. Adapter 与降级

### 5.1 Adapter 做什么

```text
校验 JSON shape
定位 span
丢弃额外字段
比较模型值 vs 确定性候选
计算 evidence start/end
合并客户别名
映射 reason_code
```

Adapter 由后端维护，不由 AI 直接写正式字段。

### 5.2 不允许多候选猜值

- qty 多候选 → 当前行 `AMBIGUOUS_QUANTITY`；
- family 多命中 → `FAMILY_NOT_EVIDENCED` / `UNKNOWN`；
- 不允许“取第一个”“取最像”“让模型再选一次”。

### 5.3 单行降级

- 单行失败不影响其他行；
- qty/family 失败必须阻断或单行 fallback；
- 不得静默生成确定 SKU+数量；
- 失败信息只写结构化诊断，不写原文 PII。

### 5.4 别名与 RapidFuzz

- 先客户已确认 alias，再租户 alias；
- 同名多义不自动选；
- RapidFuzz 只做候选排序，不做最终决定；
- P0 阈值/候选由后端配置固定，AI 不参与。

---

## 6. AI 状态、超时与唤醒

### 6.1 状态

`/api/v1/ai/status` 返回：

```text
state: OFFLINE | WARMING | READY | DEGRADED
available_modes
last_error（安全文案）
```

### 6.2 超时

- AI 超时不能阻塞整个请求；
- 超时后走单行 fallback 或明确 503；
- 不把超时当“无字段”静默成功。

### 6.3 唤醒

`POST /api/v1/ai/wake`：

- 成功 200；
- 频率限制 429 `RATE_LIMITED`；
- 不可用 503 `AI_AND_FALLBACK_UNAVAILABLE`；
- 前端按 `Retry-After` 延迟。

---

## 7. 测试与验收

### 7.1 必跑

```text
H1 required_cases = 35
H5 truth_table = 16
Gate 0 contract tests = 42 passed
```

重点用例：

```text
H1-PACK-1—4
H1-AMB-1
H1-UPM
H1-UNIT-PRICE
H1-DEC-COMMA-NEG
H1-UOM-PLURAL
H5 16 行
```

### 7.2 禁止硬编码

- 不得复制一份 H1 词表到 prompt；
- 不得复制一份 H5 否定词到代码；
- 词表从 `field-evidence-v2.json` / `condition-triggers-v3.json` 读取；
- oracle 与实现必须可回归。

### 7.3 交付清单

- [ ] PII 掩码通过三 token 测试
- [ ] H1 35 例通过
- [ ] H5 16 例通过
- [ ] `AMBIGUOUS_QUANTITY` 有测试
- [ ] `pack_size` 有测试
- [ ] 多标签 STOCK+PRICE 有测试
- [ ] 历史否定/显式询价有测试
- [ ] 超时/降级有测试
- [ ] 不修改 `gate0/`

---

## 8. 交接问题格式

```text
契约项：
Gate 0 文件：
输入：
期望：
实际：
是否阻断：
```

不要直接改 Gate 0；需要契约变更时开 `gate0-v5`。
