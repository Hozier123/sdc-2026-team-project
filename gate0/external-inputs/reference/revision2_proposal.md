# KiraOrder v1.2 评审复核与 v1.3 拟议解决方案（待批准）

> **文件性质**：独立复核与拟议修订执行方案，不是已生效契约。
>
> **修订版本**：Revision 2（已吸收《KiraOrder v1.3 拟议方案评审与批准建议》）
>
> **当前状态**：`GATE_0_READY / FULL_EXECUTION_NOT_YET_APPROVED`
>
> **重要边界**：本文件没有修改 `01`—`04` 四份规则文件，也没有修改 v2.1 基线。只有在 He Minghao 明确批准后，才能据此实施修订。
>
> **后端负责人**：He Minghao。人员分工以用户最新直接指令为准；v2.1 §12 和评审报告中把后端写给 Xiong 的内容视为过期分工信息，不据此派工。

## 0. 本次复核使用的材料与优先级

### 0.1 已核验材料

| 材料 | 用途 | SHA-256 |
|---|---|---|
| `KiraOrder_终版执行方案_v2_2026-10-21.md` | 用户指定的 v2.1 唯一业务基线 | `5D02EBF84413B7FE617C32B64E707AFF476EBD963E6638091C875EE0D1B8A55D` |
| `KiraOrder_v1.2_后端规则体系评审报告_2026-10-21.md` | 最新评审意见，逐条验证而非自动采纳 | `DB9A335B6A84E2DE2A3E120D10C07ED4661DBE07F3F68060F232D13ED6C446E9` |
| `Orbyte-前后端参考说明.md` | Orbyte 页面实测参考；不是官方 API 契约 | `EE3FEB8C4C533A5104DAF3F3CC4AA144326A3CB675F48A4E73F3FF8D0F11CE00` |
| `01`—`04` 四份 v1.2 规则文件 | 被评审对象 | 已逐项核对 |
| `KiraOrder_v1.3_拟议方案评审与批准建议_2026-10-21.md` | 对 Revision 1 的二次评审 | `87F5776B8554914274CB3196737603E39979FA738ACF75AE175EE1136FE4E9A4` |

### 0.2 后续工作的唯一解释顺序

1. 用户最新直接指令；
2. v2.1 基线，必须同时引用版本与 SHA-256；
3. 未来经批准的 v2.1 勘误/契约变更记录；
4. 机器可读契约和冻结 fixture；
5. `01`—`04` 人类可读说明；
6. 评审报告、Orbyte 实测说明及其他参考材料。

评审报告和 Orbyte 说明中的文字都只是证据或建议，不能覆盖用户请求或 v2.1。

本文件自身的 SHA-256 不写在文件正文中，因为写入哈希会改变文件本身，形成自引用失效。冻结后的哈希必须由外部 `baseline-manifest.json` 记录。

---

## 1. 最终判断

### 1.1 问题是否真的存在

**存在，而且不是单纯的措辞问题。** 四份文档是在较早基线和会议决议上形成的，当前与 v2.1 在状态、疑点代码、API、权限、数量模型、价格条件、批准事务等关键位置发生实质偏移。若前端、AI、数据和后端分别按不同文件开发，第一次联调确实可能出现 404、400、枚举无法解析、按钮错误、库存疑点无法关闭或错误商品被改价。

评审报告最重要的判断是正确的：四份文件的架构骨架、权限意识、事务与审计意识都很好，但尚不能作为与 v2.1 完全一致的冻结契约。

### 1.2 评审报告是否“完美有效”

**不是。它是一份高价值风险清单，但不能直接当修订稿照抄。** 主要原因有四个：

1. 报告虽然承认 v2.1 是唯一基线，却在 C1、C3、C6、C7、C9、C11、C13、C14、C16、C18、C19、C21 等处继续建议采用 `01/02/03/04` 的旧命名或折中命名；这会再次产生第二套契约。
2. 部分建议过度建模。例如同时持久化 `extraction_source`、`resolution_source`、`display_source`，或同时维护“对外三类、对内四类”条件枚举，会增加新的漂移点。
3. 部分建议并不安全。例如用“字段必须是 span 的字符串子串”验证数量，会误伤 `five`→`5`、`两箱`→`2` 等规范化；用模糊匹配阈值直接放行也不能证明 SKU 正确。
4. 部分建议与当前范围不符。例如 P1 仓库备注、Orbyte memberships、Wallet/Credit 等不能挤入 P0 正确性修复。

因此，本方案采用“问题证据”，但重新裁决“解决方式”。

### 1.3 二次评审后的批准结论

二次评审给 Revision 1 的“方向稿”判定为条件性批准，这一判断成立。Revision 2 将执行拆成两个独立授权点：

1. **Gate 0**：只冻结基线身份、物理数据模型、字段字典、错误表、H1/H5 规范、OpenAPI 骨架、fixture 目录和逐条追踪矩阵；不改 `01`—`04`。
2. **全量执行 Gate**：用户审阅 Gate 0 产物后，才修改 v2.1 勘误、`01`—`04`、机器契约和测试。

Revision 2 不采用“为赶时间把 OWNER 创建/编辑、审计或回复草稿静默降为 P1”的建议。用户已指定 v2.1 为唯一基线，因此默认完整实现 v2.1：OWNER 具备 v2.1 权限，审计和批准后回复仍是 P0。任何范围收缩都必须由用户另行明确批准并写入变更记录。

### 1.4 我的责任与自我反思

这些问题确实有一部分来自我先前生成四份文件时的工作方法不足：

1. **没有先锁定基线哈希。** 文件名仍是 v2，而内容后来变为 v2.1；我只按标题/会议材料工作，没有把行数与 SHA-256 作为输入前置条件。
2. **错误地让会议术语形成了第二套契约。** `NEEDS_REVIEW`、`APPROVED`、`ask_target`、`draft_version`、`/drafts/...` 等命名在局部上更顺手，但不应凌驾于已确认的唯一基线。
3. **缺少逐条需求追踪矩阵。** 没有先建立“v2.1 条款 → 01 → 02 → 03 → 04 → fixture → 测试”的映射，导致同一概念在四处重复手写。
4. **重视了批准事务的原子性，却低估了编辑后的派生状态重算。** 这直接造成 `effective_qty`、库存疑点重开/关闭、价格条件目标行等缺口。
5. **没有先做反例攻击。** 如果先用“真实 span + 错误字段”“错行降价”“减量后再加量”“去问客户但客户没确认”等场景压测，H1—H4 应当在冻结前被发现。
6. **把 FROZEN 当成了内容正确性的证明。** 冻结只能限制变化，不能替代哈希、OpenAPI、fixture 和契约测试。
7. **对外部参考的边界没有单独建层。** Orbyte 页面术语适合做适配层参考，但不应直接重命名领域模型或假装已取得正式 API。

解决这些根因比逐句修文档更重要，否则下一版还会出现同样的漂移。

---

## 2. C1—C21 硬冲突复核

> “真实”表示四份文档确实与 v2.1 不一致；不表示评审报告给出的修法一定正确。

