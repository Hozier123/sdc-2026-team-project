import re
from pathlib import Path

from pglast import parse_sql


MIGRATION = Path(__file__).parents[2] / "migrations" / "0001_baseline.sql"
EXPECTED_TABLES = {
    "tenants", "users", "customers", "product_families", "family_aliases",
    "products", "uom_aliases", "customer_tier_prices", "inventory",
    "alias_cache", "inbound_messages", "orders", "draft_versions",
    "approval_requests", "delivery_orders", "activity_log", "audit_logs",
    "field_diffs",
}


def test_migration_defines_the_single_physical_model():
    sql = MIGRATION.read_text(encoding="utf-8")
    tables = set(re.findall(r"CREATE TABLE\s+([a-z_]+)", sql, flags=re.IGNORECASE))
    assert tables == EXPECTED_TABLES
    forbidden = {"drafts", "skus", "draft_lines", "issues", "conditions",
                 "delivery_order_lines", "approval_decisions"}
    assert tables.isdisjoint(forbidden)


def test_migration_contains_immutability_and_uniqueness_guards():
    sql = MIGRATION.read_text(encoding="utf-8")
    required_tokens = {
        "draft_versions_immutable",
        "delivery_orders_immutable",
        "activity_log_append_only",
        "audit_logs_append_only",
        "field_diffs_append_only",
        "approval_request_snapshot_guard",
        "one_pending_approval_per_draft",
        "alias_cache_scope_phrase_unique",
        "customers_tenant_phone_unique",
    }
    for token in required_tokens:
        assert token in sql


def test_migration_parses_as_postgresql_and_contains_review_hardening():
    sql = MIGRATION.read_text(encoding="utf-8")
    assert parse_sql(sql)
    required_fragments = {
        "demo_token_hash text NOT NULL UNIQUE",
        "credit_flag IN ('NONE','OVERDUE_NOTICE')",
        "unit_price_rm > 0",
        "target_type IN ('FAMILY','SKU')",
        "WHERE active",
        "source IN ('PASTE','DEMO','WHATSAPP_SIM')",
        "actor_role text CHECK",
        "reason_code text NOT NULL",
        "TG_OP = 'DELETE'",
        "BEFORE UPDATE OR DELETE ON approval_requests",
    }
    for fragment in required_fragments:
        assert fragment in sql
