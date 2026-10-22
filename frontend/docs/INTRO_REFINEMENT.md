# 首页排版与内容整合

本次只调整进入工作台前的介绍页。

- 色彩沿用原稿：星空底 `#05090f`、深蓝 `#101e2a`、主文 `#e2ebe9`、副文 `#b4c5cf`、薄荷绿 `#a5e6c7`。
- 字体统一使用原稿已内嵌的 Cormorant Garamond；以字号、字重和留白区分层级。标题与正文不再混用 Cinzel、Arial。
- 结构：球体周围三个步骤承载完整说明 → 简洁的品牌收尾、产品摘要与进入按钮。删除收尾处重复的三个介绍卡片和口号。
- 桌面保留左、右、左的三步叙事；手机一次显示当前步骤，给球体与正文独立空间。收尾采用不透明背景，避免底层标题透出形成叠字。
- 保留 70% 初始页缩放、星空与球体、减少动态效果支持和进入工作台的同源消息桥。

按用户指定读取的规范：

- [frontend-design](https://github.com/anthropics/claude-code/blob/main/plugins/frontend-design/skills/frontend-design/SKILL.md)：一个字体家族、明确层级、控制行长，保留原稿的视觉记忆点。
- [vercel-react-best-practices](https://github.com/vercel-labs/agent-skills/blob/main/skills/react-best-practices/SKILL.md)：静态内容保持在组件外，保留被动滚动监听与 ref 驱动画布；本次不新增依赖或网络字体。
- [ui-ux-pro-max](https://github.com/nextlevelbuilder/ui-ux-pro-max-skill)：对已有界面执行 typography/overlay 的 UX 定向搜索，采用可读字号、对比度和合理行长规范。

三个 skill 在本机未预装，本次从公开官方仓库临时读取。未上传本地项目或用户材料。
