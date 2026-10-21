# KiraOrder H1 确定性字段证据契约

> 状态：`GATE0_DRAFT` / `field-evidence-v2`（2026-10-22 rev3：pack_size、多候选、uom 复数）  
> 目标：证明 AI 给出的每个业务字段确实来自对应 masked span；“值合法”不等于“有原文证据”。

PII 掩码公共 token 固定为 `MASK_TOKENS = [REDACTED_PHONE] | [REDACTED_MYKAD] | [REDACTED_EMAIL]`。后端必须在持久化、日志记录和 AI 调用前替换；不得使用 `[PHONE]`、`[EMAIL]` 等第二套简写。token 作为一个完整占位符参与 Unicode code point 偏移计算。

## 1. 不可变规则

1. **先定位**：模型 `span` 必须唯一定位到 masked message 的 Unicode code point 半开区间 `[start,end)`。
2. **重复文本**：相同 span 文本重复出现时，只能按模型行顺序、出现顺序和非重叠约束确定位置；仍不唯一则仅该行 fallback。重复项若字段证据与已消费项完全一致，判 `DUPLICATE_SPAN` 去重；证据不同则保留为不同行。
3. **数量**：只从已定位 span 解析完整阿拉伯数字 token 或下表数字词；**最长匹配优先**；不使用编辑距离、LLM 二次猜测或跨 span 借值。
4. **小数/金额**：**先**用 `qty_exclude_pattern`/`code_exclude_pattern` 做**保长掩码**剔除金额与编码 token，**再**在掩码后的串上执行小数守卫；守卫命中则该字段不产生 qty 候选，直接 `LOW_CONFIDENCE_MATCH(reason_code=INVALID_QUANTITY)`。qty 候选必须排除货币金额 token（`RM`/`RM\s*` 紧邻的数字）和日期/编码 token；剔除必须保长，不能改变后续 offset。
5. **单位/规格/等级**：只接受版本化 exact alias 或明确正则；只允许 Unicode NFKC、大小写和空白归一化，不能模糊替换字符含义。
6. **商品族**：当前租户正式族名、`family_aliases` 或当前客户已确认 alias 必须在该 span 中精确命中。
7. **多候选**：若候选不能唯一关联当前商品行，不选“最像”的值；保留阻断疑点。
8. **边界强类型**：正式 qty 是 integer。模型仅返回 ASCII 数字字符串时，Adapter 可转 integer 并记录 `MODEL_TYPE_COERCED`；**类型转换后仍必须与确定性候选比对**，不相等仍产生 `LOW_CONFIDENCE_MATCH/FIELD_NOT_EVIDENCED`。其他字符串拒绝。
9. **失败隔离**：无效字段不进入 Resolver、不写普通日志；只降级当前行。qty/family 失败必须阻断或单行 fallback，不能静默形成确定 SKU+数量。

## 2. 规范化、定位与投影

```text
input: masked_text, ordered raw AI items
if len(masked_text) > 4000 code points:
    return 422 MESSAGE_TOO_LONG     # 不进入定位，不调用 AI
for each item:
  locate exact span text in masked_text
  exclude already consumed overlapping ranges
  require exactly one valid range
  normalize only NFKC + casefold + whitespace collapse
  match in normalized space
  map every start/end back to masked_text code point index
  parse field candidates inside this range
  compare model values with deterministic candidates
```

