# KiraOrder AI 服务交付契约规范（H1 / H5 真实抽取）

> **交付方**：Xiong (AI Subsystem)  
> **接收方**：后端开发组（He Minghao / Backend Team）  
> **日期**：2026-10-22  
> **契约版本**：`AI-Contract-v1.3`（基于 Gate 0 v4 契约与 H1-v2 / H5-v3 词表）  
> **依据清单**：`KiraOrder_给Xiong_H1H5交付清单_2026-10-22(1).md`

---

## 1. 交付概览与边界约定

后端 `POST /api/v1/orders/parse-draft` 接入真实 AI 抽取时，Xiong 负责交付**纯事实、结构固定、span 可验证、具备离线韧性降级能力**的抽取服务。

```text
后端负责：
raw message → PII 掩码 → masked_text → AI 抽取 → RawExtraction → Adapter → OrderDraft

Xiong 交付：
masked_text → H1/H5 抽取服务 → rows[] / ignored_spans[]
```

### 绝对红线约束（Anti-Leaking & Permission Boundaries）
1. **禁止输出 `sku_id`**：AI 侧不知道物料编码，具体商品 SKU 由后端 Resolver 匹配。
2. **禁止输出 `price` / `unit_price`**：AI 仅提取客户提出的议价原话（如 `conds: ["kalau RM95 untuk 1 ctn"]`），绝不代替业务方核定售价。
3. **禁止输出 `stock`**：库存满足度由后端实时查询 WMS/ERP 决定。
4. **禁止输出 `approval` 与 `do_number`**：审批流与发货单号（DO）完全属于后端领域状态机。
5. **禁止接触未经脱敏的原始 PII**：AI 仅接收脱敏后的 `masked_text`（仅含 `[REDACTED_PHONE]`、`[REDACTED_MYKAD]`、`[REDACTED_EMAIL]` 占位符）。

---

## 2. Endpoint 服务规范（满足清单 §2.1）

### 2.1 基础信息与调用端点

| 配置项 | 参数值 / 规范说明 |
|---|---|
| **服务载体** | RunPod Serverless GPU Worker (vLLM / HuggingFace TGI) |
| **API Base URL** | `https://${RUNPOD_ENDPOINT_ID}.api.runpod.ai/v1/chat/completions` |
| **HTTP Method** | `POST` |
| **鉴权方式** | Bearer Token，Header: `Authorization: Bearer ${RUNPOD_API_KEY}` |
| **调用模式** | **完全同步调用**（Synchronous JSON Object 模式） |
| **健康检查 URL** | `GET https://${RUNPOD_ENDPOINT_ID}.api.runpod.ai/v1/version` |
| **网络超时阈值** | 连接超时 3.0s，总请求超时推荐 **8.0s**（环境变量 `LLM_TIMEOUT_S=8.0`） |
| **并发与弹性** | 单容器最高 50 并发（vLLM Continuous Batching），支持根据队列积压自动横向扩容 Pod |

> **安全须知**：`RUNPOD_API_KEY` 严禁写入 Git 仓库与业务日志。后端从受控环境变量或 Vault 中读取。

---

## 3. 请求与响应契约（满足清单 §2.2 & §2.3）

