# KiraOrder Gate 0 执行手册

> **用途**：从现在开始，在 **90–120 分钟**内产出 Gate 0 的全部产物。  
> **不做**：不改 `01`—`04` 正文，不改 v2.1 基线，不写业务后端代码。  
> **基线**：v2.1，SHA-256 `5D02EBF84413B7FE617C32B64E707AFF476EBD963E6638091C875EE0D1B8A55D`（1475 行）  
> **提案**：Revision 2，SHA-256 `40DA19F4FE5CA0282B7127F66E934872B91A2BD920F8D833B79BEAB0684DF12B`（738 行）  
> **前一版复审**：SHA-256 `87F5776B8554914274CB3196737603E39979FA738ACF75AE175EE1136FE4E9A4`（425 行）  
> **Gate 0 完成定义**：§1—§4 的产物全部存在、可解析、四方确认、manifest 记录哈希；`01`—`04` 和 v2.1 未被修改。

---

## 0. 先明确边界

### 0.1 现在做 / 现在不做

| 现在做（Gate 0） | 现在不做 |
|---|---|
| baseline manifest、变更记录、errata 草案 | 改 `01`—`04` 正文 |
| 物理 schema、字段字典、错误表 | 改 v2.1 基线 |
| H1/H5 规范与词表 | 写 FastAPI 业务逻辑 |
| OpenAPI 骨架、fixture 目录 | 改前端页面 |
| 逐条追踪矩阵、测试清单 | 改 seed/答案键 |
| 四方确认/签字 | 做 P1/P2 功能 |

### 0.2 时间盒

| 时间 | 动作 | 产出 |
|---|---|---|
| 0–15 min | 锁基线、建目录、写 manifest | `baseline-manifest.json` |
| 15–45 min | 三个硬契约 | `db-schema.md`、`fields.md`、`errors.md` |
| 45–75 min | H1/H5 + OpenAPI + fixture | `field-evidence.md`、`condition-triggers.md`、`openapi.yaml`、fixtures |
| 75–90 min | 四方确认、签字、冻结 | Gate 0 签字表 + `gate0-v1` |

> 如果只有 60 分钟：先做 §1 + §2 的 `db-schema/fields/errors`；H1/H5/OpenAPI/fixtures 放到下一小时。**不要跳过 §1 的 manifest。**

---

## 1. 0–15 分钟：锁基线、建目录、写 manifest

### 1.1 建目录

把下面命令里的 `$REPO` 改成你的仓库根目录（例如 `C:\Users\n_bom\Desktop\SDC HACKATHON\kiraorder`）：

```powershell
$REPO = "C:\Users\n_bom\Desktop\SDC HACKATHON\kiraorder"   # 改成你的仓库根
New-Item -ItemType Directory -Force -Path `
  "$REPO\contracts\fixtures", `
  "$REPO\migrations", `
  "$REPO\docs", `
  "$REPO\tests\contract" | Out-Null
```

最终结构：

```text
$REPO/
├── baseline-manifest.json
├── contracts/
│   ├── db-schema.md
│   ├── fields.md
│   ├── errors.md
│   ├── condition-triggers.md
│   ├── field-evidence.md
│   ├── openapi.yaml
│   └── fixtures/
├── migrations/
│   └── 0001_baseline.sql
├── docs/
│   ├── 05_KiraOrder_v1.3_契约变更记录.md
│   └── v2.1-erratum-1.md
└── tests/
    └── contract/
```

### 1.2 算哈希

```powershell
$V21 = "C:\Users\n_bom\Desktop\SDC HACKATHON\项目方向选择\最终方案\KiraOrder_终版执行方案_v2_2026-10-21.md"
$PROP = "C:\Users\n_bom\Documents\ChatGPT\SDC HACKATHON\output\KiraOrder_v1.2_评审复核与v1.3拟议解决方案_待批准_2026-10-21.md"
$REVIEW = "C:\Users\n_bom\Desktop\小项目\KiraOrder_v1.3_Revision2_复审与Gate0批准建议_2026-10-21.md"

foreach ($p in @($V21, $PROP, $REVIEW)) {
  $f = Get-Item -LiteralPath $p
  $h = (Get-FileHash -LiteralPath $p -Algorithm SHA256).Hash
  "{0}`n  lines={1} bytes={2}`n  sha256={3}" -f $p, (Get-Content -LiteralPath $p -Encoding UTF8).Count, $f.Length, $h
}
```

### 1.3 写 `baseline-manifest.json`

把下面模板复制到 `$REPO\baseline-manifest.json`，把 `created_at` 改成当前时间：

