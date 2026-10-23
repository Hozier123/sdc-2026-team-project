# Public deployment readiness checklist

日期：2026-10-23  
状态：**未部署**。本清单只定义部署前必须完成的事项，不代表已有公开链接。

## 1. 责任人

```text
[✓] 部署负责人：He Minghao
[✓] 平台：Replit Core；账号 owner：He Minghao
[✓] 前端负责人：Ye Lianghui
[✓] 上线时间窗：2026-10-24 录制 demo 前
[✓] 回滚负责人：He Minghao
```

公开部署仍未执行；负责人已确定，下一步是实际创建后端 Repl。

## 2. 后端

```text
[ ] 运行 python -m app.migrations
[ ] /healthz = 200
[ ] /readyz = 200
[✓] 数据侧 seed 计数签字（2026-10-23，范围仅 seed）
[ ] 数据库使用专用非生产/演示库
[ ] DATABASE_URL 只放平台 Secrets
[ ] CORS_ALLOW_ORIGINS 加入前端公开域名
[ ] 启动命令使用 0.0.0.0:$PORT
[ ] AI_PROVIDER 保持 auto/Stub，除非 RunPod 已验收
```

## 3. 前端

```powershell
cd frontend
npm ci
npm run test
npm run build
```

```text
[ ] 构建产物可生成
[ ] VITE_API_BASE_URL 指向公开后端 /api/v1
[ ] 不把 demo token 写入构建产物
[ ] 公开站点可加载
```

## 4. 托管方案（已定）

```text
前端：Replit Static Deployment
后端：Replit Web Deployment（FastAPI）
数据库：Neon
不做 FastAPI 托管 dist
```

决策记录见 [public-deployment-decision.md](public-deployment-decision.md)。

部署时记录实际 URL 和平台证明。

## 5. 部署后冒烟

```text
[ ] GET /healthz = 200
[ ] GET /readyz = 200
[ ] GET /api/v1/me（demo token）= 200
[ ] 前端登录
[ ] 客户列表
[ ] parse-draft（Stub 或真实 AI）
[ ] 草稿保存
[ ] 审批/DO 流程
[ ] 无 5xx
```

## 6. 安全

```text
[ ] 不提交 .env
[ ] 不把 key/token 写入截图/日志
[ ] 公开站点只使用合成演示数据
[ ] demo token 只通过私发/密码管理器提供
[ ] CORS 不设为 *
```

## 7. 证据与回滚

```text
[ ] 保存公开 URL
[ ] 保存部署截图
[ ] 保存 smoke 结果
[ ] 记录平台/版本/时间
[ ] 记录回滚步骤和负责人
```

## 8. 当前不能做

```text
[✓] Replit Core 账号 owner：He Minghao
[✓] 前端负责人：Ye Lianghui
[✗] 没有公开 URL
[✗] Stub 环境尚未部署
[✗] RunPod 真实 AI 未验收
```

因此公开部署仍未执行；账号、负责人和架构已定，下一步是创建后端 Repl。
