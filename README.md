# KiraOrder for Orbyte

SDC Hackathon 2026 · Domain 2 · Orbyte Smart SME Challenge

**当前状态：Gate 0 已冻结（`1.3.0-gate0-v4`）；前端 GitHub Pages、后端 Replit、Neon PostgreSQL 已公开部署；官方 AI-only 证据为 23/23 LLM、0 fallback，final 6 为 5 PASS / 1 KNOWN_LIMITATION；UOM 仍为 24/31（7 处 known gaps）；TEST32 v5 freeze manifest 已由 He/Zhan review 并 merge，但 12 条 workflow 仍为 `NOT_RUN`。RunPod 当前 Active=0，公网 parse 走 fallback，不是 integrated live-AI demonstration。UAT、正式录制、官方提案/工具声明 PDF 与最终提交包仍未完成；本地测试和公开部署不等于完整验收，也不代表赛事提交已完成。**

数据侧 seed 计数签字：2026-10-23，签字人 Zhou Jingxi，范围仅 seed 计数与导入证据；业务字段级验收、AI 准确率和 UAT 另行确认。记录见 [evidence/data-signoff/2026-10-23.md](evidence/data-signoff/2026-10-23.md)。AI 评测草案边界见 [docs/ops/ai-evaluation-intake.md](docs/ops/ai-evaluation-intake.md)。

## 项目信息

| 项目 | 内容 |
| --- | --- |
| 产品名 | KiraOrder for Orbyte |
| 注册队名 | Falcons |
| 赛道 | Domain 2 — Orbyte Smart SME Challenge |
| SDG | SDG 8，重点为 8.2、8.3 |
| 队长、学校 | Zhou Jingxi，Xiamen University Malaysia |
| 成员及分工 | He Minghao（后端、规则、部署）；Xiong Peicheng（AI、RunPod、部署）；Ye Lianghui（前端）；Zhou Jingxi（数据、质量、评估）；Zhan Zhengrong（手工基线、材料与提交整合） |
| 仓库 | https://github.com/Hozier123/sdc-2026-team-project |
| 前端 | https://hozier123.github.io/sdc-2026-team-project/ |
| 后端 API | https://kiraorder-api.replit.app/api/v1 |
| 后端健康检查 | https://kiraorder-api.replit.app/readyz |

计划解决的问题：将马来西亚批发商收到的 WhatsApp 混语订单，转为经核对、经人工批准、可追溯的送货单。不确定的信息交给适当的人处理。当前已有公开 Pages/后端部署、Local Demo 和 AI-only 证据；完整 E2E、独立 UAT 与真人试用仍未完成。

## 仓库根目录

本结构对应团队《KiraOrder 终版执行方案 v2（2026-10-21）》附录 B。文档中的 `kiraorder/` 指本仓库根目录，不需要再嵌套一层同名文件夹。

```text
sdc-2026-team-project/
├── .github/workflows/          # 后端/前端 CI：隔离 PostgreSQL 与前端构建
├── backend/                    # FastAPI 后端
│   ├── app/                    # 业务路由、解析、审批、DO、AI 状态编排、进程内 AI adapter
│   ├── tests/                  # 单元、PostgreSQL 集成、契约回归
│   ├── tools/                  # 试次记录导出、六样例 AI 证据运行器
│   ├── pyproject.toml
│   ├── requirements.lock       # 精确版本安装约束
│   └── README.md               # 安装、启动、迁移与测试说明
├── data/
│   ├── seed/                   # T1/T2 合成种子、manifest 与哈希
│   └── README.md               # 数据目录说明
├── docs/
│   ├── audit/                  # 后端审计与当前状态更新
│   ├── ops/                    # 导出、重置、AI 一致性协议
│   ├── rules/                  # v1.3 工作规则
│   ├── competition-checklist.md
│   └── setup-windows.md
├── evidence/
│   ├── backend-foundation/     # 后端基础实测记录（非业务 KPI）
│   ├── gate0/                  # Gate 0 独立确认材料
│   │   ├── README.md
│   │   └── 确认书.md
│   └── README.md               # 基线、测试结果与截图的归档说明
├── frontend/                   # 前端：React + TypeScript + Vite
│   ├── src/                    # 应用壳、页面组件、API 客户端与契约生成类型
│   ├── tests/                  # 自动回归与冻结 Gate 0 合成样例
│   ├── contracts/              # 冻结 OpenAPI 快照及溯源哈希
│   ├── scripts/                # 契约类型生成、fixture 服务与交付打包
│   ├── docs/                   # 前端说明、审核与验收记录
│   └── README.md               # 启动、连接后端与验证说明
├── gate0/                      # Gate 0 规格与机器契约基线
├── scripts/                    # 评测、初始化、演示重置等辅助脚本
│   └── .gitkeep
├── submission/                 # 赛事正式提交材料
│   ├── README.md
│   ├── REPLIT PROOF OF USE.pdf  # EXAMPLE ONLY，待替换
│   ├── RUNPOD PROOF OF USE.pdf  # EXAMPLE ONLY，待替换
│   └── Submission Template SDC Hackathon.pdf  # 空白表，待填写
├── tests/                      # 测试代码、测试数据及冻结集记录
│   └── .gitkeep
├── .env.example                # 配置变量示例，值为空
├── .gitattributes              # PDF 按二进制处理
├── .gitignore
├── LICENSE                     # Apache License 2.0
└── README.md
```

