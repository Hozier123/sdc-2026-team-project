# Public deployment decision

日期：2026-10-23  
状态：**已定架构，未部署**  
范围：Stub 预发布环境；不含真实 AI 验收

## 1. 决策

```text
平台：Replit
前端：Replit Static Deployment
后端：Replit Web Deployment（FastAPI / Uvicorn）
数据库：Neon PostgreSQL（专用非生产库）
AI：AI_PROVIDER=auto → Stub，直到 RunPod 验收完成
架构：前后端分离，两个部署，不做 FastAPI 托管前端 dist
```

选择理由：

```text
[✓] 不需要先改 FastAPI 静态托管代码
[✓] 前后端可独立发布、回滚
[✓] 前端 build 由 VITE_API_BASE_URL 固定 API 地址
[✓] Replit 可作为工具使用证明
[✓] Stub 可先做公开演示，真实 AI 后切
```

## 2. 负责人

| 职责 | 负责人 | 说明 |
|---|---|---|
| 总体部署、后端、Secrets | He Minghao | 后端部署、CORS、DB、/healthz、/readyz |
| 前端 build、静态部署、UI smoke | 前端负责人（待确认姓名） | `npm run build`、VITE_API_BASE_URL、登录/草稿/审批 |
| 平台账号所有者 | 团队负责人 / He | Replit 账号、部署权限、公开 URL |
| 数据与签字 | Zhou Jingxi | seed 计数已签；业务/UAT 另立 |
| RunPod / 真实 AI | Xiong | 端点恢复与模型可用性 |
| UAT | 测试/数据/前端 | 真人试次与证据 |

**开放项：** 前端负责人姓名、Replit 账号所有者、公开域名。

## 3. 环境

### Backend

```text
DATABASE_URL=<Replit Secret>
CORS_ALLOW_ORIGINS=https://<frontend-domain>
AI_PROVIDER=auto
# RunPod 恢复后再改为 runpod_adapter
```

启动：

```text
uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

迁移：

```text
python -m app.migrations
```

### Frontend

```text
VITE_API_BASE_URL=https://<backend-domain>/api/v1
```

构建：

```text
npm ci
npm run build
```

## 4. 部署顺序

```text
1. Replit 后端部署（Stub）
2. 跑迁移
3. 验证 /healthz、/readyz、/me
4. 前端 build + 静态部署
5. 前端接公开 API，跑 smoke
6. 记录公开 URL 和截图
7. 等 Xiong 恢复后再切真实 AI
```

## 5. 验收标准

```text
[ ] 后端公开地址可访问
[ ] /healthz = 200
[ ] /readyz = 200
[ ] /me（T1 token）= 200
[ ] 前端公开地址可访问
[ ] 前端登录成功
[ ] 客户列表
[ ] parse-draft（Stub）
[ ] 草稿编辑
[ ] 审批/DO
[ ] CORS 无报错
[ ] 不泄露 DB URL/token
```

## 6. 明确不做

```text
[✗] FastAPI 托管前端 dist
[✗] 现在切 AI_PROVIDER=runpod_adapter
[✗] 把 Stub 演示写成真实 AI
[✗] 把本地 127.0.0.1 当公网地址
[✗] 提交 .env / DATABASE_URL / token
```

## 7. 前置条件

```text
[ ] Replit 账号可用
[ ] 能创建/访问两个 Deployment
[ ] 前端负责人可执行 build 和 UI smoke
[ ] Neon 连接串只放入 Replit Secrets
```

如果 Replit 账号或前端负责人未定，停在第 1 步，不进入部署。
