# KiraOrder · Impeccable 前端检查与提升方案

日期：2026-10-23

## 结论

当前前端已有一致的暗色视觉、明确的业务状态和可靠的基本交互，适合继续精修。优先解决手机端可读性和任务层级，再收敛样式与动画资源开销。

保留用户已确认的 Marcellus 默认字体、Cormorant Garamond 展示标题与数字、四张精简统计卡、暗色配色、首页循环背景和鼠标跟随。不重新添加减少动效按钮，不恢复已撤回的滚轮进入工作台动画，不补回已删除的卡片介绍。

## 1. 来源、方法与覆盖范围

- 用户输入的“impessible”按上下文匹配为官方项目 [pbakaus/impeccable](https://github.com/pbakaus/impeccable)。本次通过 skill-installer 下载并安装其 `.agents/skills/impeccable`，安装位置为 `/Users/apple/.codex/skills/impeccable`；SKILL 元数据版本为 **4.7.0**。
- 使用 [Impeccable audit 方法](https://github.com/pbakaus/impeccable/blob/main/.agents/skills/impeccable/reference/audit.md) 的五个维度：可访问性、性能、主题与令牌、响应式、实现一致性。额外提供基于现有产品的设计观察；本报告没有运行独立双评审的 `critique` 流程，也没有把以下人工判断包装成自动检测分数。
- 工作台、新建订单、订单核对页：检查桌面 1280×720 和手机模拟视口 375×812。老板审批列表、初始页：检查桌面。使用 Codex 内置浏览器；模拟视口不能代表真机触控和 GPU 性能。
- 对 `src` 与 `index.html` 运行了一次 Impeccable 静态检测，原始结果见 [检测 JSON](</Users/apple/Desktop/SDC Hackathon/前端/kiraorder/docs/impeccable-detector-2026-10-23.json>)。逐项核对了检测结果。
- 执行 `npm test`：**53/53 通过**；执行 `npm run build`：类型契约检查、TypeScript 与 Vite 构建通过。
- 检查使用现有本地合成演示数据，没有提交审批、创建订单或上传项目材料。前端源代码本轮未修改。

限制：未做全站 WCAG 认证、全流程读屏测试、200% 文字缩放、真实触屏手势测试、弱网性能分析、真实后端/AI 联调，也未穷举打印、仓库及全部错误状态。静态扫描不能代替这些验证。

## 2. 五维基线

以下是依据本轮范围给出的人工基线分数，每维 0–4，用来安排后续工作，不是自动化合格证明。

| 维度 | 基线 | 证据与判断 |
|---|---:|---|
| 可访问性 | 2/4 | 有语义按钮、字段标签、跳转主内容、焦点反馈；占位文字对比度不足，部分手机文本只有 6–8px。 |
| 性能 | 3/4 | 3D 首页已懒加载并拆包；双视频与持续帧循环仍有资源优化空间，尚未测帧率与耗电。 |
| 主题与令牌 | 2/4 | 已有字体、颜色、状态和动作令牌；多个历史断点和局部硬编码导致规则覆盖不统一。单一暗色主题本身不是问题。 |
| 响应式 | 2/4 | 已测的工作台、新建、核对页在 375px 无页面横向溢出；信息排序和头部触控尺寸仍需改善。 |
| 实现一致性 | 3/4 | 有产品相关的核对、人工批准、版本和库存语义；流程条在新建页与核对页出现明显字号差异，样式积累较重。 |
| **合计** | **12/20** | **可用，有明确改进项；先解决可读性。** |

本轮范围内未发现阻止已测试导航或查看任务的 P0 问题。以下记录 **6 项已确认问题：P1 两项、P2 三项、P3 一项**；另列一项待性能测量的 P2 风险。

## 3. 优先级与具体修复建议

### F1 · P1：消息输入框占位文字对比度不足

- **位置**：[styles.css:1645](</Users/apple/Desktop/SDC Hackathon/前端/kiraorder/src/styles.css:1645>)，新建订单的消息文本框。
- **实测**：浏览器计算样式为文字 `rgb(81,103,122)`（`#51677a`）、不透明背景 `rgb(11,20,30)`（`#0b141e`），placeholder opacity 为 1；按照 sRGB 相对亮度公式计算为 **3.15:1**。
- **影响**：示例消息不易辨认，初次使用者更难理解应输入什么。普通占位文本也应满足文字对比度要求；参考 [WCAG 1.4.3](https://www.w3.org/WAI/WCAG22/Understanding/contrast-minimum.html)。
- **建议**：增加统一的 `--text-placeholder` 令牌，调整到至少 4.5:1；保留可见字段标签，不把输入要求只放在 placeholder 中。
- **验收**：新建页 textarea、搜索框等占位文字逐项核验；普通尺寸文本至少 4.5:1。
- **对应方法**：`$impeccable colorize`、`$impeccable audit`。

### F2 · P1：手机端仍残留 6–8px 的信息文字

- **位置**：[styles.css:4818](</Users/apple/Desktop/SDC Hackathon/前端/kiraorder/src/styles.css:4818>)、[styles.css:5029](</Users/apple/Desktop/SDC Hackathon/前端/kiraorder/src/styles.css:5029>)、[styles.css:5327](</Users/apple/Desktop/SDC Hackathon/前端/kiraorder/src/styles.css:5327>)、[styles.css:5355](</Users/apple/Desktop/SDC Hackathon/前端/kiraorder/src/styles.css:5355>)。
- **实测**：375px 下演示提示 6px；订单核对页流程文字 7px、步骤数字 6px；“YOUR DECISION”7px；语言提示 8px。新建页流程文字已有独立覆盖，显示 11px，形成同组件跨页面差异。
- **影响**：影响阅读、流程定位和识别当前需要处理的事项。Marcellus 在这个尺寸下的细节更难辨认。字号本身没有通用的 WCAG 最小像素值，本项是可读性问题，不以“低于某像素”直接判定 WCAG 失败。
- **建议**：保留 Marcellus，业务正文建议 14–16px，辅助文字 12–13px，表头/简短元信息最低目标 11–12px；空间不够时换行、缩短标签或重排，不继续缩小字体。核对页流程条复用新建页的可读规则。
- **字体细节**：当前加载 Marcellus Regular，`font-synthesis: none`；层级优先用字号、间距和颜色建立，不把区分完全寄托在 500/600/700 等未提供的字重上。
- **验收**：375px 下关键标签无需放大即可读；新建、核对、审批相关步骤语义和字号一致；增加文字缩放检查。
- **对应方法**：`$impeccable typeset`、`$impeccable adapt`。

### F3 · P2：手机工作台把具体任务放得过低

- **位置**：[App.tsx:819](</Users/apple/Desktop/SDC Hackathon/前端/kiraorder/src/App.tsx:819>)、[App.tsx:900](</Users/apple/Desktop/SDC Hackathon/前端/kiraorder/src/App.tsx:900>)、[App.tsx:908](</Users/apple/Desktop/SDC Hackathon/前端/kiraorder/src/App.tsx:908>)。
- **实测**：375×812 下，四卡区从约 y=313 到 y=545；订单队列从约 y=568 开始；“Up next”从约 y=1314 开始。
- **影响**：第一屏主要是标题和计数，用户要向下寻找具体任务。“Up next”虽然已经按最早待处理订单计算，但手机上很难及时看到。
- **建议**：保留四卡形态，压缩非任务性留白；把“Up next”在手机上改成计数区与队列之间的一条紧凑待办入口，显示客户、需要处理的事项、进入按钮。最近活动继续置后。
- **进一步完善**：现有 `next` 按阻断订单优先、同组时间排序（[App.tsx:805](</Users/apple/Desktop/SDC Hackathon/前端/kiraorder/src/App.tsx:805>)）；队列则直接过滤后截取六条，没有明确使用同一排序（[App.tsx:901](</Users/apple/Desktop/SDC Hackathon/前端/kiraorder/src/App.tsx:901>)）。建议统一排序口径，并标明“最早待处理”，避免用户猜测推荐依据。不新增接口中不存在的紧急度或 SLA。
- **验收**：375×812 初始屏能看到至少一个明确的具体处理入口；队列与推荐任务按同一明确规则排序；键盘阅读顺序与视觉顺序一致。
- **对应方法**：`$impeccable layout`、`$impeccable adapt`、`$impeccable clarify`。

### F4 · P2：手机顶栏的次级操作命中区偏小

- **位置**：[business-ui.css:942](</Users/apple/Desktop/SDC Hackathon/前端/kiraorder/src/business-ui.css:942>)，以及顶栏身份与连接状态控件。
- **实测**：角色按钮约 80×22px，权限头像 32×32px，离线状态按钮高约 25.5px。菜单按钮本身为 44×44px。
- **影响**：手指操作比鼠标更容易点偏，角色入口与权限入口相邻、较紧凑。
- **建议**：保持现在的文字对齐和紧凑外观，通过内边距或整合身份触发区域把手机命中区提高到约 44px；避免扩大后产生重叠点击区。角色与权限功能继续可达，不隐藏关键操作。
- **说明**：44px 是本方案的触控舒适目标；WCAG 2.2 的 AA 目标尺寸要求包含 24px 和间距例外，不能只用“低于44”直接判定违规。
- **验收**：以真实触屏补测误触、菜单关闭、焦点恢复和安全区；不因调整命中区再次造成头像与文字错位。
- **对应方法**：`$impeccable adapt`。

### F5 · P2：历史样式覆盖造成组件规格分叉

- **位置**：`src/styles.css` **6673 行**、`src/business-ui.css` **1196 行**；共享 `.stepper` 等选择器分散在多个断点和后置覆盖中。
- **已确认现象**：核对页流程条仍为 7px，而新建页通过额外的页面级规则修到11px。这比文件长短本身更能说明维护问题。
- **建议**：先提炼字体、状态、间距、控件高度等令牌；再按组件归并流程条、字段、队列、顶部身份区域。分批迁移，删除被替代的规则，避免再追加一层全局覆盖。现有 `docs/DESIGN_REFINEMENT.md` 已记录历史，但根目录缺少供 Impeccable 直接读取的 `PRODUCT.md` 和 `DESIGN.md`；后续可把已确认事实归档，不凭空补写业务要求。
- **验收**：每个共享组件有一套基础规则和明确断点；每批只改变目标组件；工作台、新建、核对、审批截图回归无意外变化。
- **对应方法**：`$impeccable extract`、`$impeccable document`。

### F6 · P3：Toast 的装饰可更克制

- **位置**：[styles.css:3304](</Users/apple/Desktop/SDC Hackathon/前端/kiraorder/src/styles.css:3304>)、[styles.css:3311](</Users/apple/Desktop/SDC Hackathon/前端/kiraorder/src/styles.css:3311>)。
- **检测结果**：一条 `side-tab` warning（3px 单侧边线）；一条 `bounce-easing` advisory（缓动控制点 y 超过1）。
- **人工复核**：两条都属于成功通知 `.toast`，不是整个页面的卡片或首页弹簧实现。边线有反馈语义，不作为严重问题；用户已选择的首页弹簧不因这条规则而删除。
- **建议**：如果统一细节，可把通知改成细边框与状态图标，进场只用轻微位移/透明度，缓动150–220ms。可排在其他项目之后。
- **对应方法**：`$impeccable polish`。

### R1 · P2 待测风险：首页动画资源与降级

- **依据**：[SeamlessBackdrop.tsx](</Users/apple/Desktop/SDC Hackathon/前端/kiraorder/src/components/SeamlessBackdrop.tsx>) 使用两路同源视频做重叠过渡；[PlanetGreeting.tsx:319](</Users/apple/Desktop/SDC Hackathon/前端/kiraorder/src/components/PlanetGreeting.tsx:319>) 固定 `motionPaused=false`，Canvas 为持续渲染；[useIntroMotion.ts](</Users/apple/Desktop/SDC Hackathon/前端/kiraorder/src/components/useIntroMotion.ts>) 有独立帧循环。
- **现场观察**：首页一个 Canvas；重叠时两路视频均在播放、readyState 为4。这与循环过渡设计一致，当前实测不是静止图片。
- **已具备优化**：首页按需加载、独立 three chunk、DPR 上限1.5。构建 three 包为1,122.31kB、gzip309.97kB；不能把它直接当作工作台首屏必载体积。
- **待测风险**：弱网下远程媒体可靠性、双视频解码成本、隐藏标签页时不必要的工作、触屏上没有鼠标也运行光标物理循环。尚无帧率、长任务或电池数据，不能宣称已经卡顿。
- **建议**：保持当前可见动效强度与无缝循环，优先增加页面可见性暂停/恢复；触屏不启动鼠标专属帧循环；有分辨率或带宽依据后再决定视频规格。保留背景海报/渐变故障兜底，失败时“进入工作台”始终可用。不增加动效控制按钮，不直接改成静态首屏。
- **验收**：真机测量帧率、播放恢复、循环接缝和弱网入口可用性；隐藏页面后相关工作停止，恢复后无明显跳帧或卡死。若需要支持操作系统减少动态偏好，应单独确认体验策略，避免悄悄覆盖此前确认的动态效果。
- **对应方法**：`$impeccable optimize`。

## 4. 推荐实施方案

### 第一批：可读性与命中区

范围：F1、F2、F4。Marcellus 保持默认字体，大标题与数字不换字；集中处理占位颜色、辅助字号、共享流程条、顶栏触控区域。

完成标志：已测页面不存在6–8px的关键业务说明；占位文字达到对比目标；角色入口可舒适点击且保持现有对齐。先做这批，对当前体验收益最大、视觉方向变动最小。

### 第二批：工作台任务层级

范围：F3。桌面保留“四张统计卡＋订单队列＋侧栏”；手机保持“四张卡”，把“下一单”改为紧凑任务入口并提前，不增加介绍性长文。

建议的手机内容顺序：

```text
顶栏
简短标题 + 新建订单
四张统计卡（更紧凑）
最早待处理：客户 + 待核对事项 + 进入
订单队列
最近活动
```

完成标志：进入页面就能找到一项具体可处理任务；统计卡仍可点击筛选；推荐排序可解释，订单信息和权限规则不变。

### 第三批：样式归并与资源效率

范围：F5、R1，最后处理F6。按组件拆解历史覆盖，先锁定现状截图再迁移；首页只改善资源生命周期，不借机改动用户已确认的循环、强度和鼠标风格。

推荐调用顺序：`typeset / adapt / colorize` → `layout / clarify` → `extract / optimize` → `audit` → **`polish`**。这些是实施时的方法路由，当前交付仅为检查与方案。

## 5. 已验证并应保留的优点

- 主动作使用薄荷色，订单状态同时有文字与颜色，支持快速扫读；没有只用颜色表达状态。
- 已测窄屏无页面级横向溢出，新建页输入框16px、客户选择控件高度46px，基础表单已适配手机。
- 首页 Enter 键可进入工作台；角色菜单用 ArrowDown 打开，Escape 关闭后焦点回到原触发按钮。这些基本键盘行为实测通过。
- 自定义公司/角色菜单通过 portal 渲染；不受父容器裁切。源码包含未保存保护、权限区分和错误恢复。
- 53项领域/接口等测试通过，生产构建通过。但这些测试不能替代字体、可读性、真实触控和性能验收。

## 6. 检测器结果与解释边界

运行目标：`impeccable detect --json src index.html`。退出码 **2** 表示存在主要检测命中，不是扫描器崩溃。结果为一条 warning、一条 advisory，均定位到Toast。

扫描器把 Vite 的 `/assets/marcellus.css`、`/assets/intro-fonts.css` 按项目根目录解析，没有自动映射到 `public/assets`，因此发出两条链接样式读取警告。该部分静态分析不完整，不代表浏览器字体404；本轮浏览器已经确认 Marcellus 生效。占位对比度与手机字号结论来自实际 DOM 计算样式，不来自这两条检测命中。

没有注入检测覆盖层，没有进行URL模式的自动化浏览器扫描；也没有给用户安装自动编辑钩子。当前技能可在后续对话调用，检测结果不会自动修复页面。

## 7. 本地截图证据

| 页面 | 桌面 | 手机375px |
|---|---|---|
| 工作台 | [截图](</Users/apple/Desktop/SDC Hackathon/前端/kiraorder/docs/screenshots/impeccable-workspace-desktop.png>) | [截图](</Users/apple/Desktop/SDC Hackathon/前端/kiraorder/docs/screenshots/impeccable-workspace-mobile.png>) |
| 新建订单 | [截图](</Users/apple/Desktop/SDC Hackathon/前端/kiraorder/docs/screenshots/impeccable-new-desktop.png>) | [截图](</Users/apple/Desktop/SDC Hackathon/前端/kiraorder/docs/screenshots/impeccable-new-mobile.png>) |
| 订单核对 | [截图](</Users/apple/Desktop/SDC Hackathon/前端/kiraorder/docs/screenshots/impeccable-review-desktop.png>) | [截图](</Users/apple/Desktop/SDC Hackathon/前端/kiraorder/docs/screenshots/impeccable-review-mobile.png>) |
| 审批列表 | [截图](</Users/apple/Desktop/SDC Hackathon/前端/kiraorder/docs/screenshots/impeccable-approvals-desktop.png>) | 未实测 |
| 初始页 | [截图](</Users/apple/Desktop/SDC Hackathon/前端/kiraorder/docs/screenshots/impeccable-intro-desktop.png>) | 未实测 |

后续可以按上面的批次逐项实施，也可只选择其中一批。实施后重新运行 audit 并复测对应尺寸；最后做 polish 收尾。
