# KiraOrder H5 条件触发契约

> 状态：`GATE0_DRAFT` / `condition-triggers-v3`（2026-10-21：补三语价格变体与 TEST/CT 编号分离）  
> 目标：只有明确条件/询价/议价语义才生成 `CUSTOMER_CONDITION`；裸金额与历史陈述不能误触发。

## 1. 触发原则

1. PRICE 必须满足：明确议价短语，或“金额 + 条件/询价语气”。裸 `RM95` 只作金额证据，不单独触发。
2. STOCK 必须命中库存条件短语；`stock` 出现在商品编码/普通名词中不触发。
3. 同一片段允许多标签，例如 `kalau ada, boleh kurang` 同时生成 STOCK 与 PRICE；实现不得用排他的 `elif`。
4. 历史词本身不会永久抑制：若同句有明确询价/议价（`Can follow last price RM95?`），仍触发 PRICE。
5. PRICE 必须记录 `condition_scope/target_line_ids/requested_unit_price/price_basis`。无法唯一关联时 scope=`UNKNOWN` 且 blocking=true。
6. P0 只执行 `price_basis=UNIT`。`TOTAL/UNKNOWN` 必须向客户确认单位价，不能自行除法或默认单价；wire 枚举只允许 `UNIT/TOTAL/UNKNOWN`，不得造 `UNKNOWN_OR_TOTAL` 等混合值。
7. 人工误报处理固定为 `NOT_A_CONDITION + 非空 note`，并追加 `CONDITION_DISMISSED` 活动供回放。

## 2. 16 行真值表

| # | 输入 | 结果 | `price_basis` / 说明 |
|---:|---|---|---|
| 1 | `Last order was RM95.` | 不生成条件 | 历史陈述；金额只是普通文本证据 |
| 2 | `Total last time RM95.` | 不生成条件 | 无条件、询价或议价语气 |
| 3 | `kalau RM95 boleh` | PRICE | 条件标记+金额；默认 `UNKNOWN`，UI 可预选但须人工确认 UNIT |
| 4 | `RM95?` | PRICE | 问号构成询价；target 和 basis 仍须确认 |
| 5 | `boleh kurang sikit?` | PRICE | 无金额议价；确认后人工录入单位价 |
| 6 | `kalau ada, boleh kurang` | STOCK + PRICE | 同一片段生成两个 Issue；不能丢掉一个 |
| 7 | `If available, send 5 ctn` | STOCK | STOCK 条件 `blocking=false`；缺货由行级 `INSUFFICIENT_STOCK` 阻断 |
| 8 | `hantar esok` | 不生成条件 | 普通送货要求，不含条件标记 |
| 9 | `Stock code A95` | 不生成条件 | 商品/库存编码，不是金额或库存条件 |
| 10 | `RM95 for 5 ctn` | PRICE，阻断 | `price_basis=UNKNOWN`、`amount_allocation=UNALLOCATED`；先确认单位价，禁止 `95÷5` 自动应用 |
| 11 | `Can follow last price RM95?` | PRICE | 明确询价覆盖历史陈述负向上下文 |
| 12 | `kalau RM95 untuk 1 ctn` | PRICE，阻断 | 明确“金额对应 1 个规范单位”，`price_basis=UNIT`；仍需人工接受后才能应用 |
| 13 | `can less?` | PRICE | 英文 `can (be) less/cheaper` 的可选 `be` 必须被覆盖 |
| 14 | `老价钱?` | PRICE | 中文裸 `老价钱` 在问句/协商语境下触发 |
| 15 | `harga lama?` | PRICE | 马来语 `harga lama` 在问句/协商语境下触发 |
| 16 | `boleh diskaun?` | PRICE | 马来语 `diskaun` 在问句/协商语境下触发 |

## 3. 版本化触发词表

