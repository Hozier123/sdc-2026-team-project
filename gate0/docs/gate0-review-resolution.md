# Gate 0 审查意见处置记录

> 审查输入：`Gate0_审查报告与修改建议_2026-10-21.md`  
> SHA-256：`F477633979D0C10BDEC27611D870094E4B6FF28E2855350C16D6AC910BE75840`  
> 处置版本：Gate 0 draft revision 2 → `gate0-v3`（draft revision 4）；状态仍为 `AWAITING_CROSS_FUNCTIONAL_SIGNOFF`。

## P0 处置

| 审查项 | 结论 | 已落地内容 | 机器验收 |
|---|---|---|---|
| P0-1 安全边界 | 采纳 | parse 请求改为 `message_text`；后端负责掩码；响应固定 `masked_message` | fixture + schema + completeness |
| P0-2 OrderDraft | 采纳 | 增加 `customer/totals/allowed_actions/blocked_actions/conditions/masked_message` | completeness + fixture schema |
| P0-3 DraftSummary | 采纳 | 增加客户、脱敏预览、阻断/升级计数、来源与动作 | completeness |
| P0-4 MeResponse | 采纳 | 增加 `tenant:{id,name}` 与 `permission_summary`；权限使用 `AllowedAction` | completeness |
| P0-5 审批列表/详情 | 采纳 | 增加客户、总额、行数、快照客户、库存复核；按钮改为 OWNER 动作 | fixture schema + completeness |
| P0-6 H4 别名写入口 | 采纳 | `WorkingLineInput` 增加 `save_to_alias_cache/alias_scope`；fixture 展示 CUSTOMER 写入 | parity + fixture schema |
| P0-7 DO/仓库模型 | 采纳 | 独立 `DeliveryOrderLine` 与 `WarehouseDeliveryOrder`；明确 applied price 和角色裁剪 | completeness + fixture schema |
| P0-8 AI 状态 | 采纳 | 唯一 `AiState=OFFLINE/WARMING/READY/DEGRADED`，状态与唤醒共用 | completeness + parity |
| P0-9 用户认证 | 采纳 | `users.demo_token_hash NOT NULL UNIQUE`；禁止 seed 明文 token | migration parse/smoke |
| P0-10 信用标记 | 采纳 | 数据库/API 统一 `NONE/OVERDUE_NOTICE`；布尔值只作派生展示 | migration + parity |
| P0-11 span wire | 采用推荐 A 并兼容 | `span` 为字符串，偏移拆为 `span_start/span_end`；`source_span` 为 deprecated 字符串别名 | fixture schema + erratum E9 |
| P0-12 数据库/审计 | 全部采纳 | alias 撤销及 FAMILY/SKU、actor role、field diff 版本/原因、正价格、审批禁止 DELETE | PostgreSQL parse + PGlite 空库执行 |
| P0-13 可重现验证 | 采纳 | 固定 Python/Node 依赖；0 skip；H1/H5 行为、完整度、parity、DDL smoke、hash 一键校验 | `scripts/verify_gate0.py` |

## 同步采纳的安全 P1

- 保存数组默认 `[]`，写入时 `family_id` 可由 SKU 推导；价格原因统一为 `override_reason`。
- 租户显式记录 `timezone/currency`；入站消息记录 `source`。
- 审批详情增加 `stock_check`；活动与审计增加事件发生时的 `actor_role`。
- H5 的 `discount` 要求请求/问句语境，增加否定近邻；金额分配表达固定为 `UNKNOWN + UNALLOCATED`。

## 有意未执行的动作

- 未修改受保护的 `01`—`04` 和 v2.1 原件；这些文件只做哈希与关键术语 parity 校验。签字后在 P0-A 与后端实现并行升级到 v1.3。
- 未创建任何 `gate0-v*` 标签，未把任何姓名写成已批准；四方签字仍是进入业务代码前的门禁。
- 未写 FastAPI、规则引擎或业务仓储代码；本轮仅交付规格书、机器契约、DDL 和契约验证。