```json
{
  "gate0_version": "gate0-v1",
  "created_at": "2026-10-21T19:15:00+08:00",
  "approved_by": "He Minghao",
  "baseline": {
    "name": "KiraOrder v2.1",
    "path": "C:/Users/n_bom/Desktop/SDC HACKATHON/项目方向选择/最终方案/KiraOrder_终版执行方案_v2_2026-10-21.md",
    "sha256": "5D02EBF84413B7FE617C32B64E707AFF476EBD963E6638091C875EE0D1B8A55D",
    "lines": 1475,
    "bytes": 124468
  },
  "proposal": {
    "name": "Revision 2",
    "path": "C:/Users/n_bom/Documents/ChatGPT/SDC HACKATHON/output/KiraOrder_v1.2_评审复核与v1.3拟议解决方案_待批准_2026-10-21.md",
    "sha256": "40DA19F4FE5CA0282B7127F66E934872B91A2BD920F8D833B79BEAB0684DF12B",
    "lines": 738,
    "bytes": 55453
  },
  "review": {
    "name": "Revision 2 复审",
    "path": "C:/Users/n_bom/Desktop/小项目/KiraOrder_v1.3_Revision2_复审与Gate0批准建议_2026-10-21.md",
    "sha256": "C97C47E649A9C5A9A82F5D17E29C5A6F44C2C7D46479291BC3F7D236BEED5CEE",
    "lines": 265,
    "bytes": 20347
  },
  "prior_review": {
    "name": "Revision 1 复审",
    "path": "C:/Users/n_bom/Desktop/小项目/KiraOrder_v1.3_拟议方案评审与批准建议_2026-10-21.md",
    "sha256": "87F5776B8554914274CB3196737603E39979FA738ACF75AE175EE1136FE4E9A4",
    "lines": 425,
    "bytes": 34882
  },
  "orbyte_reference": {
    "path": "C:/Users/n_bom/Documents/xwechat_files/wxid_mxrdsfytoh4r12_f048/msg/file/2026-10/Orbyte-前后端参考说明.md",
    "sha256": "EE3FEB8C4C533A5104DAF3F3CC4AA144326A3CB675F48A4E73F3FF8D0F11CE00",
    "lines": 127
  },
  "gate0_outputs": {
    "db_schema": "contracts/db-schema.md",
    "fields": "contracts/fields.md",
    "errors": "contracts/errors.md",
    "condition_triggers": "contracts/condition-triggers.md",
    "field_evidence": "contracts/field-evidence.md",
    "openapi": "contracts/openapi.yaml",
    "fixtures": "contracts/fixtures/",
    "change_record": "docs/05_KiraOrder_v1.3_契约变更记录.md",
    "erratum": "docs/v2.1-erratum-1.md"
  },
  "signoff": {
    "backend": "He Minghao",
    "frontend": "",
    "ai": "",
    "data": ""
  }
}
```

校验 JSON：

```powershell
Get-Content "$REPO\baseline-manifest.json" -Raw | ConvertFrom-Json | Out-Null
"manifest JSON OK"
```

### 1.4 写 `docs/05_KiraOrder_v1.3_契约变更记录.md` v0.1

不要写长篇；只登记“改什么/依据/影响/验收”。模板：

```markdown
# KiraOrder v1.3 契约变更记录

> 状态：GATE0_DRAFT
> 基线：v2.1 / 5D02EBF84413...A55D
> 提案：Revision 2 / 40DA19F4FE5C...DF12B

| ID | 变更 | 依据 | 影响文件 | 机器产物 | 验收 | 批准 |
|---|---|---|---|---|---|---|
| G0-01 | 物理表/JSONB 聚合 | Rev2 §7.7 | 01 §6; 04 §1/§6–§9 | db-schema + migration | 空库迁移 + seed | 待签 |
| G0-02 | 字段字典/终止/原因/价格口径 | Rev2 §7.8 | 01 §4/§5; 02 §2; 04 §13 | fields + OpenAPI | 字段/枚举一致 | 待签 |
| G0-03 | 错误/成功体/请求 ID | Rev2 §7.10 | 01 §15; 02 §3/§16 | errors + OpenAPI | fixture 通过 | 待签 |
| G0-04 | H1 字段证据 | Rev2 §7.11 | 01 §10; 03 §6–§8; 04 §10 | field-evidence + 词表 | DEV-39—41 | 待签 |
| G0-05 | H5 条件触发 | Rev2 §7.12 | 01 §8/§9; 03 §11; 04 §10 | condition-triggers + 词表 | TEST-29/30/32 | 待签 |
| G0-06 | v2.1 errata 分层 | Rev2 §8.1 | 基线勘误 | erratum | 独立哈希/批准 | 待签 |
| G0-07 | OWNER/审计/回复 P0 | v2.1 §3.5/§4.9 | 01 §7/§12; 02 §11–§14 | role/approval/reply fixtures | OWNER 路径通过 | 待签 |
```

### 1.5 写 `docs/v2.1-erratum-1.md` v0.1

