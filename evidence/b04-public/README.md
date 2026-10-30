# B04 公开签收摘要

2026-10-30。后端交付人 He，独立复验人 Zhou Jingxi。本文件根据经用户转交并已本地归档核对的报告/证据生成，不是新的第三方签名或重新执行结果。原始文件与完整个人/环境路径记录不在公开仓库发布。

## 最小交接与补件

Zhou 在独立 venv 和回环 PostgreSQL/API 中完成一次真实 direct 流程与 DB 核对，实际模式 FALLBACK；另完成 mock 启动和一个预期 FAIL、可定位的负例。最小交接满足原 B04 验收条件。后来补回的 58 个原始文件全部匹配先前大小/哈希清单，没有用新清单代替旧依据。

T1 direct：白糖库存 35→33，其余 39 SKU 不变；DO 总额 RM6.00；SAVE_LINES、APPROVE、INVENTORY_DEDUCT 各一次，最终 DO_GENERATED / version 2。负例有保存后的草稿，没有 DB 快照，不独立声称无副作用。T1 其余三路线的 Zhou 独立执行不由此推导。

## T2 独立四例

| 路线 | 核心 HTTP/DB | 实际 AI 模式 | 库存 | DO |
| --- | --- | --- | --- | --- |
| direct | API_PASS / PASS | FALLBACK | 25→23 | RM18.00 |
| owner-approve | API_PASS / PASS | FALLBACK | 23→21 | RM17.00 |
| owner-reject | API_PASS / PASS | FALLBACK | 21→21 | 无 DO |
| stock-blocked | API_PASS / PASS | FALLBACK | 21→21 | 无 DO，批准 400 |

46 项源码/种子/case 哈希与当时交付快照匹配。顺序重复批准为 409 ALREADY_APPROVED，两项跨租户读取为 404；核心原始库存/DO/审计/状态及请求绑定离线核对通过。

5 项 REVIEW 保留：四例的保护侧 T1 未变，以及重复批准后库存/DO/审计未变，缺少成对原始 after/retry DB 快照。存在响应记录和执行人断言不等于这些缺失快照已被独立重算。

环境报告为 PostgreSQL 17.9、EUC_CN cluster / UTF8 业务库；开发侧用 17.10，版本差异保留。历史服务均已停止，不是现在的接入入口。以上独立试次未连接公开 API、未调用 GPU、未使用 MockTransport。

## 配合材料与正式范围

映射准备与完整附件补审准备级通过：18/18 payload 文件、10/10 原映射文件匹配，14 条台账 schema 校验 0 错误。独立整包复算因复验方缺 ZIP 本体未完成，不把文件级检查写为整包验签。

v5/scorer 等私密资产已收并完整哈希匹配，仍保留 draft/PENDING_INDEPENDENT 和外部冻结未生效状态。正式预期绑定、证据 schema 加固及执行由 D03 统筹；正式 execution 仍 NOT_RUN。B04 签收不覆盖 B05 隔离/复位、并发专项、前端/公开部署或正式评分。

## 公开工具验证

本交付分支在最新 main 基础上运行 83 项离线测试通过（驱动 35，核验器 48），Ruff 与格式检查通过。没有因此重跑真实 API/DB/GPU。

发布的 `backend/tests/fixtures/b04-audit-direct.zip` 仅为公开 canonical seed 的合成 DEV 测试数据，供损坏副本测试；没有角色会话、冻结答案或 Zhou 私有回包。数据来源在 fixture 的 PROVENANCE.md 中说明。

[结项摘要 JSON](closeout.json) · [B04 结项记录](../../docs/ops/b04-closure.md)
