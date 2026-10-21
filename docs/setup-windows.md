# Windows 安装与协作

当前仓库是 KiraOrder 的目录模板，没有业务服务、依赖清单或启动脚本。不要沿用旧示例的 `python src/main.py` 或根目录 `requirements.txt`。

## 获取仓库

安装 Git：https://git-scm.com/install/windows 。

```powershell
git clone https://github.com/Hozier123/sdc-2026-team-project.git
cd sdc-2026-team-project
Copy-Item -LiteralPath .env.example -Destination .env
```

已有本地副本时，先保存或提交自己的实际修改，再更新：
```powershell
git switch main
git pull --ff-only
```

如发生冲突，保留双方工作并正常合并，不用强制推送覆盖队友的提交。

## 模块放置

- 后端：`backend/`，计划使用 FastAPI。
- 前端：`frontend/`，计划使用 React + TypeScript + Vite；页面位于 `frontend/src/pages/`。
- 合成种子数据：`data/seed/`。
- 测试及冻结集：`tests/`。
- 辅助脚本：`scripts/`。
- 实测证据：`evidence/`。
- 架构及接口说明：`docs/`。
- 正式参赛材料：`submission/`。

模块负责人开始实现时，再分别添加真实依赖清单和启动步骤；目前没有要求运行的安装或构建命令。前端工程不要额外套一层项目目录。

## 团队协作

使用自己的提交身份，示例值应替换：
```powershell
git config user.name "YOUR_NAME"
git config user.email "YOUR_GITHUB_EMAIL_OR_NOREPLY_EMAIL"
git switch -c feature/your-task-name
```

开始功能实现后，按实际进度提交，发起 Pull Request 供队友审阅。不要把目录占位文件或模板初始化当作已经实现的功能。

## 后续部署约定

开发时 Vite 代理到 FastAPI；部署时 FastAPI 托管前端构建产物，使用一个 Replit 部署。当前仅保留这一约定，尚未实现。由负责人接入后补齐项目链接、运行命令、Secrets 配置和平台证明。