上面的目录树列出主要目录及入口文件。GitHub 可能将只有一个子目录的路径折叠显示，例如 `src/pages`；这仍然表示嵌套的两个目录。

空目录中的 `.gitkeep` 仅用于让 Git 保留目录；后续加入实际文件后可移除占位文件。`data/README.md` 和 `frontend/README.md` 提供目录说明，也让 GitHub 根目录分别显示 `data/` 和 `frontend/`。前端工程直接放在 `frontend/`，后端直接放在 `backend/`。

`gate0/` 作为一个整体保存规格书、机器契约、迁移和验证工具，不拆分到业务目录，也不在冻结后静默修改。四方确认材料独立保存在 `evidence/gate0/`，通过受控文件清单哈希与对应 Git 标签关联。

Gate 0 已冻结于 [`gate0-baseline-v1`](https://github.com/Hozier123/sdc-2026-team-project/tree/gate0-baseline-v1)，提交为 `3478c31fbbcaf295130e87a992ccdff1a4fabf8e`，对应内部 `gate0-v4 / draft revision 5`。正式四方确认见 [确认书](evidence/gate0/确认书.md) 及 [证据绑定说明](evidence/gate0/README.md)。`gate0/docs/gate0-signoff.md` 和 manifest 中的待签状态保留了制备快照，最终确认以外部证据及上述标签为准。维护说明不会改写冻结快照或移动标签。

01—04 后续 v1.3 工作文档放在 `docs/rules/`，与后端实现同步更新；`gate0/external-inputs/protected/` 中的 v1.2 原件继续保留。

## 环境与运行方式

已有可启动的后端服务与前端工作台。不要运行旧的 `python src/main.py`。旧的根目录 `src/`、`runpod/`、示例测试、仅供演示的 `requirements.txt` 和 `.replit` 已从当前版本移除，历史提交保留。

先克隆仓库：
```powershell
git clone https://github.com/Hozier123/sdc-2026-team-project.git
cd sdc-2026-team-project
if (-not (Test-Path -LiteralPath .env)) {
    Copy-Item -LiteralPath .env.example -Destination .env
}
```

仓库已有本地副本的组员，先妥善保存现有修改，再运行 `git pull --ff-only` 更新。真实 `.env` 已被 Git 忽略。

后端使用 Python 3.13 + PostgreSQL 17，依赖、显式迁移命令、`/healthz` 与 `/readyz` 及完整测试步骤见 [backend/README.md](backend/README.md)。安装与协作说明见 [docs/setup-windows.md](docs/setup-windows.md)；历史基线记录见 [后端基础验证记录](evidence/backend-foundation/README.md)，当前完成状态与边界见 [后端审计报告](docs/audit/backend-audit-2026-10-23.md)。

前端使用 Node.js 22 + npm，在 `frontend/` 内执行 `npm ci`、`npm run dev`（默认 http://127.0.0.1:5173/）。连接真实后端时在界面填入 API base `http://127.0.0.1:8000/api/v1` 与会话 Bearer token，或用 `.env.local` 的 `VITE_API_BASE_URL` 设置默认地址。前端测试与构建为 `npm test`、`npm run build`，CI 见 `.github/workflows/frontend.yml`；详细说明见 [frontend/README.md](frontend/README.md)。

已定开发与部署方式：
- 开发：前端通过 `VITE_API_BASE_URL` 直接连接 FastAPI；当前 Vite 配置未启用 API 代理。
- 前端部署：GitHub Pages，主地址 `https://hozier123.github.io/sdc-2026-team-project/`；Replit 前端为旧版/legacy。
- 后端部署：Replit Core，Autoscale，public `https://kiraorder-api.replit.app`；数据库 Neon PostgreSQL 17.11。
- AI：代码默认 `AI_PROVIDER=auto`；当前公网配置为 `runpod_adapter`，RunPod Active=0，public parse 走 fallback，不是 integrated live-AI demonstration。
- 公开部署已存在；不要把本地 `npm run dev` 当作已部署。
- 决策见 [docs/ops/public-deployment-decision.md](docs/ops/public-deployment-decision.md)；检查清单见 [docs/ops/public-deployment-checklist.md](docs/ops/public-deployment-checklist.md)。

## 配置项

`.env.example` 给出配置变量名，值为空。后端实际读取：

```text
DATABASE_URL
AI_PROVIDER（auto | stub | http | runpod_adapter；默认 auto）
AI_SERVICE_URL / AI_HEALTH_URL / AI_WAKE_URL
AI_API_KEY / AI_TIMEOUT_S
RUNPOD_API_KEY / RUNPOD_ENDPOINT_ID / RUNPOD_MODEL_NAME / LLM_TIMEOUT_S
AI_WAKE_RATE_LIMIT_S / AI_WARMUP_GRACE_S
CORS_ALLOW_ORIGINS
```

`AI_PROVIDER=runpod_adapter` 才会启用进程内 `OrderAiAdapter`；需要
`RUNPOD_API_KEY`、`RUNPOD_ENDPOINT_ID`。代码默认 `auto`（无 `AI_SERVICE_URL` 时为
Stub）；当前公网部署配置为 `runpod_adapter`，RunPod `Active=0` 时 public parse
走 fallback。不存在 `/api/v1/extract`，AI 由 `parse-draft` 进程内调用。

真实密钥只放本地环境或 Replit Secrets，不写入代码、文档或截图。业务演示只使用团队自建合成数据。
六样例证据运行器见 [docs/ops/ai-sample-runbook.md](docs/ops/ai-sample-runbook.md)。

## 当前实现与验收边界

```text
已完成并有自动测试：
身份/租户权限、seed、PII、parse、目录解析、客户记忆、字段证据、
草稿保存/状态、条件与澄清、三语回复、审批/DO/库存事务、
客户/草稿/审批/活动/审计/仓库读取、AI 状态与唤醒、
进程内 RunPod adapter（默认关闭）、六样例证据运行器、
checks_enabled 三个软检查、并发/回滚、导出证据绑定、契约 fixture 回归。
```

当前 main 的 CI（Backend foundation + Frontend）通过；后端 non-integration 本地套件最近一次为 **307 passed**。完整集成测试需要 `TEST_DATABASE_ADMIN_URL`，不能把 307 当作完整集成结果。外部边界仍未完成：

- RunPod 当前 `Active=0`，public parse 走 fallback；真实模型质量/延迟需重新开窗口才能做 online verification；
- AI-only 23/23 LLM 已完成，但 accuracy 仍为 `NOT_COMPUTED`；UOM 24/31，7 处 known gaps；
- TEST32 12 条 workflow 仍为 `NOT_RUN`，没有完整 E2E；
- 前端与数据负责人的独立 UAT、真人试用记录仍未完成；
- 正式提案、工具声明、幻灯片与路演视频仍待最终确认。

01—04 的 v1.3 工作文档放在 `docs/rules/`，以独立提交随实现更新；不回写冻结原件。

## 必要链接与正式材料

| 内容 | 链接或状态 |
| --- | --- |
| 原型 / 可访问构建 | https://hozier123.github.io/sdc-2026-team-project/ |
| Replit 项目 / 部署 | 后端 https://kiraorder-api.replit.app；前端旧版 https://kiraorder-web.replit.app（legacy） |
| RunPod 端点 | https://lx22t9308hc10c.api.runpod.ai；当前 Active=0，见 evidence/runpod/2026-10-24/ |
| 幻灯片 | 待最终材料确认 |
| 5–7 分钟 YouTube 路演及原型演示 | 待正式录制 |
| 正式提案 | `submission/` 最终 PDF 待放入；当前为官方空白/示例表单 |
| 技术与工具声明 | `submission/` 最终 PDF 待放入；当前为官方空白/示例表单 |
| 平台使用证明 | Replit/RunPod 实际截图已归档；submission 内仍是 EXAMPLE ONLY，提交前必须替换 |

正式文件命名按官方模板填写实际队名：
- `SDC2026_TeamName_Preliminary.pdf`
- `SDC2026_TeamName_TechDeclaration.pdf`

## Replit 使用说明

后端使用 Replit Core，Autoscale（2 vCPU / 4 GiB），region Asia，public 域名
`https://kiraorder-api.replit.app`。前端主部署已迁移到 GitHub Pages；
`https://kiraorder-web.replit.app` 保留为 legacy/old UI，不作为最终评审入口。
Replit Core 为 He Minghao 自费；Ye Lianghui 的 Replit Agent 使用由平台
sponsor/credit 覆盖，具体见 Technical & Tools Declaration。

## RunPod 使用说明

RunPod Serverless Load Balancer endpoint `lx22t9308hc10c`，vLLM + Qwen2.5-7B-Instruct-AWQ，
GPU 24 GB；当前 `Active=0`、0 workers，public parse 走 fallback。使用证明见
`evidence/runpod/2026-10-24/`，包括 overview、workers-zero 和 shutdown logs。
RunPod 约 US$25 sponsor credit；不得把 0 workers 写成持续可用。

## 提交检查

参见 [docs/competition-checklist.md](docs/competition-checklist.md)。目录模板完成不等于参赛材料完成，GitHub 上传也不等于官网提交。最终需补齐可运行原型、文档、平台证明、幻灯片和视频，并按组委会要求开放评审访问、在官网提交。

## 许可证与来源

保留 [Apache License 2.0](LICENSE)。初始资料来自官方 SDC GitHub 提交模板；本次目录按团队终版执行方案附录 B 调整。最终提交时申报模板、第三方资源及 AI 辅助工具的实际使用。
