# R08 候选与问题接口约定 v0.1r1

版本：R08-CONTRACT-v0.1r1。状态：REVISED_REVIEW_DRAFT / INTERFACE_SAMPLE / NOT_LIVE。原 v0.1 ZIP 5c18e25c…d8605d 保留不变，本稿另发新版本与完整哈希。

本稿已登记 v0.1 的实际审核：Ye CONSUMABLE_WITH_MODIFICATIONS；Zhou 合同语义 PASS、样例 PASS_WITH_CONDITIONS；Xiong 接受第 1–2 节边界并要求更正 R07 状态。此次落实指定修订，交 Ye／Zhou 核补件闭合；不抹去已有结论，也不自动签成无条件 PASS 或冻结。本稿不是运行时代码实现、真实联调或任何 E 项通过记录。

## 1. 采用的接口层和所有权

**R08 的主交付接口是后端→前端最终 API：Python OrderDraftResponse，对应前端 wire schema OrderDraft。** WorkingLine、Issue、SkuCandidate、IssueResolution、SaveLinesRequest 是本稿的约定对象。前端不直接消费模型 JSON 或 RawRow。

**RawExtraction / RawRow 是后端接收 R07 的上游输入边界。** R09 的 parse/resolver 消费该对象，生成最终候选、问题及动作；R08 记录兼容规则，不接管 R07 的抽取和模型责任。Xiong 无需提供他不拥有的 SKU／价格／库存／blocking。

| 内容 | 负责生成／校验 | 使用方 |
|---|---|---|
| fam、qty/uom/pack_size 提议、span、字段证据、全局 conditions、实际 ai_mode | R07／adapter；后端再次守卫 | R09 后端 |
| 持久化 line_id、SKU、完整身份候选、租户／客户价和库存、issue、blocking、允许动作 | He 的后端 R09 | Ye 的 R10 |
| client_line_ref、手选 SKU、confirmed_qty、显式单位、resolution、expected_version | 前端提交人的确认输入；后端重新验证 | 保存接口 |
| 语义、阻断和样例验收结论 | Zhou | He／Ye |

新增三语语义只覆盖 FAM_GULA / FAM_BERAS / FAM_GARAM；不纳入 TELUR/S03。完整租户目录、原有有效族及现有其他功能仍保留；不得把 R07 白名单裁成三个族。目录外输入的阻断是防护样例，不是扩大自动识别承诺。

## 2. 上游兼容规则：保留 R07 的未确定项

1. R07 条件没有 target_line_ids。RawRow.conds 只是 span 包含关系下的局部集合，必须同时处理 RawExtraction.conditions，不能丢掉行外条件。backend 确定可证明的关联后写最终 Issue；无法确定时 line_id=null、target_line_ids=[]，保留候选行并阻断，等待人工确认。不把局部关联升级为已证明的全局目标。
2. 当前 condition_scope 只可靠地产生 SINGLE_LINE／UNKNOWN，kind 实际为 STOCK／PRICE／OTHER；不推断 MULTI_LINE、ORDER_LEVEL、TIME 或 TOTAL 已有上游能力。金额口径不明时 requested_unit_price=null、price_basis=UNKNOWN，原金额保留在 data_used；不能直接当单位价。
3. field_evidence 只有 qty/uom/pack_size，不新增或伪造 family evidence。family 仍由 adapter／后端目录守卫验证。人工改正值由 MANUAL_SELECTED／confirmed_*／版本与审计表示，不把确认值倒写成原抽取证据。
4. 上游 ignored_spans 的 (-1,-1) 原样保留为“无法定位”。保留 text，不用于字符串切片或高亮，不据此认定业务条件可忽略；其他非法／不匹配坐标不转成可信位置。最终 WorkingLine／Issue 的已知无效偏移使用 null；WorkingLine 回退 source_span，Issue 以 span 为主。Issue.source_span 是 deprecated，仅旧数据兼容回退，新样例不再输出该键；不把无效 (0,0) 伪装成有效证据。
5. 所有有效坐标采用 masked_message 的 Unicode code point，左闭右开；要求 message[start:end] 与原文完全相同。JavaScript 切片需按 Array.from(message)，不能直接以 UTF-16 下标处理 emoji。原文只交脱敏 masked_message，不交原始 PII。
6. R07 路径 fam 应是有效当前租户族或 UNKNOWN；其他 provider 的 null／目录外 family 不直接信任，后端归入未知并给阻断问题。AdapterLine 的临时 LINE_index 不能当持久化 line_id；client_line_ref 也不等于数据库 line_id。
7. 实际 ai_mode 原样传递；任何真实模式均不得由字段看似正确反推。按用户转交 Xiong 的最新边界回执，当前应记录为 **R07 TESTED_OFFLINE + one live preflight observed (v2 evidence; P-2 not signed)**：03:28 已有一次真实候选 preflight，不再写成“无 live／无真实模型 JSON”。本次只收到 Xiong 的转交说明，未收到并独立核验该 v2 证据原件，也没有由 He 新调用模型。R07-FIELD-v0.1 原附件及 Ye 回执内较早的 LIVE_UNVERIFIED 原文保留为历史，不改原字节；P-2 仍未签，不签 R07 验收或语义 PASS。
8. C-8 输入预算限制保留：4,000 中文字符压力输入未获支持保证，8192 窗口与 2048 输出预算的缺口不由本稿补齐。完整上下文不得静默截断；预算处理和有效模型窗口仍归 Xiong。