| 编号 | 是否真实 | 最终裁决 | 对评审建议的评价 |
|---|---|---|---|
| C1 状态集 | 是 | 公共状态严格采用 v2.1：`DISAMBIGUATION_REQUIRED / READY_FOR_APPROVAL / PENDING_OWNER_APPROVAL / DO_GENERATED / REJECTED`。不得公开 `DRAFT / NEEDS_REVIEW / APPROVED / CANCELLED`。解析过程中的瞬态不进入 API；`REJECTED` 另配 `termination_reason` 区分老板驳回与跟单员作废。 | 报告建议保留 `01` 状态集，不符合唯一基线，不采用。 |
| C2 疑点代码 | 是 | 采用 v2.1 的 8 个 `IssueCode`。`INVALID_QUANTITY`、`SOURCE_EVIDENCE_INVALID` 作为校验原因或 `LOW_CONFIDENCE_MATCH.reason_code`，不再成为第二套公共疑点码。 | “二选一”已没有必要；基线已替团队选定。未上线时不要引入 `legacy_code`。 |
| C3 条件类型 | 是 | AI、领域、API、数据统一使用 v2.1 四类：`STOCK / PRICE / TIME / OTHER`。`STOCK_IF_AVAILABLE` 等只可作为词表规则名或 UI 文案。 | “对外三类、对内四类”会制造映射负担，不采用。 |
| C4 升级原因 | 是 | 采用 `PRICE_OVERRIDE_BELOW_TIER / AMOUNT_OVER_THRESHOLD / CUSTOMER_CREDIT_FLAG`。 | 建议正确，采用。 |
| C5 来源字段 | 是 | 行级只持久化一个当前 SKU 解析来源 `match_source`；原始来源保存在不可变 `ai_initial_snapshot`。人工只改数量时不改 `match_source`，人工重新选 SKU 时变为 `MANUAL_SELECTED`。UI 徽章直接由后端返回该字段，不再增加 `display_source/extraction_source`。`ai_mode` 增加 `MIXED`。 | 识别了真实问题，但“三个持久化字段”过重，只部分采用。 |
| C6 路由字段 | 是 | 统一为 v2.1 的 `ask`。 | 报告偏好 `ask_target` 不符合唯一基线，不采用。 |
| C7 版本字段 | 是 | 对已有版本化资源进行修改的请求使用 `expected_version`：PUT lines、approve、discard；parse、wake 不需要。`decide` 复核审批记录绑定的 `draft_version`，客户端不重复提交草稿明细。响应返回当前 `version`。 | 报告偏好 `draft_version` 不采用。审批快照内部仍叫 `draft_version`。 |
| C8 数量模型 | 是 | 服务端保存只读 `requested_qty`，客户端可提交 `confirmed_qty`，服务端派生 `effective_qty`。改价采用 `unit_price_override / override_reason / save_to_alias_cache`。 | 方向正确，采用；`effective_qty` 永远不可由客户端提交。 |
| C9 解析路径 | 是 | 采用 `POST /api/v1/orders/parse-draft`。 | 报告建议改成 `/drafts/parse` 不采用。 |
| C10 保存路径 | 是 | 采用 `PUT /api/v1/orders/drafts/{draft_id}/lines`，一次保存完整 lines、显式 `deleted_line_ids` 与 resolutions；每个现有 line_id 必须出现在 lines 或 deleted_line_ids 中且只能出现一次，禁止靠省略隐式删除。删除逐疑点公共写接口。 | 批量保存正确，但路径必须保留 v2.1 的 `/orders`。 |
| C11 批准路径 | 是 | 采用 `POST /api/v1/orders/{draft_id}/approve` + `expected_version`。 | 报告采用旧路径/字段的建议不采用。 |
| C12 老板决定 | 是 | 采用单一 `POST /api/v1/approvals/{approval_id}/decide`。 | 建议正确，采用。 |
| C13 响应格式 | 是 | 错误采用 v2.1 的扁平 `{error_code,message,details}`；成功按端点直接返回 OpenAPI 中固定的模型。所有响应声明 `X-Request-ID` 头；正文不再嵌套 `{data}` 或 `{error}`。 | 报告建议嵌套 `{data}`/`{error}` 不采用。 |
| C14 审计接口 | 是 | 采用 `GET /api/v1/orders/{do_number}/audit-detail`。 | 补审计正确，但报告建议的新路径不采用。 |
| C15 回复草稿 | 是 | 按 v2.1，批准后模板包含 DO 号、明细和总额，并明确 `Draft — not sent`，不得自动发送。 | 报告给了两个选项；基线已经裁决为“含总额”。 |
| C16 澄清结构 | 是 | 使用单一合并的 `clarification_draft` 与 `clarification_lang`；可在对象内带 `issue_ids/not_sent`，但不再同时暴露一套平行数组。 | “单数 + 数组”会产生同步问题，不采用。 |
| C17 DO 字段 | 是 | 补齐 v2.1 字段；同时修复 v2.1 自身 SQL 漏掉 `escalation_reasons` 的问题。DO 行必须同时保存 `tier_unit_price` 与 `applied_unit_price`。 | 方向正确，采用并加强。 |
| C18 AI 数量类型 | 是 | 模型 wire 契约使用 JSON 整数。为抵抗模型偶发输出，Adapter 可把仅含 ASCII 数字且满足正整数规则的字符串一次性规范化为 int，并记录兼容诊断；其他字符串单行 fallback。数据文件仍可使用十进制字符串，导入边界转整数。 | 报告建议把正式 wire 类型改字符串，违反 v2.1，不采用；仅保留边界兼容。 |
| C19 未知商品族 | 是 | 严格使用字符串 `"UNKNOWN"`。旧 `null` 只可在一次性迁移适配器中读取，不进入新契约。 | 报告建议改 `null` 不采用。 |
| C20 混合 AI 模式 | 是，且 v2.1 本身也有缺口 | 为 `AiMode` 增加 `MIXED`；只有所有行规则解释时才是 `ALIAS_ONLY`，所有未命中行均走同一路径时才是 `LLM` 或 `FALLBACK`。 | 建议正确，属于必要勘误。 |
| C21 信用标记 | 是 | 数据模型采用 `credit_flag: NONE / OVERDUE_NOTICE`，升级原因采用 `CUSTOMER_CREDIT_FLAG`。若 UI 需要布尔值，只能由后端派生，不作为第二真相。 | 报告建议把主字段改为布尔值，不符合 v2.1，不采用。 |

结论：C1—C21 全部是真实“偏移”，但评审报告的修法只有一部分可直接采用。现在不再做“偏好选择”，先恢复 v2.1 一致性。

---

## 3. H1—H16 规则漏洞复核

