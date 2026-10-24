# Submission audit — 2026-10-24

- 范围：当前 `main` 的 tracked 文件 + evidence 归档
- 结论：evidence/SHA 通过；secret 扫描未发现 tracked 的真实凭据
- 提交条件：打包必须排除 `.env`、`.tmp/`、`.venv/`、缓存和私有 TEST32 包

## 1. Evidence / SHA

`evidence/SHA256.txt` 已补齐到 **20** 条，全部按 `git cat-file blob` 的存储字节复算一致。

覆盖：

- AI-only：official raw `17F44B9B…`、annotated `05959A4E…`、manual / v2
- He 6 cases：final `8223C89E…`、两份 HISTORICAL
- E2E：blocker `97FEE667…`、post55 `DCA16B6E…`、T2 `70A1BF9B…`
- RunPod proof：3 张 console 截图
- data signoff、canonical-6 checksum、benchmark

旧 raw / blocker 未覆盖；所有索引与文件存在。

## 2. Secret scan

扫描 tracked 文件及 evidence 文本，检查：

```text
RunPod rpa_ key
OpenAI sk- key
postgres:// / postgresql:// production URL
DATABASE_URL / RUNPOD_API_KEY assignment
T2_DEMO_TOKEN / tok_ token
Bearer token
AWS AKIA key
private key block
```

结果：

```text
tracked 真实 RunPod/DB/T2 凭据：0
```

命中的非敏感项：

- `.env`：本地真实配置，已 ignore 且未 tracked；**不得打包**
- `backend/tests/*`：`tok_t1_clerk` / `tok_t2_clerk` 是 demo token
- `backend/README.md`、`docs/ops/*`：`RUNPOD_API_KEY=...`、`DATABASE_URL=<Replit Secret>` 是占位符
- `.github/workflows/backend-foundation.yml`：`postgresql://postgres:...@127.0.0.1` 是 CI localhost
- `.venv` / `.tmp` / caches：依赖或本地临时文件，不进入提交包

## 3. 打包规则

```text
[✓] 只打包 tracked 文件
[✓] evidence/SHA256.txt 与 EVIDENCE_INDEX 一起
[✓] 排除 .env / .tmp / .venv / __pycache__ / node_modules / dist
[✗] 不打包 TEST32_review_*.zip
[✗] 不打包 TEST32_answers_*.json
[✗] 不打包 T1_seed.json / T2_seed.json 的私人核验副本
```

## 4. 状态

```text
Evidence SHA: PASS（20/20）
Secret scan: PASS（tracked）
Packaging: 需按上述排除规则执行
```

本报告不替代 TEST32 的 Zhan 业务核验，也不代表 UAT 通过。
