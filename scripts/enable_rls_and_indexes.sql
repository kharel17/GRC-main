-- GRC Platform — Enable Row Level Security and Indexes
-- Enforces multi-tenancy at the database level.

-- Disable all policies before recreating to avoid errors if run multiple times.
-- Also drop policies if they exist.
DROP POLICY IF EXISTS org_isolation ON risks;
DROP POLICY IF EXISTS org_isolation ON controls;
DROP POLICY IF EXISTS org_isolation ON evidence;
DROP POLICY IF EXISTS org_isolation ON tickets;
DROP POLICY IF EXISTS org_isolation ON assets;
DROP POLICY IF EXISTS org_isolation ON compliance_items;
DROP POLICY IF EXISTS org_isolation ON control_applicability;
DROP POLICY IF EXISTS org_isolation ON document_analyses;
DROP POLICY IF EXISTS org_isolation ON audit_logs;
DROP POLICY IF EXISTS org_isolation ON ticket_comments;
DROP POLICY IF EXISTS org_isolation ON ticket_activities;
DROP POLICY IF EXISTS org_isolation ON asset_risk_mapping;
DROP POLICY IF EXISTS org_isolation ON risk_control_mappings;
DROP POLICY IF EXISTS org_isolation ON evidence_control_matches;

-- 1. Enable Row Level Security (RLS) and FORCE it (so table owner is subject to RLS) on primary scoped tables
ALTER TABLE risks ENABLE ROW LEVEL SECURITY;
ALTER TABLE risks FORCE ROW LEVEL SECURITY;

ALTER TABLE controls ENABLE ROW LEVEL SECURITY;
ALTER TABLE controls FORCE ROW LEVEL SECURITY;

ALTER TABLE evidence ENABLE ROW LEVEL SECURITY;
ALTER TABLE evidence FORCE ROW LEVEL SECURITY;

ALTER TABLE tickets ENABLE ROW LEVEL SECURITY;
ALTER TABLE tickets FORCE ROW LEVEL SECURITY;

ALTER TABLE assets ENABLE ROW LEVEL SECURITY;
ALTER TABLE assets FORCE ROW LEVEL SECURITY;

ALTER TABLE compliance_items ENABLE ROW LEVEL SECURITY;
ALTER TABLE compliance_items FORCE ROW LEVEL SECURITY;

ALTER TABLE control_applicability ENABLE ROW LEVEL SECURITY;
ALTER TABLE control_applicability FORCE ROW LEVEL SECURITY;

ALTER TABLE document_analyses ENABLE ROW LEVEL SECURITY;
ALTER TABLE document_analyses FORCE ROW LEVEL SECURITY;

-- 2. Enable RLS and FORCE it on relationally scoped tables
ALTER TABLE audit_logs ENABLE ROW LEVEL SECURITY;
ALTER TABLE audit_logs FORCE ROW LEVEL SECURITY;

ALTER TABLE ticket_comments ENABLE ROW LEVEL SECURITY;
ALTER TABLE ticket_comments FORCE ROW LEVEL SECURITY;

ALTER TABLE ticket_activities ENABLE ROW LEVEL SECURITY;
ALTER TABLE ticket_activities FORCE ROW LEVEL SECURITY;

ALTER TABLE asset_risk_mapping ENABLE ROW LEVEL SECURITY;
ALTER TABLE asset_risk_mapping FORCE ROW LEVEL SECURITY;

ALTER TABLE risk_control_mappings ENABLE ROW LEVEL SECURITY;
ALTER TABLE risk_control_mappings FORCE ROW LEVEL SECURITY;

ALTER TABLE evidence_control_matches ENABLE ROW LEVEL SECURITY;
ALTER TABLE evidence_control_matches FORCE ROW LEVEL SECURITY;

-- 3. Define Policies for primary scoped tables
CREATE POLICY org_isolation ON risks
  USING (organization_id = current_setting('app.org_id', true)::uuid);

CREATE POLICY org_isolation ON controls
  USING (organization_id = current_setting('app.org_id', true)::uuid);

CREATE POLICY org_isolation ON evidence
  USING (organization_id = current_setting('app.org_id', true)::uuid);

CREATE POLICY org_isolation ON tickets
  USING (organization_id = current_setting('app.org_id', true)::uuid);

CREATE POLICY org_isolation ON assets
  USING (organization_id = current_setting('app.org_id', true)::uuid);

CREATE POLICY org_isolation ON compliance_items
  USING (organization_id = current_setting('app.org_id', true)::uuid);

CREATE POLICY org_isolation ON control_applicability
  USING (organization_id = current_setting('app.org_id', true)::uuid);

CREATE POLICY org_isolation ON document_analyses
  USING (organization_id = current_setting('app.org_id', true)::uuid);

-- 4. Define Policies for relationally scoped tables
CREATE POLICY org_isolation ON audit_logs
  USING (user_id IN (SELECT id FROM users WHERE organization_id = current_setting('app.org_id', true)::uuid));

CREATE POLICY org_isolation ON ticket_comments
  USING (ticket_id IN (SELECT id FROM tickets WHERE organization_id = current_setting('app.org_id', true)::uuid));

CREATE POLICY org_isolation ON ticket_activities
  USING (ticket_id IN (SELECT id FROM tickets WHERE organization_id = current_setting('app.org_id', true)::uuid));

CREATE POLICY org_isolation ON asset_risk_mapping
  USING (asset_id IN (SELECT id FROM assets WHERE organization_id = current_setting('app.org_id', true)::uuid));

CREATE POLICY org_isolation ON risk_control_mappings
  USING (risk_id IN (SELECT id FROM risks WHERE organization_id = current_setting('app.org_id', true)::uuid));

CREATE POLICY org_isolation ON evidence_control_matches
  USING (evidence_id IN (SELECT id FROM evidence WHERE organization_id = current_setting('app.org_id', true)::uuid));

-- 5. Create Performance Indexes
CREATE INDEX IF NOT EXISTS idx_risks_org ON risks(organization_id);
CREATE INDEX IF NOT EXISTS idx_controls_org ON controls(organization_id);
CREATE INDEX IF NOT EXISTS idx_evidence_org ON evidence(organization_id);
CREATE INDEX IF NOT EXISTS idx_tickets_org ON tickets(organization_id);
CREATE INDEX IF NOT EXISTS idx_assets_org ON assets(organization_id);
CREATE INDEX IF NOT EXISTS idx_compliance_items_org ON compliance_items(organization_id);
CREATE INDEX IF NOT EXISTS idx_control_applicability_org ON control_applicability(organization_id);
CREATE INDEX IF NOT EXISTS idx_document_analyses_org ON document_analyses(organization_id);

-- Compound and relation indexes
CREATE INDEX IF NOT EXISTS idx_control_applicability_org_annex ON control_applicability(organization_id, control_annex);
CREATE INDEX IF NOT EXISTS idx_audit_logs_user ON audit_logs(user_id);
CREATE INDEX IF NOT EXISTS idx_ticket_comments_ticket ON ticket_comments(ticket_id);
CREATE INDEX IF NOT EXISTS idx_ticket_activities_ticket ON ticket_activities(ticket_id);
CREATE INDEX IF NOT EXISTS idx_risk_control_mappings_risk ON risk_control_mappings(risk_id);
CREATE INDEX IF NOT EXISTS idx_evidence_control_matches_evidence ON evidence_control_matches(evidence_id);
