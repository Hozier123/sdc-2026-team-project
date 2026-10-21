# Orbyte 实测参考：给 Ye Lianghui 与 He Minghao

检查日期：2026-10-21（Asia/Shanghai）。平台：https://orbyte-xyz.alphareds.com/ 。已使用提供的体验账号成功登录；当前组织显示为 `SDC_Committee_Demo_2`，角色为 `Company Admin`。本说明不包含密码或会话凭据。

依据：登录后实际页面、浏览器计算样式、页面自然发出的请求。仅浏览及展开菜单/表单，没有保存配置、创建记录或提交审批。结论只覆盖该环境和该账号可见范围。

## 先看结论

1. 可以直接借鉴蓝色主色、淡蓝背景、白色卡片、紧凑表格、语义色标签、左侧组织切换与分组导航。
2. 此桌面布局是**左侧栏导航**，不是顶部导航。团队拟做的顶部 Orbyte Context Bar 应称为 KiraOrder 的适配设计，不能称为官方原样组件。
3. 可见术语是 **Organization、Role、Approver、Reviewer、Memberships**。Workspace 在这里是工作模块菜单分组；当前观察不足以证明它是独立租户实体。
4. **没有在可见导航、组织设置、个人菜单中找到 Wallet / Credit / One Credit Wallet。** 这不等于整个平台没有该能力；不能据此宣称已经核对钱包字段或打通扣费。
5. 当前目录中的 `sources/` 没有可读项目文件，未获得团队 OpenAPI 契约。下面是映射建议，不能宣称已逐字段核对团队契约。

## 给前端 Ye Lianghui

### 可复用的设计变量（实测）

| 项目 | 页面样式值 | 建议用途 |
|---|---|---|
| 主色 | `#0767E8` | 主操作、选中导航、链接 |
| 页面背景 | `#F4F8FF` | 工作台底色 |
| 卡片底色 | `#FFFFFF` | 筛选、列表、摘要区 |
| 主要文字 | `rgb(28 49 83 / 90%)` | 标题、正文 |
| 次要文字 | `rgb(28 49 83 / 70%)` | 辅助说明、日期 |
| 禁用文字 | `rgb(28 49 83 / 40%)` | 禁用或不可用项 |
| 分隔线 | `rgb(28 49 83 / 12%)` | 表格线、面板边框 |
| 信息色 | `#08C7D9` | 提交类状态的基色 |
| 警告色 | `#FF9F43` | 复核类状态的基色 |
| 成功色 | `#28C76F` | 批准类状态的基色 |
| 错误色 | `#FF4C51` | 错误、失败 |
| 次级色 | `#808390` | 次要按钮 |
| 主色淡底 | 主色 8%～16% 透明度 | 选中态和状态底色；实际导航约 9.4% |

以上为页面 CSS 变量和实际计算样式，不是从品牌手册获得的官方规范。状态标签使用淡底与更深的文字；不要直接把浅青色作为白底小字。

### 字体与尺寸（1440 × 1000 桌面视口）

- 字体：Public Sans；正文 15px / 约 22px 行高，次级文字 13px / 20px。
- Dashboard 页面标题：28px / 42px，字重 500。
- 卡片标题：18px / 28px，当前页面字重 700。
- 主题基础圆角：6px；常见按钮圆角 6px、导航项圆角 8px、组织切换按钮圆角 9px。
- 首页筛选按钮及 Collapse all：高 40px；导航一级项：高 42px；组织切换按钮：高 52px。
- 展开左侧栏：宽 360px；正文从 x=384 开始，即侧栏右侧留 24px。
- 没有可供测量的顶部导航栏高度；不要把 40px 按钮高度或 52px 组织选择器高度当成顶部栏尺寸。
- 这些是当前页面/视口的测量值，不代表所有页面或移动端固定规格。中文字体回退可由团队补充 Noto Sans SC / Microsoft YaHei；这是建议，不是官方已验证配置。

### 建议落地到 KiraOrder

1. 先统一底色、文字色、Public Sans 和按钮圆角，再调整业务布局；视觉相似度主要来自这些基础元素。
2. 如果保留顶部 Context Bar，建议组织字段显示为 `Current organization`，角色显示 `Role`。将组织名放在标签下或旁边，搭配小图标和下拉箭头。
3. Context Bar 高度可暂定 56～64px，但这是团队自定义尺寸；官方参考组件位于左侧栏。
4. 钱包若必须演示，明确写 `Credits · Demo` 或 `Mock credits`，与组织和角色分开显示；不要伪装成从 Orbyte 拉取的真实余额。
5. 列表页沿用“标题 → 搜索/筛选 → 表格 → 状态标签 → 行操作 → 分页”的结构。状态必须同时有文字，不能仅靠颜色。
6. 首页可借鉴 Pending Actions：按 Submit / Review / Approve 分流，展示待处理数量、到期时间和业务跳转。
7. 保留 KiraOrder 自己的产品标识，文字说明“Orbyte ecosystem demo / integration prototype”。截图可用于对照设计；不要把独立原型描述成官方已上线模块。

配套文件：`orbyte-reference-tokens.css`，仅含本次实测的浅色模式参考变量。

## 给后端 He Minghao

### 术语与建议映射

下列代码名是 **KiraOrder 内部字段建议**，不是官方 API 字段名。