| 编号 | 判断 | 拟议解决方案 | 对评审建议的评价 |
|---|---|---|---|
| H1 字段没有绑定原文 | 真实，Critical | Adapter 先从已定位 `span` 通过版本化、非模糊的解析器生成字段候选，再验证模型的 `qty/uom/size/grade/fam` 是否与候选完全等价。支持明确列入词表的中文/英文/马来数字词和单位别名；无证据字段不得进入 Resolver，转 `LOW_CONFIDENCE_MATCH(reason_code=...)` 或单行 fallback。 | 方向正确，但“必须是字符串子串”过严；改为可执行的确定性证据规范。 |
| H2 价格条件没有目标行 | 真实，Critical；v2.1 已规定 | `condition_scope/candidate_line_ids/target_line_ids` 必须进入数据、API、保存事务和批准复核。非目标行降价不能满足当前条件，但可作为独立改价按自身规则审计。 | 基本正确，采用 v2.1 原规则。 |
| H3 数量状态无法重算 | 真实，Critical；v2.1 已规定 | 每次 PUT 与 approve 都用 `effective_qty` 重建/对账库存类疑点。库存疑点稳定派生键固定为 `(draft_id, line_id, issue_code, condition_id|null)`；历史变化写入版本快照和活动，不依赖旧 `resolved` 布尔值放行。 | 正确，采用并补充历史策略。 |
| H4 三个危险动作 | 真实，Critical | 不为其增加复杂守卫，直接从公共 `ResolutionChoice` 删除 `MARK_UNRESOLVED / ASK_CUSTOMER_AT_TIER_PRICE / USE_FALLBACK_RESULT`。使用 v2.1 的人工选 SKU、`CONFIRMED_WITH_CUSTOMER`、`NOT_A_CONDITION`、删除行。 | 报告仍想保留部分旧动作；删除更简单、更安全、也更符合基线。 |
| H5 条件误报与漏报 | 真实，Critical；v2.1 自身也矛盾 | 裸 `RM95` 只作为价格证据，不单独触发。PRICE 触发应为议价短语，或“金额 + 条件/询价语气”。补 `available` 等多语词；同一片段允许 STOCK 与 PRICE 多标签；误报用 `NOT_A_CONDITION + note`。 | 方向正确，但需加入历史陈述/询价上下文，不只是删一个正则。 |
| H6 有货条件双重阻塞 | 真实，High | `CUSTOMER_CONDITION(STOCK)` 是 `blocking=false` 的派生审计记录；只有 `INSUFFICIENT_STOCK` 阻塞。满足与不满足均保存 `auto_resolved_by` 和 `data_used`。 | 正确，v2.1 已裁决。 |
| H7 库存为零无法闭环 | 真实，High | 增加删除行操作；删除到零行返回 `EMPTY_ORDER`。不允许用数量 0 绕过正整数规则。 | 正确，采用。 |
| H8 高于等级价未定义 | 四份文档中真实；v2.1 已部分裁决 | P0 允许高于等级价，但 `override_reason` 必填并写活动；它本身不触发老板升级，除非总额或信用规则触发。把配置名明确为只控制低于等级价的升级，避免 `price_override_requires_owner` 歧义。 | 报告要求再次二选一已无必要。 |
| H9 别名污染 | 真实，High | v2.1 已有 `phrase_norm` 唯一索引；四份文档必须同步。另要求别名来自当前脱敏 span，不能只含数量/单位/停用词，保存时显示目标 SKU 和作用域。不要用固定“长度 ≥ 3”代替语义校验。 | 大方向正确；固定字符长度并不足够。 |
| H10 证据失败死锁 | 真实，High | 删除 `SOURCE_EVIDENCE_INVALID` 公共码；归入 `LOW_CONFIDENCE_MATCH`，提供人工选择 SKU 或删除行。技术失败不得靠“标记未解决但视为解决”闭环。 | 报告识别正确，基线化处理更干净。 |
| H11 重复/重叠 span | 真实，High | 完全相同区间去重并记录诊断；不同但重叠的区间不得静默合并或生成两条确定行，应把完整强边界片段重新 fallback 或转 `LOW_CONFIDENCE_MATCH`。 | 不新增 `DUPLICATE_SPAN` 公共 IssueCode，使用诊断 reason。 |
| H12 库存变化错误码 | 真实，High | 保存时已知缺货用业务校验；事务加锁后才发现库存变化用 409 `STOCK_CHANGED`。老板审批保持 PENDING。 | 正确，采用 v2.1。 |
| H13 重复批准无法恢复 | 真实，High | 409 `ALREADY_APPROVED.details` 必须返回 `do_number/approved_at`，前端按幂等成功打开已有 DO。 | 正确，采用。 |
| H14 快照可变 | 真实，High | 每个草稿版本使用不可变行快照；审批请求保存 lines、totals、reasons 和客户原话快照。后续版本不得修改已提交审批看到的内容。 | 正确，必须补。 |
| H15 单价/总价不明确 | 真实，High；评审低估了风险 | 增加 `price_basis: UNIT / TOTAL / UNKNOWN`。P0 只执行 UNIT。TOTAL/UNKNOWN 保持阻断并生成澄清；客户确认单位价后，跟单员填写 `confirmed_unit_price`、将 basis 确认为 UNIT 并写 note，之后才能走正常改价/升级。无法取得单位价时转人工，不生成 DO。 | “裸金额默认单价”仍可能严重错价，不足够安全；本方案补上可闭环路径。 |
| H16 OWNER_SELF_APPROVED 不可达 | 相对四份文档真实，但不是 v2.1 缺陷 | 完整回归 v2.1 权限：OWNER 可解析、编辑、批准常规单；OWNER 自己提交且仅命中升级规则时直接生成 DO 并记录 `OWNER_SELF_APPROVED`。该能力保留在 P0，不以工期为由静默降级。 | 二次评审提出的“P0 只批/驳”只有用户明确批准范围收缩后才能采用；当前不采用。 |

---

## 4. M1—M12 中等级问题复核

| 编号 | 判断与最终处理 |
|---|---|
| M1 非法数量双重语义 | 真实。模型行非法时单行 fallback/`LOW_CONFIDENCE_MATCH`；客户端 PUT 非法时 400 校验错误。不要恢复公共 `INVALID_QUANTITY` IssueCode。 |
| M2 缺等级价 | 真实，但报告建议做成可解决疑点不合适。导入和启动时必须完整校验价格矩阵；运行时仍缺失则返回配置故障并禁止生成草稿/DO，记录安全的配置诊断。用户无法在疑点卡片里修复后台配置。 |
| M3 `confirmed_items` 兼容 | 真实风险，但 v2.1 明确保留。实现必须把“保存新版本 + 批准新版本”放入同一事务，要求 `expected_version`，响应返回实际版本；标记 deprecated，前端迁移到 PUT 后再移除。不能静默批准未保存明细。 |
| M4 同日订单边界 | 真实，P1。无历史时只允许新单；多个历史单必须选 `related_do_number`；选择补单时必填。 |
| M5 `business_date` | 真实，P1。按租户时区生成并持久化业务日期，不能依赖服务器本地时间；重置和测试显式传入。 |
| M6 数量上限 | 真实。`MAX_LINES=12` 与 v2.1 一致；`MAX_QTY_PER_LINE` 应为租户配置或明确默认值，不能未经数据分析永久写死 100,000。 |
| M7 演示令牌 | 风险真实，但 `DEMO_` 前缀不是安全措施。数据库只存哈希，原始令牌由部署 Secrets/受控演示登录提供，配合 DEMO_MODE、限流、可撤销和纯合成数据。 |
| M8 parse 限流 | 真实；v2.1 已要求。四份文档补齐按令牌/租户限流与 429 处理。 |
| M9 活动事件 | 部分真实。采用 v2.1 事件集，并补 `CONDITION_DISMISSED`、`STOCK_CHANGED` 等真正影响审计的事件。`OWNER_SELF_APPROVED` 必须保留。 |
| M10 模板 payload | 真实。后端返回 `{template_id, lang, text, placeholders, issue_ids, not_sent}` 或等价单一对象；前端只展示/复制，不重算价格或模板。字段名需在 OpenAPI 固定。 |
| M11 审批详情 | 真实。新增只读 `GET /api/v1/approvals/{approval_id}` 是合理的 v1.3 增量，返回不可变快照、差异、升级原因与提交信息。 |
| M12 `picking_note` | 不是 P0 阻断，且 v2.1 未要求。要么从 02 示例移除，要么在 P1 仓库视图确定需求后正式加入；现在不应顺手扩范围。 |

---

## 5. 评审报告遗漏或判断不足的事项

1. **人员分工已经过期。** v2.1 §12 和评审 §8.2 把后端写给 Xiong、把 He 写给数据；用户最新直接指令和 Orbyte 参考文件都明确 He Minghao 负责后端。技术基线可继续使用，但人员表必须单独更正。
2. **v2.1 的 SQL 与模型自身不完全一致。** 文本要求 `DeliveryOrder.escalation_reasons`，SQL `delivery_orders` 表却漏了该列；修订时必须补齐。
3. **v2.1 的 H1 保护仍不完整。** 它只校验 `span`、闭集 fam 和正整数 qty，没有证明各字段来自 span。
4. **v2.1 的 PRICE 触发规则与负例矛盾。** `RM\d+` 单独触发会误报 `Last order was RM95.`。
5. **v2.1 的 `AiMode` 无法表达逐行混合路径。** 既允许单行 fallback，又没有 `MIXED`。
6. **v2.1 没有定义金额的 UNIT/TOTAL 口径。** 这是比命名冲突更危险的业务风险。
7. **`price_override_requires_owner` 命名与规则不完全一致。** 规则只规定低于等级价升级，高于等级价只要求理由；配置语义需要收紧。
8. **审批快照的不可变性没有数据库级保证。** 仅保存 `draft_version` 不足以防止实现原地修改旧行。
9. **成功响应未完全统一。** 既然错误体已固定为扁平格式，成功体也应在 OpenAPI 逐端点固定，不能由各文档自行包裹。
10. **文件名仍写 v2。** 即使内容是 v2.1，后续人和脚本仍可能选错。不要覆盖旧文件；应在批准后复制为明确的 v2.1 文件名，并用 manifest 记录哈希。