```markdown
# KiraOrder v2.1 Erratum 1

> 状态：DRAFT / 待批准
> 只放“对基线自身的正确性勘误”，不放四份文档的普通对齐。

| ID | 勘误 | 原文/现状 | 改为 | 理由 | 影响 |
|---|---|---|---|---|---|
| E1 | AiMode 混合路径 | `LLM/FALLBACK/ALIAS_ONLY` | 增加 `MIXED` | 单行 fallback 无法表达 | 01/02/03/04 |
| E2 | SQL 漏字段 | `delivery_orders` 缺 `escalation_reasons` | 补列 | 模型/SQL 不一致 | 01/04/migration |
| E3 | H1 字段证据 | 只校验 span/闭集/qty | 增加字段证据规范 | 防静默错配 | 03/01/04 |
| E4 | H5 裸金额误报 | `RM\d+` 单独触发 | 议价短语/询价语气触发 | 历史陈述误报 | 01/03/04 |
| E5 | 金额口径 | 无 UNIT/TOTAL | 增加 `price_basis` | 总价/单价歧义 | 01/02/04 |
| E6 | 快照不可变 | 仅 draft_version | 不可变 JSONB 快照 + 触发器 | 审批版本可能被改 | 01/04/migration |
| E7 | 成功体/请求 ID | 未逐端点固定 | 直接模型 + `X-Request-ID` | 前端/错误处理不一致 | 01/02 |
| E8 | 物理 schema | v2.1 SQL 与 01 表名不同 | 采用 v2.1 表名 + 聚合 JSONB | 单一物理真相 | 01/04/migration |
```

---

## 2. 15–45 分钟：三个硬契约

### 2.1 `contracts/db-schema.md`

先写表清单，再写列定义。表清单直接用 Revision 2 §7.7，不要重新设计：

| 表 | 作用 | 关键约束 |
|---|---|---|
| `tenants` | 租户规则/阈值 | `amount_threshold_rm`、`checks_enabled`、`below_tier_price_override_requires_owner`、`credit_flag_requires_owner` |
| `users` | 身份/角色 | `CLERK/OWNER/WAREHOUSE`；项目分工不进枚举 |
| `customers` | 客户主档 | `phone_e164` 合成号段；`credit_flag` |
| `product_families` | 商品族 | 族 ID/名称/版本 |
| `family_aliases` | 族多语别名 | 同租户 `phrase_norm` 不跨族重复 |
| `products` | SKU 真相 | `family_id/pack_size/grade/base_unit` |
| `uom_aliases` | 单位别名 | canonical unit + 精确别名；P0 不做换算 |
| `customer_tier_prices` | SKU×Tier 等级价 | `(tenant_id, product_id, tier)` 唯一；`NUMERIC(12,2)` |
| `inventory` | 可用库存 | `(tenant_id, product_id)` 唯一；`CHECK >= 0` |
| `alias_cache` | 客户/租户别名 | `phrase_norm` 唯一；`customer_id` 可空 |
| `inbound_messages` | 脱敏入站 | 只存 masked text |
| `orders` | 草稿聚合根 | `version`；`working_lines/issues/clarification/escalation_preview` JSONB |
| `draft_versions` | 不可变版本 | `(draft_id, version)` 唯一；snapshot JSONB |
| `approval_requests` | 老板审批 | 提交版本 + lines/totals/reasons 快照；一草稿一 PENDING |
| `delivery_orders` | 已批准 DO | `draft_id` 唯一；`lines` JSONB；`escalation_reasons` |
| `activity_log` | UI 时间线 | append-only |
| `audit_logs` | 审计头 | append-only |
| `field_diffs` | 字段差异 | `audit_id` 子记录；append-only |

列定义模板：

```markdown
### orders

| 列 | 类型 | 空 | 默认 | 约束 | 说明 |
|---|---|---:|---|---|---|
| tenant_id | text | 否 | — | FK tenants | 租户 |
| draft_id | text | 否 | — | PK | 草稿 ID |
| customer_id | text | 否 | — | FK customers | 客户 |
| message_id | text | 是 | — | FK inbound_messages | 入站消息 |
| status | text | 否 | — | CHECK | v2.1 五状态 |
| version | int | 否 | 1 | >0 | 乐观锁 |
| ai_mode | text | 否 | — | CHECK | LLM/FALLBACK/ALIAS_ONLY/MIXED |
| ai_initial_snapshot | jsonb | 是 | — | — | 初始快照 |
| working_lines | jsonb | 否 | '[]' | — | 当前行 |
| issues | jsonb | 否 | '[]' | — | 当前疑点/条件 |
| clarification | jsonb | 是 | — | — | 澄清对象 |
| escalation_preview | jsonb | 否 | '[]' | — | 升级预演 |
| termination_reason | text | 是 | — | CHECK | OWNER_REJECTED/CLERK_DISCARDED/SYSTEM_TERMINATED |
| created_at/updated_at | timestamptz | 否 | now() | — | UTC |
```

至少写全这 6 张关键表：`orders`、`draft_versions`、`approval_requests`、`delivery_orders`、`inventory`、`customer_tier_prices`。其余表先写“列清单 + 约束”，Gate 0-B 再补。

最小 DDL 片段（可直接放进 `migrations/0001_baseline.sql`，按你的命名调整）：

