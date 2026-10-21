BEGIN;

CREATE TABLE tenants (
  tenant_id text PRIMARY KEY,
  name text NOT NULL,
  timezone text NOT NULL DEFAULT 'Asia/Kuala_Lumpur',
  currency text NOT NULL DEFAULT 'MYR' CHECK (currency = 'MYR'),
  amount_threshold_rm numeric(12,2) NOT NULL CHECK (amount_threshold_rm >= 0),
  checks_enabled jsonb NOT NULL DEFAULT '{}'::jsonb CHECK (jsonb_typeof(checks_enabled) = 'object'),
  below_tier_price_override_requires_owner boolean NOT NULL DEFAULT true,
  credit_flag_requires_owner boolean NOT NULL DEFAULT true,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE users (
  user_id text PRIMARY KEY,
  tenant_id text NOT NULL REFERENCES tenants(tenant_id),
  display_name text NOT NULL,
  demo_token_hash text NOT NULL UNIQUE,
  role text NOT NULL CHECK (role IN ('CLERK','OWNER','WAREHOUSE')),
  active boolean NOT NULL DEFAULT true,
  created_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (tenant_id, user_id)
);

CREATE TABLE customers (
  customer_id text PRIMARY KEY,
  tenant_id text NOT NULL REFERENCES tenants(tenant_id),
  name text NOT NULL,
  phone_e164 text,
  tier text NOT NULL,
  credit_flag text NOT NULL DEFAULT 'NONE'
    CHECK (credit_flag IN ('NONE','OVERDUE_NOTICE')),
  active boolean NOT NULL DEFAULT true,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (tenant_id, customer_id)
);
CREATE UNIQUE INDEX customers_tenant_phone_unique
  ON customers (tenant_id, phone_e164) WHERE phone_e164 IS NOT NULL;

CREATE TABLE product_families (
  family_id text PRIMARY KEY,
  tenant_id text NOT NULL REFERENCES tenants(tenant_id),
  family_name text NOT NULL,
  family_version integer NOT NULL DEFAULT 1 CHECK (family_version > 0),
  active boolean NOT NULL DEFAULT true,
  created_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (tenant_id, family_id)
);

CREATE TABLE family_aliases (
  alias_id text PRIMARY KEY,
  tenant_id text NOT NULL REFERENCES tenants(tenant_id),
  family_id text NOT NULL,
  language text,
  phrase text NOT NULL,
  phrase_norm text NOT NULL CHECK (length(phrase_norm) > 0),
  created_at timestamptz NOT NULL DEFAULT now(),
  FOREIGN KEY (tenant_id, family_id)
    REFERENCES product_families(tenant_id, family_id),
  UNIQUE (tenant_id, phrase_norm)
);

CREATE TABLE products (
  product_id text PRIMARY KEY,
  tenant_id text NOT NULL REFERENCES tenants(tenant_id),
  family_id text NOT NULL,
  sku_code text NOT NULL,
  name text NOT NULL,
  pack_size text,
  grade text,
  base_unit text NOT NULL,
  active boolean NOT NULL DEFAULT true,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  FOREIGN KEY (tenant_id, family_id)
    REFERENCES product_families(tenant_id, family_id),
  UNIQUE (tenant_id, product_id),
  UNIQUE (tenant_id, sku_code)
);

CREATE TABLE uom_aliases (
  alias_id text PRIMARY KEY,
  tenant_id text NOT NULL REFERENCES tenants(tenant_id),
  canonical_unit text NOT NULL,
  language text,
  alias text NOT NULL,
  alias_norm text NOT NULL CHECK (length(alias_norm) > 0),
  created_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (tenant_id, alias_norm)
);

CREATE TABLE customer_tier_prices (
  tenant_id text NOT NULL REFERENCES tenants(tenant_id),
  product_id text NOT NULL,
  tier text NOT NULL,
  unit_price_rm numeric(12,2) NOT NULL CHECK (unit_price_rm > 0),
  updated_at timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (tenant_id, product_id, tier),
  FOREIGN KEY (tenant_id, product_id)
    REFERENCES products(tenant_id, product_id)
);

CREATE TABLE inventory (
  tenant_id text NOT NULL REFERENCES tenants(tenant_id),
  product_id text NOT NULL,
  available_qty integer NOT NULL CHECK (available_qty >= 0),
  updated_at timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (tenant_id, product_id),
  FOREIGN KEY (tenant_id, product_id)
    REFERENCES products(tenant_id, product_id)
);

CREATE TABLE alias_cache (
  alias_id text PRIMARY KEY,
  tenant_id text NOT NULL REFERENCES tenants(tenant_id),
  customer_id text,
  phrase text NOT NULL,
  phrase_norm text NOT NULL CHECK (length(phrase_norm) > 0),
  target_type text NOT NULL CHECK (target_type IN ('FAMILY','SKU')),
  family_id text,
  product_id text,
  active boolean NOT NULL DEFAULT true,
  revoked_at timestamptz,
  confirmed_by text NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  FOREIGN KEY (tenant_id, customer_id)
    REFERENCES customers(tenant_id, customer_id),
  FOREIGN KEY (tenant_id, family_id)
    REFERENCES product_families(tenant_id, family_id),
  FOREIGN KEY (tenant_id, product_id)
    REFERENCES products(tenant_id, product_id),
  FOREIGN KEY (tenant_id, confirmed_by)
    REFERENCES users(tenant_id, user_id),
  CHECK (
    (target_type = 'FAMILY' AND family_id IS NOT NULL AND product_id IS NULL)
    OR
    (target_type = 'SKU' AND product_id IS NOT NULL AND family_id IS NULL)
  ),
  CHECK (
    (active AND revoked_at IS NULL)
    OR
    (NOT active AND revoked_at IS NOT NULL)
  )
);
CREATE UNIQUE INDEX alias_cache_scope_phrase_unique
  ON alias_cache (tenant_id, COALESCE(customer_id, ''), phrase_norm)
  WHERE active;

CREATE TABLE inbound_messages (
  tenant_id text NOT NULL REFERENCES tenants(tenant_id),
  message_id text NOT NULL,
  customer_id text NOT NULL,
  source text NOT NULL CHECK (source IN ('PASTE','DEMO','WHATSAPP_SIM')),
  masked_text text NOT NULL CHECK (length(masked_text) <= 4000),
  language text,
  received_at timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (tenant_id, message_id),
  FOREIGN KEY (tenant_id, customer_id)
    REFERENCES customers(tenant_id, customer_id)
);

CREATE TABLE orders (
  tenant_id text NOT NULL REFERENCES tenants(tenant_id),
  draft_id text NOT NULL,
  customer_id text NOT NULL,
  message_id text,
  status text NOT NULL CHECK (status IN (
    'DISAMBIGUATION_REQUIRED','READY_FOR_APPROVAL',
    'PENDING_OWNER_APPROVAL','DO_GENERATED','REJECTED'
  )),
  version integer NOT NULL DEFAULT 1 CHECK (version > 0),
  ai_mode text NOT NULL CHECK (ai_mode IN ('LLM','FALLBACK','ALIAS_ONLY','MIXED')),
  ai_initial_snapshot jsonb,
  working_lines jsonb NOT NULL DEFAULT '[]'::jsonb CHECK (jsonb_typeof(working_lines) = 'array'),
  issues jsonb NOT NULL DEFAULT '[]'::jsonb CHECK (jsonb_typeof(issues) = 'array'),
  clarification jsonb,
  escalation_preview jsonb NOT NULL DEFAULT '[]'::jsonb CHECK (jsonb_typeof(escalation_preview) = 'array'),
  termination_reason text CHECK (termination_reason IN (
    'OWNER_REJECTED','CLERK_DISCARDED','SYSTEM_TERMINATED'
  )),
  terminated_by_user_id text,
  termination_note text CHECK (termination_note IS NULL OR length(termination_note) <= 500),
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (tenant_id, draft_id),
  FOREIGN KEY (tenant_id, customer_id)
    REFERENCES customers(tenant_id, customer_id),
  FOREIGN KEY (tenant_id, message_id)
    REFERENCES inbound_messages(tenant_id, message_id),
  FOREIGN KEY (tenant_id, terminated_by_user_id)
    REFERENCES users(tenant_id, user_id),
  CHECK (ai_initial_snapshot IS NULL OR jsonb_typeof(ai_initial_snapshot) = 'object'),
  CHECK (clarification IS NULL OR jsonb_typeof(clarification) = 'object'),
  CHECK (
    (status <> 'REJECTED' AND termination_reason IS NULL
      AND terminated_by_user_id IS NULL AND termination_note IS NULL)
    OR
    (status = 'REJECTED' AND termination_reason IS NOT NULL)
  ),
  CHECK (
    termination_reason IS NULL
    OR termination_reason = 'SYSTEM_TERMINATED'
    OR (terminated_by_user_id IS NOT NULL AND length(btrim(termination_note)) > 0)
  )
);

CREATE TABLE draft_versions (
  tenant_id text NOT NULL,
  draft_id text NOT NULL,
  version integer NOT NULL CHECK (version > 0),
  snapshot jsonb NOT NULL CHECK (jsonb_typeof(snapshot) = 'object'),
  created_by text NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (tenant_id, draft_id, version),
  FOREIGN KEY (tenant_id, draft_id)
    REFERENCES orders(tenant_id, draft_id),
  FOREIGN KEY (tenant_id, created_by)
    REFERENCES users(tenant_id, user_id)
);

CREATE TABLE approval_requests (
  approval_id text PRIMARY KEY,
  tenant_id text NOT NULL REFERENCES tenants(tenant_id),
  draft_id text NOT NULL,
  draft_version integer NOT NULL CHECK (draft_version > 0),
  status text NOT NULL CHECK (status IN ('PENDING','APPROVED','REJECTED')),
  reasons jsonb NOT NULL CHECK (jsonb_typeof(reasons) = 'array'),
  snapshot jsonb NOT NULL CHECK (jsonb_typeof(snapshot) = 'object'),
  requested_by text NOT NULL,
  requested_at timestamptz NOT NULL DEFAULT now(),
  decided_by text,
  decided_at timestamptz,
  decision_note text CHECK (decision_note IS NULL OR length(decision_note) <= 500),
  FOREIGN KEY (tenant_id, draft_id, draft_version)
    REFERENCES draft_versions(tenant_id, draft_id, version),
  FOREIGN KEY (tenant_id, requested_by)
    REFERENCES users(tenant_id, user_id),
  FOREIGN KEY (tenant_id, decided_by)
    REFERENCES users(tenant_id, user_id),
  CHECK (
    (status = 'PENDING' AND decided_by IS NULL AND decided_at IS NULL AND decision_note IS NULL)
    OR
    (status = 'APPROVED' AND decided_by IS NOT NULL AND decided_at IS NOT NULL)
    OR
    (status = 'REJECTED' AND decided_by IS NOT NULL AND decided_at IS NOT NULL
      AND length(btrim(decision_note)) > 0)
  )
);
CREATE UNIQUE INDEX one_pending_approval_per_draft
  ON approval_requests (tenant_id, draft_id) WHERE status = 'PENDING';

CREATE TABLE delivery_orders (
  do_number text PRIMARY KEY,
  tenant_id text NOT NULL REFERENCES tenants(tenant_id),
  draft_id text NOT NULL,
  draft_version integer NOT NULL CHECK (draft_version > 0),
  customer_id text NOT NULL,
  lines jsonb NOT NULL CHECK (jsonb_typeof(lines) = 'array'),
  final_total_rm numeric(12,2) NOT NULL CHECK (final_total_rm >= 0),
  prepared_by text NOT NULL,
  approved_by text NOT NULL,
  escalation_reasons jsonb NOT NULL DEFAULT '[]'::jsonb CHECK (jsonb_typeof(escalation_reasons) = 'array'),
  approval_mode text NOT NULL CHECK (approval_mode IN ('DIRECT','OWNER_APPROVED','OWNER_SELF_APPROVED')),
  reply_draft jsonb NOT NULL CHECK (jsonb_typeof(reply_draft) = 'object'),
  related_do_number text REFERENCES delivery_orders(do_number),
  approved_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (tenant_id, do_number),
  UNIQUE (tenant_id, draft_id),
  FOREIGN KEY (tenant_id, draft_id, draft_version)
    REFERENCES draft_versions(tenant_id, draft_id, version),
  FOREIGN KEY (tenant_id, customer_id)
    REFERENCES customers(tenant_id, customer_id),
  FOREIGN KEY (tenant_id, prepared_by)
    REFERENCES users(tenant_id, user_id),
  FOREIGN KEY (tenant_id, approved_by)
    REFERENCES users(tenant_id, user_id)
);

CREATE TABLE activity_log (
  activity_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  tenant_id text NOT NULL REFERENCES tenants(tenant_id),
  draft_id text,
  do_number text,
  event_type text NOT NULL,
  payload jsonb NOT NULL DEFAULT '{}'::jsonb CHECK (jsonb_typeof(payload) = 'object'),
  actor_user_id text,
  actor_role text CHECK (actor_role IN ('CLERK','OWNER','WAREHOUSE')),
  created_at timestamptz NOT NULL DEFAULT now(),
  FOREIGN KEY (tenant_id, draft_id)
    REFERENCES orders(tenant_id, draft_id),
  FOREIGN KEY (tenant_id, do_number)
    REFERENCES delivery_orders(tenant_id, do_number),
  FOREIGN KEY (tenant_id, actor_user_id)
    REFERENCES users(tenant_id, user_id)
);

CREATE TABLE audit_logs (
  audit_id text PRIMARY KEY,
  tenant_id text NOT NULL REFERENCES tenants(tenant_id),
  draft_id text NOT NULL,
  draft_version integer NOT NULL CHECK (draft_version > 0),
  do_number text,
  actor_user_id text,
  actor_role text CHECK (actor_role IN ('CLERK','OWNER','WAREHOUSE')),
  action text NOT NULL,
  payload jsonb NOT NULL DEFAULT '{}'::jsonb CHECK (jsonb_typeof(payload) = 'object'),
  created_at timestamptz NOT NULL DEFAULT now(),
  FOREIGN KEY (tenant_id, draft_id, draft_version)
    REFERENCES draft_versions(tenant_id, draft_id, version),
  FOREIGN KEY (tenant_id, do_number)
    REFERENCES delivery_orders(tenant_id, do_number),
  FOREIGN KEY (tenant_id, actor_user_id)
    REFERENCES users(tenant_id, user_id)
);

CREATE TABLE field_diffs (
  field_diff_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  audit_id text NOT NULL REFERENCES audit_logs(audit_id),
  draft_version integer NOT NULL CHECK (draft_version > 0),
  line_id text,
  field_path text NOT NULL,
  before_value jsonb,
  after_value jsonb,
  source text NOT NULL,
  reason_code text NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE OR REPLACE FUNCTION kiraorder_forbid_update_delete()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
  RAISE EXCEPTION '% is append-only/immutable; % is forbidden', TG_TABLE_NAME, TG_OP
    USING ERRCODE = '55000';
END;
$$;

CREATE TRIGGER draft_versions_immutable
  BEFORE UPDATE OR DELETE ON draft_versions
  FOR EACH ROW EXECUTE FUNCTION kiraorder_forbid_update_delete();

CREATE TRIGGER delivery_orders_immutable
  BEFORE UPDATE OR DELETE ON delivery_orders
  FOR EACH ROW EXECUTE FUNCTION kiraorder_forbid_update_delete();

CREATE TRIGGER activity_log_append_only
  BEFORE UPDATE OR DELETE ON activity_log
  FOR EACH ROW EXECUTE FUNCTION kiraorder_forbid_update_delete();

CREATE TRIGGER audit_logs_append_only
  BEFORE UPDATE OR DELETE ON audit_logs
  FOR EACH ROW EXECUTE FUNCTION kiraorder_forbid_update_delete();

CREATE TRIGGER field_diffs_append_only
  BEFORE UPDATE OR DELETE ON field_diffs
  FOR EACH ROW EXECUTE FUNCTION kiraorder_forbid_update_delete();

CREATE OR REPLACE FUNCTION kiraorder_guard_approval_request()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
  IF TG_OP = 'DELETE' THEN
    RAISE EXCEPTION 'approval request is immutable and may not be deleted'
      USING ERRCODE = '55000';
  END IF;

  IF OLD.tenant_id IS DISTINCT FROM NEW.tenant_id
     OR OLD.draft_id IS DISTINCT FROM NEW.draft_id
     OR OLD.draft_version IS DISTINCT FROM NEW.draft_version
     OR OLD.reasons IS DISTINCT FROM NEW.reasons
     OR OLD.snapshot IS DISTINCT FROM NEW.snapshot
     OR OLD.requested_by IS DISTINCT FROM NEW.requested_by
     OR OLD.requested_at IS DISTINCT FROM NEW.requested_at THEN
    RAISE EXCEPTION 'approval request submission snapshot is immutable'
      USING ERRCODE = '55000';
  END IF;

  IF OLD.status <> 'PENDING' THEN
    RAISE EXCEPTION 'decided approval request is immutable'
      USING ERRCODE = '55000';
  END IF;

  IF NEW.status NOT IN ('APPROVED','REJECTED') THEN
    RAISE EXCEPTION 'approval request may only transition from PENDING to APPROVED or REJECTED'
      USING ERRCODE = '23514';
  END IF;

  RETURN NEW;
END;
$$;

CREATE TRIGGER approval_request_snapshot_guard
  BEFORE UPDATE OR DELETE ON approval_requests
  FOR EACH ROW EXECUTE FUNCTION kiraorder_guard_approval_request();

CREATE INDEX orders_tenant_status_updated_idx
  ON orders (tenant_id, status, updated_at DESC);
CREATE INDEX approvals_tenant_status_requested_idx
  ON approval_requests (tenant_id, status, requested_at DESC);
CREATE INDEX activity_tenant_created_idx
  ON activity_log (tenant_id, created_at DESC);
CREATE INDEX audit_draft_version_idx
  ON audit_logs (tenant_id, draft_id, draft_version);
CREATE INDEX field_diffs_audit_idx
  ON field_diffs (audit_id);

COMMIT;