## Revision 2 复审追加处置

复审输入 SHA-256：`7A503BF02A168E63A636A3C933F13D06530C894147051B4FED64E51ED5809480`。

| 项目 | 裁决 | 落地 |
|---|---|---|
| `condition_id` 悬空 | 采用显式字段，不采用隐含复合键 | `CND_ + first24(SHA-256(draft_id|condition_kind|span_start|span_end))`；目标行不进入哈希，避免解决过程中 ID 改变 |
| CLERK 审批只读 | 采用推荐的本人过滤 | 列表服务端强制 `requested_by=current_user`；详情越权 404；`allowed_actions=[]`；decide 仍仅 OWNER |
| PII token 分叉 | 统一为详细 `[REDACTED_*]` | 新增 `pii-mask-tokens-v1.json`；fixture、文档与测试统一三种 token |
| bootstrap/CI | 先交付本地一键 bootstrap | `scripts/bootstrap_gate0.ps1` 安装 pinned Python/Node 依赖并调用统一 verifier |
| H5 UNIT 正向 | 增加第 12 行 | `kalau RM95 untuk 1 ctn → PRICE/UNIT/blocking`，由 oracle 实际执行；v2 扩到 16 行 |
| DO 客户名 | 采用快照字段 | `DeliveryOrder.customer_name` 必填；直接批准、自批和审计 fixture 同步 |

复审列出的其余 P2（提交人/操作者显示名、400/422 统一、clarification 存储说明等）不作为本次签字前阻断项，登记到 P0-A 待办，不在 Gate 0 临时扩张。

## Closeout（2026-10-21 21:14）

| 项目 | 裁决 | 落地 |
|---|---|---|
| P1-1 验证环境自包含 | 采纳 | `tests/contract/requirements.txt` 增加 `jsonschema-path==0.3.2`、`pathable==0.4.1`、`openapi-schema-validator==0.6.3`，防止干净安装解析到不兼容的 `0.5.0/0.6.0` |
| pnpm 缺失 | 采纳 | `bootstrap_gate0.ps1` 依次尝试 `GATE0_PNPM`、`pnpm`、`corepack pnpm`、`npx pnpm@11.25.0` |
| 离线/受限网络 | 采纳 | bootstrap 支持 `GATE0_WHEELHOUSE`，通过 `scripts/install_python_wheels.py` 从固定 wheels 安装，不依赖 pip 临时目录 |
| 干净目录验证 | 采纳 | 不带 `-SkipInstall` 从空目录执行 bootstrap：42 passed、PGlite 18 表/12 trigger 事件、72 hashes、0 skip |
| 证据 | 已更新 | `docs/gate0-validation.log`、`docs/gate0-validation-report.md`、`docs/gate0-hashes.txt` 记录本轮结果 |

## gate0-v2（2026-10-21 23:xx）：三岗回执处置

输入：AI 回执（A1—A8 + B1—B7）、前端回执（F01/F02/F03/F06—F10/F13—F17）、数据回执（1—4）。

