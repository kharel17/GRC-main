-- GRC Platform - Mock Data Cleanup Script
-- This script removes all hardcoded demo/mock users, organizations,
-- and their associated risks, controls, assets, tickets, compliance, and evidence records,
-- while preserving the ISO 27001 framework library data, control applicability mapping
-- for real tenants, and active developer/admin users.

BEGIN;

-- 1. Ensure real user(s) are associated with the real organization
-- Organization '24de3639-ee40-4563-a207-dd66436a0da8' is the target real tenant.
UPDATE users
SET organization_id = '24de3639-ee40-4563-a207-dd66436a0da8',
    organization_name = (SELECT name FROM organizations WHERE id = '24de3639-ee40-4563-a207-dd66436a0da8')
WHERE email IN ('bcolorc17@gmail.com', 'grchelios@gmail.com');

-- 2. Define lists of mock items to purge
-- Identifies organizations that are mock/demo
CREATE TEMP TABLE temp_mock_orgs AS
SELECT id FROM organizations 
WHERE name IN ('Acme Corporation', 'Platform Team', 'Test Org')
   OR id = '00000000-0000-0000-0000-000000000010';

-- Identifies users that are mock/demo
CREATE TEMP TABLE temp_mock_users AS
SELECT id FROM users
WHERE email LIKE '%@company.com'
   OR id IN (
     '00000000-0000-0000-0000-000000000001',
     '00000000-0000-0000-0000-000000000002',
     '00000000-0000-0000-0000-000000000003'
   );

-- 3. Sever any circular relationships to mock organizations or users
UPDATE organizations
SET primary_contact_id = NULL
WHERE id IN (SELECT id FROM temp_mock_orgs);

UPDATE users
SET organization_id = NULL,
    invited_by = NULL,
    manager_id = NULL
WHERE id IN (SELECT id FROM temp_mock_users);

-- 4. Delete dependent records linked to mock organizations or users
-- Clean up tickets, comments and activities
DELETE FROM ticket_comments
WHERE author_id IN (SELECT id FROM temp_mock_users)
   OR ticket_id IN (SELECT id FROM tickets WHERE organization_id IN (SELECT id FROM temp_mock_orgs));

DELETE FROM ticket_activities
WHERE user_id IN (SELECT id FROM temp_mock_users)
   OR ticket_id IN (SELECT id FROM tickets WHERE organization_id IN (SELECT id FROM temp_mock_orgs));

DELETE FROM tickets
WHERE organization_id IN (SELECT id FROM temp_mock_orgs)
   OR created_by IN (SELECT id FROM temp_mock_users)
   OR assigned_to_id IN (SELECT id FROM temp_mock_users);

-- Clean up evidence and AI evidence control matches
DELETE FROM evidence_control_matches
WHERE evidence_id IN (SELECT id FROM evidence WHERE organization_id IN (SELECT id FROM temp_mock_orgs));

DELETE FROM evidence
WHERE organization_id IN (SELECT id FROM temp_mock_orgs)
   OR uploaded_by IN (SELECT id FROM temp_mock_users)
   OR verified_by IN (SELECT id FROM temp_mock_users);

-- Clean up document analyses
DELETE FROM document_analyses
WHERE organization_id IN (SELECT id FROM temp_mock_orgs)
   OR uploaded_by IN (SELECT id FROM temp_mock_users);

-- Clean up compliance items
DELETE FROM compliance_items
WHERE organization_id IN (SELECT id FROM temp_mock_orgs)
   OR owner_id IN (SELECT id FROM temp_mock_users);

-- Clean up risk control mappings
DELETE FROM risk_control_mappings
WHERE mapped_by IN (SELECT id FROM temp_mock_users)
   OR risk_id IN (SELECT id FROM risks WHERE organization_id IN (SELECT id FROM temp_mock_orgs));

-- Clean up controls
DELETE FROM controls
WHERE owner_id IN (SELECT id FROM temp_mock_users)
   OR created_by IN (SELECT id FROM temp_mock_users);

-- Clean up risks
DELETE FROM risks
WHERE organization_id IN (SELECT id FROM temp_mock_orgs)
   OR owner_id IN (SELECT id FROM temp_mock_users)
   OR created_by IN (SELECT id FROM temp_mock_users);

-- Clean up assets
DELETE FROM assets
WHERE organization_id IN (SELECT id FROM temp_mock_orgs)
   OR owner_id IN (SELECT id FROM temp_mock_users);

-- Clean up control applicability (Statement of Applicability) entries for mock organizations
DELETE FROM control_applicability
WHERE organization_id IN (SELECT id FROM temp_mock_orgs);

-- Clean up audit logs
DELETE FROM audit_logs
WHERE user_id IN (SELECT id FROM temp_mock_users);

-- Clean up notifications
DELETE FROM notifications
WHERE user_id IN (SELECT id FROM temp_mock_users);

-- Clean up refresh tokens
DELETE FROM refresh_tokens
WHERE user_id IN (SELECT id FROM temp_mock_users);

-- 5. Delete mock users and organizations themselves
DELETE FROM users WHERE id IN (SELECT id FROM temp_mock_users);
DELETE FROM organizations WHERE id IN (SELECT id FROM temp_mock_orgs);

-- 6. Clean up temp tables
DROP TABLE temp_mock_users;
DROP TABLE temp_mock_orgs;

COMMIT;
