# KiraOrder Gate 0 签字与冻结记录

> 当前状态：`AWAITING_CROSS_FUNCTIONAL_SIGNOFF` / `gate0-v4`（draft revision 5）  
> 本文件不代替真实确认；没有姓名、时间和确认方式的行一律视为未签。
> `gate0-v3` 已被本次三岗回执修订取代；签字对象以新的 `gate0-hashes.txt` 为准。

## 签字表

| 角色 | 姓名 | 确认范围 | 状态 | 时间 | 证据 |
|---|---|---|---|---|---|
| 后端 | He Minghao | schema、fields、errors；授权按推荐值制作 Gate 0 | 待最终哈希确认 | — | 当前会话中的执行授权 |
| 前端 | — | 成功/错误体、字段、`X-Request-ID` | 待确认 | — | — |
| AI | — | qty/int、fam=`UNKNOWN`、H1/H5 | 待确认 | — | — |
| 数据 | — | seed、物理表名、词表、TEST-01—32 | 待确认 | — | — |

## 评审清单

- [x] manifest 中所有输入文件的哈希、行数、字节数已实测核对
- [x] schema 含表清单、关键列、唯一约束、append-only 与不可变触发器
- [x] fields 覆盖 Issue、WorkingLine、OrderDraft、Approval、DeliveryOrder
- [x] errors 覆盖 400/401/403/404/409/422/429/503 及旧码映射
- [x] H1 有 qty/uom/family 词表、8 条规则和失败映射
- [x] H5 有 16 行真值表、触发词表、负例与 `price_basis=UNIT` 正向例
- [x] H1/H5 真值用例由确定性 oracle 实际执行，不只是检查 JSON 数量
- [x] OpenAPI 含 16 个契约路径并通过 OpenAPI 3.1 正式校验器
- [x] `OrderDraft/DraftSummary/Me/Approval/DO/AI` 的前端完整度由机器测试锁定
- [x] fixtures 不少于 8 个且请求/响应全部通过 Draft 2020-12 schema 校验
- [x] `0001_baseline.sql` 已在空 PGlite PostgreSQL 运行时执行（18 张表；审批 UPDATE/DELETE trigger 均存在）
- [x] Python/Node 依赖版本已固定；验证缺依赖直接失败，无 skip
- [x] 传递依赖已 pin：`jsonschema-path 0.3.2`、`pathable 0.4.1`、`openapi-schema-validator 0.6.3`
- [x] 干净目录不带 `-SkipInstall` 执行 bootstrap：42 passed / 0 skipped / 73 hashes
- [x] bootstrap 支持 `GATE0_PNPM`/corepack/npx 与 `GATE0_WHEELHOUSE` 离线兜底
- [x] `users.demo_token_hash`、CreditFlag 枚举、alias active/revoke、actor_role、field diff 版本/原因已落入 DDL
- [x] `condition_id` 的生成算法、格式与稳定键已写死并由 fixture 测试
- [x] CLERK 审批读取仅限本人、无决定动作；越权详情按 404
- [x] PII token 唯一词表为 `[REDACTED_PHONE]/[REDACTED_MYKAD]/[REDACTED_EMAIL]`
- [x] 一键 bootstrap、H5 UNIT 正向用例和 `DeliveryOrder.customer_name` 已补齐
- [x] `01`—`04` 与 v2.1 原文件未被本次操作修改
- [x] gate0-v4 最终输出哈希已重算并完成独立复核
- [x] AI A1—A8、前端 F01—F17、数据 1—4 回执项已处置
- [ ] 后端对最终哈希签字
- [ ] 前端签字
- [ ] AI 签字
- [ ] 数据签字
- [ ] 创建并推送 `gate0-v4` 标签

## 冻结规则

四方确认完成前，不进入业务代码阶段，也不创建 `gate0-v4` 标签。签字完成后把姓名、时间、证据与最终哈希补入本文件；若采用“24 小时无异议”，必须附群消息时间和截图路径。冻结后改动必须开启 `gate0-v5`。

## 冻结后的动作顺序

`Gate 0 签字 → P0-A（后端实现与 01—04 v1.3 同步）→ P0-B（H1—H5、批量保存、批准硬复核）→ P0-C（OWNER、审计、回复）`。

## 签字后的冻结命令（在包含 Gate 0 的仓库根执行）

Gate 0 目录本身不是 git 仓库；请把整个 `Gate 0/` 放进项目仓库后执行：

```powershell
$hash = (Get-FileHash "Gate 0\docs\gate0-hashes.txt" -Algorithm SHA256).Hash
git add "Gate 0"
git commit -m "Gate 0 v4 closeout: 42 tests, 73 hashes, clean bootstrap"
git tag -a gate0-v4 -m "Gate 0 v4; gate0-hashes SHA256=$hash"
git push
git push --tags
```

签字前不得执行以上命令；`gate0-v4` 一旦推送，任何改动都必须开 `gate0-v5`。

