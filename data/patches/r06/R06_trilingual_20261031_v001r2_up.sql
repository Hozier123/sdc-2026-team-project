-- R06 trilingual family-alias patch — revision r2 (DRAFT — DO NOT EXECUTE WITHOUT HE/R02 AUTHORIZATION)
-- Owner of execution: He (R06). Author of content: Zhou (R04).
-- Target: T1 candidate environment only. Never run on production, protected, gate0, B05, or frozen seed.
-- Data version: TRILINGUAL-2026-10-31-v001 (UNCHANGED: the same 6 alias rows as v001)
-- Patch revision: r2. Supersedes R06_trilingual_20261031_v001_up.sql for execution; v001 is kept for archive.
--
-- Why r2 exists (He's review, 2026-11-01 00:57 UTC+8):
--   v001 wrapped BEGIN/COMMIT around the insert but left the row-count check to a human
--   comment. Running the whole file would COMMIT before anyone could inspect the count.
--   r2 asserts inside the transaction: any unexpected row count raises and rolls back.
--   No data change: the 6 (alias_id, family_id, language, phrase, phrase_norm) tuples are identical to v001.
--
-- Scope: FAM_GULA, FAM_BERAS, FAM_GARAM; 6 new family-level aliases.
-- Not included: SKU-level exact aliases (would risk ALIAS_ONLY and invalidate E01's LLM requirement).
-- Rollback: R06_trilingual_20261031_v001r2_down.sql
--
-- Safe to run as one file: it either commits exactly the intended state or aborts with no change.

BEGIN;

-- 1) 冲突预检：同租户同 phrase_norm 若已指向其他 family，拒绝导入，不覆盖。
DO $$
DECLARE
    conflicts integer;
BEGIN
    SELECT count(*) INTO conflicts
    FROM family_aliases fa
    JOIN (VALUES
        ('白糖', 'FAM_GULA'),
        ('sugar', 'FAM_GULA'),
        ('大米', 'FAM_BERAS'),
        ('rice', 'FAM_BERAS'),
        ('食盐', 'FAM_GARAM'),
        ('salt', 'FAM_GARAM')
    ) AS e(phrase_norm, family_id) ON e.phrase_norm = fa.phrase_norm
    WHERE fa.tenant_id = 'T1'
      AND fa.family_id <> e.family_id;

    IF conflicts > 0 THEN
        RAISE EXCEPTION 'R06 abort: % existing phrase(s) point to another family; refusing to overwrite', conflicts;
    END IF;
END $$;

-- 2) alias_id 冲突预检。
--    r2 修正：去掉 tenant_id 过滤。alias_id 是全局主键，被任何租户占用都必须先暴露，
--    而不是等 INSERT 撞主键才报错。
DO $$
DECLARE
    conflicts integer;
BEGIN
    SELECT count(*) INTO conflicts
    FROM family_aliases fa
    JOIN (VALUES
        ('ALS_TRIL_20261031_GULA_ZH', 'T1', '白糖', 'FAM_GULA'),
        ('ALS_TRIL_20261031_GULA_EN', 'T1', 'sugar', 'FAM_GULA'),
        ('ALS_TRIL_20261031_BERAS_ZH', 'T1', '大米', 'FAM_BERAS'),
        ('ALS_TRIL_20261031_BERAS_EN', 'T1', 'rice', 'FAM_BERAS'),
        ('ALS_TRIL_20261031_GARAM_ZH', 'T1', '食盐', 'FAM_GARAM'),
        ('ALS_TRIL_20261031_GARAM_EN', 'T1', 'salt', 'FAM_GARAM')
    ) AS e(alias_id, tenant_id, phrase_norm, family_id) ON e.alias_id = fa.alias_id
    WHERE fa.tenant_id <> e.tenant_id
       OR fa.phrase_norm <> e.phrase_norm
       OR fa.family_id <> e.family_id;

    IF conflicts > 0 THEN
        RAISE EXCEPTION 'R06 abort: % row(s) already use a reserved alias_id with different content', conflicts;
    END IF;
END $$;

-- 3) 幂等插入 + 影响行数自断言（0 = 已加载，6 = 本次新增；其他一律回滚）。
DO $$
DECLARE
    inserted integer;