```sql
CREATE TABLE draft_versions (
  tenant_id text NOT NULL,
  draft_id text NOT NULL,
  version int NOT NULL,
  snapshot jsonb NOT NULL,
  created_by text NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (draft_id, version)
);

CREATE TABLE approval_requests (
  approval_id text PRIMARY KEY,
  tenant_id text NOT NULL,
  draft_id text NOT NULL,
  draft_version int NOT NULL,
  status text NOT NULL CHECK (status IN ('PENDING','APPROVED','REJECTED')),
  reasons jsonb NOT NULL,
  snapshot jsonb NOT NULL,
  requested_by text NOT NULL,
  requested_at timestamptz NOT NULL DEFAULT now(),
  decided_by text,
  decided_at timestamptz,
  decision_note text
);
CREATE UNIQUE INDEX one_pending_per_draft
  ON approval_requests (draft_id) WHERE status = 'PENDING';

CREATE TABLE delivery_orders (
  do_number text PRIMARY KEY,
  tenant_id text NOT NULL,
  draft_id text NOT NULL UNIQUE,
  customer_id text NOT NULL,
  lines jsonb NOT NULL,
  final_total_rm numeric(12,2) NOT NULL,
  prepared_by text NOT NULL,
  approved_by text NOT NULL,
  escalation_reasons jsonb NOT NULL DEFAULT '[]',
  related_do_number text,
  approved_at timestamptz NOT NULL DEFAULT now()
);
```

**Gate 0 验收**：表清单/关键列/唯一约束/append-only 与 immutability 触发器都写进 `db-schema.md`；`migrations/0001_baseline.sql` 能在空库执行。不要在 Gate 0 写业务 SQL。

### 2.2 `contracts/fields.md`

不要只写“新增字段”，要写完整对象。至少 6 张表：

```markdown
## Issue
| 字段 | 类型 | 可空 | 值/说明 |
|---|---|---:|---|
| issue_id | string | 否 | ISS_... |
| code | IssueCode | 否 | 8 个公共码 |
| line_id | string | 是 | 行级疑点 |
| span | string | 是 | 脱敏原文 |
| condition_kind | STOCK/PRICE/TIME/OTHER | 是 | 条件类 |
| condition_scope | SINGLE_LINE/MULTI_LINE/ORDER_LEVEL/UNKNOWN | 是 | 价格条件范围 |
| candidate_line_ids | string[] | 否 | 候选行 |
| target_line_ids | string[] | 否 | 人工确认目标行 |
| requested_unit_price | decimal string | 是 | 只由原文提取 |
| price_basis | UNIT/TOTAL/UNKNOWN | 是 | 价格口径 |
| reason_code | enum | 是 | 细分原因 |
| ask | CUSTOMER/OWNER/CLERK/SYSTEM | 否 | v2.1 字段 |
| data_used | object | 否 | 使用的数据 |
| blocking | bool | 否 | 是否阻断 |
| resolved | bool | 否 | 是否解决 |
| resolution | ResolutionChoice | 是 | 消息级处理 |
| resolution_note | string | 是 | 备注 |
| auto_resolved_by | STOCK_CHECK | 是 | 自动解决 |
```

同样写全 `WorkingLine`、`OrderDraft`、`SaveLinesRequest`、`ApprovalRequest/Detail`、`DeliveryOrder`。

**7 个命名裁决（直接填，不要再讨论）**：

| 问题 | 采用 | 规则 |
|---|---|---|
| `confirmed_unit_price` vs `unit_price_override` | 两个都保留，但语义分开 | `WorkingLine.unit_price_override` = 行级写入；`IssueResolution.confirmed_unit_price` = 消息级 `ACCEPT_REQUESTED_PRICE` 的输入；后端映射到目标行 |
| `below_tier_price_override_requires_owner` vs `price_override_requires_owner` | 用新名 | 写进 errata；04 seed/01 schema 同步 |
| `MISSING_TIER_PRICE` HTTP | 建议 422 | 前端显示“配置缺失”；若坚持 500，写 errata |
| 401/403/404 code | `INVALID_TOKEN/FORBIDDEN_ACTION/RESOURCE_NOT_FOUND` | 与 01/02 对齐，减少前端改动 |
| `AI_WAKE_RATE_LIMITED` vs `RATE_LIMITED` | 统一 `RATE_LIMITED` + `details.scope` | 02 加旧码映射 |
| P1 `discard` 端点 | `POST /api/v1/orders/drafts/{id}/discard` | `expected_version` + `termination_reason=CLERK_DISCARDED` + note |
| `MISSING_TIER_PRICE` / `MESSAGE_TOO_LONG` / `REJECTION_REASON_REQUIRED` / `INVALID_QUANTITY` | 都补进 errors | 不要留到实现时再定 |

### 2.3 `contracts/errors.md`

按下面表填；`建议`列是默认值，你可以改，但只能改一次并写 errata：