| 项目 | 裁决 | 落地 |
|---|---|---|
| AI A1 复合数字词 | 采纳 | `contract_oracles._parse_quantity` 实现 ms `belas/puluh`、en `teen/tens`、zh `十X/X十Y`，最长匹配优先；新增 7 个 H1 required_cases |
| AI A2 小数静默截断 | 采纳 | `decimal_guard_pattern` + `INVALID_QUANTITY`；`1.5kg`/`0.5 ctn` 无 qty；新增 H1-DEC-1/2/NEG |
| AI A3 字符串强转绕过 | 采纳 | `MODEL_TYPE_COERCED` 后继续比对 qty；`"6"` vs 5 产生 `FIELD_NOT_EVIDENCED`；新增 H1-TYPE-NEG2 |
| AI A4 span 偏移 +1 | 采纳 | parse/save/approval fixture 的 line/issue offset 修正；parse `condition_id` = `CND_A4EEE3BE314D75567CF81BF8`；新增通用切片断言 |
| AI A5 H5 双真相 | 采纳 | H5 oracle 改为读取 `condition-triggers-v3.json` 的 pattern；补 `can less?`/`老价钱?`/`harga lama?`/`boleh diskaun?`；truth 16 行 |
| AI A6 / 数据 1 TEST 编号冲突 | 采纳（推荐 2） | Gate 0 H5 用例改名 `H5-CT-01—03`；冻结集 `TEST-01—32` 归数据岗；`condition-triggers.md` §7 和 `05` 变更记录同步 |
| AI A7 / 数据 2 签字范围 | 采纳 | `docs/gate0-signoff.md` 数据范围改为 `TEST-01—32`；外部签字页同步 |
| AI A8 qty 金额污染 | 采纳 | `qty_exclude_pattern` + `code_exclude_pattern`；`RM95 ... 3 ctn` → 3；新增 H1-AMT/AMT-NEG |
| 数据 3 uom 扩展 | 采纳 | `field-evidence.md` 明确 P0 loader 读租户 `uom_aliases`；`btl/can/papan/pkt/tin/box/roll/unit` canonical 映射；`db-schema.md` 同步 |
| 数据 4 dev 文件命名 | 采纳 | `tests/dev_41.json` 承载 DEV-01—41；`tests/frozen_eval_32.json` 仍为 32 条（P0-A 落地） |
| 前端 F01 候选/库存 | 采纳 | `WorkingLine.candidate_skus[]` + `SkuCandidate`（sku/规格/单位/等级价/库存） |
| 前端 F02 客户来源 | 采纳 | `GET /customers` + `CustomerListResponse`；CLERK/OWNER，WAREHOUSE 403 |
| 前端 F03 DO 关联/读取 | 采纳 | `OrderDraft/DraftSummary.do_number`；`GET /delivery-orders/{do_number}`；`GET /warehouse/delivery-orders/{do_number}`（P1 仓库绑定） |
| 前端 F06 UNKNOWN 单位价 | 采纳 | `parse_draft` 的 `requested_unit_price=null`；只有 UNIT 才填 |
| 前端 F07 span 偏移 | 采纳 | 同 A4；通用切片测试 |
| 前端 F08 reasons 类型 | 采纳 | `fields.md` 统一 `EscalationReason[]`；新增对象定义 |
| 前端 F09 缺货保存语义 | 采纳 | PUT lines 成功 200 + 版本 +1 + blocking Issue；approve 才 400；新增 `save_lines_insufficient_stock_200` |
| 前端 F10 STOCK 阻断 | 采纳 | STOCK `blocking=false`；缺货仅由行级 `INSUFFICIENT_STOCK` 阻断 |
| 前端 F13 approve_202 动作 | 采纳 | 响应针对调用者；CLERK 的 `allowed_actions=[]`；OWNER 读取时再给动作 |
| 前端 F14 价格冲突 | 采纳 | `confirmed_unit_price` 与目标行 `unit_price_override` 同时出现必须一致，否则 422；`confirmed_unit_price` 是消息级唯一来源 |
| 前端 F15 别名回读 | 采纳 | `WorkingLine.saved_alias` + `AliasRecord`；保存响应回读；未勾选不静默撤销 |
| 前端 F16 库存复核量 | 采纳 | `StockCheckSummary.lines[].effective_qty`；`STOCK_CHANGED.details.lines[].effective_qty` |
| 前端 F17 FieldDiff 路径 | 采纳 | `field_path` 相对 `line_id`（`unit_price_override`/`sku_id`），不用数组下标 |



## gate0-v3（2026-10-22 00:25）：二轮回执处置

