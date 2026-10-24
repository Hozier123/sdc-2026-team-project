# KiraOrder AI service delivery contract (H1 / H5 extraction)

> **Supplier:** Xiong (AI Subsystem)<br>
> **Recipient:** He Minghao / Backend Team<br>
> **Date:** 2026-10-22<br>
> **Contract version:** `AI-Contract-v1.3` (based on Gate 0 v4 and H1-v2 / H5-v3 lexicons)<br>
> **Reference checklist:** H1/H5 delivery checklist for Xiong, dated 2026-10-22, revision (1).

**Historical handoff specification:** requirements, performance figures, acceptance statements, and code examples below preserve the handoff's recorded scope. Translation does not constitute a new benchmark or acceptance run. For later deployment status and current known limitations, consult the [root README](../../README.md) and [evidence index](../../evidence/EVIDENCE_INDEX.md).

## 1. Delivery overview and boundaries

For real AI integration with backend `POST /api/v1/orders/parse-draft`, Xiong supplies an extraction service with factual output, a fixed structure, verifiable spans, and an offline fallback.

```text
Backend responsibility:
raw message → PII masking → masked_text → AI extraction → RawExtraction → Adapter → OrderDraft

Xiong's delivery:
masked_text → H1/H5 extraction service → rows[] / ignored_spans[]
```

### Data and permission boundaries

1. **Never output `sku_id`:** the AI side does not determine product codes; the backend Resolver matches concrete SKUs.
2. **Never output `price` / `unit_price`:** extract only the customer's quoted negotiation text, such as `conds: ["kalau RM95 untuk 1 ctn"]`. Do not decide the selling price.
3. **Never output `stock`:** the backend checks current WMS/ERP stock.
4. **Never output `approval` or `do_number`:** approval and delivery-order identifiers belong entirely to the backend state machine.
5. **Never access unmasked original PII:** receive only masked `masked_text`, using `[REDACTED_PHONE]`, `[REDACTED_MYKAD]`, and `[REDACTED_EMAIL]` placeholders.

## 2. Endpoint specification (checklist §2.1)

### 2.1 Connection details

| Setting | Value / specification |
|---|---|
| **Service host** | RunPod Serverless GPU Worker (vLLM / HuggingFace TGI) |
| **API Base URL** | `https://${RUNPOD_ENDPOINT_ID}.api.runpod.ai/v1/chat/completions` |
| **HTTP Method** | `POST` |
| **Authentication** | Bearer token; header `Authorization: Bearer ${RUNPOD_API_KEY}` |
| **Call mode** | Fully synchronous, JSON Object mode |
| **Health-check URL** | `GET https://${RUNPOD_ENDPOINT_ID}.api.runpod.ai/v1/version` |
| **Network timeout** | 3.0s connection timeout; recommended 8.0s total request timeout (`LLM_TIMEOUT_S=8.0`) |
| **Concurrency and scaling** | Up to 50 concurrent requests per container through vLLM Continuous Batching; Pods can scale horizontally with the queue backlog |

> **Security:** never commit `RUNPOD_API_KEY` to Git or business logs. The backend reads it from controlled environment variables or a Vault.

## 3. Request and response contract (checklist §2.2 and §2.3)

Complete JSON validation schemas:

- Request: [request.schema.json](request.schema.json).
- Response: [response.schema.json](response.schema.json).

### 3.1 Request body

```json
{
  "masked_text": "Tepung Gandum 5 ctn 1kg [REDACTED_PHONE]",
  "language_hint": "ms",
  "request_id": "req-20261022-001"
}
```

- `masked_text` (**required**, `string`, maximum 4000 Unicode code points): the masked buyer message. Reject overlong messages immediately with 422.
- `language_hint` (optional, `string | null`): a language hint such as `"ms"`, `"en"`, `"zh"`, or `"zh-Hans"`.
- `request_id` (optional, `string | null`): tracing ID, propagated unchanged into audit logs.

### 3.2 Response body

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