| 页面实测 | 含义 / 边界 | 内部字段建议 |
|---|---|---|
| Current organization / Home organization | 当前组织上下文 / 组织选择器中的归属组织标记 | `organization_id`、`organization_name`；若已有 `tenant_id`，在适配层显式映射 |
| Organization memberships | 用户加入组织的成员关系；页面提供邀请和状态筛选 | 独立 `membership` 关系，关联用户与组织 |
| Users → Role → Company Admin | 访问角色；当前体验账号的一种角色，不能视为完整枚举 | `access_role_ids` 或 `access_roles` |
| Approver / Reviewer | 用户列表及通知设置里的两个独立关系字段 | `approver_id`、`reviewer_id`；是否允许多人仍待契约确认 |
| Project Focus → Role | 项目分工；页面图例包含 BE / Backend、FE / Frontend、QA / Tester 等 | `project_role`，不要与访问角色共用枚举 |
| Workspace | My Tasks、Project Focus 等工作模块的导航分组 | 不因菜单名称新增 `workspace_id` 租户层级 |
| Pending Actions → Submit / Review / Approve | 待办动作分类；页面可见 Pending Submission 状态 | `action_type` 与 `status` 分开建模 |
| ACTIVE | 当前用户状态 | 与会员邀请状态、业务审批状态分别管理 |
| Wallet / Credit | 本次未找到 | Mock 独立封装，字段名、单位、账本规则待官方确认 |

重要：主页同时出现 Review 和 Approve、用户表同时出现 Reviewer 和 Approver，支持“复核/批准分离”的建模建议。但仅凭页面不能证明所有业务均强制执行“提交 → 复核 → 批准”的固定状态机；尚未提交真实业务记录验证。

### 实际模块导航

| 一级模块 | 当前账号可见子模块 |
|---|---|
| Dashboard | Dashboard；On leave today；Pending Actions |
| Organization | Clients、Projects、Users、Profile Change Requests、Organization Settings |
| Workspace | My Tasks、Project Focus、Meeting Summary、Settings & Notifications |
| Talent Hub / Leave | Leave Calendar、Leave Requests、Leave Balance |
| Talent Hub / eClaims | Claim Approvals、My Claims、Entitlement Group、Entitlement Report |
| Reports | Task Reporting、Delivery Analytics |
| Settings / Work | Claim Type Setup |

Organization Settings 的标签页是 Authentication methods、Member invitations、Memberships、Integrations。Integrations 页显示 Qwen API key 配置与 AI features disabled，提示组织 AI 能力有配置门槛。没有读取、填写或保存任何密钥。

Project Focus 文案明确描述按 client、project、role 进行用户月度分配，并提供 Timeline / Calendar / Submission / Task / Table 多视图。因此可借鉴“组织主数据 + 用户工作模块 + 汇总报告”的结构，而不能把它当成已经存在的订单业务模块。

### 浏览器请求能证明到什么程度

页面自然产生的成功请求包含：

- `/api/auth/organizations`
- `/api/users/{id}/roles`
- `/api/roles/{id}/permissions`
- `/api/menus/role/{id}?appId=1`
- `/api/organizations/memberships?organizationId=...`
- `/api/clients`、`/api/projects`、`/api/project-focus`

观察到请求域名为 `arg-services-sit.alphareds.com`。这些是当前网页的运行请求，不是官方公开 OpenAPI 文档；没有取得响应字段定义、版本稳定性或对外调用授权，不能据此写成已验证的生产集成契约。用户角色、权限、按角色菜单分别有请求入口，建议后端分别建模，并在服务端执行权限判断。

### 现在就能安排的修改

1. UI 对外用 Organization；内部保留已有租户隔离逻辑，通过适配层统一名称和 ID，避免全局搜索替换。
2. 把访问角色、项目分工、审核人关系拆开；不要把 Company Admin、Backend、Reviewer 混成一个枚举。
3. 为待办项分别保存动作分类、业务状态、业务对象引用、到期时间、可执行操作。操作是否合法由服务端决定。
4. 将 Credits 作为待验证能力边界：余额所属组织/用户、计费单位、扣费时点、预留与结算、失败退款、幂等与流水均待官方契约确认。
5. 团队展示可以表述为“参照 Orbyte 的组织上下文、角色权限和模块结构设计；当前为独立原型与模拟集成”。不要表述为真实 SSO、钱包或 OpenAPI 已打通。

## 页面证据与限制

- `01-dashboard.png`：工作台总览，配色、组织选择器、待办分类。
- `05-users.png`：Company Admin、Role、Approver、Reviewer、ACTIVE。
- `08-project-focus.png`：项目角色及多视图结构。
- `06-integrations.png`：组织级集成设置和 AI 不可用提示。
- `styles.json`：实际样式值；`navigation.json`：逐组导航记录；`observations.json`：页面文字记录。

入口最初出现 Temporary issue，通过进入登录页后成功登录。后续打开更深的设置页面并刷新时再次出现同类提示；不能把该页面未加载出来的内容当成不存在，也没有尝试修改账号以修复服务端问题。部分列表为空，不能证明完整业务生命周期。未观察到的钱包、计费和正式接入能力均保留为待验证。

用户提供的图片是队友转述与建议，不能单独作为主办方正式规则来源。本次不确认“非强制使用”“不扣分”等赛事政策，也不将图片中的行动建议当作额外操作授权。