| 项目 | 裁决 | 落地 |
|---|---|---|
| AI N1 uom 大小写 | 采纳 | `_parse_uom` 在 normalize 后匹配；新增 H1-UOM-UPPER/MIXED |
| AI N2 qty 偏移 | 采纳 | 金额/编码保长掩码；`parse_quantity` 返回 qty_start/qty_end；新增偏移断言 |
| AI N3 小数/金额顺序 | 采纳 | 先金额/编码掩码，再 decimal guard；新增 H1-AMT-DEC |
| AI N4 否定/语境第二真相 | 采纳 | H5 v3 增加 `negative_contexts`/`context_markers`，oracle 从词表读取 |
| AI N5 uom 私有表 | 采纳 | `_parse_uom` 只读 `field-evidence-v1.json` 的 aliases/extensions |
| AI N6 外部说明 | 采纳 | 改为 v2→v3、H5 16 行、pii lexicon |
| 前端 F01 当前行库存 | 采纳 | `WorkingLine.available_qty` 只读字段；fixture 同步 |
| 前端 F07 审批快照 span | 采纳 | `approval_detail` span_end=12；切片测试覆盖 nested `masked_customer_text` |
| 前端 F09 缺货 fixture | 采纳 | Issue 绑定 LIN_001、span 0:12、clarification_draft 非空、COPY_CLARIFICATION 可用 |
| 数据依赖冲突 | 采纳 | `referencing==0.31.1` + `jsonschema-path==0.3.2`；干净安装可解析 |
| 数据 manifest 路径 | 采纳（自包含） | 全部外部输入放 `external-inputs/`，manifest path 相对；测试 `ROOT / path` |
| baseline 文件名 | 采纳 | 原文件重命名 v2.1；manifest baseline.path 指向 v2.1，内容哈希不变 |

## gate0-v4（2026-10-22 01:15）：三轮回执处置

| 项目 | 裁决 | 落地 |
|---|---|---|
| AI N7 多候选静默取最早 | 采纳 | `AMBIGUOUS_QUANTITY` + `parse_quantity` 多候选阻断；新增 H1-AMB-1 |
| AI N8 pack_size 被当 qty | 采纳 | `field-evidence-v2` 加 `pack_size.patterns`/`parse_pack_size`；新增 H1-PACK-1—4 |
| AI N9 逗号小数误伤 | 采纳 | 逗号只在后接单位时视为小数；新增 H1-DEC-COMMA-NEG |
| AI A1 uom 复数 | 采纳 | `cans/tins/boxes/rolls/btls/pkts` 等进入 tenant extensions；新增 H1-UOM-PLURAL |
| AI A2 词表版本 | 采纳 | `field-evidence-v1` → `field-evidence-v2`，fixtures normalizer 同步 |
| AI A3 路由说明 | 采纳 | 最终说明补 `pii-mask-tokens-v1.json` |
| AI A4 坐标系 | 采纳 | oracle docstring 明确 normalized-span；Adapter 负责映射回 masked code point |
| AI A5 test-data-map 标题 | 采纳 | 改为 gate0-v4，并注明冻结集不随包分发 |
| AI A6 根目录旧 v2 文件 | 采纳 | v3 签字页/说明归档，根目录只留 v4 当前文件 |
| 前端 clarification 语言 | 采纳 | `parse_draft` ms 模板正文改马来语 |
| 前端候选示例 | 采纳 | 已确定行 `candidate_skus=[]`；新增 `parse_draft_ambiguous.json` 展示未解析候选 |
| 数据 parity ROOT | 采纳 | `test_v21_parity.py` 第 46 行改为 `ROOT / path` |
| 数据版本命名 | 采纳 | 统一 `gate0-v4` / draft revision 5；包名/说明/签字页/tag 一致 |
| 数据旧数字/依赖 | 采纳 | 说明 73 哈希；validation report 改 referencing 0.31.1 |
