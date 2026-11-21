-- Seeds the one demo tenant. Demo data comes from sample_data/*.json via bootstrap_demo_data().
-- The id must equal DEMO_TENANT_ID in backend/app/models/entities.py.
BEGIN;
SET LOCAL app.tenant_id = '00000000-0000-4000-8000-000000000001';
INSERT INTO tenants (id, name) VALUES ('00000000-0000-4000-8000-000000000001', 'CloudDesk Demo') ON CONFLICT (id) DO NOTHING;
COMMIT;