### 5.1 二次评审补充的 C22—C39

| 编号 | 裁决 | Revision 2 落点 |
|---|---|---|
| C22 物理表/结构 | 真实，P0 | §7.7 已选择 v2.1 表名与聚合 JSONB 模型 |
| C23 终止原因 | 真实，P0 | §7.8 `termination_*` |
| C24 低置信原因 | 真实，P0 | §7.8 `Issue.reason_code` |
| C25 显式删除 | 真实，P0 | §7.8/§7.9 `deleted_line_ids` |
| C26 来源语义 | 真实，P0 | 只持久化 `match_source`，初始来源在快照 |
| C27 两套动作 | 真实，P0 | 整体删除 `IssueResolutionAction` |
| C28 成功体/请求 ID | 真实，P0 | §7.10 固定直接成功体与响应头 |
| C29 错误表 | 真实，P0 | §7.10.1 |
| C30 ignored 字段 | 真实，P1 | raw `ignored` → Adapter `ignored_spans` |
| C31 disambiguations | 真实，P1 | 只读 deprecated 派生字段 |
| C32 电话字段 | 真实，P1 | 统一 `phone_e164`，seed 保证合成号码 |
| C33 阈值字段 | 真实，P1 | 统一 `amount_threshold_rm` |
| C34 租户规则开关 | 真实，P1 | `checks_enabled` 与两项升级开关进入 schema/seed |
| C35 TOTAL 价格路径 | 真实，P1 | §3 H15 与 §7.8：询问单位价后闭环，否则转人工 |
| C36 TEST-01—24 | 真实，P1 | 由原始方案 B 补录，禁止反推答案 |
| C37 文件名/manifest | 真实，P1 | Gate 0 manifest；批准后复制明确 v2.1 名称 |
| C38 人员分工 | 已由用户裁决 | He Minghao 为后端负责人 |
| C39 审计/回复优先级 | 二次评审指出得对 | 保持 v2.1 P0，不降级 |

---

## 6. Orbyte 参考说明的采纳判断

### 6.1 建议采纳

| 参考内容 | 采纳方式 |
|---|---|
| 对外术语使用 Organization | UI/适配层可显示 `organization`，内部继续使用安全边界明确的 `tenant_id`；建立一处映射，禁止全局改名。 |
| 访问角色、项目分工、Approver/Reviewer 是不同概念 | KiraOrder 的 `Role` 只表示访问角色；团队成员的 Backend/Frontend 不进入权限枚举；审批人关系不与项目分工混用。 |
| Submit/Review/Approve 与业务状态分开 | 待办对象保存 `action_type`、业务对象引用、状态和 `allowed_actions`；动作是否合法仍由服务端判断。 |
| 角色、权限、菜单由不同页面请求支持 | 坚持后端鉴权和显式权限响应；前端菜单不是安全边界。 |
| Wallet/Credit 未验证 | 所有材料明确写 Mock/Demo；不得声称已接官方余额、扣费、退款或账本。 |
| 当前只是独立原型/模拟集成 | README、隐私页与演示口径使用 “Orbyte ecosystem demo / integration prototype”。 |

### 6.2 暂不采纳为实际契约

| 内容 | 原因 |
|---|---|
| 直接把所有 `tenant_id` 改为 `organization_id` | 会改动隔离主键并扩大风险；官方字段契约尚未获得。 |
| 新建完整 membership/多 Approver/多 Reviewer 模型 | 当前 P0 不需要，也未确认官方业务规则。 |
| 调用实测网页的 `/api/...` 请求 | 这些是浏览器内部请求，不是获授权、稳定的公开 OpenAPI。 |
| Wallet/Credit 账本和扣费 | 能力未在当前账号可见，也没有正式字段、幂等和退款契约。 |
| 因网页导航名创建 `workspace_id` 租户层级 | 证据不足，且会引入错误领域概念。 |

### 6.3 对后续实际文件的影响

如果用户批准修订：

- `01` 增加一个“Orbyte 适配边界”小节，只说明 `tenant ↔ organization` 映射、服务端权限和未接 Wallet/Credit；
- `02` 可使用 Organization 文案，但接口字段仍按后端 OpenAPI；
- `03/04` 不因 Orbyte 页面参考改变 AI Schema 或种子主键；
- README/演示材料加入“独立原型与模拟集成”声明；
- 不把网页内部请求复制成 KiraOrder API。

---

## 7. 拟冻结的 v1.3 核心契约

### 7.1 公共枚举

```text
Role = CLERK | OWNER | WAREHOUSE

DraftStatus =
  DISAMBIGUATION_REQUIRED |
  READY_FOR_APPROVAL |
  PENDING_OWNER_APPROVAL |
  DO_GENERATED |
  REJECTED

IssueCode =
  MULTIPLE_PACK_SIZES |
  MULTIPLE_GRADES |
  MISSING_UOM |
  LOW_CONFIDENCE_MATCH |
  INSUFFICIENT_STOCK |
  CUSTOMER_CONDITION |
  SAME_DAY_ORDER |
  UNUSUAL_QTY

ConditionKind = STOCK | PRICE | TIME | OTHER
ConditionScope = SINGLE_LINE | MULTI_LINE | ORDER_LEVEL | UNKNOWN
AskWho = CUSTOMER | OWNER | CLERK | SYSTEM

ResolutionChoice =
  CONFIRMED_WITH_CUSTOMER |
  ACCEPT_REQUESTED_PRICE |
  NOT_A_CONDITION |
  SEPARATE_ADD_ON |
  DUPLICATE |
  CHANGE_EXISTING

EscalationCode =
  PRICE_OVERRIDE_BELOW_TIER |
  AMOUNT_OVER_THRESHOLD |
  CUSTOMER_CREDIT_FLAG

AiMode = LLM | FALLBACK | ALIAS_ONLY | MIXED
```

除 `MIXED` 为必要勘误外，其余均直接服从 v2.1。

### 7.2 P0 API

| 方法与路径 | 作用 |
|---|---|
| `POST /api/v1/orders/parse-draft` | 解析并创建草稿 |
| `GET /api/v1/orders/drafts` | 草稿列表 |
| `GET /api/v1/orders/drafts/{draft_id}` | 草稿详情 |
| `PUT /api/v1/orders/drafts/{draft_id}/lines` | 原子保存行与疑点处理 |
| `POST /api/v1/orders/{draft_id}/approve` | 按当前已保存版本批准/升级 |
| `GET /api/v1/approvals` | 老板待办 |
| `GET /api/v1/approvals/{approval_id}` | v1.3 增量：审批详情 |
| `POST /api/v1/approvals/{approval_id}/decide` | 老板批准/驳回 |
| `GET /api/v1/orders/{do_number}/audit-detail` | DO 差异审计 |
| `GET /api/v1/activity` | 活动时间线 |
| `GET /api/v1/me` | 身份、租户、角色、权限 |
| `GET /api/v1/ai/status` | AI 状态 |
| `POST /api/v1/ai/wake` | 唤醒 AI |

对现有版本化草稿进行修改的请求（PUT lines、approve、discard）使用 `expected_version`；parse、wake 不使用。老板 decide 复核审批请求已绑定的 `draft_version` 和当前草稿版本。角色和租户只从 Bearer token 会话取得。

### 7.3 数量与库存不变量

```text
requested_qty = 初始解析得到的正整数，只读
confirmed_qty = 人工确认的正整数，可空
effective_qty = confirmed_qty ?? requested_qty，只读派生
```

- PUT 后按当前 working lines 对账库存疑点；
- approve 在库存锁内重新计算；
- 旧的 `SATISFIED/resolved` 结果没有放行权；
- 删除商品行必须显式发生，不能把数量设 0；
- 空订单拒绝。

### 7.4 价格条件不变量

1. PRICE 条件必须保留脱敏原话；
2. 多商品且无法唯一关联时 `condition_scope=UNKNOWN`；
3. 接受价格前必须确认 `target_line_ids` 和 `price_basis`；
4. `requested_unit_price` 只能由确定性规则从原文提取，不自动应用；
5. 每个目标行必须存在有效成交价和改价原因；
6. 非目标行改价不能满足该条件；
7. 低于等级价触发老板；高于等级价要求理由与审计；
8. TOTAL 价格 P0 不自动执行。

