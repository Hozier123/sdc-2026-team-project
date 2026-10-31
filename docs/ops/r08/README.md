# R08 已审核接口归档

**R08-CONTRACT-v0.1r1 的接口定义、语义、样例及指定修订已完成本轮审核；正式冻结／结项待下游实现与运行验证。**

本目录是供R09／R10使用的已审接口参考。R08负责最终OrderDraftResponse（wire OrderDraft）的WorkingLine／Issue等约定；RawExtraction／RawRow只作R09接R07的上游边界。

## 从这里开始

- [接口主稿 v0.1r1](v0.1r1/CONTRACT_v0.1r1_REVIEW.md)
- [18份接口样例](v0.1r1/samples/) ／ [样例索引](v0.1r1/SAMPLE_INDEX.json)
- [v0.1到v0.1r1修订说明](v0.1r1/REVIEW_CHANGELOG.md)
- [最新审核摘要](status/REVIEW_SUMMARY_v001_20261101T042513UTC8.md)
- [当前分阶段状态](status/STATUS_R08_r1_v001_20261101T041551UTC8.json)
- [R08结项范围与依赖判断](status/R08_CLOSEOUT_ASSESSMENT_r1_v001_20261101T041551UTC8.md)

## 固定审核对象

[原v0.1r1审核ZIP](v0.1r1/archive/R08_CONTRACT_v0.1r1_REVIEW_20261101.zip) ／ [ZIP SHA-256](v0.1r1/archive/R08_CONTRACT_v0.1r1_REVIEW_20261101.zip.sha256)

文件大小109,878 B，完整SHA-256：

27c9aaa335edbaaa4a57ce1f4f2dbf450f38428ed33f9c29f7e1a261de625381

主稿、18份样例、修订说明及原ZIP均逐字节归档，没有为GitHub修改已审内容。archive/ORIGINAL_PACKAGE_SHA256SUMS.txt的39项路径指ZIP内部成员，不是本目录的文件清单。本目录发布文件另有带版本／时间戳的SHA256SUMS_PUBLISHED清单和ARCHIVE_INDEX。

## 当前完成范围

- Zhou：合同语义PASS，r1接口样例PASS；样例仅为INTERFACE_SAMPLE / NOT_LIVE。
- Xiong：r1接口边界可接收、无新异议；R07仍是TESTED_OFFLINE + one live preflight observed (v2 evidence; P-2 not signed)，不签R07验收或P-2。
- Ye：指定修订与clerk入口在wire／动作层闭合，消费审核仍CONSUMABLE_WITH_MODIFICATIONS，待R10实现五项展示功能。
- R09负责后端实现及保存／批准约束；R11负责相关真实独立验证。R08暂不登记FROZEN／CLOSED，没有新增E01–E09或R11通过结论。

R09和R10可按本版本推进；最终验证后补消费限制解除与R08冻结记录。若接口未变不重做整轮接口审核，变更接口时另出有区别的新版本。

## 工件与历史状态

v0.1r1/validation为原离线检查记录：18样例、7项破坏检测、TypeScript wire exit 0；原包内另含复现脚本和固定源码快照。当前GitHub归档只校验复制、哈希、JSON和链接完整性，没有新运行应用或模型。

原包中的早期待审状态原字节保留；以上最新回执状态优先作为本轮审核记录。样例客户、SKU、金额、库存、时间和ai_mode均为人工wire示意，不能摘作实测模式或R05答案。

归档版本：R08-GITHUB-ARCHIVE-v001_20261101T042513UTC8。合同仍为v0.1r1；后续审核状态补充使用独立版本和时间戳，不覆盖已审合同。
