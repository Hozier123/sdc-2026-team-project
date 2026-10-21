# KiraOrder v1.2 后端与数据对接规则

> 契约状态：`FROZEN_v1.2`  
> 后端负责人：He Minghao  
> 数据与质量负责人：Zhou Jingxi  
> 前置真相源：`01_KiraOrder_v1.2_后端完整规则框架.md`

## 0. 目的

本文规定两租户合成种子数据、条件词表、开发集、冻结集、答案键、演示重置和评测结果如何与后端对接。目标是让数据文件可直接校验、导入和复现，不依赖人工临时清洗。

核心原则：

> 数据组负责构造独立、可验证的合成业务事实；后端负责Schema、导入约束和运行规则；答案键不得被应用读取。

---

## 1. 文件布局

```text
data/
├── seed/
│   ├── tenant_sinaran.json
│   ├── tenant_kilat.json
│   ├── users.json
│   ├── customers.json
│   ├── product_families.json
│   ├── skus.json
│   ├── tier_prices.json
│   ├── inventory.json
│   ├── customer_aliases.json
│   └── demo_state.json
├── lexicon/
│   └── conditions_v0.yaml
└── schemas/
    ├── seed.schema.json
    ├── evaluation_case.schema.json
    └── answer_key.schema.json

tests/
├── datasets/
│   ├── dev_32.json
│   ├── frozen_eval_32.json
│   ├── ab_tool_messages.json
│   └── first_use_tasks.json
├── answers/
│   ├── dev_answers.json
│   └── frozen_answers.json
└── FROZEN_SHA256.txt

evidence/
├── README.md
├── evaluation_results/
├── baseline_manual_raw.csv
├── ab_timing_raw.csv
└── first_use.csv
```

开发集和冻结集必须分开。运行时代码不得导入`tests/answers/`。

---

## 2. 通用格式规则

| 数据 | 文件格式 | 文件内类型 | 导入后类型 |
|---|---|---|---|
| ID | JSON字符串 | string | string/uuid |
| 金额 | JSON字符串 | `"95.00"` | Decimal/Numeric |
| 数量 | JSON字符串 | `"5"` | 正整数 |
| 布尔值 | JSON boolean | true/false | boolean |
| 时间 | ISO 8601字符串 | UTC | timestamp UTC |
| 条件词表 | YAML | 明确字段 | 后端规则对象 |

### 2.1 数量

虽然文件中使用字符串，P0数量必须能转换为正整数：

```text
合法："1"、"5"、"100"
非法："0"、"-1"、"1.5"、"five"
```

种子数据不得包含小数库存或小数订单数量。用于负例测试的小数只能出现在消息文本和预期疑点中。

### 2.2 金额

- 固定两位小数字符串；
- 币种MYR；
- 导入使用Decimal；
- 舍入为`ROUND_HALF_UP`；
- 不在JSON中使用浮点数。

### 2.3 ID

使用稳定人工ID，便于测试和演示：

```text
T1
USR_SITI
CUS_ALI
FAM_MILO
SKU_MILO_1KG
```

禁止每次seed随机生成不同ID。

---

## 3. 租户数据

### 3.1 T1

```json
{
  "tenant_id": "T1",
  "name": "Sinaran Food Supply",
  "industry": "food_and_grocery_wholesale",
  "currency": "MYR",
  "timezone": "Asia/Kuala_Lumpur",
  "owner_approval_threshold": "1500.00",
  "active": true
}
```

要求：约40 SKU/25商品族、8个客户。

### 3.2 T2

```json
{
  "tenant_id": "T2",
  "name": "Kilat Hardware & Cleaning Supply",
  "industry": "hardware_and_cleaning_wholesale",
  "currency": "MYR",
  "timezone": "Asia/Kuala_Lumpur",
  "owner_approval_threshold": "800.00",
  "active": true
}
```

要求：约15 SKU/10商品族、5个客户。

### 3.3 验证

- 阈值非负且两位小数；
- ID唯一；
- 时区和币种存在；
- 两租户数据完全隔离；
- 相同别名或商品名不能导致跨租户解析。

---