### 7.5 AI 字段证据不变量

```text
先定位 span
→ 从 span 生成确定性字段候选
→ 校验模型字段与候选语义等价
→ 校验 fam 有家族名/别名证据
→ 只有通过的字段进入 Resolver
→ 失败只降级当前行
```

不得因为 fam 在闭集、qty 是正整数，就认为它们来自原文。

### 7.6 批准事务必须补回的复核

除四份文档已有的锁、版本、疑点与库存流程外，必须显式补回：

1. 所有订单行均有非空 SKU；
2. SKU 属于当前租户；
3. PRICE 条件存在仍有效的目标行；
4. 接受客户价格的每个目标行均已有效改价并有原因；
5. `effective_qty` 重新计算并不超过锁定库存；
6. 审批版本及不可变快照与当前待批对象一致。

### 7.7 物理数据模型裁决

Revision 2 明确采用 **v2.1 表名 + 聚合 JSONB 快照**，不再同时建设 `orders`/`drafts`、`products`/`skus` 两套物理表。原因是当前数据库按 v2.1 设计为空库迁移并重建 seed，且每张草稿最多 12 行，聚合保存和不可变快照比双重行表更简单、更符合 P0 时间盒。

#### 7.7.1 P0 物理表

| 表 | 作用 | 关键裁决 |
|---|---|---|
| `tenants` | 租户规则和阈值 | 使用 `amount_threshold_rm`、`checks_enabled`、`below_tier_price_override_requires_owner`、`credit_flag_requires_owner`；不另建 `owner_approval_threshold` |
| `users` | 身份与访问角色 | `CLERK/OWNER/WAREHOUSE`；项目分工不进入该枚举 |
| `customers` | 客户主档 | 使用 `phone_e164` 与 `credit_flag`；演示 seed 保证电话为合成号段 |
| `product_families` | AI 闭集商品族 | 保存族 ID、名称和版本；族别名可独立表维护 |
| `family_aliases` | 商品族多语别名 | 同租户 `phrase_norm` 不得跨族重复 |
| `products` | SKU 真相表 | 等价于旧文档的 `skus`；含 `family_id/pack_size/grade/base_unit` |
| `uom_aliases` | 单位别名 | canonical unit + 精确别名；P0 不做隐式数量换算 |
| `customer_tier_prices` | SKU × Tier 等级价 | 金额 `NUMERIC(12,2)`；seed 导入时验证矩阵完整 |
| `inventory` | 当前可用库存 | `(tenant_id, product_id)` 唯一；批准事务固定顺序加锁 |
| `alias_cache` | 客户/租户别名 | 使用 `phrase_norm` 唯一索引；等价于旧 `customer_aliases` |
| `inbound_messages` | 脱敏入站消息 | 只保存 masked text；绝不保存未掩码原文 |
| `orders` | 草稿聚合根 | 等价于旧 `drafts`；`working_lines/issues/clarification/escalation_preview` 使用 JSONB |
| `draft_versions` | 不可变草稿版本 | 保存 lines/issues/conditions/totals/clarification 的完整 JSONB 快照和创建者 |
| `approval_requests` | 老板审批 | 保存提交版本及 lines/totals/reasons/customer spans 不可变快照；决定字段仍在本表 |
| `delivery_orders` | 已批准 DO | `lines` 为不可变 JSONB；补 `escalation_reasons`；一草稿一 DO |
| `activity_log` | UI 时间线 | append-only；短事件和安全 payload |
| `audit_logs` | 审计记录头 | append-only；关联 draft/version/DO/actor/action |
| `field_diffs` | 字段差异明细 | `audit_id` 子记录；保存 AI 初稿与人工终稿的字段级差异 |

P0 不另建 `draft_lines/issues/conditions/delivery_order_lines/approval_decisions` 作为第二真相。条件保存在 `orders.issues` 的 `CUSTOMER_CONDITION` 对象和版本快照中；DO 行保存在不可变 `delivery_orders.lines`。若将来出现报表性能需求，再由迁移增加只读物化视图，不改变事务真相源。

#### 7.7.2 旧名到物理名映射

| 旧文档概念 | P0 物理实现 |
|---|---|
| `skus` | `products` |
| `drafts` | `orders` |
| `customer_aliases` | `alias_cache` |
| `activity_logs` | `activity_log` |
| `draft_lines/issues/conditions` | `orders` 聚合 JSONB + `draft_versions` 快照 |
| `delivery_order_lines` | `delivery_orders.lines` JSONB |
| `approval_decisions` | `approval_requests.decided_* / decision_note / status` |

因为当前不是带历史数据的生产迁移，四份文档和 seed 直接改用物理名，不默认创建可写兼容视图。若实际代码已依赖旧名，Gate 0 必须先盘点，再决定一次性迁移或只读兼容视图。

### 7.8 字段字典

| 字段 | 类型/闭集 | 可空 | 权威语义 |
|---|---|---:|---|
| `termination_reason` | `OWNER_REJECTED / CLERK_DISCARDED / SYSTEM_TERMINATED` | 终态前可空 | 公共状态仍为 `REJECTED`；用本字段区分终止来源 |
| `terminated_by_user_id` | string | 是 | SYSTEM 终止时可空；其他情况必须有 |
| `termination_note` | string ≤ 500 | 终态前可空 | OWNER_REJECTED、CLERK_DISCARDED 必填 |
| `Issue.reason_code` | `INVALID_QUANTITY / FIELD_NOT_EVIDENCED / FAMILY_NOT_EVIDENCED / DUPLICATE_SPAN / OVERLAPPING_SPAN / SOURCE_EVIDENCE_INVALID / UNKNOWN_PRODUCT / NO_CANDIDATE / LOW_SCORE / SMALL_SCORE_GAP` | 是 | 只细分 8 个公共 IssueCode，不成为第二套公开疑点 |
| `price_basis` | `UNIT / TOTAL / UNKNOWN` | 非价格条件可空 | P0 仅能执行 UNIT；TOTAL/UNKNOWN 保持阻断 |
| `deleted_line_ids` | unique list[string] | 否，默认空 | 显式删除；现有行不得仅靠省略删除 |
| `match_source` | `SUGGESTED_DEFAULT / LLM_EXTRACTED / RAPIDFUZZ_FALLBACK / MANUAL_SELECTED` | 否 | 当前 SKU 解析来源的唯一持久化字段；原始来源另存初始快照 |
| `ai_mode` | `LLM / FALLBACK / ALIAS_ONLY / MIXED` | 否 | 草稿级路径摘要，由行来源集合派生 |
| `ignored` | raw AI list[string] | 否，默认空 | 只存在模型原始边界 |
| `ignored_spans` | list[SpanView] | 否，默认空 | Adapter 定位后的内部/API 字段，由 `ignored` 派生 |
| `disambiguations` | derived list | 是 | 只读兼容字段，由指定 IssueCode 派生并标 deprecated；客户端不得写入 |
| `phone_e164` | E.164 string | 是 | 正式字段名；演示数据必须为合成号码，不另建 `synthetic_phone` 真相 |
| `amount_threshold_rm` | decimal string/API，NUMERIC/DB | 否 | 租户老板升级阈值唯一字段 |
| `checks_enabled` | object[bool] | 否 | 租户级检查开关；seed 必须给默认值 |
| `below_tier_price_override_requires_owner` | bool | 否 | 仅控制成交价低于等级价的升级；替代含义过宽的 `price_override_requires_owner` |
| `credit_flag_requires_owner` | bool | 否 | 控制信用提醒升级 |
| `requested_qty` | positive int | 否 | 服务端初始快照，只读 |
| `confirmed_qty` | positive int | 是 | 人工确认量 |
| `effective_qty` | positive int | 否 | 服务端派生，不接受客户端提交 |
| `expected_version` | positive int | 视端点 | PUT/approve/discard 必须；parse/wake 不使用 |
| `X-Request-ID` | response header string | 否 | 所有成功和失败响应都返回；不嵌入错误正文 |

