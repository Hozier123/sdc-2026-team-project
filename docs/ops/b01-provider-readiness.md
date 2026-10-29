# B01：统一 provider 配置、状态和预热

日期：2026-10-29。交付范围是本地实现与无 GPU 回归；真实 RunPod 验收另行留证。

## 配置与行为

应用启动时只解析一次 `AiRuntimeConfig`，解析器和 `AiOrchestrator` 共用该配置。

| Provider | 解析、探测与预热来源 |
|---|---|
| `runpod_adapter` | `RUNPOD_ENDPOINT_ID` 派生同一 origin 的 `/health`、`/v1/models`、`/v1/chat/completions`；统一使用 `RUNPOD_API_KEY` 和 `RUNPOD_MODEL_NAME`。忽略其他 provider 的 `AI_SERVICE_URL/AI_HEALTH_URL/AI_WAKE_URL/AI_API_KEY`。 |
| `http` | 使用 `AI_SERVICE_URL/AI_API_KEY`；仅在显式配置时读取 `AI_HEALTH_URL`、调用 `AI_WAKE_URL`。不对 extract URL 猜测 GET 或 wake 协议。缺少 service URL 时启动报错。 |
| `stub` | 不联系上游，状态 OFFLINE，wake 的 accepted=false。 |
| `auto` | 保留原选择语义：配置 `AI_SERVICE_URL` 才选 HTTP，否则 Stub。即使有 RUNPOD 凭据，也必须显式选择 `runpod_adapter`。 |

RunPod 的最小部署配置（真实值只存本机私有配置或 Replit Secrets）：

```text
AI_PROVIDER=runpod_adapter
RUNPOD_API_KEY=<private>
RUNPOD_ENDPOINT_ID=<endpoint-id>
RUNPOD_MODEL_NAME=Qwen/Qwen2.5-7B-Instruct-AWQ
LLM_TIMEOUT_S=4.1
AI_WARMUP_TIMEOUT_S=180
AI_READINESS_TTL_S=60
AI_WAKE_RATE_LIMIT_S=60
```

`LLM_TIMEOUT_S` 是正式解析的超时；`AI_WARMUP_TIMEOUT_S` 是后台预热步骤共享的剩余时间预算。
普通状态探测每次请求最多 2.5 秒。`AI_WARMUP_GRACE_S` 仍可被旧配置接受，但不再用经过
多少秒来推断模型就绪。所有配置都在启动时固定，修改 Secrets 后应通过正常发布加载新配置。

## 状态语义与前端兼容

现有 AiStatus/AiWakeResult 字段、权限、请求编号和 429 响应形状保持一致。

| 状态 | 含义 |
|---|---|
| OFFLINE | Stub，或上游当前不可连接／超时。 |
| WARMING | 后端已经受理后台验证任务，尚无最终结果。 |
| DEGRADED | 鉴权失败、限流、服务错误、模型不匹配、推理无效，或推理证据尚未取得／已经过期。健康 200 本身也只能证明可达。 |
| READY | 精确模型检查通过，并有最近 `AI_READINESS_TTL_S` 内的有效推理证据。HTTP 兼容模式以其有效抽取证明可用，不能宣称已核验 RunPod 模型身份。 |

`accepted=true` 表示后端受理任务，不能据此显示“模型已经就绪”或“GPU已开启”。前端继续
读取 status，直到得到结果。`available_modes` 仅在 READY 时包含 LLM；订单上的 `ai_mode`
始终保留该次实际抽取模式，不能因为后来的恢复改写历史 FALLBACK。

前端补上预热期间的状态刷新：真实会话读到 WARMING 后，等当前读取完成，再隔 3 秒
读取下一次；终态或读取错误时停止，切换会话／离开页面时清理计时器。不会周期性调用 wake，
也不会在 READY 后持续探测而延长 GPU 活跃时间。接口无需增加字段。

状态轮询只读服务／模型，不自动产生推理。wake 后台任务使用当前生产抽取 prompt 和合成
文本 `Milo 1 ctn`（闭集 family=`FAM_MILO`），检查精确数量、单位、span 和有效响应。
任务不读写订单、库存、租户、记忆或审计业务表，不控制 worker 启停。

真实 parse 的 LLM 成功更新近期证据；FALLBACK/MIXED 或异常保守清除 LLM 就绪证据。
纯客户记忆绕过 provider 不会制造就绪证据。状态发现断连后清除旧证据，恢复时要有一次新的
有效推理。较早的后台任务不能覆盖较新的 parse 结果。

限流和任务合并以应用进程为范围：同一进程同时只有一个预热任务；用户默认 60 秒内再次
请求返回 429 和 Retry-After。多进程实例各有本地状态，生产联调应先使用一个应用 worker；
若未来扩成多实例，需要共享任务和状态，当前版本不宣称已实现跨实例协调。

`fallback_available=true` 沿用契约，表示仍提供本地／人工处理路径，不是承诺任何输入都能
自动生成业务行。模型与本地解析同时失败时，原有 503 处理继续适用。

## 本地复验

从 `backend/` 运行，完全不需要 GPU、RunPod 密钥或数据库：

```powershell
.venv/Scripts/python -m pytest tests/test_ai_status.py tests/test_ai_provider_selection.py tests/ai_handoff/test_ai_extractor.py -q
```

`test_ai_status.py` 使用 MockTransport 覆盖同源配置、模型核对、有效推理、超时、断连、
401/403/429/500、无效响应、恢复、证据到期、异步任务合并、逐用户限流、迟到任务保护，
并检查响应不泄露密钥。`test_b01_integration.py` 使用真实 API、鉴权和隔离 PostgreSQL，
模型响应仍被模拟，用于检查 parse/status 一致、恢复与权限、限流和接口形状。

全量测试需要具备 CREATEDB 权限的隔离 `TEST_DATABASE_ADMIN_URL`，每项集成测试创建
自己的临时库。不要把测试连接指向线上应用库。按现有 CI 执行 Ruff 检查与全量 pytest。

## 下一步：真实验收所需条件

1. He 将这批已验证代码部署到测试／候选后端，记录发布 SHA；确认实际使用上面的 RunPod
   provider 配置和正确的公开 API origin、`/readyz`、`/openapi.json`。本修复不调整 `/healthz`
   路由，不因为公开路径差异单独重启。
2. Xiong 给出可联调窗口，核对当前 endpoint、精确 served model、worker 与预算；通过私有
   渠道配置有效 key，提供脱敏的最小推理成功记录。无需把 key 发到公开交接文件。
3. 在该窗口调用一次 wake，确认 WARMING→READY；或先真实 parse 成功，再核对 READY。
   前端不能只看到 accepted=true 就宣布完成。
4. 运行已有 `ai-sample-runbook.md` 的真实三阶段／样例验收，再通过真实前端对 T1/T2
   执行 parse，保存新的 request_id、ai_mode、模型名、配置／代码版本和脱敏响应。单位、
   金额、库存和整单流程仍按各自业务验收判定；一次预热抽取不是识别准确率证明。
5. 断连／恢复的故障注入只在隔离环境执行；当前本地模拟证据可验证错误分支。真实服务恢复
   后补采新的 LLM 证据，保留原 FALLBACK 历史。

Xiong 的服务就绪和部署后的现场实测是剩余外部条件；这些条件不影响本地修复交付。