## 4. 用户与演示令牌

建议种子对象：

```json
{
  "user_id": "USR_SITI",
  "tenant_id": "T1",
  "display_name": "Siti",
  "role": "CLERK",
  "demo_token": "仅供seed导入流程读取的合成令牌",
  "active": true
}
```

后端导入后只保存令牌哈希。至少准备：

- CLERK：Siti；
- OWNER：Boss Tan；
- WAREHOUSE：Ah Kow；
- 两租户各自角色令牌，或明确可复现的演示映射。

禁止在公开仓库中放真实Secrets。演示令牌只能访问合成数据。

---

## 5. 客户数据

```json
{
  "customer_id": "CUS_ALI",
  "tenant_id": "T1",
  "name": "Restoran Ali",
  "synthetic_phone": "+6012-000-0001",
  "tier": "A",
  "credit_term_notice": false,
  "language_preference": "ms",
  "active": true
}
```

### 5.1 固定要求

- T1共8个客户，Tier A/B混合；
- Restoran Ali：Tier A、无账期提醒；
- Kedai Mesra：带账期提醒；
- T2共5个客户，至少1个带账期提醒；
- T1电话范围`+6012-000-0xxx`；
- T2电话范围`+6012-000-1xxx`；
- 全部号码为合成数据。

### 5.2 账期提醒边界

字段只叫：

```text
credit_term_notice
```

不得添加或声称：

```text
overdue amount
days overdue
customer frozen
automatic credit blocking
```

这是模拟来自会计伙伴的布尔提醒，不是账龄系统。

---

## 6. 商品族与SKU

### 6.1 商品族

```json
{
  "family_id": "FAM_MILO",
  "tenant_id": "T1",
  "name": "Milo",
  "aliases": ["milo", "美禄", "milo粉"],
  "active": true
}
```

商品族是AI闭集选择对象，不是最终库存扣减对象。

### 6.2 SKU

```json
{
  "sku_id": "SKU_MILO_1KG",
  "tenant_id": "T1",
  "family_id": "FAM_MILO",
  "display_name": "Milo 1kg",
  "spec": "1kg",
  "grade": null,
  "base_unit": "pack",
  "active": true
}
```

SKU必须指向同租户商品族。

### 6.3 T1必备歧义结构

- Milo 1kg/2kg；
- Minyak masak 5kg瓶/17kg桶；
- Beras 5kg/10kg；
- Bawang Besar India散装kg/10kg袋；
- Telur Grade A/B/C；
- Ayam A1/A2；
- Telur papan/ctn；
- Kicap cair btl/ctn。

### 6.4 T2必备歧义结构

- Sabun cecair 1L/5L；
- Plastik sampah S/M/L；
- Sarung tangan S/M/L；
- Tisu roll/ctn。

### 6.5 导入验证

- 每个SKU有真实商品族；
- 同租户SKU ID唯一；
- `base_unit`非空；
- 多规格、等级、单位结构能够实际触发对应疑点；
- 不允许`family_id="UNKNOWN"`；未知商品只存在于测试消息和运行草稿。

---

## 7. 等级价

```json
{
  "tenant_id": "T1",
  "sku_id": "SKU_MILO_1KG",
  "customer_tier": "A",
  "unit_price": "32.00",
  "currency": "MYR"
}
```

唯一键：

```text
tenant_id + sku_id + customer_tier
```

要求：

- 演示涉及的所有SKU/Tier都有价格；
- 所有Tier价格是严格大于`0.00`的两位MYR金额；
- Tier A和B应至少有可观察差异；
- 价格足以构造低于等级价、等于等级价和金额阈值案例；
- 缺失价格必须在数据校验阶段暴露；
- 后端运行时仍以`MISSING_TIER_PRICE`阻断，不能猜价。

---

## 8. 库存

```json
{
  "tenant_id": "T1",
  "sku_id": "SKU_MILO_1KG",
  "available_quantity": "18",
  "unit": "pack",
  "updated_at": "2026-10-21T00:00:00Z"
}
```

要求：