`IssueResolutionAction` 整体删除。行级修正只通过 `WorkingLine.sku_id/confirmed_qty/unit_price_override` 与 `deleted_line_ids` 表达；消息级处理只使用 6 个 `ResolutionChoice`。

### 7.9 保存请求的完整语义

```text
SaveLinesRequest:
  expected_version: int
  lines: WorkingLine[]              # 保存后的完整剩余行集合
  deleted_line_ids: string[]        # 本次显式删除的旧行
  resolutions: IssueResolution[]    # 只处理消息级疑点
```

验证规则：

1. 每个当前旧 `line_id` 必须恰好出现在 `lines` 或 `deleted_line_ids`；
2. 同一个 ID 不能同时出现；未知删除 ID 返回 400；
3. `lines` 至少保留一行，否则 400 `EMPTY_ORDER`；
4. 客户端不得提交 `requested_qty/effective_qty/tier_unit_price/subtotal/status`；
5. 新增人工行如确有需要，使用 `client_line_ref`，由服务端生成正式 `line_id`；P0 默认优先修正已存在的低置信行；
6. 整个保存、疑点重算、价格重算、澄清重建、版本快照和活动日志在一个事务中完成。

v2.1 为方案 B 保留的 `confirmed_items` 只是一条受控兼容路径：必须同时带 `expected_version`；后端在同一事务中先按 PUT 规则生成新版本，再对该新版本执行批准；任一步失败全部回滚；响应和审计必须返回实际批准的版本号。新前端不得继续使用此字段，OpenAPI 标记 `deprecated: true`，待既有 fixture 全部迁移后删除。

### 7.10 错误与成功响应表

#### 7.10.1 错误

| HTTP | `error_code` | 触发 |
|---:|---|---|
| 400 | `DISAMBIGUATION_UNRESOLVED` | 存在未解决阻断疑点 |
| 400 | `INSUFFICIENT_STOCK` | 保存/提交时已知缺货 |
| 400 | `TARGET_LINE_REQUIRED` | PRICE 条件缺目标行 |
| 400 | `OVERRIDE_REQUIRED` | 目标行未有效改价或缺原因 |
| 400 | `NOTE_REQUIRED` | 必须备注的动作缺备注 |
| 400 | `EMPTY_ORDER` | 显式删除所有行 |
| 400 | `INVALID_LINE_OPERATION` | 行集合与删除集合不完整、重复或含未知 ID |
| 401 | `UNAUTHORIZED` | 缺失或无效令牌 |
| 403 | `FORBIDDEN` | 角色无权执行动作 |
| 403 | `TENANT_MISMATCH` | 兼容请求体租户与会话不一致 |
| 404 | `NOT_FOUND` | 当前租户不可见资源；跨租户同样返回 404 |
| 409 | `STALE_VERSION` | `expected_version` 不是最新 |
| 409 | `PENDING_OWNER_APPROVAL` | 待批期间尝试编辑/重复提交/作废 |
| 409 | `ALREADY_APPROVED` | 已生成 DO；details 返回 `do_number/approved_at` |
| 409 | `DRAFT_REJECTED` | 已终止草稿再次操作 |
| 409 | `STOCK_CHANGED` | 事务锁内发现库存已变化；审批保持 PENDING |
| 422 | `REQUEST_VALIDATION_FAILED` | 请求 JSON 类型/格式不合法 |
| 429 | `RATE_LIMITED` | parse/wake 超出配额 |
| 500 | `MISSING_TIER_PRICE` | 价格配置遗漏；正常情况下应被 seed/startup 校验提前阻止 |
| 503 | `AI_AND_FALLBACK_UNAVAILABLE` | AI 与本地兜底都不可用且不能形成安全草稿 |

错误正文固定为 `{"error_code":"...","message":"...","details":{...}}`；所有响应另带 `X-Request-ID`。

#### 7.10.2 成功体

| 端点 | HTTP | 直接响应模型 |
|---|---:|---|
| parse/get/PUT draft | 200 | `OrderDraft` |
| draft list | 200 | `DraftListResponse` |
| approve 无升级 | 200 | `DeliveryOrder`（含 `reply_draft`） |
| approve 有升级 | 202 | `ApprovalRequest` |
| approval list/detail | 200 | `ApprovalListResponse / ApprovalDetail` |
| decide approve | 200 | `DeliveryOrder`（含 `reply_draft`） |
| decide reject | 200 | `ApprovalDecisionResult(status=REJECTED)` |
| audit | 200 | `AuditDetail` |
| activity | 200 | `ActivityListResponse` |
| `/me` | 200 | `MeResponse` |
| AI status/wake | 200 | `AiStatus / AiWakeResult` |

### 7.11 H1 确定性字段证据规范

1. **定位**：先把模型 `span` 唯一定位到 masked text 的半开区间；重复出现时按顺序与非重叠约束选择，无法唯一定位则单行 fallback。
2. **数量**：从 span 提取阿拉伯数字或版本化数字词词表中的完整 token。中文、英文、马来语数字词由确定性有限规则转换；不做编辑距离或语义模型猜测。模型 qty 必须等于某个解析候选且候选能唯一关联该商品。
3. **单位/规格/等级**：只接受 `uom_aliases`、规格正则和等级别名中的精确规范化命中；大小写、Unicode 兼容形式和空白可归一化，字符含义不可模糊替换。
4. **商品族**：当前租户族名、`family_aliases` 或当前客户已确认别名必须在 span 中有精确证据；否则 `LOW_CONFIDENCE_MATCH(reason_code=FAMILY_NOT_EVIDENCED)`。
5. **多候选**：一个字段出现多个无法唯一关联的候选时，不选择“最像”的值，保留阻断疑点。
6. **兼容数字字符串**：模型若返回仅含 ASCII 数字的字符串，可在 Adapter 边界转 int 并记录 `MODEL_TYPE_COERCED` 诊断；正式 Schema 和后续层仍是 int。
7. **审计**：内部标准行保存每字段的 `raw_text/start/end/normalizer_version` 证据；无效模型字段值不进入领域对象，也不写普通日志。
8. **失败策略**：丢弃失败字段而非整单失败；qty/fam 失败必须阻断或单行 fallback，不能静默生成确定 SKU 与数量。

### 7.12 H5 条件触发真值表

| 输入 | 结果 | `price_basis`/说明 |
|---|---|---|
| `Last order was RM95.` | 不生成条件 | 历史陈述；金额只作普通文本证据 |
| `Total last time RM95.` | 不生成条件 | 无条件、询价或议价语气 |
| `kalau RM95 boleh` | PRICE | 条件标记 + 金额；basis 默认 UNKNOWN，单行可在 UI 预选 UNIT 但须确认 |
| `RM95?` | PRICE | 问号构成询价；目标行和 basis 仍需确认 |
| `boleh kurang sikit?` | PRICE | 议价短语，无金额；跟单员录入客户确认后的单位价 |
| `kalau ada, boleh kurang` | STOCK + PRICE | 同一片段允许多标签，不能 `elif` 丢掉一种 |
| `If available, send 5 ctn` | STOCK | `available` 属于 STOCK 词表 |
| `hantar esok` | 不生成条件 | 普通送货要求，无条件标记 |
| `Stock code A95` | 不生成条件 | 商品编码，不是金额条件 |
| `RM95 for 5 ctn` | PRICE，阻断 | basis=`UNKNOWN/TOTAL`；P0 先向客户确认单位价，不能直接除法应用 |
| `Can follow last price RM95?` | PRICE | 虽含历史词，但存在明确询价/议价语气 |

触发逻辑必须满足以下之一：明确议价短语；或金额与条件/询价语气共同出现。裸金额陈述不触发。`NOT_A_CONDITION` 必须备注并写 `CONDITION_DISMISSED`，供词表回放。

---

