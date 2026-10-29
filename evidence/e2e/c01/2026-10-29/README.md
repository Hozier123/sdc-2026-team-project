# C01 最终收尾：PASS（降级业务验收）

复核人：Zhou Jingxi；日期：2026-10-29。对应 DO：`DO_20261029_453C4BC2`；草稿：`DRF_39D4D66CACC440A594B1C1AEBEF151B9`，v3。

**C01 的业务面、角色网页证据和材料完整性均通过；完整原始 HAR 已实物级绑定。历史模式为 FALLBACK。** 本次归档不新增业务测试，不改变历史运行结果。

## 验收结果

| 检查 | 已复核结果 |
|---|---|
| 真实网页业务链 | 解析 → 人工选择规格 → 确认同日追加 → 保存 v3 → CLERK 直接批准 → DO → 库存 → 本单审计 |
| 商品与金额 | 面粉 1kg，4 bag × RM3.20 = RM12.80；食用油 5kg，2 btl × RM29.00 = RM58.00；合计 RM70.80 |
| 库存 | 面粉 31→27；食用油 23→21 |
| 审计 | SAVE_LINES×2，APPROVE×1，INVENTORY_DEDUCT×1 |
| OWNER | 真实 /me 200：T1 / OWNER；同一 DO 及审计查询 200 |
| WAREHOUSE | 真实 /me 200：T1 / WAREHOUSE；同一 DO 拣货查询 200；仅返回 do_number / customer_name / items / approved_at |
| 仓库字段与页面 | 无价格、金额、电话、原消息；customer_name=Restoran Ali 是允许的合成客户名称；页面只读，HAR 无写请求 |
| 完整源 HAR | 118 条请求；1,273,472 字节；12 条摘录索引与源文件 method / URL / status 逐条匹配 |

原始完整 HAR 的 SHA-256：

```text
24D15F599373EAC4591276C414ABF148F6DE67F8CE1B006220EA5DB8BD5BFCA3
```

## 文件入口

- [机器可读验收结论](acceptance.json)
- [Zhou 最新完整 HAR 复核](reviews/05-Zhou-complete-HAR-review.md)
- [Zhou 角色补判](reviews/04-Zhou-role-review.md)
- [Zhou 结论与历史追加](reviews/01-Zhou-C01-review.md)、[更新清单](reviews/02-Zhou-evidence-checklist.md)、[reviewer 原附件哈希清单](reviews/03-Zhou-attachment-hashes.txt)
- [CLERK 完整会话公开脱敏副本](network/clerk.redacted.har)、[OWNER 会话副本](network/owner.redacted.har)、[WAREHOUSE 会话副本](network/warehouse.redacted.har)
- [12 条请求摘录公开副本](network/selected-network-evidence.redacted.json)
- 原记录：[CLERK](records/clerk.txt)、[OWNER](records/owner.txt)、[WAREHOUSE](records/warehouse.txt)；措辞和历史差异见 [附注](RECORD_NOTES.md)
- 截图：[CLERK](screenshots/clerk/)、[OWNER](screenshots/owner/)、[WAREHOUSE](screenshots/warehouse/)、[历史补充屏幕材料](screenshots/supporting/)
- [逐文件源字节／公开副本映射](artifact-manifest.json)、[源文件声明](provenance/original-source-manifest.json)、[公开脱敏说明](redaction-report.json)、[本目录 SHA-256](SHA256.txt)

## 哈希与公开副本口径

原件在本地最终归档包中按原字节保留，原始完整 HAR 的实物级审核结论和哈希不变。GitHub 的 HAR／网络摘录是明确标记的公开脱敏衍生文件，清除了非必要连接信息、联系字段和本机路径，其 SHA 与原始 HAR 不同；映射见 artifact-manifest.json。公开副本保留全部118/11/8条会话条目、业务结果、源条目索引及请求编号。

本目录的 `.gitattributes` 禁止文本换行转换，SHA256.txt 按归档／Git blob 的精确字节计算。该文件不自我哈希。源 reviewer 文本及截图保持原字节。

## 验收边界

C01 是 **FALLBACK + 人工确认** 的真实业务验收，不是 LLM 成功推理证明。C07（409 响应／业务码／请求编号与隔离 PG 并发专项）仍单独待验收；本次不改变其状态。T2、B04、Gate E、正式 TEST32 不由本目录宣告通过。仓库写接口禁止的口径采用页面无入口、permissions=[]及无写请求的只读证明；没有新增写接口403实测。