- `available_quantity`可转为非负整数；
- 单位与SKU `base_unit`完全一致；
- 每个演示SKU只有一条库存记录；
- 有货条件同时存在满足和不足案例；
- 存在“库存刚好等于请求量”和“少1单位”的边界；
- 存在并发测试用最后库存场景；
- 重置后库存值固定可复现。

P0不做隐式箱/瓶换算。若数据需要换算，必须另行冻结显式换算表；当前默认不提供。

---

## 9. 客户级别名

```json
{
  "alias_id": "ALS_001",
  "tenant_id": "T1",
  "customer_id": "CUS_ALI",
  "alias_text": "milo besar",
  "target_type": "SKU",
  "target_id": "SKU_MILO_2KG",
  "confirmed_by": "USR_SITI",
  "confirmed_at": "2026-10-21T00:00:00Z",
  "active": true
}
```

验证：

- 客户、目标和确认人属于同一租户；
- target为FAMILY或SKU；
- 同一别名可以在不同客户下指向不同目标；
- Alias回放集至少包含第一次需人工、第二次可命中的场景；
- 别名命中不等于自动批准，仍需人批准DO。

---

## 10. 条件词表YAML

```yaml
version: "v0"
entries:
  - id: cond_stock_ms_001
    type: STOCK_IF_AVAILABLE
    language: ms
    match_kind: phrase
    pattern: "kalau ada"
    normalized_meaning: "only if stock is available"
    priority: 100

  - id: cond_price_ms_001
    type: PRICE_REQUEST
    language: ms
    match_kind: regex
    pattern: "kalau\\s+RM\\s*([0-9]+(?:\\.[0-9]{1,2})?)\\s+boleh"
    normalized_meaning: "customer requests a price condition"
    priority: 110
```

### 10.1 允许的类型

```text
STOCK_IF_AVAILABLE
PRICE_REQUEST
OTHER_CONDITION
```

不能另建`PRICE/STOCK/TIME`平行枚举。时间条件使用：

```text
type = OTHER_CONDITION
subtype = DELIVERY_TIME
```

### 10.2 每条规则必须有

- 稳定ID；
- 语言；
- 匹配方式；
- pattern；
- 标准含义；
- 优先级；
- 至少一个开发集正例；
- 至少一个负例。

### 10.3 必备负例

- `Please deliver tomorrow.`：普通送货要求，不一定是条件；
- `Last order was RM95.`：历史陈述，不一定议价；
- `Stock code A95.`：数字不是价格；
- `If available, send 5 ctn.`：有货条件，不是价格条件。

词表修改必须走Git评审并留提交记录。

---

## 11. 合成消息数据集

```json
{
  "case_id": "DEV_001",
  "tenant_id": "T1",
  "customer_id": "CUS_ALI",
  "message_text": "Boss, Milo 5 pack kalau ada",
  "language_style": "mixed",
  "split": "dev",
  "tags": ["missing_spec", "stock_condition"]
}
```

### 11.1 内容要求

- 马来语为主；
- 中文为主；
- 英文混写/Manglish；
- 每条1–8个商品；
- 部分包含问候和闲聊；
- 部分包含合成电话、IC样式号码，用于PII测试；
- 多规格、多等级、多单位；
- 目录外俗称；
- 合法正整数数量；
- 小数、0、负数等负例；
- 有货、价格和其他条件；
- 普通送货要求负例；
- 提示注入句。

### 11.2 条件消息最低数量

T1至少：

- 有货条件4条，满足/不满足各半；
- 价格条件4条，覆盖马来语、中文、英文；
- 其他/时间条件2条；
- 无条件送货要求负例2条。

T2至少4条带条件消息。

### 11.3 PII说明

所有消息仍是合成数据。后端在落库前掩码，因此评测预期中的`source_span`应以掩码后文本或可在掩码后文本稳定找到的商品片段为准。

---

## 12. 开发集与冻结集

### 12.1 开发集

用于：

- 调试Prompt和Adapter；
- 确定RapidFuzz第一名阈值和前两名分差；
- 完善词表；
- 修复业务规则；
- 验证Schema。

可以在冻结前修改，但每次重要变更应留Git记录。

### 12.2 冻结集

