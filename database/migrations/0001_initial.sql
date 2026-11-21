-- 0001_initial: the first migration. It already contains tenant_id, so no migration ever adds it (D1).
-- Applied migrations are never edited (CLAUDE.md rule 12). Add 0002_<name>.sql and update
-- schema.sql and the model.
BEGIN;
-- CloudDesk Postgres schema (Supabase SQL editor). 17 tables: 16 data tables + tenants.
-- This file is the authority for the table count. Keep it in step with
-- backend/app/models/entities.py: change both, then add a numbered migration.
--
-- Format rules (tests/unit/sql_ddl.py parses this file):
--   one column per line; constraints inline or as a table-level UNIQUE (...);
--   no quoted identifiers; every statement ends with a semicolon.
-- Ids and tenant_id are uuid so the RLS policy `tenant_id = current_setting(...)::uuid`
-- compares uuid with uuid (the models use String(36)). Plain CREATE TABLE: for a fresh database.

CREATE OR REPLACE FUNCTION set_updated_at() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$;

CREATE TABLE tenants (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    name varchar(200) NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now()
);
CREATE TRIGGER trg_tenants_updated_at BEFORE UPDATE ON tenants FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE TABLE profiles (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    email varchar(320) NOT NULL,
    full_name varchar(200) NOT NULL,
    role varchar(32) NOT NULL DEFAULT 'viewer' CHECK (role IN ('viewer', 'agent', 'admin')),
    avatar_url varchar(500),
    tenant_id uuid NOT NULL REFERENCES tenants(id),
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE (tenant_id, email)
);
CREATE INDEX ix_profiles_tenant_id ON profiles (tenant_id);
CREATE TRIGGER trg_profiles_updated_at BEFORE UPDATE ON profiles FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE TABLE customers (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    name varchar(200) NOT NULL,
    email varchar(320) NOT NULL,
    company varchar(200) NOT NULL DEFAULT '',
    plan_name varchar(50) NOT NULL DEFAULT 'free',
    status varchar(32) NOT NULL DEFAULT 'active',
    region varchar(50) NOT NULL DEFAULT '',
    lifetime_value double precision NOT NULL DEFAULT 0.0,
    tenant_id uuid NOT NULL REFERENCES tenants(id),
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE (tenant_id, email)
);
CREATE INDEX ix_customers_tenant_id ON customers (tenant_id);
CREATE TRIGGER trg_customers_updated_at BEFORE UPDATE ON customers FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE TABLE subscriptions (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    customer_id uuid NOT NULL REFERENCES customers(id),
    plan varchar(50) NOT NULL,
    seats integer NOT NULL DEFAULT 1,
    status varchar(32) NOT NULL DEFAULT 'active',
    renews_at timestamptz,
    mrr double precision NOT NULL DEFAULT 0.0,
    storage_quota_gb double precision NOT NULL DEFAULT 0.0,
    storage_used_gb double precision NOT NULL DEFAULT 0.0,
    api_rate_limit integer NOT NULL DEFAULT 0,
    tenant_id uuid NOT NULL REFERENCES tenants(id),
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX ix_subscriptions_tenant_customer ON subscriptions (tenant_id, customer_id);
CREATE INDEX ix_subscriptions_tenant_id ON subscriptions (tenant_id);
CREATE TRIGGER trg_subscriptions_updated_at BEFORE UPDATE ON subscriptions FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE TABLE workspaces (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    customer_id uuid NOT NULL REFERENCES customers(id),
    name varchar(200) NOT NULL,
    member_count integer NOT NULL DEFAULT 0,
    storage_used_gb double precision NOT NULL DEFAULT 0.0,
    integrations jsonb NOT NULL DEFAULT '[]'::jsonb,
    sso_enabled boolean NOT NULL DEFAULT false,
    tenant_id uuid NOT NULL REFERENCES tenants(id),
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX ix_workspaces_tenant_customer ON workspaces (tenant_id, customer_id);
CREATE INDEX ix_workspaces_tenant_id ON workspaces (tenant_id);
CREATE TRIGGER trg_workspaces_updated_at BEFORE UPDATE ON workspaces FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE TABLE products (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    slug varchar(100) NOT NULL,
    name varchar(200) NOT NULL,
    description text NOT NULL DEFAULT '',
    features jsonb NOT NULL DEFAULT '[]'::jsonb,
    tenant_id uuid NOT NULL REFERENCES tenants(id),
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE (tenant_id, slug)
);
CREATE INDEX ix_products_tenant_id ON products (tenant_id);
CREATE TRIGGER trg_products_updated_at BEFORE UPDATE ON products FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE TABLE tickets (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    ticket_number varchar(32) NOT NULL,
    customer_id uuid NOT NULL REFERENCES customers(id),
    subject varchar(300) NOT NULL,
    body text NOT NULL,
    status varchar(32) NOT NULL DEFAULT 'new' CHECK (status IN ('new', 'in_progress', 'waiting_on_customer', 'waiting_on_approval', 'escalated', 'resolved', 'closed')),
    severity varchar(32) CHECK (severity IN ('low', 'medium', 'high', 'critical')),
    category varchar(32) CHECK (category IN ('login_issue', 'billing', 'api_failure', 'workspace_permissions', 'storage_quota', 'integration', 'feature_request', 'account', 'security', 'other')),
    channel varchar(32) NOT NULL DEFAULT 'web' CHECK (channel IN ('email', 'chat', 'web', 'api')),
    assigned_to varchar(200),
    tags jsonb NOT NULL DEFAULT '[]'::jsonb,
    escalation_required boolean NOT NULL DEFAULT false,
    approval_status varchar(32) NOT NULL DEFAULT 'not_required' CHECK (approval_status IN ('not_required', 'pending', 'approved', 'rejected')),
    resolved_at timestamptz,
    tenant_id uuid NOT NULL REFERENCES tenants(id),
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE (tenant_id, ticket_number)
);
CREATE INDEX ix_tickets_tenant_customer_created ON tickets (tenant_id, customer_id, created_at);
CREATE INDEX ix_tickets_tenant_id ON tickets (tenant_id);
CREATE INDEX ix_tickets_tenant_status_severity ON tickets (tenant_id, status, severity);
CREATE TRIGGER trg_tickets_updated_at BEFORE UPDATE ON tickets FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE TABLE ticket_messages (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    ticket_id uuid NOT NULL REFERENCES tickets(id),
    role varchar(32) NOT NULL CHECK (role IN ('customer', 'agent', 'system', 'ai')),
    author_name varchar(200) NOT NULL DEFAULT '',
    body text NOT NULL,
    internal boolean NOT NULL DEFAULT false,
    attachments jsonb NOT NULL DEFAULT '[]'::jsonb,
    tenant_id uuid NOT NULL REFERENCES tenants(id),
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX ix_ticket_messages_tenant_id ON ticket_messages (tenant_id);
CREATE INDEX ix_ticket_messages_tenant_ticket_created ON ticket_messages (tenant_id, ticket_id, created_at);
CREATE TRIGGER trg_ticket_messages_updated_at BEFORE UPDATE ON ticket_messages FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE TABLE support_articles (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    slug varchar(200) NOT NULL,
    title varchar(300) NOT NULL,
    category varchar(32) NOT NULL CHECK (category IN ('login_issue', 'billing', 'api_failure', 'workspace_permissions', 'storage_quota', 'integration', 'feature_request', 'account', 'security', 'other')),
    tags jsonb NOT NULL DEFAULT '[]'::jsonb,
    summary text NOT NULL DEFAULT '',
    content text NOT NULL,
    tenant_id uuid NOT NULL REFERENCES tenants(id),
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE (tenant_id, slug)
);
CREATE INDEX ix_support_articles_tenant_id ON support_articles (tenant_id);
CREATE TRIGGER trg_support_articles_updated_at BEFORE UPDATE ON support_articles FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE TABLE incidents (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    title varchar(300) NOT NULL,
    status varchar(32) NOT NULL DEFAULT 'investigating',
    severity varchar(32) NOT NULL DEFAULT 'medium' CHECK (severity IN ('low', 'medium', 'high', 'critical')),
    affected_services jsonb NOT NULL DEFAULT '[]'::jsonb,
    description text NOT NULL DEFAULT '',
    started_at timestamptz,
    resolved_at timestamptz,
    tenant_id uuid NOT NULL REFERENCES tenants(id),
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX ix_incidents_tenant_id ON incidents (tenant_id);
CREATE INDEX ix_incidents_tenant_status ON incidents (tenant_id, status);
CREATE TRIGGER trg_incidents_updated_at BEFORE UPDATE ON incidents FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE TABLE workflow_runs (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    ticket_id uuid NOT NULL REFERENCES tickets(id),
    thread_id varchar(100) NOT NULL,
    status varchar(32) NOT NULL DEFAULT 'running' CHECK (status IN ('running', 'waiting_for_approval', 'completed', 'failed', 'escalated')),
    current_node varchar(64),
    state jsonb NOT NULL DEFAULT '{}'::jsonb,
    token_usage jsonb NOT NULL DEFAULT '{}'::jsonb,
    started_at timestamptz,
    finished_at timestamptz,
    duration_ms integer,
    tenant_id uuid NOT NULL REFERENCES tenants(id),
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX ix_workflow_runs_tenant_id ON workflow_runs (tenant_id);
CREATE INDEX ix_workflow_runs_tenant_ticket_started ON workflow_runs (tenant_id, ticket_id, started_at);
CREATE TRIGGER trg_workflow_runs_updated_at BEFORE UPDATE ON workflow_runs FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE TABLE workflow_events (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    workflow_id uuid NOT NULL REFERENCES workflow_runs(id),
    ticket_id uuid NOT NULL REFERENCES tickets(id),
    event_type varchar(32) NOT NULL CHECK (event_type IN ('node_started', 'node_completed', 'tool_called', 'llm_called', 'approval_requested', 'approval_resolved', 'error', 'workflow_completed')),
    node varchar(64),
    tool varchar(64),
    message text NOT NULL DEFAULT '',
    duration_ms integer,
    payload jsonb NOT NULL DEFAULT '{}'::jsonb,
    tenant_id uuid NOT NULL REFERENCES tenants(id),
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX ix_workflow_events_tenant_id ON workflow_events (tenant_id);
CREATE INDEX ix_workflow_events_tenant_workflow_created ON workflow_events (tenant_id, workflow_id, created_at);
CREATE TRIGGER trg_workflow_events_updated_at BEFORE UPDATE ON workflow_events FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE TABLE resolution_actions (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    ticket_id uuid NOT NULL REFERENCES tickets(id),
    workflow_id uuid NOT NULL REFERENCES workflow_runs(id),
    tool varchar(64) NOT NULL,
    arguments jsonb NOT NULL DEFAULT '{}'::jsonb,
    status varchar(32) NOT NULL DEFAULT 'planned' CHECK (status IN ('planned', 'pending_approval', 'approved', 'executed', 'rejected', 'failed')),
    result jsonb,
    requires_approval boolean NOT NULL DEFAULT false,
    idempotency_key varchar(200) NOT NULL,
    verification jsonb,
    executed_at timestamptz,
    tenant_id uuid NOT NULL REFERENCES tenants(id),
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE (tenant_id, idempotency_key)
);
CREATE INDEX ix_resolution_actions_tenant_id ON resolution_actions (tenant_id);
CREATE TRIGGER trg_resolution_actions_updated_at BEFORE UPDATE ON resolution_actions FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE TABLE approval_requests (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    ticket_id uuid NOT NULL REFERENCES tickets(id),
    workflow_id uuid NOT NULL REFERENCES workflow_runs(id),
    action jsonb NOT NULL DEFAULT '{}'::jsonb,
    risk_level varchar(16) NOT NULL DEFAULT 'high',
    reason text NOT NULL DEFAULT '',
    requested_by varchar(64) NOT NULL DEFAULT 'ai',
    status varchar(32) NOT NULL DEFAULT 'pending' CHECK (status IN ('not_required', 'pending', 'approved', 'rejected')),
    decided_by varchar(200),
    decision_note text,
    decided_at timestamptz,
    expires_at timestamptz,
    tenant_id uuid NOT NULL REFERENCES tenants(id),
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX ix_approval_requests_tenant_id ON approval_requests (tenant_id);
CREATE INDEX ix_approval_requests_tenant_status ON approval_requests (tenant_id, status);
CREATE TRIGGER trg_approval_requests_updated_at BEFORE UPDATE ON approval_requests FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE TABLE escalations (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    ticket_id uuid NOT NULL REFERENCES tickets(id),
    reason text NOT NULL,
    priority varchar(16) NOT NULL DEFAULT 'normal',
    status varchar(32) NOT NULL DEFAULT 'open' CHECK (status IN ('open', 'acknowledged', 'resolved')),
    created_by varchar(200) NOT NULL DEFAULT 'ai',
    assigned_team varchar(100) NOT NULL DEFAULT '',
    resolved_at timestamptz,
    tenant_id uuid NOT NULL REFERENCES tenants(id),
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX ix_escalations_tenant_id ON escalations (tenant_id);
CREATE INDEX ix_escalations_tenant_status ON escalations (tenant_id, status);
CREATE TRIGGER trg_escalations_updated_at BEFORE UPDATE ON escalations FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE TABLE customer_memory (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    customer_id uuid NOT NULL REFERENCES customers(id),
    memory_type varchar(32) NOT NULL CHECK (memory_type IN ('preference', 'past_issue', 'troubleshooting', 'note')),
    content text NOT NULL,
    source_ticket_id uuid REFERENCES tickets(id),
    confidence double precision,
    tenant_id uuid NOT NULL REFERENCES tenants(id),
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX ix_customer_memory_tenant_customer_type ON customer_memory (tenant_id, customer_id, memory_type);
CREATE INDEX ix_customer_memory_tenant_id ON customer_memory (tenant_id);
CREATE TRIGGER trg_customer_memory_updated_at BEFORE UPDATE ON customer_memory FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE TABLE audit_logs (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    actor varchar(200) NOT NULL DEFAULT '',
    actor_type varchar(32) NOT NULL DEFAULT 'user',
    action varchar(200) NOT NULL,
    resource_type varchar(64) NOT NULL DEFAULT '',
    resource_id varchar(64) NOT NULL DEFAULT '',
    details jsonb NOT NULL DEFAULT '{}'::jsonb,
    request_id varchar(64) NOT NULL DEFAULT '',
    tenant_id uuid NOT NULL REFERENCES tenants(id),
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX ix_audit_logs_tenant_created ON audit_logs (tenant_id, created_at);
CREATE INDEX ix_audit_logs_tenant_id ON audit_logs (tenant_id);
CREATE TRIGGER trg_audit_logs_updated_at BEFORE UPDATE ON audit_logs FOR EACH ROW EXECUTE FUNCTION set_updated_at();

-- Row-level security keyed on tenant_id (D1, CLAUDE.md section 6). The API sets
-- SET LOCAL app.tenant_id per transaction. FORCE binds the table owner too.
-- Note: Supabase's service_role has BYPASSRLS, so on Supabase these policies do not
-- constrain a backend that connects with it; the repository filter remains the boundary.
-- Re-runnable: each policy is dropped before it is created.

ALTER TABLE tenants ENABLE ROW LEVEL SECURITY;
ALTER TABLE tenants FORCE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS tenant_isolation ON tenants;
CREATE POLICY tenant_isolation ON tenants FOR ALL USING (id = current_setting('app.tenant_id')::uuid) WITH CHECK (id = current_setting('app.tenant_id')::uuid);

ALTER TABLE profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE profiles FORCE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS tenant_isolation ON profiles;
CREATE POLICY tenant_isolation ON profiles FOR ALL USING (tenant_id = current_setting('app.tenant_id')::uuid) WITH CHECK (tenant_id = current_setting('app.tenant_id')::uuid);

ALTER TABLE customers ENABLE ROW LEVEL SECURITY;
ALTER TABLE customers FORCE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS tenant_isolation ON customers;
CREATE POLICY tenant_isolation ON customers FOR ALL USING (tenant_id = current_setting('app.tenant_id')::uuid) WITH CHECK (tenant_id = current_setting('app.tenant_id')::uuid);

ALTER TABLE subscriptions ENABLE ROW LEVEL SECURITY;
ALTER TABLE subscriptions FORCE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS tenant_isolation ON subscriptions;
CREATE POLICY tenant_isolation ON subscriptions FOR ALL USING (tenant_id = current_setting('app.tenant_id')::uuid) WITH CHECK (tenant_id = current_setting('app.tenant_id')::uuid);

ALTER TABLE workspaces ENABLE ROW LEVEL SECURITY;
ALTER TABLE workspaces FORCE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS tenant_isolation ON workspaces;
CREATE POLICY tenant_isolation ON workspaces FOR ALL USING (tenant_id = current_setting('app.tenant_id')::uuid) WITH CHECK (tenant_id = current_setting('app.tenant_id')::uuid);

ALTER TABLE products ENABLE ROW LEVEL SECURITY;
ALTER TABLE products FORCE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS tenant_isolation ON products;
CREATE POLICY tenant_isolation ON products FOR ALL USING (tenant_id = current_setting('app.tenant_id')::uuid) WITH CHECK (tenant_id = current_setting('app.tenant_id')::uuid);

ALTER TABLE tickets ENABLE ROW LEVEL SECURITY;
ALTER TABLE tickets FORCE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS tenant_isolation ON tickets;
CREATE POLICY tenant_isolation ON tickets FOR ALL USING (tenant_id = current_setting('app.tenant_id')::uuid) WITH CHECK (tenant_id = current_setting('app.tenant_id')::uuid);

ALTER TABLE ticket_messages ENABLE ROW LEVEL SECURITY;
ALTER TABLE ticket_messages FORCE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS tenant_isolation ON ticket_messages;
CREATE POLICY tenant_isolation ON ticket_messages FOR ALL USING (tenant_id = current_setting('app.tenant_id')::uuid) WITH CHECK (tenant_id = current_setting('app.tenant_id')::uuid);

ALTER TABLE support_articles ENABLE ROW LEVEL SECURITY;
ALTER TABLE support_articles FORCE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS tenant_isolation ON support_articles;
CREATE POLICY tenant_isolation ON support_articles FOR ALL USING (tenant_id = current_setting('app.tenant_id')::uuid) WITH CHECK (tenant_id = current_setting('app.tenant_id')::uuid);

ALTER TABLE incidents ENABLE ROW LEVEL SECURITY;
ALTER TABLE incidents FORCE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS tenant_isolation ON incidents;
CREATE POLICY tenant_isolation ON incidents FOR ALL USING (tenant_id = current_setting('app.tenant_id')::uuid) WITH CHECK (tenant_id = current_setting('app.tenant_id')::uuid);

ALTER TABLE workflow_runs ENABLE ROW LEVEL SECURITY;
ALTER TABLE workflow_runs FORCE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS tenant_isolation ON workflow_runs;
CREATE POLICY tenant_isolation ON workflow_runs FOR ALL USING (tenant_id = current_setting('app.tenant_id')::uuid) WITH CHECK (tenant_id = current_setting('app.tenant_id')::uuid);

ALTER TABLE workflow_events ENABLE ROW LEVEL SECURITY;
ALTER TABLE workflow_events FORCE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS tenant_isolation ON workflow_events;
CREATE POLICY tenant_isolation ON workflow_events FOR ALL USING (tenant_id = current_setting('app.tenant_id')::uuid) WITH CHECK (tenant_id = current_setting('app.tenant_id')::uuid);

ALTER TABLE resolution_actions ENABLE ROW LEVEL SECURITY;
ALTER TABLE resolution_actions FORCE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS tenant_isolation ON resolution_actions;
CREATE POLICY tenant_isolation ON resolution_actions FOR ALL USING (tenant_id = current_setting('app.tenant_id')::uuid) WITH CHECK (tenant_id = current_setting('app.tenant_id')::uuid);

ALTER TABLE approval_requests ENABLE ROW LEVEL SECURITY;
ALTER TABLE approval_requests FORCE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS tenant_isolation ON approval_requests;
CREATE POLICY tenant_isolation ON approval_requests FOR ALL USING (tenant_id = current_setting('app.tenant_id')::uuid) WITH CHECK (tenant_id = current_setting('app.tenant_id')::uuid);

ALTER TABLE escalations ENABLE ROW LEVEL SECURITY;
ALTER TABLE escalations FORCE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS tenant_isolation ON escalations;
CREATE POLICY tenant_isolation ON escalations FOR ALL USING (tenant_id = current_setting('app.tenant_id')::uuid) WITH CHECK (tenant_id = current_setting('app.tenant_id')::uuid);

ALTER TABLE customer_memory ENABLE ROW LEVEL SECURITY;
ALTER TABLE customer_memory FORCE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS tenant_isolation ON customer_memory;
CREATE POLICY tenant_isolation ON customer_memory FOR ALL USING (tenant_id = current_setting('app.tenant_id')::uuid) WITH CHECK (tenant_id = current_setting('app.tenant_id')::uuid);

ALTER TABLE audit_logs ENABLE ROW LEVEL SECURITY;
ALTER TABLE audit_logs FORCE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS tenant_isolation ON audit_logs;
CREATE POLICY tenant_isolation ON audit_logs FOR ALL USING (tenant_id = current_setting('app.tenant_id')::uuid) WITH CHECK (tenant_id = current_setting('app.tenant_id')::uuid);

COMMIT;