- `rows` (**required**, `array`): extracted order lines. Every row contains exactly these six keys:
  - `span` (`string`): an exact substring of `masked_text`; concatenated spans are forbidden.
  - `qty` (`integer | null`): a positive integer in `1..999999`, or `null`. Reject `bool`, `float`, negative values, and non-ASCII digit strings.
  - `uom` (`string | null`): a unit alias such as `"ctn"`, `"pack"`, `"kg"`, `"bag"`, or `"pc"`, or `null`.
  - `fam` (`string`): a tenant-catalogue allowlisted ID such as `"FAM_FLOUR"`, or `"UNKNOWN"`; never `null`.
  - `pack_size` (`string | null`): a pack specification such as `"1kg"`, `"500g"`, or `"12 x 1L"`, or `null`.
  - `conds` (`array[string]`): original price, stock, or delivery-condition text associated with the line.
- `ignored_spans` (**required**, `array[string]`): excluded greetings, chat, or PII-placeholder spans.

## 4. Error semantics (checklist §4)

When calling the AI service, the backend must distinguish failure types and apply the corresponding fallback strategy:

| Scenario | Extraction-layer behavior | HTTP status / exception | Adapter and business handling | Idempotency / retry guidance |
|---|---|---|---|---|
| **Overlong input** (>4000 code points) | Hard rejection without calling the model | `422 Unprocessable Entity`; `MessageTooLongError` | Block the request, record a warning, and ask for a shorter order message | Do not retry unchanged input |
| **AI timeout** (>8.0s) | Catch `httpx.TimeoutException` and fall back automatically to local RapidFuzz | Successful fallback: `200 OK` (`ai_mode="FALLBACK"`); unreadable offline lexicon: `503` | Return a deterministic lexicon-based draft with `match_source="RAPIDFUZZ_FALLBACK"`; on 503, ask the user to retry later | The handoff describes retries as idempotent; use exponential backoff (1s, 2s) |
| **RunPod 5xx / crash** | On HTTP 500/502/503/504, fall back to RapidFuzz | Successful fallback: `200 OK` (`ai_mode="FALLBACK"`); unreadable offline lexicon: `503` | Generate an offline fallback draft and alert operations about the model endpoint | The handoff describes retries as idempotent; return to LLM after cold-start recovery |
| **Missing API key / endpoint** | Make no network calls; use offline mode | `200 OK` (`ai_mode="FALLBACK"`) | Support local evaluation and fully offline operation | Standalone offline operation is supported |
| **Invalid model JSON / syntax** | Isolate malformed rows through `_validate_and_sanitize` | `200 OK`, degrading affected rows to `fam="UNKNOWN", qty=null` | Flag only damaged rows for clerk correction rather than failing the entire draft | The handoff describes temperature=0.0 inference as deterministic |
| **Decimal / ambiguous quantity**, such as `2.5 ctn` | H1 guard sets `qty: null` | `200 OK` (`qty: null`) | Flag `INVALID_QUANTITY` or `AMBIGUOUS_QUANTITY` and block automatic completion | Request human quantity confirmation instead of another model call |
| **Chat / no order content** | Return no valid product lines | `200 OK` (`rows: []`, `ignored_spans: [...]`) | Create no product draft lines: Zero False Draft | Normal business flow; no retry required |
| **Model and offline fallback unavailable** | Local lexicon missing or unusable because of filesystem faults | `503 Service Unavailable`; `AiAndFallbackUnavailableError` | Return 503 and indicate degraded maintenance mode | Retry after repairing the configuration |

### 4.2 Error states and response examples

The handoff distinguishes the following cases; do not collapse them into one natural-language exception.

#### 1. AI timeout

- **Trigger:** network delay or cold start exceeds `LLM_TIMEOUT_S=8.0s`.
- **In-process Python adapter:** catch `httpx.TimeoutException`, automatically fall back to local RapidFuzz, return `200 OK`, and mark `ai_mode="FALLBACK"`, `match_source="RAPIDFUZZ_FALLBACK"`.
- **Standalone HTTP microservice:** return `504 Gateway Timeout`:

  ```json
  {
    "error": {
      "code": "AI_TIMEOUT",
      "message": "AI extraction timed out after 8.0s threshold",
      "request_id": "req-20261022-001"
    }
  }
  ```

- **Retry:** the handoff describes retry as idempotent; retry once with exponential backoff (1s, 2s).

#### 2. Malformed or illegal AI structure

