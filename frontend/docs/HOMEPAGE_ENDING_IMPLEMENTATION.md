# 首页收尾实施记录

已按 `HOMEPAGE_ENDING_PROPOSAL.md` 实施。开头保留品牌名与产品介绍；结尾只保留两行承诺句及一个实际入口。

## 变化

- 删除结尾重复的 KiraOrder 大标题和产品介绍，承诺句明确分成两行。
- 同一个 Enter workspace 按钮在 84–92% 滚动区间从底部移到承诺句下方，并切换为薄荷绿单色按钮。按钮始终可操作，未复制另一份入口。
- 文案与按钮间距约 32px；按钮高 52px。92% 后文案与入口保持位置，星云继续循环。
- 语言场从 78% 起退远，最终 Z 为 −220；中央阅读区用遮罩清空，外围语言与星云保留运动。滚动提示在收尾时隐藏。
- GSAP 只移动外层 dock，原有鼠标弹簧继续操作内部按钮；磁吸测量改用未受弹簧影响的外包裹，并在指针移动时更新位置，滚动时清除旧锚点。
- 首页取消继承业务页面的 360px 最小宽度，使 320px 窄屏可正常显示；业务页面的最小宽度规则保留。

## Taste 截图评估

ROUND 1

Seen in one second: 结尾再次出现大号 KiraOrder，像又开始介绍产品。

Idea (one sentence): 多语言消息经过读取、规则校验和人工审批，最后把下一步交给用户。

Live thing: 原生滚动和真实工作台入口。

Layout words by section: opening=品牌介绍 / story=左右阅读 / ending=重复品牌介绍。

Scores: design 6.5 · usability 7.0 · creativity 7.0 · content 7.0 → overall 6.5 after cap。

Caps applied: 既有轨道细线和少于四张真实图片仍受严格 Taste 规则封顶。本次只处理已有沉浸式首页的结尾。

Top three problems (most visible first), each with the screenshot it shows in and the fix:

1. 首尾重复品牌大标题与同一句说明（`evidence/intro-depth/desktop-close.jpg`）。删除结尾两项重复内容。
2. 承诺句、说明段和底部入口分散注意力（同图）。合成“承诺句 + 主按钮”的单一中心构图。
3. 语言可能经过结尾文字后方（同图）。退远语言场并遮去中央文字区域。

ROUND 2

Seen in one second: 两行承诺句，随后是清楚的薄荷绿入口。

Idea (one sentence): 流程介绍结束时，用户接手进入工作台。

Live thing: 同一个入口随滚动迁移，可反向还原，点击和键盘进入真实工作台。

Layout words by section: opening=品牌介绍 / story=左右阅读 / ending=中心承诺与操作。

Scores: design 6.5 · usability 8.0 · creativity 7.0 · content 8.0 → overall 6.5 after cap。

Caps applied: 既有星云/轨道、图片数量和鼠标跟随是用户已选择的方向，维持严格规则下的封顶；不把局部改进描述为整站获奖级重设计。

Top three problems (most visible first), each with the screenshot it shows in and the fix:

1. 初次窄屏检查在 354px 可用宽度发现继承的 360px 最小宽度导致横向溢出；已用仅首页生效的规则修复，320px 复查无溢出（`evidence/intro-ending/narrow-phone-close.jpg`）。
2. 原生浏览器检查中存在缩放和自动聚焦引起的视口/滚动变化；以 DOM 实测的 CSS 宽高和进度记录结果，截图保留实际预览比例。没有把未命中的 88%/92% 精确点宣称为已测点。
3. 单一星云贯穿全程，仍属于同一种视觉材料。按此次已批准的范围保留，不补充无来源图片或第二套产品演示。

## 验证

- 57/57 测试通过；生产构建和冻结契约校验通过。
- 三个收尾实现文件通过 Taste 源码 lint：0 FAIL、0 WARN。未运行其独立浏览器 inspector，浏览器检查通过当前会话允许的浏览器 API 完成。
- 最终检查 CSS 宽度 1440、768、390、320px，收尾均无横向文档溢出；文案两行，按钮一个，按钮高约 52px，文案至按钮约 31–33px。
- 实测反向返回中段时，入口恢复底部透明样式，滚动提示恢复；再次到末尾呈现承诺句与薄荷绿入口。过渡状态和最终状态见 `browser-checks.json`。
- 点击最终入口、按 Enter 均进入已渲染的工作台。滚动到末端没有触发跳转。原有 Space 原生按钮处理保持不变。
- 没有新增运行依赖、改动业务接口或执行任何订单操作。物理手机性能、Safari 和连续逐帧 FPS 未测。