用于最终独立评测。封存后：

- 不得根据结果修改原文件；
- 不得把答案硬编码进程序；
- 如发现数据本身错误，新建新版本并解释原因；
- 重新计算并记录新SHA-256；
- 原版本仍保留。

### 12.3 SHA-256

`tests/FROZEN_SHA256.txt`至少包含：

```text
filename
sha256
frozen_at
frozen_by
dataset_version
```

评测前后均计算并比对。

---

## 13. 答案键

```json
{
  "case_id": "DEV_001",
  "expected_lines": [
    {
      "family_id": "FAM_MILO",
      "sku_id": null,
      "quantity": 5,
      "raw_unit": "pack"
    }
  ],
  "expected_issue_codes": ["MISSING_SPEC"],
  "expected_condition_types": ["STOCK_IF_AVAILABLE"],
  "expected_owner_escalations": [],
  "expected_status": "NEEDS_REVIEW"
}
```

### 13.1 隔离规则

- 应用运行时不得读取答案键；
- Prompt不得包含答案键；
- Seed导入不得导入答案键；
- 只有评测脚本读取系统输出和答案键进行比较；
- 答案键与测试消息可放相邻目录，但代码依赖必须分离。

### 13.2 谁负责答案

答案键由数据与质量负责人独立维护，后端负责人只定义Schema和评测接口，不在开发时修改答案迎合实现。

---

## 14. 必备测试案例

### 14.1 业务规则

- T1总额低于、等于和高于RM1,500；
- T2总额低于、等于和高于RM800；
- 成交价等于等级价；
- 成交价低于等级价；
- 客户带/不带账期提醒；
- 三条升级原因同时命中；
- 开放疑点阻断批准。

### 14.2 商品与疑点

- 缺规格；
- 缺等级；
- 缺单位；
- 目录外商品；
- RapidFuzz候选过近；
- 数量缺失；
- 小数数量；
- 库存不足；
- source_span校验失败的模拟响应。

### 14.3 上下文路由

- 同一消息使用Restoran Ali和Kedai Mesra产生不同路由；
- 同样RM1,000在T1/T2产生不同路由；
- 同名别名在不同客户/租户不得串用。

### 14.4 AI与兜底

- AI结果正确；
- 一行AI失败、其他行保留；
- AI超时整单Fallback；
- ALIAS_ONLY全命中不调用AI；
- Alias与AI重叠时Alias优先；
- AI关闭仍能闭环；
- 提示注入`price RM0.01`不改变价格。

### 14.5 事务

- 旧版本批准；
- 双击批准；
- 两草稿竞争最后库存；
- DO失败回滚库存；
- 老板驳回缺理由；
- REJECTED不可重用。

### 14.6 权限

- T1令牌访问T2对象返回404；
- CLERK不能老板批准；
- OWNER不能编辑草稿；
- WAREHOUSE响应无价格和电话；
- 请求头不能自报角色。

---

## 15. 演示重置

### 15.1 目标

每次演示必须从相同起点开始，包括：

- 客户、目录、价格和库存；
- 草稿、审批和DO初始状态；
- 客户别名初始集合；
- T1/T2阈值；
- 今日订单种子（P1）；
- AI状态不属于数据库重置范围。

### 15.2 事务性重置

重置必须在一个受保护的事务或明确顺序中执行，失败时不能留下半重置状态。

### 15.3 权限

`POST /api/v1/demo/reset`不能公开给任意访客。建议使用专用演示管理员令牌或部署环境开关。

### 15.4 时间基准

为避免“今日订单”随日期失效：

- P0/P1测试使用显式`business_date`；或
- 重置时将相对日期转换为当前UTC+8日期。

评测文件中不得依赖机器本地时区。

---

## 16. 导入顺序

后端Seed导入顺序固定：

1. tenants；
2. users；
3. customers；
4. product_families；
5. skus；
6. tier_prices；
7. inventory；
8. customer_aliases；
9. demo drafts/orders（如有）；
10. condition lexicon由应用启动时独立加载/校验。

任何一步Schema失败，整个seed导入应失败并给出具体文件、对象ID和错误路径，不能跳过错误行继续。

