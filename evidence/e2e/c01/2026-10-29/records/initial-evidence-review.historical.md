# C01 / C07 材料核对（2026-10-29）

依据：用户 Records.txt、c01_session.har（118 条请求）、8 张截图。仅审查所给材料，未重跑订单、修改库存或向他人发消息。

## 验收结论

| 项目 | 结论 |
|---|---|
| C01 真实网页业务闭环 | PASS，FALLBACK + 人工确认路径 |
| LLM 真实推理 | 本批材料未通过，两个 parse 均为 FALLBACK |
| C07 重复批准 | 有 409 截图及未重复审计的支持证据；业务错误码与 request_id 待补 |
| C07 隔离 PostgreSQL 并发专项 | 本批材料未提供，不据此判通过 |

## C01 请求链与金额库存

身份：T1 / USR_T1_CLERK。草稿：`DRF_39D4D66CACC440A594B1C1AEBEF151B9`。DO：`DO_20261029_453C4BC2`。

| UTC+8 时间 | 行为 | 结果 |
|---|---|
| 15:09:53 | 解析 Tepung 4 bag / Minyak 2 btl | HTTP 200，FALLBACK；规格歧义 + 同日订单阻断 |
| 15:10:04 | 选择 1kg 面粉并保存 v2 | HTTP 200，剩余 SAME_DAY_ORDER |
| 15:16:53 | 将本单确认为原 DO 的 Separate add-on，保存 v3 | HTTP 200，READY_FOR_APPROVAL，阻断列表清空 |
| 15:16:58 | CLERK 批准 v3 | HTTP 200，DIRECT，生成目标 DO |
| 15:20:21—15:20:43 | 新草稿读取相同商品的当前库存 | 面粉 27 bag，食用油 21 btl |
| 15:23:47 | 查看目标 DO 审计 | SAVE_LINES 两条，APPROVE、INVENTORY_DEDUCT 各一条 |

parse request_id：`ca57c454-bf64-4868-941a-a3797858b392`；approve request_id：`1ff33119-afa7-4d04-bf33-33f9f880e9a1`，均与 TXT 对上。

| 商品 | 数量／单位 | 等级单价 | 小计 | 库存变化 |
|---|---|---|---|---|
| SKU_TEPUNG_1KG，面粉 1kg | 4 bag | RM3.20 | RM12.80 | 31 → 27 |
| SKU_MINYAK_5KG，食用油 5kg | 2 btl | RM29.00 | RM58.00 | 23 → 21 |

总额 RM70.80，与网页、批准响应和 DO 一致。库存差额分别为 4 和 2；目标 DO 的审计只见一次批准和一次扣库存。库存后值来自批准后的新草稿，时间早于 C07 重复请求；因此不能单靠库存截图证明重试后库存仍不变。

记录措辞修正：本次输入单位是 bag、btl，和所选商品一致；“不是 ctn”不是本次缺陷。“无黄色阻断提示”应限定在解决规格歧义和同日追加、保存到 v3 后；baseline 截图是 v2，仍有同日订单卡。此例包含人工确认，不能写成 LLM 一次解析无歧义。打印截图证明打印预览正常，未单独核验已保存的 PDF 文件。

## C07 的准确证据边界

15:22:10 的 HAR entry 109 确实对同一已批准草稿再次 POST approve，body 为 expected_version=3。但 HAR 记录 status=0 / net::ERR_FAILED，无响应头、无响应体、无 X-Request-ID。两张额外截图显示 409，所以保留为屏幕证据；不能补造 HAR 中不存在的 409 或 ALREADY_APPROVED 等错误码。

15:23:47 的审计发生在重试之后，仍只见 APPROVE、INVENTORY_DEDUCT 各一次，支持本单没有再次记账。严格补证只需关联清楚的一次重复请求：完整 URL、409 响应 JSON 的业务错误码、X-Request-ID，以及重试后的唯一 DO / 扣库存记录。隔离 PG 并发专项另附实际运行结果。

## AI 下一步

本 HAR 的 /ai/wake 在 15:09:06 返回 HTTP 200，但 accepted=false，message 为 “AI endpoint not configured; no wake request was sent.”，表示没有向 RunPod 发送预热请求。状态灯读 AI_HEALTH_URL / AI_SERVICE_URL，wake 还读 AI_WAKE_URL；parse 使用 RUNPOD_*，两套配置分离。

已有 12:39:23.31 的部署日志证明解析请求在 4149.6ms 后进入 RunPod 请求失败／超时分支；本批 15:09、15:20 都仍是 FALLBACK，但没有新增服务器日志，不能替这两次请求断言同一根因。

先由 Xiong 在 RunPod 控制台核 worker、端点可达性、排队／冷启动并完成一次真实最小推理，给出可测试窗口。He 在该窗口只复测一条真实 parse，记录新的 ai_mode 和 request_id；LLM 成功后再形成新的 LLM 证据。状态灯／预热需由后端适配当前 provider，不能只改文案假装 READY。

可转发的交接文字见 [Xiong-message.txt](Xiong-message.txt)。原始请求的精简脱敏摘录见 [selected-network-evidence.json](selected-network-evidence.json)，源文件哈希见 [source-manifest.json](source-manifest.json)。
