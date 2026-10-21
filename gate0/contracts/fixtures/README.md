# Gate 0 contract fixtures

Each endpoint fixture uses this test wrapper:

```json
{
  "method": "POST",
  "path": "/api/v1/...",
  "request": {},
  "status": 200,
  "headers": {"X-Request-ID": "req_fixture_001"},
  "body": {}
}
```

The wrapper is not an API envelope. The actual successful API body is the value of `body` and therefore remains the direct OpenAPI model. Error bodies are exactly `{error_code,message,details}`. `error_catalog.json` is a non-endpoint catalog used to cover every public error code.