- offset 口径固定为 Unicode code point，而非 UTF-8 byte 或 UTF-16 code unit。
- 归一化会改变长度：匹配在归一化空间执行，但 `start/end` 必须通过 index 映射回 `masked_text` 的原始 code point；禁止直接使用归一化串的 index。
- qty pipeline 固定为 `EXCLUDE_AMOUNT → EXCLUDE_CODE → DECIMAL_GUARD → CANDIDATES`；金额/编码剔除使用等长空格掩码，保证候选 offset 可直接回投。
- `parse_quantity` 必须返回 qty 的 `start/end`（span 坐标系）；Adapter 再用 index 映射回 masked text。只有 qty 值、没有证据 offset 的实现不合格。
- `masked_message`、`inbound_messages.masked_text`、span 示例和 AI 输入只允许三个版本化 PII token；原始 `message_text` 只在请求作用域内存活。
- 完全相同区间的重复模型项去重并记录 `DUPLICATE_SPAN` 诊断。
- 不同但重叠的区间不得静默合并：对完整强边界片段重新 fallback，或产生 `LOW_CONFIDENCE_MATCH(reason_code=OVERLAPPING_SPAN)`。
- 证据保存 `raw_text/start/end/normalizer_version`；`raw_text` 必须已经脱敏。

## 3. qty 词表与语法

所有 token 必须有词边界并位于当前 span。正式数量范围为正整数；业务上限由请求校验配置决定。

| 语言 | 基础 token | 值/规则 |
|---|---|---|
| 通用 | `1`—`999999` | ASCII 正整数；前导 `+/-`、小数、0 不接受；**先排除 `RM` 金额与 `A95` 这类编码** |
| ms | `satu/dua/tiga/empat/lima/enam/tujuh/lapan/delapan/sembilan/sepuluh/sebelas` | 1—11；`lapan/delapan` 同值 |
| ms | `<dua..sembilan> belas` | 12—19；exact two-token grammar |
| ms | `<dua..sembilan> puluh [satu..sembilan]` | 20—99；可选个位 |
| en | `one..twenty` | 1—20 |
| en | `<twenty..ninety>[- ]<one..nine>` | 21—99；只接受标准十位词 |
| zh | `一/二/两/三/四/五/六/七/八/九/十` | 1—10；`两=2` |
| zh | `十<一..九>` / `<二..九>十[一..九]` | 11—99；确定性十进制语法 |

- **最长匹配优先**：先尝试 `belas/puluh/十X/X十Y/EN compound`，失败再退单字 token；禁止依赖 dict 迭代顺序。
- 小数守卫正则：`(?<![\d.,])\d+\s*[.,]\s*\d+(?![\d.,])`；`1.5kg`、`0.5 ctn` 必须无 qty 候选 + `INVALID_QUANTITY`。
- 金额排除正则：`(?i)\brm\s*\d+(?:\.\d{1,2})?`；`kalau RM95 boleh 3 ctn` 的 qty 是 3，不是 95。
- 数字词匹配大小写不敏感，但不得容错拼写。`one` 出现在产品名且没有当前行 UOM/商品边界时不能单独建立 qty 关联。

## 4. uom 词表

| canonical | exact aliases（NFKC/casefold 后） |
|---|---|
| `ctn` | `ctn`, `carton`, `cartons`, `箱` |
| `pack` | `pack`, `packs`, `packet`, `packets`, `包` |
| `kg` | `kg`, `kilogram`, `kilograms`, `公斤`, `千克` |
| `pc` | `pc`, `pcs`, `piece`, `pieces`, `个`, `件` |
| `bag` | `bag`, `bags`, `袋` |

数据库 `uom_aliases` 是租户可扩展真相；本表是 Gate 0 最小 seed。**P0 loader 必须读取租户级 `uom_aliases`**，并与 `products.base_unit` 校验；本表不是封闭集。租户扩展示例：

| seed alias | canonical | 说明 |
|---|---|---|
| `btl` | `btl` | bottle |
| `can` | `can` | can |
| `papan` | `papan` | tray |
| `pkt` | `pack` | packet |
| `tin` | `tin` | tin |
| `box` | `box` | box |
| `roll` | `roll` | roll |
| `unit` | `pc` | 仅当 SKU `base_unit=pc`；否则保留 `unit` |

- 粘连写法（`10kg`、`10 kg`）都必须识别为 `qty=10, uom=kg`；`10kg bawang` 的 `kg` 归 uom，`bawang` 归商品族/描述。**uom 匹配必须在 NFKC+casefold 后的串上执行**，`5 CTN`、`10KG` 必须命中。
- P0 不用单位别名执行数量换算；`1 ctn` 不能自动变成若干 `pc`。