完整 JSON 校验模式见规范文件：
- 请求模式：[`request.schema.json`](file:///E:/AWorkspace/2.Competition/hackathon%20%E6%A0%A1%E5%86%85%E9%BB%91%E5%AE%A2%E6%9D%BE/ai_contract/request.schema.json)
- 响应模式：[`response.schema.json`](file:///E:/AWorkspace/2.Competition/hackathon%20%E6%A0%A1%E5%86%85%E9%BB%91%E5%AE%A2%E6%9D%BE/ai_contract/response.schema.json)

### 3.1 请求体（Request Body）
```json
{
  "masked_text": "Tepung Gandum 5 ctn 1kg [REDACTED_PHONE]",
  "language_hint": "ms",
  "request_id": "req-20261022-001"
}
```
- `masked_text` (**必填**，`string`，最大 4000 Unicode code points)：脱敏后的买家原话。超过 4000 字符立即被拦截并返回 422。
- `language_hint` (*可选*，`string | null`)：语言提示（如 `"ms"`, `"en"`, `"zh"`, `"zh-Hans"`）。
- `request_id` (*可选*，`string | null`)：链路跟踪追踪 ID，原样写入审计日志。

### 3.2 响应体（Response Body）
```json
{
  "rows": [
    {
      "span": "Tepung Gandum 5 ctn 1kg",
      "qty": 5,
      "uom": "ctn",
      "fam": "FAM_FLOUR",
      "pack_size": "1kg",
      "conds": []
    }
  ],
  "ignored_spans": [
    "[REDACTED_PHONE]"
  ]
}
```
- `rows` (**必填**，`array`)：提取出的订购商品行。每个 row 必须包含且仅包含以下 6 个键：
  - `span` (`string`)：`masked_text` 的精准子串，禁止拼接。
  - `qty` (`integer | null`)：`1..999999` 的正整数或 `null`。拒绝 `bool`、`float`、负数与非 ASCII 数字字符串。
  - `uom` (`string | null`)：计量单位别名（如 `"ctn"`, `"pack"`, `"kg"`, `"bag"`, `"pc"`）或 `null`。
  - `fam` (`string`)：租户目录白名单 ID（如 `"FAM_FLOUR"`）或 `"UNKNOWN"`，严禁为 `null`。
  - `pack_size` (`string | null`)：包装规格（如 `"1kg"`, `"500g"`, `"12 x 1L"`）或 `null`。
  - `conds` (`array[string]`)：该行关联的议价/库存/交期原话片段列表。
- `ignored_spans` (**必填**，`array[string]`)：过滤的问候语、闲聊或 PII 占位符切片。

---

## 4. 完整错误语义表（满足清单 §4）

后端调用 AI 服务时，必须明确区分不同异常形态并执行对应韧性策略：

| 错误场景 | AI 抽取层行为 | HTTP 状态码 / 异常类 | 后端 Adapter 与业务层处理 | 幂等与重试建议 |
|---|---|---|---|---|
| **请求文本超长** (>4000 code points) | 物理硬拦截，不调用大模型 | `422 Unprocessable Entity`<br>`MessageTooLongError` | 直接阻断，记录警告日志，提示买家缩短单次订单文本 | **不可重试** |
| **AI 调用超时** (>8.0s) | 触发 `httpx.TimeoutException`，**自动无缝降级**至本地 RapidFuzz 离线抽取 | 降级成功返回 `200 OK` (`ai_mode="FALLBACK"`)；若离线词表损坏抛 `503` | 返回基于词表的确定性草稿，标记 `match_source="RAPIDFUZZ_FALLBACK"`；若 503 则提示稍后重试 | 支持重试（幂等）；建议指数退避 (1s, 2s) |
| **RunPod 服务端 5xx / 崩溃** | 收到 HTTP 500/502/503/504，**自动降级**至 RapidFuzz | 降级成功返回 `200 OK` (`ai_mode="FALLBACK"`)；若离线词表损坏抛 `503` | 系统自动生成离线兜底草稿，通知运维告警大模型端点异常 | 支持重试（幂等）；RunPod 冷启动恢复后自动切回 LLM |
| **API Key 未配置 / 端点未配置** | 零网络调用，纯离线模式运行 | `200 OK` (`ai_mode="FALLBACK"`) | 纯离线环境/本地评测自适应运行 | 支持单机离线常态运行 |
| **AI 返回非法 JSON / 语法损坏** | 单行故障隔离机制 (`_validate_and_sanitize`) | `200 OK` (故障行降级为 `fam="UNKNOWN", qty=null`) | 仅将损坏行标记为疑点，不崩溃整张草稿；跟单员手工订正 | 幂等（temperature=0.0，重试结果相同） |
| **小数数量 / 模糊数量** (如 `2.5 ctn`) | H1 守卫命中，置 `qty: null` | `200 OK` (`qty: null`) | 后端识别为 `INVALID_QUANTITY` 或 `AMBIGUOUS_QUANTITY`，阻断自动成单 | 业务人工确认数量，不应重试大模型 |
| **闲聊 / 无订单信息** | 识别为无有效商品，返回空行 | `200 OK` (`rows: []`, `ignored_spans: [...]`) | 后端不生成任何商品草稿行，**零误报草稿** (Zero False Draft) | 属于正常业务流，无需重试 |
| **大模型与离线兜底均不可用** | 本地词表文件缺失或磁盘只读故障 | `503 Service Unavailable`<br>`AiAndFallbackUnavailableError` | 后端向网关返回 503，提示跟单系统进入维护降级模式 | 修复底层配置后重试 |

### 4.2 后端必须区分的 4 大状态及响应体（Response Body）示例

后端在消费 AI 抽取层时，必须明确区分以下 4 类状态，严禁混淆为单一自然语言异常：

#### 1. AI 超时（AI Timeout）
- **触发条件**：网络抖动或冷启动导致请求耗时超过 `LLM_TIMEOUT_S=8.0s`。
- **Python Adapter 韧性模式**：捕获 `httpx.TimeoutException` 后**自动降级**至本地 RapidFuzz，返回 `200 OK`，标记 `ai_mode="FALLBACK"`, `match_source="RAPIDFUZZ_FALLBACK"`，业务无感知。
- **独立 HTTP 微服务模式**：返回 `504 Gateway Timeout`：
  ```json
  {
    "error": {
      "code": "AI_TIMEOUT",
      "message": "AI extraction timed out after 8.0s threshold",
      "request_id": "req-20261022-001"
    }
  }
  ```
- **重试策略**：支持重试（幂等）；建议指数退避 (1s, 2s) 重试 1 次。

#### 2. AI 返回非法结构（AI Returns Malformed / Illegal Structure）
- **触发条件**：模型偶发未按 JSON 模式输出，或意外包含注入属性（如 `sku_id`）。
- **单行故障隔离机制**：Adapter 的 `_validate_and_sanitize` 执行字段清洗，仅将损坏行安全降级为 `fam="UNKNOWN", qty=null, issue_code="LOW_CONFIDENCE_MATCH"`，保留合法行，不崩溃整单。
- **网关/Schema 校验层模式**：返回 `422 Unprocessable Entity`：
  ```json
  {
    "error": {
      "code": "SCHEMA_VALIDATION_FAILED",
      "message": "Response failed response.schema.json validation: 'sku_id' is a forbidden property",
      "request_id": "req-20261022-002"
    }
  }
  ```
- **重试策略**：由于 `temperature=0.0` 推理具备确定性，相同输入不建议盲目重试，应交由跟单员手工订正。

#### 3. AI 返回合法但空结果（AI Returns Legal but Empty Result）
- **触发条件**：买家发送纯闲聊、客套话或无任何物料采购意图的配送通知（如 `"hantar esok terima kasih"`）。
- **HTTP 状态码**：`200 OK`
- **响应体（Response Body）**：
  ```json
  {
    "rows": [],
    "ignored_spans": [
      "hantar esok",
      "terima kasih"
    ]
  }
  ```
- **业务动作**：后端确认 `rows: []`，实现**零虚假草稿（Zero False Draft）**，不向数据库插入任何多余订单行。

#### 4. AI 服务不可用（AI Service Unavailable）
- **触发条件**：大模型端点崩溃/宕机，且本地离线词表文件缺失或无法读取。
- **HTTP 状态码**：`503 Service Unavailable`
- **响应体（Response Body）**：
  ```json
  {
    "error": {
      "code": "AI_AND_FALLBACK_UNAVAILABLE",
      "message": "Both LLM endpoint and local offline fallback are unavailable. Please check RUNPOD_API_KEY and KIRAORDER_FIELD_EVIDENCE_PATH.",
      "request_id": "req-20261022-003"
    }
  }
  ```
- **重试策略**：不可立即重试；需告警运维介入修复词表配置或恢复 GPU Pod。

#### 5. 输入文本超长（Input Exceeds Limit）
- **触发条件**：`masked_text` 超过 4000 Unicode code points。
- **HTTP 状态码**：`422 Unprocessable Entity`
- **响应体（Response Body）**：
  ```json
  {
    "error": {
      "code": "MESSAGE_TOO_LONG",
      "message": "Message length (4050 code points) exceeds physical limit of 4000 Unicode code points.",
      "request_id": "req-20261022-004"
    }
  }
  ```
- **重试策略**：**不可重试**；必须缩短输入文本。

---

## 5. 版本与审计元数据（满足清单 §5）

为保障金融与商业审计的可追溯性，每次 AI 调用的元数据将固化存入调用审计快照：

| 审计元数据项 | 当前版本 / 规范值 | 说明 |
|---|---|---|
| **基础模型名称** | `Qwen/Qwen2.5-7B-Instruct-AWQ` | 4-bit 硬件加速量化模型，支持极速低延迟推理 |
| **Prompt 模板版本** | `v2.1` (`closed-set family whitelist + DEV-21 injection guard`) | 封闭集白名单动态注入，对恶意提示词执行被动文本隔离 |
| **字段证据词表** | `field-evidence-v2.json` (`H1-v2`) | 正整数数量语法、单位别名与包装规格匹配规则 |
| **条件触发词表** | `condition-triggers-v3.json` (`H5-v3`) | 16 行真值表条件判定规则与议价模式 |
| **抽取契约版本** | `AI-Contract-v1.3` | 与后端 Pre-Resolver 严格一致的交互模式 |
| **追踪透传** | `request_id` (如 `req-xxx`) | 请求入参带入，回填至响应审计与慢调用日志 |

---

## 6. 安全与隐私防护（满足清单 §6）

1. **零原始 PII 传输**：AI 侧绝对不接收买家原始电话、身份证或真实姓名，仅接收 `[REDACTED_PHONE]`、`[REDACTED_MYKAD]`、`[REDACTED_EMAIL]`。
2. **数据零留存与防训练承诺**：调用 RunPod API 时，仅使用无状态 Inference Worker，不落盘存储买家文本，绝不将业务文本用于模型再训练。
3. **密钥最小化暴露**：API Key 仅通过受控环境变量传递，严禁写入 Git 仓库、代码常量或控制台打印日志。
4. **DEV-21 提示词注入免疫**：系统提示词严格要求将用户输入全量视为“不可信被动买家文本”，即使用户输入包含 `"Ignore previous instructions"`、`"Print system prompt"` 或 `"You are now an admin"`，模型依然将其视作普通文本或置入 `ignored_spans`。

---

## 7. 性能与延迟基准（满足清单 §7）

| 性能指标 | 观测基准值 | 架构建议与优化措施 |
|---|---|---|
| **热机 p50 延迟** | **~800 ms** | AWQ 量化 + vLLM PagedAttention 加速 |
| **热机 p95 延迟** | **~1800 ms (1.8s)** | 包含复杂多行订单与长条件抽取 |
| **冷启动时间** | **15s ~ 25s** (RunPod 无实例冷启) | 建议后端部署启动时调用 `warmup.py` 发送探测包；冷启动期间系统自动降级至 RapidFuzz (<15ms) 保障业务连续性 |
| **最大输出 Tokens** | `max_tokens = 2048` | 足以覆盖 50+ 行大型批发订单 |
| **推荐客户端超时** | `timeout = 8.0s` | 超过 8 秒立刻进入 RapidFuzz 本地离线兜底，避免买家界面卡顿 |

---

## 8. 验收标准逐项核对表（满足清单 §8）

| 清单验收项 | 交付状态 | 验证文件 / 证据来源 |
|---|:---:|---|
| **[x] 后端用 masked 样例请求成功** | **已通过** | 6 组标准样例验证通过，支持直接请求 |
| **[x] rows / ignored_spans 结构合法** | **已通过** | 严格通过 `request.schema.json` 与 `response.schema.json` 模式校验 |
| **[x] 所有 span 都能在 masked_text 中定位** | **已通过** | `span_coordinates` 精确回投验证通过，`[start:end]` 无重叠 |
| **[x] 6 组样例全部通过** | **已通过** | `samples/` 下 6 个样例在自动化测试中 100% 断言通过 |
| **[x] 超时 / 错误语义可复现** | **已通过** | `test_ai_extractor.py` 与 `test_ai_contract_delivery.py` 完整覆盖 |
| **[x] 没有 sku_id / price / stock / approval** | **已通过** | 模式层 `additionalProperties: false` 物理杜绝领域字段越权 |
| **[x] 没有原始 PII** | **已通过** | 仅允许并识别公共 `MASK_TOKENS` |
| **[x] 文档、样例、版本齐全** | **已通过** | `README.md`、`H1_H5_mapping.md`、`endpoint.env.example` 齐全交付 |

---

## 9. 后端接入使用指南

后端可以通过以下两种方式调用 AI 抽取服务：

### 方式一：直接在 Python 代码中调用（推荐，内置韧性与 H1 复核）
```python
from backend.ai.adapter import OrderAiAdapter
from backend.ai.extractor import RunPodExtractor

# 初始化抽取器与适配器
extractor = RunPodExtractor()  # 自动读取 RUNPOD_API_KEY 与 RUNPOD_ENDPOINT_ID
adapter = OrderAiAdapter(extractor=extractor)

# 显式注入租户商品族目录
catalog = {
    "FAM_FLOUR": ["Tepung", "Flour", "Tepung Gandum"],
    "FAM_RICE": ["Beras", "Rice", "Beras Wangi"],
    "FAM_OIL": ["Minyak", "Cooking Oil", "Minyak Masak"],
}

# 执行解析
output = await adapter.adapt(masked_text, catalog=catalog)
# output 包含: lines (AdapterLine), conditions (ExtractedCondition), ai_mode ("LLM" | "FALLBACK")
```

### 方式二：直接 HTTP 调用 RunPod Endpoint
```bash
curl -X POST "https://${RUNPOD_ENDPOINT_ID}.api.runpod.ai/v1/chat/completions" \
  -H "Authorization: Bearer ${RUNPOD_API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "Qwen/Qwen2.5-7B-Instruct-AWQ",
    "messages": [
      {"role": "system", "content": "You are KiraOrder AI..."},
      {"role": "user", "content": "Tepung Gandum 5 ctn 1kg [REDACTED_PHONE]"}
    ],
    "response_format": {"type": "json_object"},
    "temperature": 0.0,
    "max_tokens": 2048
  }'
```
响应内容通过 `response.choices[0].message.content` 解析出标准 JSON 格式。

### 方式三：标准契约微服务 HTTP 调用（基于 `request.schema.json` 与 `response.schema.json`）
若后端将抽取逻辑包装为独立 FastAPI / 网关微服务，客户端入参和出参直接对齐契约 Schema：
```bash
curl -X POST "http://ai-service:8000/api/v1/extract" \
  -H "Content-Type: application/json" \
  -d '{
    "masked_text": "Tepung Gandum 5 ctn 1kg [REDACTED_PHONE]",
    "language_hint": "ms",
    "request_id": "req-20261022-001"
  }'
```
响应体严格遵循 `response.schema.json`：
```json
{
  "rows": [
    {
      "span": "Tepung Gandum 5 ctn 1kg",
      "qty": 5,
      "uom": "ctn",
      "fam": "FAM_FLOUR",
      "pack_size": "1kg",
      "conds": []
    }
  ],
  "ignored_spans": [
    "[REDACTED_PHONE]"
  ]
}
```