| HTTP | code | 触发 | 建议/备注 |
|---:|---|---|---|
| 400 | `DISAMBIGUATION_UNRESOLVED` | 阻断疑点未清 | v2.1 |
| 400 | `INSUFFICIENT_STOCK` | 保存/提交已知缺货 | v2.1 |
| 400 | `TARGET_LINE_REQUIRED` | 价格条件缺目标行 | v2.1 |
| 400 | `OVERRIDE_REQUIRED` | 目标行未有效改价/缺原因 | v2.1 |
| 400 | `NOTE_REQUIRED` | 必须备注未写 | v2.1 |
| 400 | `EMPTY_ORDER` | 删除所有行 | Revision 2 |
| 400 | `INVALID_LINE_OPERATION` | 行集合/删除集合不完整/重复/未知 ID | Revision 2 |
| 401 | `INVALID_TOKEN` | 缺失/无效令牌 | 与 01/02 对齐 |
| 403 | `FORBIDDEN_ACTION` | 角色无权 | 与 01/02 对齐 |
| 403 | `TENANT_MISMATCH` | 请求体租户与会话不一致 | v2.1 |
| 404 | `RESOURCE_NOT_FOUND` | 不存在/跨租户 | 与 01/02 对齐 |
| 409 | `STALE_VERSION` | `expected_version` 不是最新 | v2.1；02 映射旧 `DRAFT_VERSION_CONFLICT` |
| 409 | `PENDING_OWNER_APPROVAL` | 待批期间编辑/重复提交/作废 | v2.1 |
| 409 | `ALREADY_APPROVED` | 已生成 DO；details 带 `do_number/approved_at` | v2.1 |
| 409 | `DRAFT_REJECTED` | 已终止草稿再操作 | v2.1 |
| 409 | `STOCK_CHANGED` | 事务锁内库存变化；审批保持 PENDING | v2.1 |
| 422 | `REQUEST_VALIDATION_FAILED` | JSON 类型/格式不合法 | Revision 2 |
| 422 | `MESSAGE_TOO_LONG` | 超过 4000 Unicode | 补 |
| 422 | `REJECTION_REASON_REQUIRED` | 老板驳回缺理由 | 补 |
| 422 | `INVALID_QUANTITY` | 客户端数量非法 | 补；或 400 |
| 422 | `MISSING_TIER_PRICE` | 价格配置缺失 | 建议 422；seed/startup 先校验 |
| 429 | `RATE_LIMITED` | parse/wake 超配额 | `details.scope=PARSE/AI_WAKE` |
| 503 | `AI_AND_FALLBACK_UNAVAILABLE` | AI/兜底都不可用 | v2.1 |

旧码→新码映射（至少这 4 行）：

| 旧码（01/02） | 新码 | 备注 |
|---|---|---|
| `DRAFT_VERSION_CONFLICT` | `STALE_VERSION` | 409 |
| `FORBIDDEN_ACTION` | `FORBIDDEN_ACTION` | 不变 |
| `RESOURCE_NOT_FOUND` | `RESOURCE_NOT_FOUND` | 不变 |
| `AI_WAKE_RATE_LIMITED` | `RATE_LIMITED` | `details.scope=AI_WAKE` |

**Gate 0 验收**：每个错误都有 HTTP、code、触发、前端行为、fixture 名；`X-Request-ID` 在成功/失败都返回。

---

## 3. 45–75 分钟：H1/H5 + OpenAPI + fixtures

### 3.1 `contracts/field-evidence.md`

直接抄 Revision 2 §7.11 的 8 条，再加三张词表：

```markdown
## 1. 定位
span 唯一映射到 masked text 半开区间；重复出现按顺序/非重叠；失败单行 fallback。

## 2. qty 词表
| 语言 | 词 | 值 |
|---|---|---|
| ms | satu/dua/tiga/... | 1/2/3/... |
| en | one/two/three/... | 1/2/3/... |
| zh | 一/二/两/三/十/... | 1/2/2/3/10/... |

## 3. uom 词表
| canonical | aliases |
|---|---|
| ctn | ctn/carton/箱 |
| pack | pack/packet/包 |
| kg | kg/kilogram/公斤 |

## 4. family 证据
族名/family_aliases/客户级别名精确命中；否则 FAMILY_NOT_EVIDENCED。

## 5. 失败映射
| 失败 | 处理 |
|---|---|
| qty 无证据/非法 | 单行 LOW_CONFIDENCE_MATCH(reason_code=INVALID_QUANTITY) |
| uom/size/grade 无证据 | 丢弃该字段，交 Resolver |
| fam 无证据 | LOW_CONFIDENCE_MATCH(reason_code=FAMILY_NOT_EVIDENCED) |
| span 定位失败 | reason_code=SOURCE_EVIDENCE_INVALID |

## 6. 测试
DEV-39/40/41；中文数字/马来数字/`ctn→箱` 各一条。
```

### 3.2 `contracts/condition-triggers.md`

直接抄 Revision 2 §7.12 的真值表，再加词表条目：

| id | type | pattern | 说明 |
|---|---|---|---|
| cond_stock_ms_001 | STOCK | `kalau ada` | 有货条件 |
| cond_stock_en_001 | STOCK | `if available` | 英文有货 |
| cond_stock_zh_001 | STOCK | `有货的话` | 中文有货 |
| cond_price_ms_001 | PRICE | `kalau\s+RM\s*\d+` | 价格条件 |
| cond_price_ms_002 | PRICE | `boleh kurang` | 议价，无金额 |
| cond_price_zh_001 | PRICE | `便宜/老价钱/少一点` | 中文议价 |
| cond_price_en_001 | PRICE | `can less/discount/cheaper` | 英文议价 |
| cond_other_001 | OTHER | `kalau sempat/hantar sebelum` | 时间/其他 |

