# KiraOrder v1.3 契约变更记录

> 状态：`GATE0_DRAFT`  
> 唯一基线：v2.1 / `5D02EBF84413...A55D`  
> 执行提案：Revision 2 / `40DA19F4FE5C...DF12B`  
> 规则：本表只登记 Gate 0 契约裁决；当前不修改 `01`—`04`，不写业务代码。

| ID | 变更 | 依据 | P0-A 后影响文件 | Gate 0 机器产物 | 验收 | 批准 |
|---|---|---|---|---|---|---|
| G0-01 | 统一物理表名，草稿与 DO 采用 JSONB 聚合/不可变快照 | Rev2 §7.7 | 01 §6；04 §1、§6—§9 | `db-schema.md` + `0001_baseline.sql` | 空库迁移；约束和触发器存在 | 待四方签 |
| G0-02 | 固定状态、字段、终止原因、数量与价格口径 | Rev2 §7.1、§7.8 | 01 §4—§5；02 §2；04 §13 | `fields.md` + OpenAPI | 完整度测试固定关键 schema 必填字段、枚举与 wire 类型 | 待四方签 |
| G0-03 | 固定成功体、错误体、HTTP、旧码映射与请求 ID | Rev2 §7.10；Gate0 §2.3 | 01 §15；02 §3、§16 | `errors.md` + OpenAPI + fixtures | 400—503 全覆盖；所有响应含头 | 待四方签 |
| G0-04 | 固化 H1 字段证据、词表和失败降级 | Rev2 §7.11 | 01 §10；03 §6—§8；04 §10 | `field-evidence.md` | DEV-39—41 + 多语/单位例 | 待四方签 |
| G0-05 | 固化 H5 条件触发真值表和词表 | Rev2 §7.12 | 01 §8—§9；03 §11；04 §10 | `condition-triggers.md` + `condition-triggers-v3.json` | 16 行真值表；含 UNIT 正向；H5-CT-01—03；TEST-01—32 归数据岗 | 待四方签 |
| G0-06 | 把 v2.1 自身正确性修正与普通文档对齐分层 | Rev2 §8.1 | 基线 Erratum；01—04 后续对齐 | `v2.1-erratum-1.md` | 独立哈希、独立批准 | 待四方签 |
| G0-07 | OWNER、审批详情、审计与回复保持 P0 | v2.1 §3.5、§4.9；Rev2 H16 | 01 §7、§12；02 §11—§14 | OpenAPI + OWNER/审计 fixtures | OWNER 全路径与幂等恢复 | 待四方签 |
| G0-08 | 补齐工作台/审批/仓库可直接渲染的语义模型 | Gate0 复审 P0-1—P0-8 | 02 §4—§15 | OpenAPI + fields + fixtures | Draft/Me/Approval/DO/AI 完整度测试通过 | 待四方签 |
| G0-09 | 加固身份、信用、别名撤销、审计版本与审批不可删除约束 | Gate0 复审 P0-9—P0-12 | 01 §6、§14；04 schema | DB schema + migration | 空库执行；18 表；约束和 UPDATE/DELETE trigger 验证 | 待四方签 |
| G0-10 | 建立可重现且缺依赖即失败的 Gate 0 验证链 | Gate0 复审 P0-13 | 四方验收 | pinned requirements + PGlite + verify script + log | 0 skip；H1/H5 执行；OpenAPI 正式校验；哈希复核 | 待四方签 |
| G0-11 | 写死条件身份、审批只读范围与 PII token；补齐三个签前 P1 | Revision 2 复审 §3/§5 | 01/02/03 后续对齐 | condition_id + mine filter + mask lexicon + bootstrap + UNIT case + DO customer | 合约/fixture/行为/权限/安全测试全部通过 | 待四方签 |
| G0-12 | 按 AI/前端/数据回执开 gate0-v2：H1 数字语法与小数/金额守卫、H5 v2 与 TEST/CT 分离、候选/客户/DO/别名/库存读模型、保存/价格冲突语义 | AI 回执 A1—A8；前端回执 F01—F17；数据回执 1—4 | 01—04 后续对齐 | 60 个受控文件；新增 `condition-triggers-v2.json`、候选/客户/DO fixture | 41 tests；60 hashes；0 skip | 待四方签 |
| G0-13 | 开 gate0-v3：qty 偏移保长、uom 归一化、金额/编码先掩码、H5 context 词表化、external-inputs 自包含、available_qty/缺货 fixture、referencing 0.31.1 | AI 二轮 N1—N6；前端二轮 F01/F07/F09；数据二轮路径/依赖 | 01—04 后续对齐 | `condition-triggers-v3.json`、`external-inputs/`、72 受控文件 | 42 tests；72 hashes；0 skip | 待四方签 |
| G0-14 | 开 gate0-v4：qty 多候选 AMBIGUOUS_QUANTITY、pack_size 独立取证、逗号小数收紧、uom 复数、H1 v2；clarification 语言、候选示例、parity ROOT | AI 三轮 N7—N9/A1—A6；前端三轮；数据三轮 | 01—04 后续对齐 | `field-evidence-v2.json`、`parse_draft_ambiguous.json`、73 受控文件 | 42 tests；73 hashes；0 skip | 待四方签 |

## 执行顺序

1. 当前 Gate 0：修订并冻结本目录中的机器契约，不改 `01`—`04`，不写业务代码；当前为 `gate0-v4`（draft revision 5）。
2. 四方签字且哈希冻结后进入 P0-A：后端实现与 `01`—`04` v1.3 对齐并行进行。
3. P0-B：H1—H5/H12—H14、批量保存和批准六项硬复核。
4. P0-C：OWNER 全能力、审批详情、审计和回复。

未经四方签字，不创建 `gate0-v4` 标签；任何签后改动必须开启 `gate0-v5`，不得静默覆盖。
