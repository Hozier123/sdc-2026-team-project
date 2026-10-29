# B01 / C01 parse：真实热态联调通过

窗口：2026-10-29 22:45–23:15（UTC+8）。API 为已发布 Replit 后端，使用现有 T1 CLERK 会话和真实 RunPod；未模拟模型响应。

应用版本 `555f0fa669ac40e2d7b9d9ceacdbfb6d24301127`，Replit 发布记录 `7c492845`；前端保持 PR #68 的已发布版本。

| 最终测试 | 时间 UTC+8 | HTTP / 模式 | 耗时 | request_id |
|---|---|---|---|---|
| B01 简单单 | 23:03:58.558 | 200 / LLM | 2176.5 ms | b01-4a6d8686d3d34821956f9e02efb5f2ec |
| C01 原输入 | 23:04:01.399 | 200 / LLM | 2363.1 ms | b01-ccd64e68d2c04b60a6bae111e9b522b7 |

最终 wake：`b01-97cf5c0cfc5241a8a323c77e009a8b48`，返回 accepted=true / WARMING；随后状态 `b01-9072fa6999e14b3e848356def3553d28` 在解析之前已为 READY，两条解析后也都是 READY。

## 结果与修正

RunPod 公共端点的 `/health`、`/v1/models` 和真实合成抽取均成功，精确模型为 `Qwen/Qwen2.5-7B-Instruct-AWQ`。
初轮两条 parse 已为 LLM，但独立预热把模型的 `pack_size=""`（没有规格）误判为无效。
[PR #70](https://github.com/Hozier123/sdc-2026-team-project/pull/70) 只把 RunPod 探测中的空规格归一化为 null，保留模型、span、family、数量、单位和非空规格检查。39 项状态回归和全量 CI（后端 470、前端 59）通过；修正版本已发布并完成上表复测。

修正版本的第一次手动 wake 遇到真实 429 / Retry-After=45，该轮两条解析仍是 LLM；按限流等待后，最终轮完成 wake→READY→parse。原始记录保留在各自 runs 目录，不混为一轮连续运行。

白糖正确解析为 `SKU_GULA_1KG`、2 bag、1kg、RM6.00。C01 原输入 `Tepung 4 bag
Minyak 2 btl` 的数量/单位正确；面粉继续保留规格歧义，油为 `SKU_MINYAK_5KG`、2 btl、RM58.00。同日订单阻断保持，未因模型成功而自动放行。

## 实际副作用与范围

三轮共创建 6 个合成草稿；6/6 parse 为 LLM，FALLBACK=0。未保存人工修改、未批准、未生成新 DO、未扣库存，也未复位数据。草稿编号完整列于 acceptance-summary.json。

本记录覆盖 B01 热态预热/状态/解析，以及 C01 原输入的真实 API 解析；不替代新一轮完整 LLM 审批闭环、冷启动故障测试、TEST32 或识别准确率评分。原有 C01 FALLBACK + 人工确认的历史验收不改写。worker 启停仍由 Xiong 负责，推理调用已于 23:04:04 前结束。

## 证据

- `acceptance-summary.json`：版本、模式、请求编号、实际副作用和范围。
- `runs/`：三轮逐请求时间、脱敏请求、实际响应及原始判定。
- `diagnostics/`：200 健康/模型/最小抽取、空规格原始结果、本地修正后真实探测和 CI 链接。
- `final-business-checks.json`：最终解析字段和阻断核对。
- `SHA256.txt`：本目录逐文件校验；本地已扫描全部六角色令牌及配置中的密钥、连接串，无命中。

不含 Authorization、真实 token/key、私有连接串、原始私密会话文件或包含余额的用户参考截图。