## 8. 修订实施方案（用户批准后才执行）

### 8.1 先建立治理层

采用两段式批准：

**第一段：Gate 0。** 新建但不实施业务修订：

1. `baseline-manifest.json`：记录 v2.1、评审、提案及参考文件的路径、字节数、行数、SHA-256、批准人和时间；
2. `05_KiraOrder_v1.3_契约变更记录.md` v0.1：只登记拟变更项和影响范围；
3. `v2.1-erratum-1.md`：只放对基线自身的正确性勘误；
4. `contracts/db-schema.md`：固化 §7.7 的物理模型、关系和迁移策略；
5. `contracts/fields.md`：固化 §7.8 字段字典；
6. `contracts/errors.md`：固化 §7.10 错误和前端行为；
7. `contracts/condition-triggers.md` 与 `field-evidence.md`：固化 H5/H1；
8. 明确 He Minghao 为后端负责人，修正过期 RACI；
9. 由后端、前端、AI、数据四方确认 Gate 0。

**第二段：全量执行。** Gate 0 经用户批准后，才修改 v2.1 勘误、`01`—`04`、OpenAPI、Schema、fixture、seed 和测试。

变更必须按下列层次分开，不允许把基线勘误静默藏进四份文档：

| 层 | 只包含 | 产物 |
|---|---|---|
| v2.1 erratum | `MIXED`、H1、H5、price basis、不可变快照、SQL 漏字段、成功体/头部、物理 schema 裁决 | `v2.1-erratum-1.md`，独立哈希与批准 |
| v1.3 文档对齐 | 状态、疑点、条件、升级、API、权限、数量、DO、危险动作删除、Orbyte 边界 | `05` 变更记录 + `01`—`04` 修订 |
| 实现与验证 | 数据库迁移、OpenAPI、AI/seed Schema、fixture、代码和测试 | `contracts/`、`migrations/`、`tests/` |

### 8.2 机器可读真相源

不建议同时手工维护 `enums.yaml + OpenAPI + 四份 Markdown`。建议：

- `contracts/openapi.yaml`：公共 API、字段、错误、枚举的唯一机器真相源；
- `contracts/ai-output.schema.json`：模型原始输出；
- `contracts/seed.schema.json`：种子数据；
- `contracts/db-schema.md` + `migrations/0001_baseline.sql`：唯一物理数据库基准；
- `contracts/fields.md`、`contracts/errors.md`：供人审阅，并由 OpenAPI 校验一致；
- `contracts/fixtures/*.json`：联调实例；
- TypeScript 类型和文档枚举由 OpenAPI 生成或校验；
- Python/Pydantic 实现必须通过 OpenAPI 契约测试。

这样只有一个公共 API 真相源，不会把 `enums.yaml` 再变成第五份手写契约。

### 8.3 四份文件的具体修改范围

#### `01` 后端完整规则框架

- §5：替换为 v2.1 枚举；增加 `Issue.reason_code` 和 `MIXED` 勘误引用；
- §6：改用 §7.7 的物理表；补 family/uom aliases、库存、等级价、版本快照、终止字段、审批快照和 DO `escalation_reasons`；
- §7/§12：完整回归 OWNER 权限和 `OWNER_SELF_APPROVED`，状态终止原因单独建模；
- §8/§9：删除危险动作，使用 6 个 ResolutionChoice；加入目标行、price basis、删除行和 H5 真值表；
- §10：加入 §7.11 字段证据、数字字符串边界兼容和 span 重叠处理；
- §11/§13：补 `effective_qty` 重算、批准 6 项硬复核、不可变快照和高于等级价规则；
- §14/§15：补完整事件、审计/审批详情/回复、错误与成功模型、`X-Request-ID`、限流；
- 新增 Orbyte 适配边界，但内部主键仍是 `tenant_id`。

#### `02` 后端与前端

- §2：类型从 OpenAPI 生成；删除 `IssueResolutionAction`、旧状态、旧疑点和旧升级码；
- §3：改为直接成功体、扁平错误体和 `X-Request-ID`；
- §5—§7：改用 `/orders/...`、单数 `clarification_draft`、`match_source` 和终止原因；
- §8—§10：行级编辑通过 lines，消息级使用 ResolutionChoice；增加 `deleted_line_ids`、price basis、目标行和 STOCK 派生事实；
- §11—§13：按钮只依赖 `allowed_actions`；完整支持 OWNER 工作台、自提交路径、审批详情和 `STOCK_CHANGED`；
- §14/§17：DO/审计/回复均保留 P0；回复含总额并标 `Draft — not sent`；
- §16：前端错误行为与 §7.10 一一对应；
- Organization 只作为显示术语，不改变接口主键。

#### `03` 后端与 AI

- §4/§5：原始 Schema 回归 `qty:int`、`fam:"UNKNOWN"`、四类 `conds` 和 raw `ignored`；
- §6/§7：实现 §7.11 的证据对象、数字字符串兼容、失败 reason、重复/重叠 span 和响应大小限制；
- §8/§9：定义 `MIXED`，只持久化 `match_source`，`ignored` 映射到内部 `ignored_spans`；
- §11：条件候选服从 §7.12，同一片段允许多标签；
- §13—§16：记录 model/prompt/schema/normalizer 版本并补回归；
- 不向模型发送 Orbyte 网页请求、价格、库存或审批数据；`detected_language` 由后端模板逻辑产生，不扩充模型契约。

#### `04` 后端与数据

- §1/§6—§10：seed 改用 §7.7 物理名；补 family/uom aliases、phrase_norm、跨族/跨客户冲突和四类条件；
- §2/§5：统一 `phone_e164/credit_flag/amount_threshold_rm/checks_enabled`；
- §12：开发集文件明确 `dev_38.json`，冻结集保持 TEST-01—32；
- §13：答案键使用 v2.1 枚举、reason_code、price_basis、target lines 和 contract_version；
- §14/§17：补 H1/H2/H3/H5/H11、显式删除、OWNER、快照不变和错误码校验；
- TEST-01—24 的逐条消息与答案键由数据负责人从方案 B 原始数据补录，不根据评审表反推；
- 保持答案键隔离、SHA-256 和冻结集不得进入提示词。

### 8.4 优先顺序

| 阶段 | 内容 | 完成门槛 |
|---|---|---|
| Gate 0-A | manifest、RACI、errata/v1.3 分层 | 所有人引用相同 SHA、负责人和优先级 |
| Gate 0-B | DB schema、字段字典、错误/成功体、H1/H5 规范 | 无待解释字段；四方签字 |
| Gate 0-C | OpenAPI 骨架、JSON Schema、fixture 目录、追踪矩阵 | lint 通过；例子可解析 |
| P0-A | C1—C21 对齐 + 物理迁移 | OpenAPI、数据库和四份文档无枚举/路径/表名漂移 |
| P0-B | H1—H16 正确性 + 批量保存 + 批准硬复核 | 错字段、错行价格、数量状态、并发、幂等测试通过 |
| P0-C | 完整 OWNER、审批详情、审计、回复 | v2.1 P0 演示无需范围绕行 |
| P1 | 同日订单、作废完善、仓库列表/视图、模拟入站 | 对应 DEV/P1 fixture 通过 |
| P2 | Orbyte 正式适配、Credits/Wallet | 取得正式授权与 API 契约后再做 |

阶段按验收门推进，不绑定已经过去或未经确认的钟点。若需要范围收缩，必须在 Gate 0 单独列出并由用户批准。

### 8.5 clause-to-section 执行矩阵

