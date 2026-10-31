-- R06 trilingual family-alias rollback — revision r2 (DRAFT)
-- Owner of execution: He (R06). Author of content: Zhou (R04).
-- Data version: TRILINGUAL-2026-10-31-v001 (UNCHANGED). Patch revision: r2.
-- Supersedes R06_trilingual_20261031_v001_down.sql for execution; v001 is kept for archive.
--
-- Why r2 exists (He's review, 2026-11-01 00:57 UTC+8): v001 left the affected-row check to a
-- human comment placed after COMMIT. r2 asserts inside the transaction and rolls back on any
-- unexpected count. No change to what is deleted: only the six aliases created by this patch.
--
-- Removes only the six aliases created by v001/v001r2.
-- Does not touch historical aliases, alias_cache, or any human-confirmed memory.
--
-- Safe to run as one file: it either commits the intended rollback or aborts with no change.

BEGIN;

DO $$
DECLARE
    removed integer;
    legacy integer;
BEGIN
    DELETE FROM family_aliases
    WHERE tenant_id = 'T1'
      AND (alias_id, phrase_norm, family_id) IN (
          ('ALS_TRIL_20261031_GULA_ZH', '白糖', 'FAM_GULA'),
          ('ALS_TRIL_20261031_GULA_EN', 'sugar', 'FAM_GULA'),
          ('ALS_TRIL_20261031_BERAS_ZH', '大米', 'FAM_BERAS'),
          ('ALS_TRIL_20261031_BERAS_EN', 'rice', 'FAM_BERAS'),
          ('ALS_TRIL_20261031_GARAM_ZH', '食盐', 'FAM_GARAM'),
          ('ALS_TRIL_20261031_GARAM_EN', 'salt', 'FAM_GARAM')
      );

    GET DIAGNOSTICS removed = ROW_COUNT;
    RAISE NOTICE 'R06 v001r2 rollback removed rows: %', removed;

    IF removed NOT IN (0, 6) THEN
        RAISE EXCEPTION 'R06 rollback abort: unexpected affected row count % (expected 0 or 6)', removed;
    END IF;

    -- 历史别名必须仍在：撤回只撤本轮新增，不碰 KB-T1-20261022-r1 的行。
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
        RAISE EXCEPTION 'R06 rollback abort: legacy alias rows missing or changed (% of 6); stop and report', legacy;
    END IF;

    -- 本轮 6 条应已不存在。
    IF EXISTS (
        SELECT 1 FROM family_aliases
        WHERE tenant_id = 'T1'
          AND alias_id IN (
              'ALS_TRIL_20261031_GULA_ZH','ALS_TRIL_20261031_GULA_EN',
              'ALS_TRIL_20261031_BERAS_ZH','ALS_TRIL_20261031_BERAS_EN',
              'ALS_TRIL_20261031_GARAM_ZH','ALS_TRIL_20261031_GARAM_EN'
          )
    ) THEN
        RAISE EXCEPTION 'R06 rollback abort: patch rows still present after delete';
    END IF;

    RAISE NOTICE 'R06 v001r2 rollback post-state OK: patch rows gone, 6 legacy rows intact';
END $$;

COMMIT;

-- 若 removed 不是 0/6，或历史行校验失败，脚本已回滚：不要按 phrase 单独强删，按 BLOCKED 回报。
