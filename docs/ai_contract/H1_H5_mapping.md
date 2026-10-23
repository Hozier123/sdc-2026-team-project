# KiraOrder H1 / H5 提取规则到输出契约映射规范

> **版本**：`H1-v2` / `H5-v3` / `AI-Contract-v1.3`  
> **更新日期**：2026-10-22  
> **权威标准**：`gate0/contracts/field-evidence.md`、`gate0/contracts/condition-triggers.md`、`gate0/contracts/lexicons/field-evidence-v2.json`、`gate0/contracts/lexicons/condition-triggers-v3.json`

---

## 1. 架构职责边界（Absolute Responsibility Boundary）

为杜绝领域越权与脏数据污染，KiraOrder 明确切分 AI 抽取子系统与后端业务子系统的边界：

```text
[客户原始文本]
      ↓
[后端 PII 掩码层] (脱敏电话、身份证、邮箱等，生成 MASK_TOKENS)
      ↓
[masked_text]
      ↓
╔══════════════════════════════════════════════════════════════════════════╗
║                     Xiong 交付：AI 抽取子系统                             ║
║                                                                          ║
║  输入：masked_text (Unicode code point <= 4000)                          ║
║  输出：RawExtraction { rows: [span, qty, uom, fam, pack_size, conds],    ║
║                       ignored_spans: [...] }                             ║
║                                                                          ║
║  ★ 绝对禁止输出：sku_id, price, unit_price, stock, approval, do_number    ║
║  ★ 纯事实抽取：仅输出文本切片证据、候选词及客户谈判原话                    ║
╚══════════════════════════════════════════════════════════════════════════╝
      ↓
[后端 OrderAiAdapter & Pre-Resolver] (坐标投影校验、H1确定性复核、H5条件引擎)
      ↓
[后端 Resolver / ERP 领域服务] (SKU ID 决议、库存检查、价格核算、审批与 DO 生成)
```

### 违规防御清单
1. **禁止生成 `sku_id`**：AI 侧不知道商品物料编码，只能输出闭集 `fam`（如 `FAM_FLOUR`）和规格 `pack_size`（如 `1kg`）。具体 SKU 由后端根据租户账套解析。
2. **禁止决定价格 `price` / `unit_price`**：AI 仅抽取客户提出的报价原话（如 `conds: ["kalau RM95 untuk 1 ctn boleh?"]`），不得确认该价格是否被采纳或修改商品实际单价。
3. **禁止判定库存 `stock`**：客户原话中的 `kalau ada` 仅作为库存触发条件，库存充足与否由后端 WMS/ERP 实时锁库判定。
4. **禁止审批 `approval` 与生成单号 `do_number`**：审批锁（Approval Lock）与交付单号由后端领域状态机管理。
5. **禁止回传真实 PII**：AI 仅处理 `[REDACTED_PHONE]`、`[REDACTED_MYKAD]`、`[REDACTED_EMAIL]` 掩码占位符。

---

## 2. H1 v2 字段映射规范（Field Evidence Mapping）

每个商品行（`rows[]`）必须包含且仅包含以下 6 个字段：

| 字段名称 | 类型 | 规范说明与值域 | H1 v2 提取流水线与验证规则 |
|---|---|---|---|
| `span` | `string` | masked_text 的精确子串（非空） | 对应 masked_text 的 Unicode 半开区间 `[start, end)`；必须是原文子串，严禁拼接。 |
| `qty` | `integer \| null` | 正整数 `1..999999` 或 `null` | 经过 `UnitPriceMarkerMask → AmountMask → CodeMask → DecimalGuard` 处理；小数/模糊数量/缺省数量必须置为 `null`。拒绝 `bool`、负数、0 与浮点数。 |
| `uom` | `string \| null` | 规范化计量单位或 `null` | 匹配 `field-evidence-v2.json` 的 exact aliases（如 `ctn`, `pack`, `kg`, `pc`, `bag`, `btl`, `can`, `papan`）。严禁跨单位自动折算。 |
| `fam` | `string` | 租户闭集家族 ID 或 `"UNKNOWN"` | 严格属于**本次请求注入的**租户目录白名单（T1 如 `FAM_TEPUNG`；generic 合同样例的 `FAM_FLOUR`/`FAM_RICE` 只用于 legacy HTTP 翻译，不是 T1 目录）或 `"UNKNOWN"`。严禁输出 `null` 或未定义名称。 |
| `pack_size` | `string \| null` | 包装规格字符串或 `null` | 正则匹配包装规格（如 `1kg`, `500g`, `12 x 1L`, `5kg`）。在解析数量前保长掩码剔除，防止规格数字误入订购数量。 |
| `conds` | `array[string]` | 条件原话切片数组 | 命中客户谈判、库存假设或时间交期等条件的文本原话片段。无条件时必须为 `[]`。 |