## 3. 最终 API 的必备约束

- 继续使用现有封闭枚举，不修改 gate0、冻结 OpenAPI／契约、种子或答案。特别是 MISSING_TIER_PRICE 是已有 HTTP 错误码，不是现有 IssueCode／IssueReasonCode，不能塞进这些枚举字段。
- 每份响应包含 issues、conditions、lines[].candidate_skus、blocking_issues、allowed_actions、blocked_actions。无行时 lines=[]，没有顶层 candidate_skus 新字段。conditions 是 issues 中 CUSTOMER_CONDITION 的一致子集，不产生第二套有冲突的状态。
- blocking_issues 等于所有 blocking=true 且 resolved=false 的问题 code 去重集合，**不是 issue_id 列表**。未解决时状态 DISAMBIGUATION_REQUIRED，APPROVE_AND_GENERATE_DO、SUBMIT_FOR_OWNER、OWNER_APPROVE 均不在 allowed_actions；blocked_actions 为这些动作给出原因。前端只展示，后端批准入口必须独立拒绝。
- 后端真实拒绝未解决批准的已有目标错误为 HTTP 400 / DISAMBIGUATION_UNRESOLVED；无相应真实调用证据时只写预期，不能写“已拒绝”。版本不符优先按当前后端校验顺序返回 409 / STALE_VERSION，不把所有拒绝强行归同一码。
- DecimalString 为两位小数字符串；价格缺失不是 0.00，也不是空字符串。普通 WorkingLine 的价格可为 null；现有 SkuCandidate 的 tier_unit_price 不可为 null。
- CUSTOMER_CONDITION 的 condition_id 严格按冻结文档推导：CND_ + SHA-256(UTF-8(draft_id|condition_kind|span_start|span_end)) 的前 24 位大写十六进制。当前条件样例均为 CND_6BAFF2E046E11A9F84B97079；改人工目标或金额口径不改变原条件 span 身份。不得再使用 SAMPLE_C01 占位。
- SaveLinesRequest 必须带当前 expected_version；现有行用 line_id，新手工行用 client_line_ref，二者恰好一个。SKU、单位、规格、等级、数量、价格、权限及库存都由后端重新校验；保存不出 DO、不扣库存，前端收到新版本再展示后端判定。
- UI 当前数量范围为 1–100000，后端 confirmed_qty 为 1–999999；本稿不改数值上限，不据 UI 的小范围宣称接口全范围已联调。空数量不可用 1 占位。

## 4. 六类问题的响应与恢复

| 类别 | code / reason_code | 候选及阻断 | 人工处理与保存 |
|---|---|---|---|
| 未知商品 | LOW_CONFIDENCE_MATCH；UNKNOWN_PRODUCT / FAMILY_NOT_EVIDENCED / NO_CANDIDATE 按真实原因选 | 不造 SKU；没有可靠候选则空；blocking=true | 从授权当前租户目录选实际 SKU，MANUAL_SELECTED，后端核价／库存；不能凭客户端提交一个字符串就算目录中存在 |
| 多规格／等级 | MULTIPLE_PACK_SIZES / MULTIPLE_GRADES；无额外 reason 可为 null | 所有兼容身份候选完整保留；不能靠排序、价格、有货代选；blocking=true | 人工选 SKU 并保存，MANUAL_SELECTED，重新核价／库存。当前样例覆盖 GULA 多规格；没有捏造真实三族中的等级数据或声称等级运行验证 |
| 缺单位 | MISSING_UOM / FIELD_NOT_EVIDENCED | 单位空；不默认 bag；即使所列候选碰巧同单位也不能代替用户确认 | 人工补明确单位并保存；单位冲突继续阻断 |
| 缺数量 | LOW_CONFIDENCE_MATCH / INVALID_QUANTITY 或 AMBIGUOUS_QUANTITY | 不创建普通可批行；issue.line_id=null，保留原文／已确定内容；blocking=true | Add a confirmed product：client_line_ref + SKU + confirmed_qty + uom；MANUAL_SELECTED。不能提交一个数量 1 的假抽取行 |
| 缺价 | LOW_CONFIDENCE_MATCH / NO_CANDIDATE；data_used.r08.problem_kind=MISSING_TIER_PRICE | 先判身份，不删缺价 SKU 制造唯一；采用下节兼容阻断表达 | 人工确认身份／价格事实；缺客户等级价须有权人员配置，前端 override 不能代替缺失等级价；无配置则维持阻断 |
| 条件／目标不明 | CUSTOMER_CONDITION；reason 可为 null | 保留 span/kind/scope/候选目标／已确认目标，金额口径或目标不明 blocking=true | RESOLVE_ISSUE 对应现有 resolutions；PRICE 接受必须给目标、UNIT、confirmed_unit_price、note。选其他 SKU／改目标／变价时重新校验并使失效确认回到未解决，不丢原条件 |

