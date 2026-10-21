# KiraOrder Gate 0 机器校验报告

> 执行日期：2026-10-21（Asia/Shanghai）  
> 修订：gate0-v4 / draft revision 5  
> 状态：技术验收通过；跨职能签字尚未完成。

## 结果

| 校验 | 固定工具/方法 | 结果 |
|---|---|---|
| manifest/lexicon/fixture JSON | Python 标准库 + 契约测试 | 通过 |
| OpenAPI 3.1 | PyYAML 6.0.3 + openapi-spec-validator 0.7.2 | 通过；16 个契约路径（13 P0 + 3 读模型）；本地 ref 全解析 |
| fixture 请求/响应 | jsonschema 4.26.0 / Draft 2020-12 | 通过；所有 endpoint fixture 匹配 schema |
| 前端语义完整度 | schema required/enums 断言 | 通过；Draft/Summary/Me/Approval/DO/Warehouse/AI 均覆盖 |
| H1 行为 | 版本化词表 + 确定性 oracle | 通过；35 例（多语复合数字、类型、小数/金额、DEV-39—41） |
| H5 行为 | 16 行真值表逐行执行 | 通过；多标签、否定近邻、合法 price basis、UNKNOWN 不分摊、UNIT 正向与三语变体 |
| 条件稳定身份 | SHA-256 确定性 fixture 测试 | 通过；同一证据重算得到同一 `condition_id` |
| 审批读取权限 | OpenAPI 参数/角色过滤测试 | 通过；CLERK 只读本人、无动作、越权 404 |
| PII 公共语言 | `pii-mask-tokens-v1` + fixture 扫描 | 通过；只允许三个 `[REDACTED_*]` token |
| v2.1/01—04 parity | SHA-256 + 关键术语断言 | 通过；受保护原件未修改 |
| PostgreSQL 语法 | pglast 7.21 | 通过 |
| 空库迁移 | PGlite 0.5.10 | 通过；18 表、12 个 trigger 事件；审批 guard 同时覆盖 UPDATE/DELETE |
| 干净目录 bootstrap | `scripts/bootstrap_gate0.ps1`（不带 `-SkipInstall`） | 通过；固定依赖 + pnpm fallback + 42 tests + 73 hashes |
| pytest | pytest 8.4.2 | `42 passed`，0 failed，0 skipped，退出码 0 |
| Gate 0 输出哈希 | `scripts/verify_gate0.py` | 通过；73 个受控文件逐一与 `gate0-hashes.txt` 一致 |

完整控制台摘录见 `docs/gate0-validation.log`。

## 干净目录复现

### 正常联网环境

```powershell
powershell -ExecutionPolicy Bypass -File scripts/bootstrap_gate0.ps1
```

### 离线/受限环境

bootstrap 支持三个可选环境变量：

```powershell
$env:GATE0_WHEELHOUSE = "<wheelhouse-with-pinned-wheels>"
$env:GATE0_PNPM = "<pnpm.cjs>"
$env:GATE0_NODE = "<node.exe>"
powershell -ExecutionPolicy Bypass -File scripts/bootstrap_gate0.ps1
```

若未设置 `GATE0_PNPM`，脚本依次尝试 `pnpm`、`corepack pnpm`、`npx pnpm@11.25.0`。若未设置 `GATE0_NODE`，脚本尝试 PATH 中的 `node`，再尝试 Codex 内置 Node。若未设置 `GATE0_WHEELHOUSE`，脚本使用 `pip install -r tests/contract/requirements.txt`。缺少任何依赖会失败，不会 skip。

## 验证环境

- Python 3.13.5
- pytest 8.4.2
- PyYAML 6.0.3
- jsonschema 4.26.0
- referencing 0.31.1
- openapi-spec-validator 0.7.2
- jsonschema-path 0.3.2
- pathable 0.4.1
- openapi-schema-validator 0.6.3
- pglast 7.21
- Node v24.19.0
- PGlite 0.5.10
- pnpm 11.25.0

> **传递依赖必须保持这组 pin**：`openapi-spec-validator 0.7.2` 要求 `jsonschema-path<0.4` 与 `openapi-schema-validator<0.7`；干净安装若解析到 `jsonschema-path 0.5.0` / `pathable 0.6.0`，会在 `SchemaPath.contents()` 处失败。这类“顶层 pin 正确、传递依赖漂移”的问题已写入 `tests/contract/requirements.txt`。

## 边界

- 这里验证的是 Gate 0 规格、机器契约、fixture 与空库 DDL，不代表业务后端已经实现。
- 18 步演示属于 P0-A 后端验收；Gate 0 的测试以“不存在业务代码”为断言，不再用 skip 掩盖。
- 正式部署仍须在目标 PostgreSQL 版本执行一次迁移 smoke test。
- 未创建 `gate0-v4` Git 标签；前端、AI、数据与后端最终哈希签字未全部完成。