**必须写清楚**：

- 裸 `RM95` 只作证据，不触发；
- `Last order was RM95`、`Total last time RM95`、`Stock code A95` 不触发；
- `RM95?`、`Can follow last price RM95?` 触发 PRICE；
- `kalau ada, boleh kurang` 生成 STOCK+PRICE 两条；
- `hantar esok` 不触发；
- `NOT_A_CONDITION` + note + `CONDITION_DISMISSED`。

### 3.3 `contracts/openapi.yaml` 骨架

不要写完整业务；先固定 13 个 P0 路径和核心 schema：

```yaml
openapi: 3.1.0
info:
  title: KiraOrder v1.3 API
  version: 1.3.0
servers:
  - url: /api/v1
paths:
  /orders/parse-draft:
    post:
      operationId: parseDraft
      responses:
        '200': { $ref: '#/components/responses/OrderDraft' }
  /orders/drafts:
    get:
      operationId: listDrafts
      responses:
        '200': { $ref: '#/components/responses/DraftList' }
  /orders/drafts/{draft_id}:
    get:
      operationId: getDraft
      parameters:
        - { name: draft_id, in: path, required: true, schema: { type: string } }
      responses:
        '200': { $ref: '#/components/responses/OrderDraft' }
  /orders/drafts/{draft_id}/lines:
    put:
      operationId: saveLines
      parameters:
        - { name: draft_id, in: path, required: true, schema: { type: string } }
      requestBody:
        required: true
        content:
          application/json:
            schema: { $ref: '#/components/schemas/SaveLinesRequest' }
      responses:
        '200': { $ref: '#/components/responses/OrderDraft' }
  /orders/{draft_id}/approve:
    post:
      operationId: approve
      parameters:
        - { name: draft_id, in: path, required: true, schema: { type: string } }
      requestBody:
        required: true
        content:
          application/json:
            schema: { $ref: '#/components/schemas/ApproveRequest' }
      responses:
        '200': { $ref: '#/components/responses/DeliveryOrder' }
        '202': { $ref: '#/components/responses/ApprovalRequest' }
  /approvals:
    get:
      operationId: listApprovals
      responses:
        '200': { $ref: '#/components/responses/ApprovalList' }
  /approvals/{approval_id}:
    get:
      operationId: getApproval
      parameters:
        - { name: approval_id, in: path, required: true, schema: { type: string } }
      responses:
        '200': { $ref: '#/components/responses/ApprovalDetail' }
  /approvals/{approval_id}/decide:
    post:
      operationId: decide
      parameters:
        - { name: approval_id, in: path, required: true, schema: { type: string } }
      requestBody:
        required: true
        content:
          application/json:
            schema: { $ref: '#/components/schemas/DecideRequest' }
      responses:
        '200': { $ref: '#/components/responses/DeliveryOrder' }
  /orders/{do_number}/audit-detail:
    get:
      operationId: auditDetail
      parameters:
        - { name: do_number, in: path, required: true, schema: { type: string } }
      responses:
        '200': { $ref: '#/components/responses/AuditDetail' }
  /activity:
    get:
      operationId: activity
      responses:
        '200': { $ref: '#/components/responses/ActivityList' }
  /me:
    get:
      operationId: me
      responses:
        '200': { $ref: '#/components/responses/Me' }
  /ai/status:
    get:
      operationId: aiStatus
      responses:
        '200': { $ref: '#/components/responses/AiStatus' }
  /ai/wake:
    post:
      operationId: aiWake
      responses:
        '200': { $ref: '#/components/responses/AiWake' }
components:
  responses:
    OrderDraft:
      description: TODO
      content:
        application/json:
          schema: { $ref: '#/components/schemas/OrderDraft' }
    DraftList:
      description: TODO
      content:
        application/json:
          schema: { $ref: '#/components/schemas/DraftListResponse' }
    DeliveryOrder:
      description: TODO
      content:
        application/json:
          schema: { $ref: '#/components/schemas/DeliveryOrder' }
    ApprovalRequest:
      description: TODO
      content:
        application/json:
          schema: { $ref: '#/components/schemas/ApprovalRequest' }
    ApprovalList:
      description: TODO
      content:
        application/json:
          schema: { $ref: '#/components/schemas/ApprovalListResponse' }
    ApprovalDetail:
      description: TODO
      content:
        application/json:
          schema: { $ref: '#/components/schemas/ApprovalDetail' }
    AuditDetail:
      description: TODO
      content:
        application/json:
          schema: { $ref: '#/components/schemas/AuditDetail' }
    ActivityList:
      description: TODO
      content:
        application/json:
          schema: { $ref: '#/components/schemas/ActivityListResponse' }
    Me:
      description: TODO
      content:
        application/json:
          schema: { $ref: '#/components/schemas/MeResponse' }
    AiStatus:
      description: TODO
      content:
        application/json:
          schema: { $ref: '#/components/schemas/AiStatus' }
    AiWake:
      description: TODO
      content:
        application/json:
          schema: { $ref: '#/components/schemas/AiWakeResult' }
  headers:
    X-Request-ID:
      schema: { type: string }
  schemas:
    Error:
      type: object
      required: [error_code, message]
      properties:
        error_code: { type: string }
        message: { type: string }
        details: { type: object }
    SaveLinesRequest:
      type: object
      required: [expected_version, lines]
      properties:
        expected_version: { type: integer, minimum: 1 }
        lines: { type: array, items: { $ref: '#/components/schemas/WorkingLine' } }
        deleted_line_ids: { type: array, items: { type: string } }
        resolutions: { type: array, items: { $ref: '#/components/schemas/IssueResolution' } }
    WorkingLine: { type: object }
    IssueResolution: { type: object }
    OrderDraft: { type: object }
    DeliveryOrder: { type: object }
    ApprovalRequest: { type: object }
    ApprovalDetail: { type: object }
    AuditDetail: { type: object }
    DraftListResponse: { type: object }
    ApprovalListResponse: { type: object }
    ActivityListResponse: { type: object }
    MeResponse: { type: object }
    AiStatus: { type: object }
    AiWakeResult: { type: object }
    ApproveRequest: { type: object }
    DecideRequest: { type: object }
```

