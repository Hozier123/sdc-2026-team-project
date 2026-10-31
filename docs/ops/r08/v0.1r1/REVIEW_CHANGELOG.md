# R08 v0.1 → v0.1r1 指定修订

原包 95,950 B，SHA-256 5c18e25c6eaa6b1b8df84ab17211a0df379d884e4327c1e6ae53795f2dd8605d；原主稿 34422c0ea0853c93b60adc9150b92a3a510cd87de669921ab850f66c31ab89b8。原稿、原 ZIP 及原回执保留不变，新包另发。

| 来源／条目 | 本次落实 | 修订核对位置 |
|---|---|---|
| Ye A：确定性条件 ID | 按 draft_id/kind/code-point span 生成，当前值 CND_6BAFF2E046E11A9F84B97079；三状态一致 | build_samples.py、verify_samples.py、condition_target 三样例 |
| Ye B：deprecated Issue.source_span | 新 Issue 只输出 span，source_span 仅旧数据兼容；WorkingLine.source_span 保留 | 主稿 §2、全部样例 |
| Ye C：提交版／worktree | 源快照固定 4f95dd8，未把其未提交展示代码当已取得或已发布 | 主稿 §5、回执登记 |
| Zhou P3-1：保存预期 | save_expectation 明确 422/MISSING_TIER_PRICE、NOT_RUN、version_after=1、UNCHANGED | missing_price_after_manual 及 transition 检查 |
| Zhou P3-2：缺价语义分流 | NO_CANDIDATE 只兼容占位；R10 必须消费 problem_kind/explanation；不可消费则另提专用码重新评审 | 主稿 §5、price_route 检查 |
| Zhou P3-3：clerk 入口／配置分工 | ask 改 CLERK；EDIT_DRAFT／目录选 SKU，诊断摘要只读；Zhou 核含义，He 核目标权限并协调有权数据执行人；未获授权继续阻断 | 主稿 §5、缺价样例 metadata |
| Zhou 建议：负例规范 | 六类负例统一 expected.http_status/error_code/behavior 等字段，actual_result=NOT_RUN；正常保存也有 save_expectation | 全部 negative／after_manual 样例 |
| Xiong：R07 当前状态 | 按用户转交登记一次 03:28 live preflight，v2 证据、P-2 未签；未取得独立原件，不写“无 live／无模型 JSON” | 主稿 §2.7、CURRENT_STATUS.json |
| 跨平台解包 | 新包所有路径 ASCII，内容 UTF-8；原包编码及收件环境报告并列记录 | ZIP 文件名检查、回执登记 |

这些是已完成的修订，不等于 Ye／Zhou 已核补件闭合。保留原合同 PASS／样例有条件 PASS／消费有条件通过和 Xiong 边界接收；R08 仍待补件闭合后冻结，不重置为“三方尚未审核”。

R10 五项展示待办仍待实现；R09 运行时及 R11 验证仍 NOT_RUN。本版没有执行配置、模型或业务写入，不改变 E 项成绩、P-2 或 C13 分工。