BEGIN
    WITH expected(alias_id, family_id, language, phrase, phrase_norm) AS (
        VALUES
            ('ALS_TRIL_20261031_GULA_ZH', 'FAM_GULA', 'zh', '白糖', '白糖'),
            ('ALS_TRIL_20261031_GULA_EN', 'FAM_GULA', 'en', 'Sugar', 'sugar'),
            ('ALS_TRIL_20261031_BERAS_ZH', 'FAM_BERAS', 'zh', '大米', '大米'),
            ('ALS_TRIL_20261031_BERAS_EN', 'FAM_BERAS', 'en', 'Rice', 'rice'),
            ('ALS_TRIL_20261031_GARAM_ZH', 'FAM_GARAM', 'zh', '食盐', '食盐'),
            ('ALS_TRIL_20261031_GARAM_EN', 'FAM_GARAM', 'en', 'Salt', 'salt')
    )
    INSERT INTO family_aliases (alias_id, tenant_id, family_id, language, phrase, phrase_norm)
    SELECT e.alias_id, 'T1', e.family_id, e.language, e.phrase, e.phrase_norm
    FROM expected e
    WHERE NOT EXISTS (
        SELECT 1
        FROM family_aliases fa
        WHERE fa.tenant_id = 'T1'
          AND fa.phrase_norm = e.phrase_norm
    );

    GET DIAGNOSTICS inserted = ROW_COUNT;
    RAISE NOTICE 'R06 v001r2 inserted rows: %', inserted;

    IF inserted NOT IN (0, 6) THEN
        RAISE EXCEPTION 'R06 abort: unexpected affected row count % (expected 0 or 6)', inserted;
    END IF;
END $$;

-- 4) 终态自检：6 条目标别名齐全且指向正确；6 条历史别名未被改动。
DO $$
DECLARE
    target integer;
    legacy integer;
BEGIN
    SELECT count(*) INTO target
    FROM family_aliases fa
    JOIN (VALUES
        ('白糖', 'FAM_GULA'),
        ('sugar', 'FAM_GULA'),
        ('大米', 'FAM_BERAS'),
        ('rice', 'FAM_BERAS'),
        ('食盐', 'FAM_GARAM'),
        ('salt', 'FAM_GARAM')
    ) AS e(phrase_norm, family_id)
      ON e.phrase_norm = fa.phrase_norm AND e.family_id = fa.family_id
    WHERE fa.tenant_id = 'T1';

    IF target <> 6 THEN
        RAISE EXCEPTION 'R06 abort: post-state check failed, % of 6 target aliases present', target;
    END IF;

    -- 历史行按 (alias_id, family_id, phrase_norm) 三元组核对，不断言 language
    -- （库内这 6 条的 language 实际为 NULL；R04 CSV 的 ms 标注只是文档语义，不回填）。
    SELECT count(*) INTO legacy
    FROM family_aliases fa
    JOIN (VALUES
        ('ALS_FAM_007', 'FAM_BERAS', 'beras 大米'),
        ('ALS_FAM_008', 'FAM_BERAS', 'beras'),
        ('ALS_FAM_013', 'FAM_GARAM', 'garam 食盐'),
        ('ALS_FAM_014', 'FAM_GARAM', 'garam'),
        ('ALS_FAM_015', 'FAM_GULA', 'gula 白糖'),
        ('ALS_FAM_016', 'FAM_GULA', 'gula')
    ) AS e(alias_id, family_id, phrase_norm)
      ON e.alias_id = fa.alias_id
     AND e.family_id = fa.family_id
     AND e.phrase_norm = fa.phrase_norm
    WHERE fa.tenant_id = 'T1';

    IF legacy <> 6 THEN
        RAISE EXCEPTION 'R06 abort: legacy alias rows differ from KB-T1-20261022-r1 (% of 6 matched); stop and report', legacy;
    END IF;

    RAISE NOTICE 'R06 v001r2 post-state OK: 6 target aliases present, 6 legacy rows unchanged';
END $$;

COMMIT;

-- 执行后请回传：up 的 NOTICE 行（inserted 数）、前后只读查询输出、执行时间、库名、执行人。
-- 影响行数 0 代表"已加载、未重复插入"；6 代表"本次新增"；其他值脚本已回滚，按 BLOCKED 回报。