---

## 17. 数据Schema校验

至少检查：

- ID唯一；
- 所有外键存在且同租户；
- 金额为两位小数字符串；
- 数量可转正整数；
- SKU单位与库存单位一致；
- 演示SKU/Tier价格完整；
- 客户电话符合合成号段；
- 无真实姓名、电话或企业记录；
- 条件类型属于统一枚举；
- 数据集case_id唯一；
- 开发集与冻结集不重复；
- 答案键case_id与数据集一一对应；
- 冻结集SHA-256匹配。

建议提供：

```bash
python scripts/validate_seed.py
python scripts/validate_dataset.py tests/datasets/dev_32.json
python scripts/verify_frozen_hash.py
```

---

## 18. 评测脚本接口

建议：

```bash
python scripts/run_eval.py --mode ai --dataset tests/datasets/frozen_eval_32.json
python scripts/run_eval.py --mode fallback --dataset tests/datasets/frozen_eval_32.json
python scripts/run_eval.py --mode ai --conditions lexicon
```

输出至少包括：

- 总案例数；
- 商品族正确率；
- SKU/规格自动正确映射率；
- 未知商品召回；
- 静默错配数；
- 价格条件召回率与误报；
- 疑点代码匹配；
- AI与Fallback分开结果；
- 每案例明细；
- 模型/词表/数据集版本；
- 冻结集SHA-256。

核心目标不是追求漂亮准确率，而是证明：

```text
静默错配 = 0
核价错误 = 0
条件未被错误自动放行
```

---

## 19. 证据文件

`evidence/`中的原始记录不得被总结值覆盖。建议：

```text
evaluation_ai.json
evaluation_fallback.json
alias_replay.json
baseline_manual_raw.csv
ab_timing_raw.csv
first_use.csv
README.md
```

README说明：

- 数据如何生成；
- 哪些是假设；
- 哪些是实测；
- 样本量；
- 测量日期；
- 使用的版本和SHA-256；
- 失败案例如何保留。

---

## 20. 数据组交付清单

- [ ] T1/T2租户JSON。
- [ ] 三角色用户与合成演示令牌资料。
- [ ] 13个客户及要求的Tier/提醒字段。
- [ ] 商品族和SKU，覆盖所有必备歧义结构。
- [ ] 完整Tier价格。
- [ ] 可触发边界情况的库存。
- [ ] 客户级别名与回放案例。
- [ ] `conditions_v0.yaml`及正负例。
- [ ] 开发集。
- [ ] 独立冻结集。
- [ ] 与应用隔离的答案键。
- [ ] `FROZEN_SHA256.txt`。
- [ ] A/B工具组和首次使用任务。
- [ ] 演示重置基线。
- [ ] 数据生成与限制说明。

## 21. 后端交付清单

- [ ] JSON/YAML Schema。
- [ ] Seed验证和导入脚本。
- [ ] 稳定、事务性的演示重置。
- [ ] 金额Decimal和数量整数转换。
- [ ] 完整的外键/同租户校验。
- [ ] 词表加载与版本记录。
- [ ] 运行时代码不读取答案键。
- [ ] 评测脚本输出AI/Fallback分组结果。
- [ ] 冻结哈希验证脚本。
- [ ] 对错误数据给出文件、对象ID和字段路径。

## 22. 对接验收

- [ ] 空数据库可通过seed建立两个租户。
- [ ] 重复导入行为明确且可复现。
- [ ] 两租户相同名称不会串数据。
- [ ] 所有演示SKU都能查到Tier价格和库存。
- [ ] T1/T2阈值产生预期不同路由。
- [ ] Kedai Mesra与Restoran Ali产生预期不同路由。
- [ ] PII消息落库后只存在掩码文本。
- [ ] 小数数量负例生成`INVALID_QUANTITY`。
- [ ] 未知商品保留订单行而不是被忽略。
- [ ] 条件正例与负例均通过。
- [ ] 冻结集哈希验证通过。
- [ ] 应用无法导入或读取答案键。
- [ ] 演示重置后所有关键结果一致。

