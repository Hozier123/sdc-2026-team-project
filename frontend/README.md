# KiraOrder for Orbyte · 前端

一条混语订货消息，经过核对与人工批准，成为可追溯的送货单。

面向操作人员的中文指南见 [KiraOrder 使用说明](docs/KiraOrder_使用说明.md)，包含快速上手、跟单核对、老板审批、仓库拣货、API 连接及常见问题。

说明与终版方案、Gate 0 契约及当前实现的逐项关系见 [使用说明与方案细节对照](docs/KiraOrder_使用说明与方案细节对照.md)，其中单独列出尚未补齐的功能和联调项。

## 启动

需要 Node.js 22 和 npm。首次运行执行 `npm ci`，随后：

```sh
npm run dev
```

浏览器打开 http://127.0.0.1:5173/ 。也可在 macOS 双击 `启动 KiraOrder.command`。

- 当前起始页：`/`，使用 `PlanetGreeting` 的 3D 语言轨道和滚动叙事。点击或轻触屏幕任意位置进入工作台；底部常驻进入提示。也可按 Enter / 空格进入，滚动或滑动继续浏览叙事。
- 原 70% 缩放版保留为 `/intro.html` 兼容入口，字体、脚本和背景已拆为本地静态资源。两种入口的工作台都保持正常比例。
- 直接进入主页：`/#/workspace`。
- 正式构建：`npm run build`；预览构建：`npm run preview`。
- 自动回归：`npm test`。接口测试使用 tests/fixtures 内冻结的 Gate 0 合成响应样例。测试中的请求文本已掩码，业务材料未打包到网站。
- 类型契约：`npm run types:check` 校验冻结 OpenAPI 的生成类型；`npm run types:generate` 重新生成。构建会自动检查类型漂移。
- 无真实后端时：运行 `npm run mock:api` 启动本机 fixture 服务，通过 Connect API 连接 `http://127.0.0.1:4191/api/v1`，使用固定合成标识 `fixture-clerk` / `fixture-owner` / `fixture-warehouse`。界面显示 FIXTURE MOCK；它只返回固定快照，不解析真实订单或调用 AI。场景切换及验收见 [前端独立开发结果](docs/前端独立开发与验收_2026-10-22.md)。

## 已实现

- 精简工作台：新建入口、四种订单计数、队列、下一单与活动；介绍横幅、口号和流程导览统一移到初始页。
- 收件箱搜索及状态筛选；新建混语消息订单；客户等级和账期上下文。
- 核对商品规格、数量、库存、单位和价格；明确的阻断疑点；客户澄清消息复制。
- 价格条件选择目标商品、人工输入成交价与原因；送老板、直接批准和最终送货单。
- 老板审批快照、库存检查、批准与带理由驳回；终态锁定。
- 送货单打印 / 保存 PDF、客户回复草稿复制、活动时间线、逐字段修改记录。
- 客户级说法记忆；仓库独立裁剪的只读拣货视图；手机布局、焦点管理和减少动态效果支持。
- 未保存修改保护；版本冲突、库存变化和重复批准的处理；本地刷新恢复。
- 活动、审批、AI 状态独立加载和局部重试；保存中统一禁用写入；无效数量就地拦截。
- 冲突恢复明确区分保留编辑与放弃编辑，保留后需重新核对和保存。仓库按商品、单位与拣货要求合并数量。
- 常驻 Privacy & data 页面；真实会话按权限一次自动预热及手动唤醒；正式鉴权错误提示；审批/审计 before_value 与 after_value 适配，以及人工单价的两位小数请求格式。

## 演示模式

默认使用 **LOCAL DEMO**，界面与演示数据服务分开。合成客户与商品展示真实业务规则，不调用 AI。解析会显示 **Offline match · non-AI**。

右上角 **Demo role** 可切换跟单员、老板和仓库。左侧租户选择器可切换食品批发与五金样例。仓库可用 `DO-T1-0001` 查看初始拣货单。

演示数据仅保存在此浏览器的 `kiraorder.demo.v1.T1` / `kiraorder.demo.v1.T2` 存储中，输入中的手机号、邮箱和证件号先掩码再保存。客户消息与回复不会自动发送。演示的目录匹配是有限规则，未知内容会要求人工确认，不能替代正式混语抽取服务。

## 接入后端

点击左侧 **Connect API**，输入完整 API base URL（如 `http://127.0.0.1:8000/api/v1`）和会话 Bearer token。连接后用户、租户和权限从 `/me` 读取；不发送自报角色请求头。远程 API 需要 HTTPS；本机开发可使用 HTTP。

