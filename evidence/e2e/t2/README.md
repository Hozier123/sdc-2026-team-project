# T2 E2E evidence

- 文件：`t2-e2e-active-20261024.json`
- 原始 SHA-256：`70A1BF9B9ACADECF8764C0CF1B748CB9D9B9DC85BE1444C3F92CA1E5E19ACDB8`
- 模式：`REAL`
- Code base：`c93d6d0`
- 状态：`T2_E2E_PASS`

## 结果

```text
GET  /api/v1/me                 200, tenant=T2, role=CLERK
POST /api/v1/orders/parse-draft 200
ai_mode=LLM
request-id=t2-e2e-active-20261024
lines=1, uom=ctn
```

T2 客户：`CUS_KILAT_01`；family 为 `UNKNOWN` 是 T2 目录不含 Tepung，
不是 401 或链路失败。

## 使用规则

```text
[✓] 可作 T2 E2E 证据
[✗] 不进入 AI-only index
[✗] 不写 23/23 T1 E2E 通过
[✗] 不写 UOM 全通过
```