- **Trigger:** the model fails to produce the expected JSON structure or includes an injected field such as `sku_id`.
- **Row isolation:** the adapter's `_validate_and_sanitize` cleans fields and safely degrades only damaged rows to `fam="UNKNOWN", qty=null, issue_code="LOW_CONFIDENCE_MATCH"`, preserving valid rows.
- **Gateway/schema validation:** return `422 Unprocessable Entity`:

  ```json
  {
    "error": {
      "code": "SCHEMA_VALIDATION_FAILED",
      "message": "Response failed response.schema.json validation: 'sku_id' is a forbidden property",
      "request_id": "req-20261022-002"
    }
  }
  ```

- **Retry:** the source handoff treats `temperature=0.0` inference as deterministic. Do not blindly repeat identical inputs; send them for clerk correction.

#### 3. Valid but empty result

- **Trigger:** greetings, chat, or delivery notices without purchase intent, such as `"hantar esok terima kasih"`.
- **HTTP status:** `200 OK`.
- **Response:**

  ```json
  {
    "rows": [],
    "ignored_spans": [
      "hantar esok",
      "terima kasih"
    ]
  }
  ```

- **Business action:** recognize `rows: []` as Zero False Draft and do not insert unnecessary order lines.

#### 4. AI service unavailable

- **Trigger:** the model endpoint is down and the local fallback lexicon is missing or unreadable.
- **HTTP status:** `503 Service Unavailable`.
- **Response:**

  ```json
  {
    "error": {
      "code": "AI_AND_FALLBACK_UNAVAILABLE",
      "message": "Both LLM endpoint and local offline fallback are unavailable. Please check RUNPOD_API_KEY and KIRAORDER_FIELD_EVIDENCE_PATH.",
      "request_id": "req-20261022-003"
    }
  }
  ```

- **Retry:** do not retry immediately; alert operations to repair the lexicon configuration or restore the GPU Pod.

#### 5. Input exceeds the limit

- **Trigger:** `masked_text` exceeds 4000 Unicode code points.
- **HTTP status:** `422 Unprocessable Entity`.
- **Response:**

  ```json
  {
    "error": {
      "code": "MESSAGE_TOO_LONG",
      "message": "Message length (4050 code points) exceeds physical limit of 4000 Unicode code points.",
      "request_id": "req-20261022-004"
    }
  }
  ```

- **Retry:** do not retry unchanged input; shorten it first.

## 5. Version and audit metadata (checklist §5)

The handoff specifies that each AI call's metadata be retained in the call's audit snapshot for financial and business traceability:

| Metadata | Version / specified value | Description |
|---|---|---|
| **Base model** | `Qwen/Qwen2.5-7B-Instruct-AWQ` | Hardware-accelerated 4-bit quantization for low-latency inference |
| **Prompt template** | `v2.1` (`closed-set family whitelist + DEV-21 injection guard`) | Dynamically inject a closed family allowlist and isolate malicious instructions as passive text |
| **Field-evidence lexicon** | `field-evidence-v2.json` (`H1-v2`) | Positive-integer quantity syntax, unit aliases, and pack-specification matching |
| **Condition-trigger lexicon** | `condition-triggers-v3.json` (`H5-v3`) | Condition and negotiation rules based on the 16-row truth table |
| **Extraction contract** | `AI-Contract-v1.3` | Interaction structure aligned with backend Pre-Resolver |
| **Trace propagation** | `request_id`, such as `req-xxx` | Passed from the request into response auditing and slow-call logs |

## 6. Security and privacy requirements (checklist §6)

1. **No original PII transmission:** the AI side must not receive original buyer phone numbers, identity numbers, or real names; use only `[REDACTED_PHONE]`, `[REDACTED_MYKAD]`, and `[REDACTED_EMAIL]` placeholders.
2. **No text retention or retraining:** the handoff specifies stateless RunPod Inference Workers, no buyer-text disk storage, and no model retraining on business messages.
3. **Limit key exposure:** supply API keys only through controlled environment variables, never through Git, code constants, or console logs.
4. **DEV-21 prompt-injection guard:** system instructions treat all user input as untrusted passive buyer text. Inputs such as `"Ignore previous instructions"`, `"Print system prompt"`, and `"You are now an admin"` must remain ordinary text or enter `ignored_spans`.

## 7. Recorded performance and latency targets (checklist §7)

The following are the source handoff's recorded figures and recommendations, not a new benchmark. Later measured evidence takes precedence for current claims.