| 变更组 | v2.1/勘误依据 | 修改位置 | 机器产物 | 验收 |
|---|---|---|---|---|
| C1/C2/C3/C4/C6/C12/C21 | §4.8/§4.11 | 01 §5/§7/§8；02 §2；04 §13 | OpenAPI enums | enum diff 为零 |
| C5/C18/C19/C20/C30 | §4.2/§4.3 + errata | 01 §10；02 §7；03 §5—§9；04 answers | AI Schema + parse fixtures | int/UNKNOWN/MIXED/ignored 测试 |
| C7/C9/C10/C11/C13 | §4.10/§4.11 | 01 §13/§15；02 §3/§6/§9/§12 | OpenAPI paths + save/approve fixtures | 方法、路径、版本、响应完全一致 |
| C14/C15/C16/C17/C28 | §4.10/§4.14 + errata | 01 §6/§9/§14/§15；02 §7/§13/§14/§17 | approval/audit/DO/reply schemas | 页面 fixture 可直接渲染 |
| C22 物理模型 | §4.12 + errata | 01 §6；04 §1/§6—§9/§16 | db-schema + migration + seed schema | 空库迁移和 seed 校验通过 |
| C23—C29 字段/错误 | errata/Revision 2 §7.8—§7.10 | 01 §4/§5/§15；02 §2/§3/§16；04 answers | fields/errors/OpenAPI | 字段字典与 OpenAPI 自动比较 |
| H1/H10/H11 | §4.2/§4.3 + errata | 01 §10；03 §6—§8；04 §10/§14 | field-evidence + AI fixtures | DEV-39—41 和重复/重叠用例 |
| H2/H5/H6/H15 | §4.5 + errata | 01 §8/§9/§13；02 §8—§10；04 §10/§14 | condition-triggers + price fixtures | TEST-29/30/32 + target/basis 用例 |
| H3/H7/H12 | §4.2/§4.13 | 01 §6/§11/§13；02 §9/§12；04 §14 | save/stock fixtures | DEV-33/34、EMPTY_ORDER、409 |
| H4/H16 | §4.9/§4.11 | 01 §7/§8/§12；02 §2/§8/§13 | role/action schemas | 危险动作不存在；OWNER 路径通过 |
| H8/H9/H13/H14 | §4.7/§4.12/§4.13 | 01 §6/§11/§13；02 §12/§13；04 §9/§14 | alias/approval/idempotency fixtures | 原因、唯一索引、快照、DO 恢复测试 |
| Orbyte 边界 | 实测参考限制 | 01 适配小节；02 文案；README/隐私页 | 无官方 API 伪契约 | 声明扫描与权限测试 |

---

## 9. 验收与证明

### 9.1 静态契约验收

- 四份文档不再各自定义冲突枚举；
- OpenAPI 中每个公开枚举与 v2.1/勘误一致；
- `contracts/db-schema.md`、迁移 SQL、seed Schema 的表名和字段一致；
- 所有 JSON 示例可解析；
- 所有路径、方法、角色、请求字段和错误格式有唯一值；
- 每个成功体、错误体和 `X-Request-ID` 都有 OpenAPI 定义与 fixture；
- Markdown 中不得出现旧状态/旧端点，除非在“迁移映射”表明确标注；
- 文档 SHA 和 Git tag 可复现。

### 9.2 必须新增或重跑的回归场景

1. 真实 Milo span + Coffee fam；
2. span 数量 5 + 模型 qty 50；
3. span 未出现规格 + 模型补规格；
4. 多商品价格条件未选目标行；
5. 只降低非目标行价格；
6. 减量自动关闭缺货疑点；
7. 再加量重新打开疑点；
8. 保存后库存变化，批准返回 `STOCK_CHANGED`；
9. “Last order was RM95”不生成条件；
10. “kalau ada, boleh kurang”同时生成 STOCK 与 PRICE；
11. 完全重复 span 不重复计量；
12. 重叠 span 不静默合并；
13. OWNER 自建常规单与自提交升级单；
14. 审批快照在后续编辑后不变；
15. `ALREADY_APPROVED` 可恢复到已有 DO；
16. 单价/总价不明确时不得自动应用；
17. 仓库响应无价格、金额、电话；
18. 未掩码 PII 不进入数据库、日志、异常和模型请求；
19. 显式删除与省略行可区分，删除全部返回 `EMPTY_ORDER`；
20. `REJECTED` 能通过 termination fields 区分老板驳回和跟单员作废；
21. `LOW_CONFIDENCE_MATCH.reason_code` 能区分无族证据、非法数量和 span 问题；
22. 模型字符串 `"5"` 只在 Adapter 边界受控转 int，其他字符串单行 fallback；
23. `confirmed_items` 兼容请求原子完成“保存新版本 + 批准”，并返回实际版本；
24. 每个响应都带 `X-Request-ID`，成功正文不包 `{data}`；
25. OWNER 创建、编辑、批常规单和自提交升级单的权限及事件正确；
26. TEST-01—24 有原始逐条数据，而不是从组级断言反推答案。

### 9.3 建议冻结的 fixture

```text
parse_draft.json
parse_mixed.json
save_lines_ready.json
save_lines_target_required.json
save_lines_explicit_delete.json
save_lines_empty_order_400.json
approve_200.json
approve_202.json
approve_stock_changed_409.json
already_approved_409.json
approval_detail.json
audit_detail.json
reply_draft.json
owner_self_approved.json
termination_owner_rejected.json
termination_clerk_discarded.json
warehouse_do_redacted.json
```

三端应以 fixture 和 OpenAPI 为准，不再靠口头解释 Markdown 示例。

---

## 10. 最终结论与建议动作

1. **评审指出的问题总体真实，必须处理。** 尤其是 v2.1 同步、H1 字段证据、H2 目标行、H3 数量重算、H4 危险动作和不可变审批快照。
2. **评审建议不是完美答案。** 凡与 v2.1 唯一基线冲突的命名、路径、权限和 wire type 建议都不能采用。
3. **四份文档不应重写，应做受控升级。** 先建立变更记录与机器契约，再分别修 01—04。
4. **v2.1 本身需要一份小型正确性勘误。** 至少覆盖 `MIXED`、H1 字段证据、裸金额误报、price basis、审批快照和 SQL 漏字段。
5. **Orbyte 参考只采纳边界与适配思想。** Organization 映射、权限分层和“不虚构 Wallet/官方集成”值得写入；网页内部 API、membership、Credits 不进入当前 P0。
6. **He Minghao 是后端负责人。** 后续修改、实现和验收均以此为人员基线。
7. **Revision 2 已从方向稿升级为可评审执行稿。** 它已经明确物理表、字段语义、错误/成功模型、H1/H5 算法、OWNER/P0 边界、逐文件落点和验收矩阵。

在用户批准前，建议保持 `01`—`04`、v2.1 和评审报告原样，避免出现“修到一半又被当成冻结版”的新风险。

### 10.1 建议的两段式批准语

第一段：

> 批准 Revision 2 作为 v1.3 的修订执行方向；批准仅创建 Gate 0 产物，包括 baseline manifest、v2.1 erratum 草案、变更记录 v0.1、物理 schema、字段字典、错误表、H1/H5 规范、OpenAPI 骨架和 fixture 目录；暂不修改 01—04 和现有基线。

第二段在 Gate 0 审阅完成后另行批准：

> 批准按已签字的 Gate 0 产物执行 v2.1 erratum、01—04 修订、OpenAPI/Schema/fixture/seed/test 更新；OWNER 全能力及审计/回复保持 v2.1 P0，不作静默范围收缩。

### 10.2 Gate 0 批准检查清单

- [ ] manifest 记录 v2.1 路径、行数、字节数、SHA、批准人和时间；
- [ ] Revision 2 的冻结哈希由 manifest 外部记录；
- [ ] v2.1 erratum 与 v1.3 文档对齐严格分层；
- [ ] §7.7 物理模型已由后端与数据确认；
- [ ] §7.8 字段字典已由前端、AI、数据确认；
- [ ] §7.10 错误、成功体和 `X-Request-ID` 已确认；
- [ ] §7.11 H1 证据规范已有词表版本和测试负责人；
- [ ] §7.12 H5 真值表已加入数据正负例；
- [ ] OWNER 全能力、审计和回复保持 P0；任何范围收缩均另行批准；
- [ ] `IssueResolutionAction` 已从拟议公共契约删除；
- [ ] TEST-01—24 原始数据的补录来源与负责人明确；
- [ ] 后端、前端、AI、数据四方完成签字。

