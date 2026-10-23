# AI 六样例与 RunPod 验收 Runbook

日期：2026-10-23  
适用分支：main（含 PR #32/#33/#34）  
不在 CI 执行，不使用真实客户数据。

## 1. 当前状态

```text
PR #32：AI 进程内 adapter + AI_PROVIDER 已合并
PR #33：行外 condition / guard 去重已合并
PR #34：六样例运行器已合并
main CI：407 passed
默认 AI_PROVIDER=auto → Stub
真实 RunPod：未验收
```

RunPod 外部阻塞：

```text
管理 API：worker ready=1 / idle=1
公开 /health（带 Bearer）：30s timeout
公开 /v1/models（带 Bearer）：90s timeout
公开 /health（不带 Bearer）：401，0.51s
```

在 Xiong 确认公开端点恢复 200 前，不要运行真实样例。

## 2. 恢复标准

Xiong 需要先确认：

```text
[ ] Active workers = 1
[ ] worker 内 vLLM 监听 0.0.0.0:8000
[ ] Health Check Path=/health
[ ] GET /health（带 Bearer）→ 200
[ ] GET /v1/models（带 Bearer）→ 200
[ ] /v1/models 的模型名精确等于 Qwen/Qwen2.5-7B-Instruct-AWQ
```

如果只是把 Active 改成 1、但公开端点仍无响应，不要重复请求。

## 3. 本地配置

`.env` 只在本机/Replit Secrets：

```text
RUNPOD_API_KEY=...
RUNPOD_ENDPOINT_ID=...
RUNPOD_MODEL_NAME=Qwen/Qwen2.5-7B-Instruct-AWQ
LLM_TIMEOUT_S=4.1
```

不要设置 `AI_SERVICE_URL` 指向 RunPod；它不是 `/extract` 协议。

真实测试时临时设置：

```powershell
$env:AI_PROVIDER="runpod_adapter"
```

或用 `.env` 中的 `AI_PROVIDER=runpod_adapter`；测试完改回 `auto`。

## 4. 三阶段预检

先用 RunPod 管理 API 只读确认 worker：

```text
GET https://api.runpod.ai/v2/<endpoint-id>/health
Authorization: Bearer <RUNPOD_API_KEY>
```

不要在终端回显 key；使用本机脚本读取 `.env` 或密码管理器注入的环境变量。
管理 API 返回 `ready=1 / idle=1` 只代表平台侧 worker 状态，不等于公开代理已可服务；
公开 `/health` 和 `/v1/models` 仍必须单独返回 200。

公开端点恢复后，依次确认：

```text
GET  /health
GET  /v1/models
POST /v1/chat/completions  {model, messages:[PONG], temperature:0, max_tokens:8}
```

验收：

```text
[ ] 三个阶段 HTTP 200
[ ] /v1/models 返回精确模型名
[ ] chat 返回 PONG
```

## 5. 六样例运行器

命令（从 `backend/`）：

```powershell
.venv\Scripts\python.exe -m tools.run_ai_samples --tenant T1
```

默认读取：

```text
docs/ai_contract/samples/normal.json
ambiguous.json
condition.json
empty.json
multi_candidate.json
multi_line.json
```

写出：

```text
evidence/ai-samples/run-<UTC时间>.json
```

stdout 每个样例：

```text
sample / ai_mode / lines / conditions / ignored_spans / elapsed_ms
```

验收：

```text
[ ] 6/6 有 actual
[ ] 6/6 ai_mode=LLM
[ ] 0 非预期 FALLBACK / MIXED
[ ] errors=0
[ ] evidence JSON 已归档
```

注意：T1 DB catalog 使用 `FAM_TEPUNG` 等 canonical ID；合同样例的
`expected_response` 使用 `FAM_FLOUR` 等合同示例 ID。Runner 保存
`expected` 与 `actual` 供人工对照，不把 family 差异自动判为 LLM 失败；
严格验收是结果存在、`ai_mode=LLM`、无错误。

## 6. 真实 parse 冒烟

六样例通过后，T1/T2 各跑一次：

```text
POST /api/v1/orders/parse-draft
Authorization: Bearer <demo-token>
```

检查：

```text
[ ] 200
[ ] lines 非空（或有明确 UNKNOWN/候选）
[ ] conditions 保留
[ ] ai_mode 为 LLM/MIXED，不能把 fallback 写成 LLM
[ ] /healthz、/readyz 仍 200
```

证据保存到：

```text
evidence/ai-samples/parse-t1-<timestamp>.json
evidence/ai-samples/parse-t2-<timestamp>.json
```

## 7. 收尾

```text
[ ] Xiong 把 Active workers 改回 0
[ ] .env 仍被 Git 忽略
[ ] evidence 不含 key/token/连接串
[ ] 更新 README / 验收表
[ ] 不把真实 AI 写成已验收，直到三阶段 + 6/6 证据齐全
```

## 8. 当前不要做

```text
不要反复重试公开端点
不要在 Active=0 时硬测 4.1s
不要用 curl 把 key 打到 shell history/截图
不要把 sample runner 的 mock 测试当真实证据
不要合并未经 CI 的改动
```
