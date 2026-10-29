# 原始记录与复核文档附注

本目录保留原始记录和 Zhou 最新复核文本的原字节，不把历史描述改写成新实测。

- CLERK 输入为 `Tepung 4 bag / Minyak 2 btl`，对应单位是 bag / btl；原 Records 中“单位是 ctn❌”属于记录措辞问题，不是本单单位错误。
- “无阻断”仅适用于处理规格歧义及 SAME_DAY_ORDER、保存到 v3 后；baseline 是 v2，仍有同日订单提示。
- OWNER TXT 的 17:04 为整理时间口径；网络实际操作为 16:48—16:56（UTC+8）。WAREHOUSE 操作为 17:13—17:16，整理时间 17:22。
- `records/initial-evidence-review.historical.md` 是最初只收到部分材料时的历史审查，不覆盖 Zhou 最新定稿。
- 最新 02 的结尾仍有一处“声明级”旧文字，最新 02 的第1项、05 完整 HAR 复核及 Zhou 最终统一回复均明确为“实物级”。本索引依最新最终结论登记；不改写 reviewer 原件。
- 04 的材料表把 WAREHOUSE PNG 写成4张；实际归档为5张，包含两张 /me 截图。逐文件映射与哈希见 artifact-manifest.json。
- 原 reviewer 清单包含 Zhou 工作区内自行生成的 SHA256.txt 和发送说明。本机归档保留其声明哈希，不根据哈希伪造这些文件内容。
- 409 裁剪截图属于支持性历史屏幕材料；原 HAR entry 109 仍是 status=0 / net::ERR_FAILED，无错误 JSON 或请求编号。C07 继续单独待验收。