非条件的行问题通过改行／补行并保存重算，不给它们伪造 ResolutionChoice。条件中的 STOCK 由原有库存检查解决；不能用普通人工 resolution 绕过库存校验。真实客户条件不能为了放行假标 NOT_A_CONDITION。

## 5. 缺价的兼容运行时表达（待 Ye／Zhou 明确审核）

**本轮不扩展可空价格 SkuCandidate，不新增枚举。** 只要某个兼容身份候选缺客户等级价，就不输出“只剩有价 SKU”的可选集合；该行 sku_id=null、candidate_skus=[]、价格／小计为 null，同时发出 blocking issue。

在现有 Issue.data_used 可扩展对象内，提议增加以下版本化语义；这些不是新的顶层 schema 或枚举：

```text
data_used.r08.problem_kind = "MISSING_TIER_PRICE"
data_used.r08.explanation = 脱敏、可直接展示的缺价及处理说明
data_used.r08.identity_candidates = 全部兼容 SKU 的身份摘要
data_used.r08.identity_candidates_complete = true
data_used.r08.priced_candidate_list_withheld = true
data_used.r08.selectable = false
data_used.r08.recovery = "CONFIRM_SKU_THEN_AUTHORIZED_PRICE_CONFIGURATION"
```

identity_candidates 是**不可直接点选的诊断摘要**，包括 sku_id/family_id/display_name/pack_size/grade/base_unit/tier_unit_price/available_qty；其中缺价为 null，仅用于解释，不能当 SkuCandidate 强转。全部属于当前租户和授权客户；不能藏掉缺价项。身份候选不全时必须显式报告不完整并继续阻断，不能声称唯一或编造完整列表。

NO_CANDIDATE 仅是现有 reason_code 的兼容占位，**不表示目录里没有兼容身份**。R10 对 problem_kind=MISSING_TIER_PRICE 必须优先消费 explanation 和只读摘要，不能仅按“没有候选”显示。该消费行为是本方案的必需配套条件；如 Ye 最终确认无法消费，保持该组合不可交付，并另提专用 reason/code 及契约变更重新评审，不能自行绕过冻结契约或静默退回误导文案。

Ye 的正式 CODE_ONLY 回执已确认可承载并列出五项 R10 待办：诊断类型收窄访问器、缺价专属标题／explanation、不可点选的只读身份摘要（null 显示 Not configured）、422/MISSING_TIER_PRICE 明确文案、无 gate0／枚举改动的透传兼容。当前均未实现，仍不能把 schema 可承载写成 UI 已支持。reference 的 4f95dd8 为提交版；Ye 另有未提交 worktree 展示代码，同样未渲染 r08，历史快照不冒充其未提交代码。

**处理入口与分工：** 本版缺价 issue.ask 改为 CLERK，现有行保留，clerk 在有 EDIT_DRAFT 权限时从 Choose from product directory 进入，选择真实 SKU 后提交 SaveLinesRequest。诊断摘要仍 selectable=false，不直接点选；目录选择是独立入口。缺价导致保存拒绝时不写入成功确认，原 draft／version 不变，人工选择仅存在于提交请求或本地编辑态。R10 需明确提示“SKU 已在本次请求中选定，仍需有权人员配置等级价”，并保留可重新选择／提交的入口。不能只给一个 clerk 无操作入口的 ask=SYSTEM 问题。

Zhou 核客户等级、价格含义和配置依据；He 负责核环境／数据权限并协调有权数据执行人，通过已有授权数据操作渠道进行候选环境配置和留前后记录；clerk 只能确认 SKU／发起处理请求，不能手填 tier 价或据此取得数据库权限。AUTHORIZED_DATA_OPERATOR 是分工描述，不新增应用角色／权限／自助配置端点，也不假定 OWNER 自动有配置权。未获目标环境授权或无有权执行人时继续阻断；本版没有执行任何配置。实际配置及重新保存核价归 R09，配套入口与提示归 R10，运行验证归 R11。

