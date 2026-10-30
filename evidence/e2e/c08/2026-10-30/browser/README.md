# C08 浏览器证据（已补，2026-10-30 16:04）

本目录放 C08 的浏览器截图。口径来自 [Zhou 2026-10-30 回复](../reviews/01-Zhou-scope-2026-10-30.md)，以及 `acceptance.json` 的 `browser_evidence` 字段。

## 已补文件

| 文件 | 结果 |
|---|---|
| [c08_01_picking_current.png](c08_01_picking_current.png) | f8ff1d7 构建（页脚 v1.4.0）；顶栏 **Ah Kow / Warehouse**；DO `DO_20261029_453C4BC2` 与拣货明细；无价格/电话/原消息 |
| [c08_02_forbidden_403.png](c08_02_forbidden_403.png) | Console 一行显示完整 URL + 403 + `FORBIDDEN_ACTION` 响应体；无令牌 |
| [source/](source/) | 转换前原始 JPEG 字节，源 SHA256 记在 `acceptance.json` |

## 为什么需要两张图

Zhou 允许引用 C01 的仓库页证据，但 C01 的浏览器会话发生在 2026-10-29 17:13–17:16（UTC+8），早于 `f8ff1d7` 的 Pages 部署（19:51），所以 C01 页面图不是当前 Gate E 构建。按 Zhou 的第 7 条，需要补一张**当前 picking 页**截图；另加一条 **403** 截图。

## 交付要求（已满足）

| 文件 | 要求 |
|---|---|
| `c08_01_picking_current.png` | 当前 `f8ff1d7` 构建的 picking 页，DO 为 `DO_20261029_453C4BC2`；屏上可见 **Ah Kow / Warehouse** 身份；页面无价格、电话、原消息 |
| `c08_02_forbidden_403.png` | DevTools 里 `GET /api/v1/delivery-orders/DO_20261029_453C4BC2` 返回 **403**，且同一屏能看到 `FORBIDDEN_ACTION` 响应体（或完整 URL + 403） |

可选：`c08_03_warehouse_200.png`（同页 `/warehouse/...` 的 200 响应，C01 已覆盖，可不交）、脱敏后的 HAR。

**不要**用 `audit-detail` 的 403 代替；必须用完整 DO 接口。

## 操作步骤（约 3 分钟）

1. 打开 <https://hozier123.github.io/sdc-2026-team-project/>，点 **Connect API**：
   - API base：`https://kiraorder-api.replit.app/api/v1`
   - Session token：T1 WAREHOUSE 的演示令牌（私发，不要截图）
   - 连接后确认右上角身份是 **Ah Kow / Warehouse**。
2. 进入仓库页，输入 `DO_20261029_453C4BC2`，点 **Find picking list**。
3. 截图 `c08_01_picking_current.png`：要包含身份标识、DO 号、picking 明细；确认没有单价/金额/电话/原消息。
4. 打开 DevTools（F12）→ **Network**，保留日志。
5. 在 **Console** 里执行（把令牌换成真实值，执行后清掉这行历史）：

   ```js
   (async () => {
     const token = prompt("warehouse token");
     const target = "https://kiraorder-api.replit.app/api/v1/delivery-orders/DO_20261029_453C4BC2";
     const res = await fetch(target, { headers: { Authorization: "Bearer " + token } });
     console.log("GET " + target + " -> " + res.status, await res.text());
   })();
   ```

   期望 Console 打印一行：`GET https://.../DO_20261029_453C4BC2 -> 403 {"error_code":"FORBIDDEN_ACTION",...}`，同时 Network 出现该请求。这样**完整 URL、403、响应体在同一行**，截图即可满足 Zhou 的要求。Pages 源已在后端 CORS 白名单内，Console 能读到响应体。用函数包起来是为了避免 DevTools 顶层 `const` 重复声明。
6. 在 Network 里选中该请求：
   - **Headers** 面板的 Request URL 要能看清完整路径；
   - **Response** 面板要能看清 `FORBIDDEN_ACTION` 响应体；
   - 若一屏放不下，按 `Esc` 打开 Console 抽屉，让“URL + 403 + 响应体”同屏。
7. 截图 `c08_02_forbidden_403.png`。**不要展开 Request Headers 的 Authorization**；如果已经露出，打码。
8. 把两张 PNG 放进本目录，回到包根目录运行 `py -3.13 hash_tree.py` 重算 `SHA256.txt`。

## 已执行的收尾（2026-10-30 16:04）

- 原始 JPEG 按原字节保留在 [source/](source/)，另转成真正的 PNG 放在本目录；
- `acceptance.json` 的 `browser_evidence` 改为 `CAPTURED`，记录 `files`、`source_files` 与五项 `verification`；
- 主 `README.md` 的浏览器小节与“未覆盖”已更新；
- 已重算 `evidence/SHA256.txt` 和包级 `PACK_SHA256.txt`；
- `overall_status` 仍为 `NOT_SIGNED_OFF`，等独立复核后再改。