所有正则在 NFKC、casefold、空白折叠后执行，并保留原始 masked span。下表的 `pattern` 是机器实现的语义模板；实际编译时须加词边界并通过正负例。`PRICE_HELPER` 不单独生成 Issue；`TIME_OR_OTHER` 在 P0 一律落 `OTHER`，P1 起才细分 `TIME`。

| id | kind | language | pattern/phrase | 说明 |
|---|---|---|---|---|
| `cond_stock_ms_001` | STOCK | ms | `kalau ada` | 有货才要 |
| `cond_stock_ms_002` | STOCK | ms | `jika ada` | 有货条件 |
| `cond_stock_en_001` | STOCK | en | `if available` | 英文库存条件 |
| `cond_stock_en_002` | STOCK | en | `if in stock` | 英文库存条件 |
| `cond_stock_zh_001` | STOCK | zh | `有货的话` | 中文库存条件 |
| `cond_stock_zh_002` | STOCK | zh | `如果有货` | 中文库存条件 |
| `cond_price_ms_001` | PRICE | ms | `kalau\s+RM\s*\d+(?:\.\d{1,2})?` | 条件金额 |
| `cond_price_ms_002` | PRICE | ms | `boleh kurang(?: sikit)?` | 议价，可无金额 |
| `cond_price_en_001` | PRICE | en | `can\s+(?:be\s+)?(?:less|cheaper)` | 英文议价；覆盖 `can less?` |
| `cond_price_en_002` | PRICE | en | `discount` | 必须同时具备问句、请求动词或协商语境；否定语境不触发 |
| `cond_price_en_003` | PRICE | en | `can\s+follow\s+(?:the\s+)?last\s+price` | 历史价格询价 |
| `cond_price_zh_001` | PRICE | zh | `便宜一点|少一点|按老价钱|可以优惠` | 明确中文议价 |
| `cond_price_zh_002` | PRICE | zh | `便宜|老价钱|打折` | 需问句/协商语境；覆盖 `老价钱?` |
| `cond_price_ms_003` | PRICE | ms | `harga lama` | 需问句/协商语境 |
| `cond_price_ms_004` | PRICE | ms | `diskaun` | 需问句/协商语境 |
| `cond_price_unit_ms_001` | PRICE | ms | `RM<amount> untuk 1 <uom>` | 明确单位价；`price_basis=UNIT` |
| `cond_query_001` | PRICE helper | any | `?` / `？` | 只有附近存在金额时组成 PRICE |
| `cond_other_ms_001` | TIME/OTHER | ms | `kalau sempat` | P0 落 `OTHER` |
| `cond_other_ms_002` | TIME/OTHER | ms | `hantar sebelum` | P0 落 `OTHER` |

## 4. 金额、范围和目标行

- 金额 token：`RM` 与正 decimal，最多两位小数；提取为 decimal string，不使用 binary float。
- `requested_unit_price` 只有证据明确为单位价时填写；否则金额可留在 `data_used.amount_text`，字段为空（**UNKNOWN 时必须为 null**）。
- 单行消息且条件唯一关联该行时，可设 `condition_scope=SINGLE_LINE` 并给候选目标；用户仍须确认接受价格所影响的行。
- 多行消息只有明确逐行绑定证据才设 `MULTI_LINE`；无法绑定设 `UNKNOWN`，`target_line_ids=[]`，返回 `TARGET_LINE_REQUIRED`。
- `RM95 for 5 ctn` 不能自动认作 UNIT，也不能在 wire 中使用不存在的混合枚举。P0 固定输出 `price_basis=UNKNOWN`、`amount_allocation=UNALLOCATED` 并先澄清；只有 `RM95 untuk 1 ctn`、`RM95 per ctn` 这类明确单单位表达才直接提取 `price_basis=UNIT`。确认单位价后使用 `IssueResolution.confirmed_unit_price`、`price_basis=UNIT` 和 note。
- 接受价格只修改 `target_line_ids`；非目标行改价不能解决该 Issue。

## 5. 负向上下文

