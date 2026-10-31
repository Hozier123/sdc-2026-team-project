# F01：Xiong 独立复核清单

请在这个 PR 的当前 commit 上审核。使用你本人有权使用的测试会话；不要把凭据放进 URL、仓库、PR 评论或截图。复测可在全新浏览器配置中进行，避免旧会话影响结果。

1. 从公开 `https://hozier123.github.io/sdc-2026-team-project/#/workspace` 进入，核对实际页面版本、LOCAL DEMO 标识、HTTPS API 默认值和空令牌框；工作台首次加载应能独立于介绍页视频及 3D 资源。
2. 用 T1/T2 的 CLERK、OWNER、WAREHOUSE 会话分别连接，核对 `/me` 返回身份与页面一致；真实模式不得只靠前端角色切换。仓库会话应进入 Warehouse。
3. 从真实 Pages 页面确认带 Authorization 请求的 CORS，401 无效合成令牌的错误码和 Request 编号，以及仓库会话读取 `/orders/drafts` 的 403、错误码和请求编号。不要用业务写操作制造错误。
4. 刷新真实会话，核对令牌框为空、要求重连、失败仍留在重连态；重新输入有效会话后能读取真实后端记录。只有主动选择返回，才进入 LOCAL DEMO。
5. 检查本次会话令牌不在 localStorage、sessionStorage 或 URL。核对公开摘要与本地原始交付哈希；无法取得原件的检查应明确记为未核，不能默认为通过。
6. 阅读 [README.md](README.md) 的副作用和范围限制。若观察到不同的公网版本、接口结果或安全问题，记录实际版本、时间和可分享的脱敏证据，给出不通过或待补证结论。

完成后，请用你的 GitHub 账号在 **Review changes → Approve** 中写明：`F01 独立复核 PASS/FAIL；受审 commit SHA；公网版本；完成的检查项；未覆盖项；复核时间（Asia/Shanghai）`。GitHub 的审核账号、时间和受审提交构成内部复核记录。只有你本人提交审核通过后，才合并此 PR 并将 F01 状态改为完成；不要由执行人代填或代签。