其余 schema 按 `fields.md` 补。**先保证 `openapi.yaml` 能被 lint/解析，再谈完整。**

### 3.4 `contracts/fixtures/` 最小集合

至少先放这 8 个，其他 Gate 0-C 补：

```text
parse_draft.json
save_lines_ready.json
save_lines_target_required.json
approve_200.json
approve_202.json
approve_stock_changed_409.json
already_approved_409.json
audit_detail.json
```

`parse_draft.json` 最小示例：

```json
{
  "data": null,
  "status": 200,
  "body": {
    "draft_id": "DRF_001",
    "version": 1,
    "status": "DISAMBIGUATION_REQUIRED",
    "ai_mode": "MIXED",
    "lines": [
      {
        "line_id": "LIN_001",
        "sku_id": null,
        "requested_qty": 5,
        "confirmed_qty": null,
        "effective_qty": 5,
        "match_source": "LLM_EXTRACTED"
      }
    ],
    "issues": [
      {
        "issue_id": "ISS_001",
        "code": "MULTIPLE_PACK_SIZES",
        "ask": "CUSTOMER",
        "blocking": true,
        "resolved": false
      }
    ],
    "blocking_issues": ["MULTIPLE_PACK_SIZES"],
    "escalation_preview": [],
    "clarification_draft": null,
    "clarification_lang": "ms"
  }
}
```

> fixture 外层用 `status`/`body` 只是测试包装，不是 API 成功体；成功体仍按 OpenAPI 直接返回模型。

### 3.5 `tests/contract/` 三个最小测试

```python
# tests/contract/test_fixtures_json.py
import json
from pathlib import Path

FIXTURES = Path(__file__).parents[2] / "contracts" / "fixtures"

def test_all_fixtures_are_json():
    for path in FIXTURES.glob("*.json"):
        json.loads(path.read_text(encoding="utf-8"))
```

```python
# tests/contract/test_openapi_parses.py
# 需要 PyYAML：pip install pyyaml；没有就暂时跳过这个测试。
import yaml
from pathlib import Path

def test_openapi_parses():
    path = Path(__file__).parents[2] / "contracts" / "openapi.yaml"
    doc = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert doc["openapi"].startswith("3.")
    assert "/orders/parse-draft" in doc["paths"]
```

```python
# tests/contract/test_demo_path.py
# Gate 0 只留占位；P0 完成后按方案 §11.1 的 18 拍补全。
def test_demo_path_placeholder():
    assert True
```

---

## 4. 75–90 分钟：四方确认、签字、冻结

### 4.1 评审清单

- [ ] `baseline-manifest.json` 与实测哈希/行数一致
- [ ] `db-schema.md` 表清单/关键列/约束/触发器完整
- [ ] `fields.md` 覆盖 Issue/WorkingLine/Draft/Approval/DO
- [ ] `errors.md` 覆盖 400/401/403/404/409/422/429/503 + 旧码映射
- [ ] `field-evidence.md` 有 qty/uom/family 词表 + 失败映射
- [ ] `condition-triggers.md` 有 11 行真值表 + 正负例
- [ ] `openapi.yaml` 能解析；13 个路径都在
- [ ] fixtures 至少 8 个 JSON 可解析
- [ ] `05_...` 变更记录/errata 草案存在
- [ ] `01`—`04`/v2.1 未被修改

### 4.2 签字表

| 角色 | 姓名 | 确认内容 | 时间 |
|---|---|---|---|
| 后端 | He Minghao | schema/fields/errors | |
| 前端 | | 成功/错误体、字段、`X-Request-ID` | |
| AI | | qty/int、fam UNKNOWN、H1/H5 | |
| 数据 | | seed/physical names、词表、TEST-01—24 | |