| 类别 | 示例 | 处理 |
|---|---|---|
| 历史陈述 | `last order was RM95`, `total last time RM95` | 无询价/议价时不触发 |
| 编码 | `A95`, `stock code RM95` | 编码边界内金额不触发 |
| 普通送货要求 | `hantar esok`, `send tomorrow` | 不因时间词单独生成条件 |
| 报价事实 | `price is RM95` | 无问号/条件/议价短语时不触发 |
| 否定询价 | `not asking for discount` | 不触发；进入回放负例 |
| 已付/不议价 | `harga lama RM95 sudah bayar`, `价格不便宜也没关系` | 不触发 |

负向规则不得压过同一语句中的显式询价。例如 `Can follow last price RM95?` 仍是 PRICE。

- `negative_contexts` 和 `context_markers` 都由 `condition-triggers-v3.json` 提供；oracle/实现不得再写第二套硬编码。
- `requires_context=true` 的 trigger 只有在 `context_markers` 命中且未命中 `negative_contexts` 时才触发。

## 6. Issue 生成与关闭

- 每个标签生成独立 `Issue(code=CUSTOMER_CONDITION)`，共享 span 但 `condition_kind` 不同。
- PRICE 默认 `blocking=true`，直到 target、UNIT basis、有效目标行成交价与理由全部满足。
- **STOCK 条件固定 `blocking=false`**；只记录客户原话与库存判定。缺货时由对应行级 `INSUFFICIENT_STOCK(blocking=true)` 单独阻断，不能让两张卡片同时要求人工解决。
- STOCK 条件由当前库存重算，可写 `auto_resolved_by=STOCK_CHECK`；批准锁内必须再次复核。
- TIME/OTHER 在 P0 不自动承诺；由 CLERK/OWNER 确认或澄清。
- `NOT_A_CONDITION` 需要 note，保存后 `resolved=true`、记录 choice/note，并写 append-only `CONDITION_DISMISSED` 活动。

## 7. 验收编号

Gate 0 的 H5 契约用例 **不再占用冻结集 `TEST-xx` 编号**；冻结集 `TEST-01—32` 归数据岗独占。

### H5 契约用例（Gate 0 内部）

| ID | 断言 |
|---|---|
| `H5-CT-01` | 裸金额/历史陈述不触发（`Last order was RM95.`、`Total last time RM95.`） |
| `H5-CT-02` | 多标签：`kalau ada, boleh kurang` 生成 STOCK+PRICE |
| `H5-CT-03` | PRICE 缺目标行或 UNIT basis 时阻断批准，返回 `TARGET_LINE_REQUIRED`/`OVERRIDE_REQUIRED` |

### 冻结集 TEST-01—32（数据岗独占，方案 §9.2 为准）

| 编号 | 主题 |
|---|---|
| TEST-01—24 | 方案 B Group A—F，保持不变 |
| TEST-25—28 | 改价升级/老板批准、跨租户阈值、权限、库存变化 |
| TEST-29 | 有货条件，有货与缺货各一种 |
| TEST-30 | 价格条件，马来语/中文/英文说法各一种（含 `can less?`/`老价钱`） |
| TEST-31 | 同一条消息，不同客户，路由随账期提醒变化 |
| TEST-32 | 没有条件标记的送货要求/闲聊，不生成条件 |

> 如果数据岗要调整 TEST-01—32 的内容，必须先发新版本并重算 `FROZEN_SHA256.txt`；不得只改编号解释。

## 8. 版本纪律

- 真值表 16 行必须逐行成为 fixture/参数化测试，结果、`price_basis` 与显式 `blocking` 一致。
- 词表新增/删改必须提升版本，增加正例和至少一个近邻负例；不得在线静默改词。
- `condition-triggers-v3` 的 `cond_price_en_001` 必须覆盖 `can less?`；`cond_price_zh_002`/`ms_003`/`ms_004` 必须带语境约束。