### H1 确定性流水线执行顺序
1. **EXCLUDE_UNIT_PRICE_MARKER**：使用 `unit_price_marker_pattern` 掩码单价修饰词（如 `RM2.50 satu`），防止修饰词干扰数量。
2. **EXCLUDE_AMOUNT**：使用 `qty_exclude_pattern` 保长掩码货币金额（如 `RM95`, `RM 12.50`）。
3. **EXCLUDE_CODE**：使用 `code_exclude_pattern` 保长掩码商品编号（如 `A95`）。
4. **DECIMAL_GUARD**：
   - 英文点号小数守卫：`(?<![\d.,])\d+\.\d+(?![\d.,])`，拦截 `2.5 ctn`。
   - 逗号单位小数守卫：`(?<![\d.,])\d+,\s*\d+\s*(?:g|kg|ml|l|liter|litre|克|公斤|毫升|升)`，拦截 `1,5kg`。
   - 若命中守卫，`qty` 强制设为 `null`，下游标记 `INVALID_QUANTITY`。
5. **PACK_SIZE_MASK**：当检测到多数量候选或 `x/装` 结构时，保长掩码规格数字（如 `5kg x 2` 中的 5kg 保留为 pack_size，数量为 2）。
6. **CANDIDATES & AMBIGUITY**：最长匹配优先解析阿拉伯数字与多语言数字词（Malay, English, Chinese）。若存在两个互不重叠且无法归属的数字候选（如 `Milo satu 10 ctn`），判定为 `AMBIGUOUS_QUANTITY` 并置 `qty=null`。

---

## 3. H5 v3 条件触发映射规范（Condition Triggers Mapping）

H5 条件抽取用于捕获批发采购中的议价、库存前置条件与交期诉求。AI 抽取层将相关短语收录至对应行或全局的 `conds[]`，后端 H5 条件引擎将其映射为领域条件结构。

### 16 行真值表（Truth Table）对应关系

| # | 客户输入原话 | 触发类别 (kind) | 价格基础 (price_basis) | 请求金额 (requested_amount) | 说明与业务动作 |
|---:|---|---|---|---|---|
| 1 | `Last order was RM95.` | *(无条件)* | - | - | 历史陈述，金额作为普通文本，不触发条件 |
| 2 | `Total last time RM95.` | *(无条件)* | - | - | 历史陈述，无议价或询价语气，不触发 |
| 3 | `kalau RM95 boleh` | `PRICE` | `UNKNOWN` | `"95"` | 条件短语+金额；price_basis 需跟单员确认 |
| 4 | `RM95?` | `PRICE` | `UNKNOWN` | `"95"` | 问号构成询价语气；price_basis 需人工确认 |
| 5 | `boleh kurang sikit?` | `PRICE` | `UNKNOWN` | `null` | 无具体金额的议价；需跟单员沟通确认 |
| 6 | `kalau ada, boleh kurang` | `STOCK` + `PRICE` | `UNKNOWN` | `null` | 同一片段生成两个条件；STOCK 记录原话，PRICE 记录议价 |
| 7 | `If available, send 5 ctn` | `STOCK` | - | - | 库存条件，STOCK 条件默认 blocking=false（缺货由行级阻断） |
| 8 | `hantar esok` | *(无条件)* | - | - | 普通送货要求，无条件词，不触发条件 |
| 9 | `Stock code A95` | *(无条件)* | - | - | 商品/物料编码，非库存或价格条件 |
| 10 | `RM95 for 5 ctn` | `PRICE` | `UNKNOWN` | `"95"` | 批量金额；禁止系统私自执行 95÷5 自动折算，必须由人工确认 |
| 11 | `Can follow last price RM95?` | `PRICE` | `UNKNOWN` | `"95"` | 显式询价语气压过历史词，触发 PRICE 条件 |
| 12 | `kalau RM95 untuk 1 ctn` | `PRICE` | `UNIT` | `"95"` | 明确单单位定价模式，提取 `price_basis=UNIT` |
| 13 | `can less?` | `PRICE` | `UNKNOWN` | `null` | 英语日常议价短语 |
| 14 | `老价钱?` | `PRICE` | `UNKNOWN` | `null` | 中文老客户议价短语，问句语境触发 |
| 15 | `harga lama?` | `PRICE` | `UNKNOWN` | `null` | 马来语老价格议价短语 |
| 16 | `boleh diskaun?` | `PRICE` | `UNKNOWN` | `null` | 马来语折扣议价短语 |

