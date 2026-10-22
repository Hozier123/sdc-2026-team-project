# Windows 安装与协作

当前已提供后端基础服务、迁移命令和测试，尚无订单业务接口。不要沿用旧示例的 `python src/main.py` 或根目录 `requirements.txt`。

## 获取仓库

安装 Git：https://git-scm.com/install/windows 。

```powershell
git clone https://github.com/Hozier123/sdc-2026-team-project.git
cd sdc-2026-team-project
if (-not (Test-Path -LiteralPath .env)) {
    Copy-Item -LiteralPath .env.example -Destination .env
}
```

已有本地副本时，先保存或提交自己的实际修改，再更新：
```powershell
git switch main
git pull --ff-only
```

如发生冲突，保留双方工作并正常合并，不用强制推送覆盖队友的提交。

## 模块放置

- 后端：`backend/`，已使用 FastAPI；后端测试在 `backend/tests/`。
- 前端：`frontend/`，计划使用 React + TypeScript + Vite；页面位于 `frontend/src/pages/`。
- 合成种子数据：`data/seed/`。
- 测试及冻结集：`tests/`。
- 辅助脚本：`scripts/`。
- 实测证据：`evidence/`。
- 架构及接口说明：`docs/`。
- 正式参赛材料：`submission/`。

后端安装 Python 3.13 和 PostgreSQL 17 后，按 [后端运行说明](../backend/README.md) 创建独立虚拟环境、按锁定约束安装依赖、配置根目录 `.env`，显式运行迁移，再启动 Uvicorn。后端探针是 `/healthz` 和 `/readyz`；完整测试需要独立测试数据库实例。不要把 Gate 0 验证依赖与后端环境混装。

前端与 AI 负责人接入时再添加各自真实依赖和启动步骤；前端工程不要额外套一层项目目录。当前没有已配置的前端构建、RunPod 调用或 Replit 部署。

## 团队协作

使用自己的提交身份，示例值应替换：
```powershell
git config user.name "YOUR_NAME"
git config user.email "YOUR_GITHUB_EMAIL_OR_NOREPLY_EMAIL"
git switch -c feature/your-task-name
```

按实际进度提交，发起 Pull Request 供队友审阅。后端 PR 的 GitHub Actions 会检查冻结 Gate 0 未变、依赖兼容性、格式和真实 PostgreSQL 测试。不要把探针和数据库基础等同于订单业务链路已实现。

`gate0/` 和 `gate0-baseline-v1` 保持不变；最终签字看 `evidence/gate0/`。后续规则文档放在 `docs/rules/`，新增实测证据放在 `evidence/`。

## 后续部署约定

开发时 Vite 代理到 FastAPI；部署时 FastAPI 托管前端构建产物，使用一个 Replit 部署。当前仅保留这一约定，尚未实现。由负责人接入后补齐项目链接、运行命令、Secrets 配置和平台证明。