会话 token 只在内存中，刷新后返回本地演示；不把 token 写进文件、URL 或 localStorage。API 需允许此前端来源的 CORS，并暴露 `X-Request-ID` 方便错误定位。可选 `.env.local` 的 `VITE_API_BASE_URL` 只用于设置默认地址，**不要把 secret 放进 VITE 环境变量**。

金额、状态、库存和 `allowed_actions` 在真实连接中完全取自后端。只有隔离的 `src/lib/demo.ts` 为演示重现领域规则。正常批准只提交 `expected_version`；改量/改价先 `PUT lines`，不使用 deprecated `confirmed_items`。

真实后端联调已实际执行（PostgreSQL 17.10 + FastAPI `127.0.0.1:8000`，冻结契约 `1.3.0-gate0-v4`）：`GET /me` 返回 200，用户、租户、角色和权限全部取自服务端；`POST /orders/parse-draft` 返回 200，手机号在落库前由服务端掩码为 `[REDACTED_PHONE]`；仓库角色调用 parse 返回 403 `FORBIDDEN_ACTION`，无效 token 返回 401 `INVALID_TOKEN`。后端目前只实现契约的一部分，以下路径仍返回 404：`GET /orders/drafts`、`GET /orders/drafts/{draft_id}`、`GET /customers`、`GET /activity`、`GET /orders/{do_number}/audit-detail`、`GET /warehouse/delivery-orders/{do_number}`、`GET /ai/status`、`POST /ai/wake`；完整界面链路需等这些后端端点补齐。P0 契约没有 DO 列表端点，送货单索引由草稿摘要中的 `do_number` 提供，详情使用正式 DO 读取端点；仓库通过 DO 号码检索。真实模式未开放无契约的目录搜索、手工新增行或作废端点；本地演示可明确关闭未提交草稿。

## 目录

```text
src/App.tsx                   应用壳、主页、路由和连接设置
src/components/orders.tsx     新建、核对和疑点处理
src/components/fulfillment.tsx 审批、送货单、仓库和审计
src/components/ui.tsx          弹窗、状态与通用组件
src/lib/types.ts               Gate 0 数据形状与写入投影
src/lib/api.ts                 真实 API 适配器
src/lib/demo.ts                隔离的本地演示数据服务
src/lib/review.ts              拣货合并、数量校验、路由及冲突编辑保留
src/components/PlanetGreeting.tsx 当前 3D 初始页，按需加载
public/intro.html              原版 70% 缩放兼容入口
public/intro-scene.html        资源拆分后的原星空场景
public/assets/intro-fonts.css  本地压缩字体，无第三方字体请求
public/assets/nebula.png       从起始 HTML 提取的视觉素材
scripts/package_delivery.py   带文件校验清单的交付打包
contracts/gate0.openapi.json   冻结机器契约快照（不含来源文档）
src/lib/gate0.generated.ts     自动生成类型，不进入运行包
src/lib/wire.ts                契约字段到页面模型的适配
scripts/fixture_api.mjs        本机固定快照 API，非生产后端
```

分步方案见 `docs/IMPLEMENTATION_PLAN.md`，交付验证见 `docs/VALIDATION.md`。源材料与确认包未被修改或上传。

演示角色切换只用于展示交互，不构成真实的身份认证；浏览器内的演示记录不应当作生产权限隔离。正式部署必须由后端执行令牌验证、租户隔离、仓库字段裁剪和批准事务。

## 审核修复与打包

逐项修复记录见 `docs/审核问题修复结果_2026-10-22.md`。本机模拟接口验证不等同于真实后端和真实 AI 联调。

运行 `npm test`、`npm run build` 后执行 `python3 scripts/package_delivery.py`，在项目上级目录生成交付 ZIP。包内 `DELIVERY_MANIFEST.json` 记录每个交付文件的 SHA-256；打包过程自动逐文件校验，并排除依赖目录、私有环境文件及来源材料。

当前 3D 页保留原实现的远程背景视频及封面，离线时背景素材可能不可用；业务页不依赖这些媒体。原 70% 兼容页的字体和背景均为本地资源。

本轮前端独立验证：55 项自动测试通过、生成类型校验及生产构建通过。真实 API 会话进入业务页面后，有 WAKE_AI 权限的用户自动发起一次预热；本地演示和仓库身份不自动唤醒。`/me` 与 `parse-draft` 的真实后端联调已完成；列表/详情端点仍待后端补齐，AI 仍为 stub 抽取（`ai_mode=FALLBACK`），尚未接入真实 AI。

## 预览图

- [桌面主页](docs/previews/homepage-desktop.png)
- [手机主页](docs/previews/homepage-mobile.png)

- [初始页 · 70%](docs/previews/intro-70-percent.png)