### `price_basis` 决议规则
1. **`UNIT`**：仅当输入中明确存在“金额对应单一计量单位”的表达（如 `RM95 untuk 1 ctn`、`RM20 per kg`、`RM 5 each`）时提取。
2. **`UNKNOWN`**：普通询价、带问号金额（`RM95?`）、批量打包询价（`RM95 for 5 ctn`）一律标记为 `UNKNOWN`。后端阻断自动批准，提示跟单员人工复核输入。
3. **`requested_amount`**：必须为标准十进制字符串（如 `"95"`, `"12.50"`），禁止使用浮点数（float），防止精度损失。

---

## 4. 故障隔离与原因码（Reason Codes）映射

当 AI 抽取结果进入后端的 `OrderAiAdapter` 时，若发现字段或证据不满足 H1/H5 要求，系统执行单行降级与故障隔离：

| 异常现象 | 输出调整 | Adapter 内部 issue_code | 内部 reason_code | 业务处理方式 |
|---|---|---|---|---|
| 数量为小数（如 `2.5 ctn` 或 `1,5kg`） | `qty: null` | `LOW_CONFIDENCE_MATCH` | `INVALID_QUANTITY` | 行进入草稿疑点卡，跟单员人工修正数量 |
| 存在冲突的数字词（如 `satu 10 ctn`） | `qty: null` | `LOW_CONFIDENCE_MATCH` | `AMBIGUOUS_QUANTITY` | 阻断自动成单，跟单员确认 1 还是 10 |
| span 中未找到指定单位 | 保留 qty，uom 置空 | `LOW_CONFIDENCE_MATCH` | `FIELD_NOT_EVIDENCED` | 提示缺失单位，按商品默认销售单位预填 |
| span 中无商品族文本证据（幻觉） | `fam: "UNKNOWN"` | `LOW_CONFIDENCE_MATCH` | `FAMILY_NOT_EVIDENCED` | 标记未识别商品，由跟单员手动关联物料 |
| 商品族不在租户目录白名单内 | `fam: "UNKNOWN"` | `LOW_CONFIDENCE_MATCH` | `UNKNOWN_PRODUCT` | 标记新物料/未上架商品 |
| span 无法在 masked_text 中唯一定位 | 该行降级 | `LOW_CONFIDENCE_MATCH` | `SOURCE_EVIDENCE_INVALID` | 单行触发 RapidFuzz 离线降级引擎重算 |
| 相同 span 文本完全重复且证据相同 | 去重 | *(去重诊断)* | `DUPLICATE_SPAN` | 合并为单行，避免重复订货 |
| 两个不同商品行的 span 发生物理重叠 | 重叠行降级 | `LOW_CONFIDENCE_MATCH` | `OVERLAPPING_SPAN` | 标记冲突区间，避免脏数据进入 Resolver |

---

## 5. 总结

- **AI 的职责**：以极高的保真度提取 `span`、闭集 `fam`、正整数/空 `qty`、`uom`、`pack_size` 及 `conds`。
- **后端的职责**：校验证据坐标、核对价格与库存、生成草稿对象与最终 ERP 订购单。
