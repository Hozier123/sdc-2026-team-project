# C04 Post-merge closeout

- **Signed artifact**：`C04_low_price_evidence_2026-10-30_r4.zip`
  - SHA256：`C0D6EB23B779AA4EDC5090ED83019B06602EB7862101BC7032EFC8706D16CDE9`
  - 大小：651,463 B
  - 签字：Zhou Jingxi，2026-10-30 23:21（UTC+8），APPROVED；UI-01 接受为 P3
- **形式复核**：Zhan，PR #84，15/15 字节一致，PASS
- **合并**：PR #84（squash），commit `a3e1da6c3f984d7fe0e6f88faa9858eaf473c281`，2026-10-30T16:10:49Z
- **仓库状态**：**MERGED**

## 合并后元数据

`acceptance.json` 已做 post-merge metadata 更新：

- `repo_status`：`PENDING_COMMIT` → `MERGED`
- 新增 `merge_commit` / `merge_commit_url` / `merged_at` / `metadata_updated_at` / `post_merge_note`
- `SHA256.txt` 已重算，覆盖本目录 15 个文件（14 个原包文件 + `POST_MERGE.md`）；源 r4 zip 内保留原 12 项 `evidence/SHA256.txt`。

**签字包 r4 不受影响**：源 zip 内保留原始的 `acceptance.json`（签字时点 `repo_status=PENDING_COMMIT`）和原始 `SHA256.txt`；仓库内这份是合并后的元数据版本。业务证据、condition、4 张截图与 r4 字节一致。

## 边界

- C04 已结项：场景 PASS → Zhou 签字 → Zhan 形式复核 PASS → PR #84 合并。
- 样例仍为 `PENDING`；C04 是历史快照，不证明老板批准/拒绝、DO 生成、库存扣减。
- C05 是另一条 Gate A 条目，不是 C04 的前置。
