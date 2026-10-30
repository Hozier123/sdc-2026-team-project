# B04 最小 HTTP 驱动

**状态：2026-10-30 按原 B04 最小驱动及独立交接范围结项。** [结项记录](b04-closure.md)列明接受范围与证据说明。

`backend/tools/run_workflow.py` 串联身份、草稿、保存、直接批准/送审、老板决定、DO、仓库和日志。每步保留 case_id/run_id、状态、request_id、原始响应和检查点。它没有数据库连接、复位、AI 唤醒或写请求自动重试。

已独立签收的驱动 SHA256：`16C08C081D107582A48CD193BFBD554A4719DF1FF8A8D01C32BCB41C88B9FFD5`。该文件原字节发布；应用版本另行记录，不能把本地 Git HEAD 当作远端部署版本。

## 离线启动

先按 [backend/README.md](../../backend/README.md) 安装后端及测试依赖。以下命令从 `backend/`、已激活 Python 环境执行：

```powershell
python -m tools.run_workflow --case ../docs/ops/b04-cases/direct.json --plan
python -m tools.run_workflow --case ../docs/ops/b04-cases/direct.json --mock
```

分别返回 PLAN_ONLY、SIMULATED_PASS。`--plan` 不联网、不写文件；mock 只验证启动和编排，不能记作真实 HTTP、数据库或 LLM 通过。

八份公开 case 都是 canonical seed 的合成 DEV 用例：[T1/T2 用例说明](b04-t2.md)。它们不是冻结 TEST32 输入或答案。

## 真实 API

操作人先核实专用试验 API 对应的数据库、缓存和部署版本，再设置进程环境：

| 环境变量 | 含义 |
| --- | --- |
| B04_API_BASE | 专用试验 API，完整以 `/api/v1` 结尾 |
| B04_ENVIRONMENT | 脱敏目标标识；单凭该字符串不能证明环境隔离 |
| B04_T1_CLERK_TOKEN / B04_T1_OWNER_TOKEN / B04_T1_WAREHOUSE_TOKEN | T1 私密角色会话 |
| B04_T2_CLERK_TOKEN / B04_T2_OWNER_TOKEN / B04_T2_WAREHOUSE_TOKEN | T2 私密角色会话 |

令牌值仅通过私密渠道取得，设置于当前进程，不放入 case、命令参数或公开记录。驱动不从 SQL 哈希恢复明文；每个使用到的角色先通过 `/me` 核验真实身份和租户。HTTPS 用于远端 API，HTTP 仅允许回环地址。

```powershell
python -m tools.run_workflow --case ../docs/ops/b04-cases/direct.json --run-id dev-direct-01 --until saved
python -m tools.run_workflow --case ../docs/ops/b04-cases/direct.json --run-id dev-direct-01 --resume
```

首条命令会创建并保存合成草稿，第二条从已保存检查点继续。新试次使用新 run_id；续跑必须保持 case、API、环境、驱动及原角色身份绑定。受测后端/模型配置改变时另开新试次，不能继承旧结果。

## 证据与失败

默认输出 `evidence/b04-runs/<run_id>/`，包括 case.json、request/response、checkpoint.json 和 summary.json。默认目录不入 Git。可通过 `--out` 指定本地证据根目录。

| 状态 | 退出码 | 含义 |
| --- | --- | --- |
| API_PASS | 0 | 当前 HTTP 流程断言通过，数据库需另证 |
| SIMULATED_PASS | 0 | 模拟编排通过 |
| CHECKPOINT | 0 | 已到指定暂停点 |
| FAIL | 1 | 业务或证据断言不符 |
| BLOCKED | 2 | 缺会话、配置或前置条件 |
| INDETERMINATE | 3 | 写请求副作用不明 |

写请求超时、中断或成功响应无法解析时，不自动重发。保留 request_id、draft_id、approval_id、DO 等标识，只读核实后端和数据库，再决定后续试次。优先查看 summary.reason 及其引用的原始请求/响应。

HTTP 200 不等于库存正确；数据库检查见 [T2 本地辅助工具](b04-t2.md)，离线回包核验见[证据核验器](b04-evidence-auditor.md)。正式 workflow 映射、判定和执行由 Zhou/D03 统筹，隔离/复位由 B05 处理。