## 5. family、规格与等级证据

- family 证据集合仅为：当前租户 `product_families.family_name`、`family_aliases.phrase_norm`、当前客户在 `alias_cache` 中已确认的别名。
- raw AI `fam=null` 只在 Adapter 兼容；正式值必须是闭集 family ID 或字符串 `UNKNOWN`。
- family 有多个 exact 命中且无法唯一归属时，不任选一个，产生阻断 `LOW_CONFIDENCE_MATCH`。
- pack size 仅接受项目登记的正则，例如 `500 g`、`2kg`、`12 x 1L`；匹配结果必须完整落在 span。P0 实现读取 `field-evidence-v2.json` 的 `pack_size.patterns`，并在 **有另一 qty 候选或 `x/装` 形态**时保长掩码，避免把 `10kg bawang` 的 10 当成 spec 丢掉。
- pack_size 本身是独立字段：`parse_pack_size(span)` 返回 `(value,start,end)`；不能在 `CANDIDATES` 后再“猜”。
- grade 仅接受当前租户版本化 alias；不得从描述相似度推断等级。

## 6. 失败映射

| 失败 | 对外/领域处理 | 诊断与后续 |
|---|---|---|
| qty 无证据、0/负数、小数或非法格式 | 当前行 `LOW_CONFIDENCE_MATCH` | `reason_code=INVALID_QUANTITY`；单行 fallback 可重试 |
| qty 有多个互不重叠候选，无法唯一归属 | 当前行 `LOW_CONFIDENCE_MATCH`（阻断） | `reason_code=AMBIGUOUS_QUANTITY`；单行 fallback，把候选列给跟单员 |
| pack_size 数字误入 qty | 剔除 spec 后再解析 | 见 `pack_size.patterns`；有另一 qty 候选或 `x/装` 形态时保长掩码 |
| uom/pack_size/grade 无证据 | 丢弃该字段后交 Resolver | `FIELD_NOT_EVIDENCED`；必要时转相应公共 IssueCode |
| family 无证据 | `LOW_CONFIDENCE_MATCH` | `FAMILY_NOT_EVIDENCED`；fam=`UNKNOWN` |
| span 无法唯一定位/越界 | `LOW_CONFIDENCE_MATCH` | `SOURCE_EVIDENCE_INVALID`；仅该行 fallback |
| 完全重复 span | 去重，不生成两条确定行 | `DUPLICATE_SPAN` 诊断与 audit |
| 不同 span 重叠 | 不静默合并 | `OVERLAPPING_SPAN`；强边界 fallback/阻断 |
| family 不在闭集 | `LOW_CONFIDENCE_MATCH` | `UNKNOWN_PRODUCT` |
| Resolver 无候选 | `LOW_CONFIDENCE_MATCH` | `NO_CANDIDATE` |
| 分数低/差距小 | `LOW_CONFIDENCE_MATCH` | `LOW_SCORE/SMALL_SCORE_GAP` |

`reason_code` 只能细分 8 个公共 `IssueCode`，不得成为第二套公共疑点卡类型。

## 7. AI 边界字段

- raw AI 可以返回 `ignored:string[]`；Adapter 将可定位项转换为 `ignored_spans:SpanView[]`。
- 原始 AI 输出只进入受限初始快照，不直接覆盖领域对象。
- 当前 SKU 来源只持久化一个 `match_source`：`SUGGESTED_DEFAULT/LLM_EXTRACTED/RAPIDFUZZ_FALLBACK/MANUAL_SELECTED`。
- 草稿 `ai_mode` 是所有行路径摘要：全 LLM、全 fallback、全 alias，或多种并存的 `MIXED`。
- `AiStatus.available_modes` 固定映射：`READY→[LLM,FALLBACK,ALIAS_ONLY]`；`WARMING/DEGRADED/OFFLINE→[FALLBACK,ALIAS_ONLY]`；仅本地兜底也缺失时才 503。