| Metric | Recorded figure | Architecture recommendation |
|---|---|---|
| **Warm p50** | **~800 ms** | AWQ quantization and vLLM PagedAttention |
| **Warm p95** | **~1800 ms (1.8s)** | Includes complex multiline orders and long conditions |
| **Cold start** | **15s ~ 25s** (RunPod with no active instance) | Call `warmup.py` with a probe during backend deployment startup; use RapidFuzz fallback (<15ms) while warming up |
| **Maximum output tokens** | `max_tokens = 2048` | Intended to cover 50+ line wholesale orders |
| **Recommended client timeout** | `timeout = 8.0s` | Fall back to local RapidFuzz after 8 seconds to avoid blocking the UI |

## 8. Recorded acceptance checklist (checklist §8)

These statuses preserve the source handoff's acceptance scope; they are not a claim that later live quality or production acceptance passed.

| Checklist item | Recorded status | Verification file / evidence |
|---|:---:|---|
| **[x] Backend requests with masked samples succeed** | **Passed** | Six standard sample requests verified |
| **[x] rows / ignored_spans have valid structure** | **Passed** | Validated against `request.schema.json` and `response.schema.json` |
| **[x] All spans can be located in masked_text** | **Passed** | Verified `span_coordinates` projection and nonoverlapping `[start:end]` ranges |
| **[x] All six samples pass** | **Passed (family not scored)** | Six generic samples pass span / qty / uom / pack_size / conditions assertions with `family_scored=false`; no family ground truth is scored here |
| **[x] Timeout / error semantics are reproducible** | **Passed** | Covered by `test_ai_extractor.py` and `test_ai_contract_delivery.py` |
| **[x] No sku_id / price / stock / approval** | **Passed** | Schema `additionalProperties: false` excludes unauthorized domain fields |
| **[x] No original PII** | **Passed** | Only shared `MASK_TOKENS` are permitted and recognized |
| **[x] Documents, samples, and versions included** | **Passed** | `README.md`, `H1_H5_mapping.md`, and `endpoint.env.example` included |

> Scoring clarification (2026-10-24): these six cases are generic contract fixtures with top-level `family_scored=false` / `reason=GENERIC_CONTRACT_SAMPLE`. Family is scored only in T1 `dev_41` / `frozen_eval_32`, using T1 IDs such as `FAM_TEPUNG`. See [family-scoring-caliber.md](family-scoring-caliber.md).

## 9. Backend integration examples

The handoff describes the following extraction integration options. Imports and examples reflect that handoff; consult current backend code and the root README for the active deployment path.

### Option 1: direct Python calls (recommended in the handoff, with fallback and H1 checks)

```python
from backend.ai.adapter import OrderAiAdapter
from backend.ai.extractor import RunPodExtractor

# Initialize the extractor and adapter.
extractor = RunPodExtractor()  # Reads RUNPOD_API_KEY and RUNPOD_ENDPOINT_ID automatically.
adapter = OrderAiAdapter(extractor=extractor)

# Explicitly inject the tenant family catalogue (T1 here; production parse-draft loads it from the tenant's DB).
# FAM_FLOUR in generic contract samples is only for legacy HTTP translation, not the T1 catalogue.
catalog = {
    "FAM_TEPUNG": ["Tepung", "Flour", "Tepung Gandum"],
    "FAM_BERAS": ["Beras", "Rice", "Beras Wangi"],
    "FAM_MINYAK": ["Minyak", "Cooking Oil", "Minyak Masak"],
}

# Parse the message.
output = await adapter.adapt(masked_text, catalog=catalog)
# output contains lines (AdapterLine), conditions (ExtractedCondition), ai_mode ("LLM" | "FALLBACK").
```

### Option 2: direct HTTP call to the RunPod endpoint

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

Parse standard JSON from `response.choices[0].message.content`.

### Option 3: contract microservice HTTP call (request.schema.json / response.schema.json)

If extraction is wrapped in a standalone FastAPI / gateway microservice, align client inputs and outputs directly with the contract schemas:

```bash
curl -X POST "http://ai-service:8000/api/v1/extract" \
  -H "Content-Type: application/json" \
  -d '{
    "masked_text": "Tepung Gandum 5 ctn 1kg [REDACTED_PHONE]",
    "language_hint": "ms",
    "request_id": "req-20261022-001"
  }'
```

The response follows `response.schema.json`:

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
