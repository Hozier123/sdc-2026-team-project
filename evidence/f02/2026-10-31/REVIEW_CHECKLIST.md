# F02 独立复核清单

请由未执行 F02 修复或本次复验的团队成员审核，审核本 PR 的确切提交，并核对原合入提交 `9628dd387d6c1037afab687a55bc575d186cf6d3`。

1. 核对 `frontend/.gitattributes` 对 `src/lib/gate0.generated.ts` 的 `text eol=lf`，并确认根目录 `gate0/** -text`、前端 `contracts/** -text` 和 `tests/fixtures/** -text` 仍有效。
2. 比较原提交前后生成文件的 Git blob，确认 F02 没有改写其内容；确认没有对全部仓库执行扩大范围的重新规范化，冻结文件未受影响。
3. 在干净检出上核对生成文件的索引和工作区换行。若有 Windows 环境，请在实际 Windows 检出并运行 `npm test`、`npm run build`；没有则明确记录 Windows 实机未测，不把本地模拟写成实机通过。
4. 核对 Node 22 的标准测试、构建和 Frontend CI 结果；确认 `types:check` 保留完整内容比较，真实字段差异仍会失败。
5. 如有差异，提交 **Request changes** 并说明受影响文件和复现条件。审核通过则用你本人的 GitHub 账号在 **Review changes → Approve** 写明：`F02 独立复核 PASS；受审 PR commit SHA；已核项目；未覆盖项；复核时间（Asia/Shanghai）`。

原 PR #74 的合并和成功 CI 是技术证据，不能代替本次独立审核签署。只有审核通过且本 PR 的 CI 通过后，才合并本 PR 并把 F02 标为完成。