## 8. 必须通过的契约用例

| ID | 输入重点 | 预期 |
|---|---|---|
| DEV-39 | span 正确但模型 qty 与 token 不同 | 模型 qty 丢弃；当前行 LOW_CONFIDENCE/fallback |
| DEV-40 | span 中没有模型 family | fam=`UNKNOWN`；`FAMILY_NOT_EVIDENCED` |
| DEV-41 | 两个模型项重叠 | 不生成两个确定行；overlap 诊断 |
| H1-MS | `dua ctn` | qty=2、uom=`ctn` |
| H1-EN | `three cartons` | qty=3、uom=`ctn` |
| H1-ZH | `两箱` | qty=2、uom=`ctn` |
| H1-UOM | `5 ctn` | `ctn→ctn`；绝不换算成 pc |
| H1-UOM-ATTACHED | `10kg bawang` | qty=10、uom=`kg` |
| H1-TYPE | 模型 qty=`"5"` | Adapter 转 5，记 `MODEL_TYPE_COERCED` |
| H1-TYPE-NEG | 模型 qty=`"five"` | 不做类型强转；按词表重解析 |
| H1-TYPE-NEG2 | span `5 ctn`、模型 qty=`"6"` | 转 6 后仍与 5 不等；`FIELD_NOT_EVIDENCED` |
| H1-MS-TEENS | `lima belas ctn` | qty=15 |
| H1-MS-TENS | `dua puluh ctn` | qty=20 |
| H1-MS-TENS-UNIT | `tiga puluh lima ctn` | qty=35 |
| H1-EN-TEEN | `twelve cartons` | qty=12 |
| H1-EN-COMPOUND | `twenty-five ctn` | qty=25 |
| H1-ZH-TEENS | `十五箱` | qty=15 |
| H1-ZH-TENS | `三十五箱` | qty=35 |
| H1-DEC-1 | `1.5kg` | qty=null；`INVALID_QUANTITY` |
| H1-DEC-2 | `0.5 ctn` | qty=null；`INVALID_QUANTITY` |
| H1-DEC-NEG | `5 ctn` | qty=5；守卫不误伤整数 |
| H1-AMT | `kalau RM95 boleh 3 ctn` | qty=3，不是 95 |
| H1-AMT-NEG | `RM95 for 5 ctn` | qty=5，不是 95 |
| H1-AMT-DEC | `kalau RM12.50 boleh, ambil 4 pack` | qty=4，不是 INVALID_QUANTITY |
| H1-UOM-UPPER | `5 CTN` | qty=5、uom=`ctn` |
| H1-UOM-MIXED | `10KG bawang` | qty=10、uom=`kg` |
| H1-PACK-1 | `美禄 500g 装, 3 包` | qty=3、pack_size=`500g` |
| H1-PACK-2 | `Minyak 12 x 1L, 5 ctn` | qty=5、pack_size=`12 x 1L` |
| H1-PACK-3 | `Tepung 5kg x 2` | qty=2、pack_size=`5kg` |
| H1-PACK-4 | `Milo 2kg, 4 ctn` | qty=4、pack_size=`2kg` |
| H1-AMB-1 | `Milo satu 10 ctn` | qty=null；`AMBIGUOUS_QUANTITY` |
| H1-UPM | `Milo RM2.50 satu, 10 ctn` | qty=10，单价限定词不参与 |
| H1-UNIT-PRICE | `RM95 untuk 1 ctn, ambil 5` | qty=5，单价表达式不参与 |
| H1-DEC-COMMA-NEG | `Air 500 g x 12, 3 pack` | qty=3；列表逗号不是小数 |
| H1-UOM-PLURAL | `3 cans` | qty=3、uom=`can` |

测试应固定词表版本；升级词表必须增加回放样例和新版本号，不能静默改变旧快照解释。