缺等级价时，当前保存逻辑先查等级价，缺失返回 HTTP 422 / MISSING_TIER_PRICE；unit_price_override 以及 PRICE condition 的客户报价都不能补这一数据缺口。样例的 missing_price_after_manual 保存预期现在有机器可读 save_expectation：http_status=422、error_code=MISSING_TIER_PRICE、actual_result=NOT_RUN、draft_version_after=1、stored_draft_behavior=UNCHANGED，stored draft 与 blocked 样例完全相同。后续有权配置并重新读取／保存才可进入已解除状态；本包没有执行该配置，也没有声称其成功。

## 6. 样例、验证和证据性质

samples/ 含六类各“阻断／人工处理后／负例”共 18 份 JSON。每份包裹元数据写 INTERFACE_SAMPLE / NOT_LIVE / HAND_AUTHORED_SYNTHETIC；draft 才是 wire 对象。元数据不能被作为新字段送入严格 schema。

所有 SKU、客户、价格、库存及时间戳均为明显 SAMPLE 标识的人工样例，不是 R04/R05 金标准、实库值、实测时间或模型输出。样例 wire 必填 ai_mode=FALLBACK 只为验证枚举形状；实际模式从未观测，元数据明确 NOT_OBSERVED。不得把这个枚举值摘出来当真实 FALLBACK 证据。

- backend：用 f347ed6 原 schemas.py 的 Pydantic 模型核所有响应及正常提交请求。
- frontend：用 Ye 指定 4f95dd8 的原 gate0.generated.ts 对响应／请求做 TypeScript 静态类型校验；wire.ts、types.ts、orders.tsx 另已按该 ref 读取供源码核对。
- 样例一致性：核 Unicode code point 回切、确定性 condition_id、金额／小计、问题子集、目标行、全部样例无 DO、未解决动作不放行、缺价保存拒绝后的存储状态完全不变；加入故意破坏的批准标志、可空候选价、emoji 偏移、零版本负例，并新增 condition_id、版本不变性、错误文案分流条件的破坏检测。
- R07 附件中的结构示例坐标已逐项回切；这只校验文档样例，不证明实际 adapter 或真实模型运行正确。

上述属于离线工件检查。样例中的拒绝 HTTP／错误码是预期，actual_http_status=null；未连接 API／数据库／模型，没有真实批准拒绝记录和实际库存前后读数。**没有 R05 E05、E01–E09 或 R11 判分结论。** Zhou 可验收接口样例语义，运行时实现和副作用仍须 R09/R11 另行验证。

所有负例统一为 negative_example.expected 对象，明确 http_status/error_code/behavior、draft_version_after、无 DO／无扣库存；actual_result 始终 NOT_RUN。预期以“已存在授权样例草稿、版本和其他输入有效，仅触发所列负例”的假定前置描述，不能拿 SAMPLE 标识向真实 API 请求后当成此预期已测。保存正常样例同样有 save_expectation，expected_version=1 产生 version=2 的语义保留。

## 7. 实现缺口和审核接收

| 项目 | 当前状态／责任 |
|---|---|
| 本稿和样例 | He 已落实 v0.1 审核指定修订，修订离线检查另有记录 |
| Xiong 边界回执 | v0.1 第 1–2 节可接收；唯一状态更正已落实。本稿不签 R07 验收、P-2 或语义 PASS；最新 preflight 仅按用户转交说明登记 |
| Zhou 审核 | 合同语义 PASS、样例 PASS_WITH_CONDITIONS；三项 P3 和负例统一建议已落实，待核本次补件闭合，不倒填无条件 PASS |
| Ye 正式消费审核 | 原件哈希 a21b4aa7…397bea2 已核；CONSUMABLE_WITH_MODIFICATIONS。A 条件 ID、B deprecated 字段已修，C 的提交版／worktree 口径已说明，R10 五项待办保持未实现；待核修改项闭合 |
| R09 运行时 | 缺价判身份／序列化、缺单位不默认、条件重绑定、保存／批准拒绝等需按最终约定实现或核实。现有源码不因样例通过而视为已满足 |
| R10 UI | 缺价专属说明及诊断候选摘要消费待 Ye 确认／实现 |
| R08 冻结／结项 | PENDING_DELTA_CLOSURE；已有三方结论保留，剩余为本次指定修订的闭合确认，不要求重做整轮审核，不能自动改成 FROZEN／CLOSED |

R08 不涉及平台发布。C13 修复／补测／审核／签收及 B05 受试保持原分工，不扩到 He。本稿不创建待批准的外发动作，回复稿留给用户转发。
