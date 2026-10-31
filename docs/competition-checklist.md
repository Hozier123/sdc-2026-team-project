# 参赛提交检查清单

更新日期：2026-10-25。材料核查基线：`main` 提交 `4250ae6840bc5b4dae63a0d4df6c7fcc27e8bd50`。

> **2026-11-01 Phase 2 材料更新**：决赛签字版 Final Solution Report、Updated PRD 和 Tools Declaration 已替换到 `submission/`，当前索引与 SHA-256 见 [submission/README.md](../submission/README.md)。本清单的核验日期与勾选状态仍为 2026-10-25 Phase 1 基线；下文表格中的 Phase 1 旧文件名已失效，材料入口以索引为准。

**当前状态：实际代码、正式提案、工具声明和 Pitch deck 已入库，演示视频已登记，仓库已公开。这里不再是目录模板清单；但材料入库不等于官网提交成功，也不等于完整业务验收通过。**

勾选只表示该项明确描述的事实已有证据；未核实的访问效果、视频时长、官网提交和质量验收不自动勾选。

## 项目与代码

- [x] 项目：KiraOrder for Orbyte；报名队名：**Falcons**。
- [x] 队长：Zhou Jingxi；学校：Xiamen University Malaysia；赛道：Domain 2 — Orbyte Smart SME Challenge；SDG 8（8.2、8.3）。
- [x] 成员分工已填写在[根 README](../README.md#project-information)：He Minghao（后端、规则、部署）、Xiong Peicheng（AI、RunPod、部署）、Ye Lianghui（前端）、Zhou Jingxi（数据、质量、评测）、Zhan Zhengrong（手工基线、材料、提交整合）。
- [x] 真实前后端代码、种子、测试、证据和工作文档已入库，不再是空目录占位。
- [x] [后端运行说明](../backend/README.md)、[前端运行说明](../frontend/README.md)及根 README 已提供当前依赖、配置和启动方式。
- [x] 保留 Apache 2.0 LICENSE 与开发提交历史。
- [x] `.env.example` 仅提供配置项、非敏感默认值和空密钥项；真实 `.env` 被忽略，不进入提交包。

## 正式材料与入口

正式文件索引和 SHA-256 见 [submission/README.md](../submission/README.md)。下列三份文件已存在，文件哈希与该索引一致；签字日期等材料说明沿用该索引，不代表本清单重新完成了内容或签字审查。

| 材料 | 当前状态与入口 |
| --- | --- |
| 正式提案（Phase 1） | 已入库：[SDC2026_Falcons_Preliminary.pdf](../submission/SDC2026_Falcons_Preliminary.pdf)；签字日期 2026/10/25。Phase 2 决赛报告见 [SDC2026_Falcons_Final.pdf](../submission/SDC2026_Falcons_Final.pdf) |
| 技术与工具声明 | 已更新为 [15 页决赛签字版](../submission/SDC2026_Falcons_TechDeclaration.pdf)（2026-11-01）；Phase 1 的 17 页版仅存 Git 历史 |
| 更新版 PRD（Phase 2） | 已入库：[SDC2026_Falcons_PRD.pdf](../submission/SDC2026_Falcons_PRD.pdf) |
| Pitch deck | Phase 2 入口：[SDC2026_Falcons_PitchDeck.pptx](../submission/SDC2026_Falcons_PitchDeck.pptx) · [HTML](../submission/SDC2026_Falcons_PitchDeck.html)；旧的 `KiraOrder_Falcons_PitchDeck_SDC2026.pptx` 已不在当前材料中 |
| 路演与原型演示视频 | 已登记：[YouTube 视频](https://youtu.be/TyrASSJDIpM)；本次未重新核验播放权限、时长和内容 |
| 当前前端入口 | 已登记：[GitHub Pages](https://hozier123.github.io/sdc-2026-team-project/)；旧 Replit 前端不是最终评审入口 |
| 后端服务 | 已登记：[Replit API](https://kiraorder-api.replit.app/api/v1)；[就绪检查](https://kiraorder-api.replit.app/readyz) |
| 平台使用证明 | 材料索引说明已纳入工具声明附录 B–D；原始证明见 [evidence/](../evidence/) |

- [x] `submission/` 已使用正式文件替换原来的空白提案和两份 EXAMPLE ONLY 证明页；旧文件仅留在 Git 历史，不是当前提交材料。
- [x] README 已登记正式提案、工具声明、幻灯片、视频和服务入口。
- [x] Replit、RunPod、AI 和第三方工具使用情况已有声明，不能把离线降级描述为持续在线 AI。

## 评审访问与安全

- [x] 仓库当前为 **Public**（2026-10-25 通过 GitHub 仓库元数据核验），不再保留“待转公开”的操作步骤。
- [x] 已有 [2026-10-24 提交审查记录](ops/submission-audit-2026-10-24.md)：当时的已跟踪文本及 evidence 扫描未发现真实凭据；该结果不等于完整历史、后续新增文件和二进制附件均已复审。
- [ ] 用未登录环境核验仓库材料可下载、视频可播放、原型可访问，并在评审期保持访问条件；本次未完成这一整套核验。
- [ ] 对最终提交包、最新附件及 Git 历史完成最终敏感信息复核，不把旧扫描结果扩展为本次全部文件已通过。

**组委会账号：不适用。**经 He Minghao 于 2026-10-25 确认，无需添加组委会 GitHub 账号，因此不再列为待办或待核验事项。仓库保持 Public，评审材料的可访问性仍按上述清单核验。本次未添加、删除或变更任何账号权限。

打包时排除真实 `.env`、`.tmp/`、`.venv/`、缓存、私有 TEST32 答案及其他不应公开的核验材料；具体范围沿用上述审查记录。

## 截止时间与官网提交

**统一采用本次核验的官方公开页面口径：2026-10-25 上午 07:59 MYT（UTC+8，与北京时间相同）。** [赛事首页](https://sdchack.my/)和[官方 FAQ](https://sdchack.my/faq)在 2026-10-25 均显示该时间。本清单删除旧的晚间截止说法，不再保留两个并列时限；页面未给出秒数，本清单不自行补充。

如组委会另有更新的书面通知，以该通知为准并保存来源；不能自行假定获得延期。[官方 FAQ](https://sdchack.my/faq)说明，截止后的提交更改须以组委会另行公告为前提。

- [ ] 由队长登录[官方 Team Portal](https://sdchack.my/login)，核对并提交正式 PDF、仓库及所需材料链接；仓库内尚未见本队提交成功的回执，不能标为已提交。
- [ ] 保存提交编号／成功页面或确认邮件、提交时间，以及实际提交版本和文件哈希。
- [ ] 核对门户中的文件和链接与上述正式材料一致。是否获准补交或截止后修改，须有官方依据。

**GitHub 发布、文件签字和材料齐备均不能替代官网成功回执。此处的未勾选表示尚无可核验的完成证据，不直接断言队伍从未提交。**

## 与材料齐备分开的验收边界

按本次核查基线的 README，以下状态仍需如实保留，不随材料上传自动变成 PASS：

- TEST32 的 12 个 workflow 用例仍为 `NOT_RUN`，完整 E2E 尚未完成。
- 独立 UAT 与真实用户试用记录尚未完整验收。
- AI-only 23/23 LLM 调用记录不等于准确率完成；准确率仍为 `NOT_COMPUTED`，UOM 为 24/31、7 项已知缺口。
- RunPod 最近归档状态为 `Active=0`，公开解析走 fallback；本次未新测在线状态，不能声称持续可用的实时 AI 演示。

后续状态只能根据实际测试、平台状态或提交回执更新；不得通过勾选清单消除已知限制。
