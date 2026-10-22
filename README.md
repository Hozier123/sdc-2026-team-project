# KiraOrder for Orbyte

SDC Hackathon 2026 · Domain 2 · Orbyte Smart SME Challenge

**当前状态：已冻结 Gate 0（`1.3.0-gate0-v4`）；后端实现身份读取、parse、草稿行保存、审批与 DO 读取；前端工作台已交付并可连接真实后端运行。** 后端尚未实现草稿/客户列表与详情、活动、仓库检索和 AI 状态等端点，AI 仍为 stub 抽取（`ai_mode=FALLBACK`）。完整业务链路尚未全部打通，不代表可用业务原型已完成。

## 项目信息

| 项目 | 内容 |
| --- | --- |
| 产品名 | KiraOrder for Orbyte |
| 注册队名 | TODO：填写报名队名 |
| 赛道 | Domain 2（按最终分配确认） |
| SDG | SDG 8，重点为 8.2、8.3 |
| 队长、学校 | TODO：按报名信息填写 |
| 成员及分工 | TODO：按团队最终分工填写 |
| 仓库 | https://github.com/Hozier123/sdc-2026-team-project |

计划解决的问题：将马来西亚批发商收到的 WhatsApp 混语订单，转为经核对、经人工批准、可追溯的送货单。不确定的信息交给适当的人处理。上述业务目标尚未实现。

## 仓库根目录

本结构对应团队《KiraOrder 终版执行方案 v2（2026-10-21）》附录 B。文档中的 `kiraorder/` 指本仓库根目录，不需要再嵌套一层同名文件夹。

```text
sdc-2026-team-project/
├── .github/workflows/          # 后端基础 CI：隔离 PostgreSQL 验收
├── backend/                    # FastAPI 后端基础
│   ├── app/                    # 存活/就绪探针、配置、连接、迁移执行器
│   ├── tests/                  # 单元与 PostgreSQL 集成测试
│   ├── pyproject.toml
│   ├── requirements.lock       # 精确版本安装约束
│   └── README.md               # 安装、启动、迁移与测试说明
├── data/
│   ├── seed/                   # 团队自建合成种子数据
│   │   └── .gitkeep
│   └── README.md               # 数据目录说明
├── docs/
│   ├── .gitkeep
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

后端使用 Python 3.13 + PostgreSQL 17，依赖、显式迁移命令、`/healthz` 与 `/readyz` 及完整测试步骤见 [backend/README.md](backend/README.md)。安装与协作说明见 [docs/setup-windows.md](docs/setup-windows.md)，实测范围与限制见 [后端基础验证记录](evidence/backend-foundation/README.md)。

前端使用 Node.js 22 + npm，在 `frontend/` 内执行 `npm ci`、`npm run dev`（默认 http://127.0.0.1:5173/）。连接真实后端时在界面填入 API base `http://127.0.0.1:8000/api/v1` 与会话 Bearer token，或用 `.env.local` 的 `VITE_API_BASE_URL` 设置默认地址。前端测试与构建为 `npm test`、`npm run build`，CI 见 `.github/workflows/frontend.yml`；详细说明见 [frontend/README.md](frontend/README.md)。

计划采用的开发与部署方式：
- 开发：Vite 将 API 请求代理到 FastAPI。
- 部署：FastAPI 托管前端构建产物，合并到一个 Replit 部署。
- 当前仅记录约定，尚未配置代理、构建或部署。

## 配置项

`.env.example` 保留方案中的六个变量名，值均为空：
`DATABASE_URL`、`RUNPOD_API_KEY`、`RUNPOD_ENDPOINT_ID`、`LLM_TIMEOUT_S`、`DEMO_MODE`、`SIM_INBOUND_KEY`。

本阶段仅使用 `DATABASE_URL`（PostgreSQL URI）；其余五项尚未接入。真实密钥只放本地环境或 Replit Secrets，不写入代码、文档或截图。业务演示只使用团队自建合成数据。

## 后续实现顺序

后端基础 PR 验收后，依次推进 seed + Bearer 鉴权 + `/me`、PII + parse（包含 H1/H5）、GET draft + PUT lines、approve/DO、approvals/decide。H1/H5 和批准主链路不能长期后置。01—04 的 v1.3 工作文档放在 `docs/rules/`，以独立提交随对应实现更新；不回写冻结原件。

## 必要链接与正式材料

| 内容 | 链接或状态 |
| --- | --- |
| 原型 / 可访问构建 | TODO：开发后填写 |
| Replit 项目 / 部署 | TODO：实际使用后填写 |
| RunPod 端点 | TODO：实际接入后填写，不含密钥 |
| 幻灯片 | TODO |
| 5–7 分钟 YouTube 路演及原型演示 | TODO |
| 正式提案 | TODO：完成后放入 `submission/`，并在此添加链接 |
| 技术与工具声明 | TODO：完成后放入 `submission/`，并在此添加链接 |
| 平台使用证明 | 目前仅有示例页，必须替换并纳入工具声明 |

正式文件命名按官方模板填写实际队名：
- `SDC2026_TeamName_Preliminary.pdf`
- `SDC2026_TeamName_TechDeclaration.pdf`

## Replit 使用说明

**待实际使用后填写。** 说明开发、测试或托管了哪些模块，提供团队自己的项目/部署链接及证明，并纳入技术与工具声明。当前表单中的证明为 EXAMPLE ONLY，不代表已使用平台。

## RunPod 使用说明

**待实际使用后填写。** 说明 GPU 工作负载、模型、Pod / Serverless 连接方式及团队自己的证明。原官方回声处理器已移除，不把示例代码当作平台使用证据。若最终不使用 GPU，需如实说明并向组委会确认要求。

## 提交检查

参见 [docs/competition-checklist.md](docs/competition-checklist.md)。目录模板完成不等于参赛材料完成，GitHub 上传也不等于官网提交。最终需补齐可运行原型、文档、平台证明、幻灯片和视频，并按组委会要求开放评审访问、在官网提交。

## 许可证与来源

保留 [Apache License 2.0](LICENSE)。初始资料来自官方 SDC GitHub 提交模板；本次目录按团队终版执行方案附录 B 调整。最终提交时申报模板、第三方资源及 AI 辅助工具的实际使用。