> 如果某端暂时没人：在群里发文件 + “24 小时内无异议视为通过”，并把消息截图放进 `docs/gate0-signoff.md`；不要因为等一个人停住。

### 4.3 冻结

```powershell
# 记录 Gate 0 产物的哈希（示例）
Get-ChildItem "$REPO\contracts" -Recurse -File |
  ForEach-Object {
    "{0}  {1}" -f (Get-FileHash -LiteralPath $_.FullName -Algorithm SHA256).Hash, $_.FullName
  } | Set-Content "$REPO\docs\gate0-hashes.txt" -Encoding UTF8
```

- 在 `baseline-manifest.json` 加 `"gate0_outputs_hash_file": "docs/gate0-hashes.txt"`；
- Git tag：`git tag gate0-v1 && git push --tags`（如果仓库已初始化）；
- 冻结后不再改 Gate 0 产物；要改就开 `gate0-v2`，不要静默覆盖。

---

## 5. Gate 0 之后：P0-A/B/C

### 5.1 顺序

| 阶段 | 内容 | 验收 |
|---|---|---|
| P0-A | C1—C21 枚举/路径/表名/字段对齐 | OpenAPI、DB、四份文档无漂移 |
| P0-B | H1/H2/H3/H4/H5/H12/H13/H14 + 批量保存 + 批准 6 项硬复核 | DEV-33—41、TEST-29/30/32、fixture 通过 |
| P0-C | OWNER 全能力、审批详情、审计、回复 | v2.1 P0 演示无需绕行 |
| P1 | 同日/作废/仓库/模拟入站 | P1 fixture |
| P2 | Orbyte 正式适配、Credits/Wallet | 正式授权/API |

### 5.2 文档/代码同步规则

每改一个契约点，必须同时更新：

1. `contracts/openapi.yaml` 或 `db-schema.md`；
2. `01`—`04` 对应章节；
3. `contracts/fixtures/` 对应 fixture；
4. `tests/contract/` 对应测试。

**一条变更没有这四样，不算完成。**

---

## 6. 常见坑（现在就要避开）

1. **不要现在改 `01`—`04` 正文**；Gate 0 先定 schema/fields/errors，否则会改两遍。
2. **不要恢复 `NEEDS_REVIEW/APPROVED/CANCELLED`**；公共状态严格 v2.1 五状态 + `termination_reason`。
3. **不要保留 `IssueResolutionAction`**；行级用 `WorkingLine`，消息级用 6 个 `ResolutionChoice`。
4. **不要用 `{data}` 成功包裹**；成功直接返回模型，错误扁平 `{error_code,message,details}`，`X-Request-ID` 放头。
5. **不要用 `draft_version` 做写请求字段**；用 `expected_version`；`decide` 不需要客户端重复提交草稿明细。
6. **不要把 `MISSING_TIER_PRICE` 做成可点击解决的疑点**；它是配置错误，seed/startup 先校验。
7. **不要用字符串 `qty` 做正式 wire**；正式 `int`，Adapter 只对 ASCII 数字字符串做一次性兼容。
8. **不要用 `null` 表示未知族**；正式 `"UNKNOWN"`，旧 `null` 只做迁移适配。
9. **不要把 OWNER/审计/回复静默降 P1**；要降级必须你明确批准并写变更记录。
10. **不要在 Gate 0 写长文**；用表、JSON、YAML、SQL；每份文档控制在 1–3 页。

---

## 7. 一页行动清单（打印/勾选）

- [ ] 设 `$REPO`，建 `contracts/migrations/docs/tests` 目录
- [ ] 算 v2.1/提案/复审/Orbyte 哈希，写 `baseline-manifest.json`
- [ ] 写 `05_KiraOrder_v1.3_契约变更记录.md` v0.1
- [ ] 写 `v2.1-erratum-1.md` v0.1（E1—E8）
- [ ] 写 `db-schema.md`（至少 6 张关键表 + 约束/触发器）
- [ ] 写 `fields.md`（Issue/WorkingLine/Draft/Approval/DO）
- [ ] 写 `errors.md`（完整错误表 + 旧码映射 + `X-Request-ID`）
- [ ] 写 `field-evidence.md`（8 条 + 3 张词表）
- [ ] 写 `condition-triggers.md`（11 行真值表 + 词表）
- [ ] 写 `openapi.yaml` 骨架（13 路径）
- [ ] 放 8 个最小 fixture
- [ ] 写 3 个 contract 测试
- [ ] 四方确认/签字（或 24h 无异议）
- [ ] 冻结 `gate0-v1`，记录 `gate0-hashes.txt`
- [ ] 开始 P0-A/B/C；`01`—`04` 与代码同步改

---

**一句话**：Gate 0 不是“再写一份文档”，而是把 Revision 2 的 738 行变成 8 个可执行文件：`manifest + db-schema + fields + errors + field-evidence + condition-triggers + openapi + fixtures`。做完这些，再动 `01`—`04` 和后端代码。
