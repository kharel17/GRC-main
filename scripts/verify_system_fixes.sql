-- ====================================================================
-- GRC PLATFORM - SYSTEM FIXES VERIFICATION SQL SCRIPT
-- Run this script in the Supabase SQL Editor to test & verify system fixes.
-- ====================================================================

-- 1. VERIFY INVITATION & PASSWORD RESET COLUMNS IN USERS TABLE
-- Expectation: Columns invitation_token_hash, invitation_expires_at,
-- reset_token_hash, reset_token_expires_at must exist.
SELECT column_name, data_type, is_nullable
FROM information_schema.columns 
WHERE table_name = 'users' 
  AND column_name IN (
    'invitation_token_hash', 
    'invitation_expires_at', 
    'reset_token_hash', 
    'reset_token_expires_at'
  );

-- 2. VERIFY INDEXES ON USERS TOKEN COLUMNS
-- Expectation: ix_users_invitation_token_hash and ix_users_reset_token_hash indexes exist.
SELECT indexname, indexdef 
FROM pg_indexes 
WHERE tablename = 'users' 
  AND indexname IN ('ix_users_invitation_token_hash', 'ix_users_reset_token_hash');

-- 3. TEST ROW LEVEL SECURITY (RLS) MULTI-TENANCY ISOLATION
-- Test 3A: Query tickets without setting organization context (Simulates background task without context)
-- Expectation: Should return 0 rows under RLS (when BYPASSRLS is False or using restricted role)
SELECT count(*) AS tickets_count_no_context FROM tickets;

-- Test 3B: Set organization context to Real Org ID and query tickets
-- Real Org ID: '24de3639-ee40-4563-a207-dd66436a0da8'
SELECT set_config('app.org_id', '24de3639-ee40-4563-a207-dd66436a0da8', false);

SELECT id, title, status, organization_id 
FROM tickets 
WHERE organization_id = current_setting('app.org_id', true)::uuid;

-- 4. VERIFY RLS POLICIES ACROSS ALL TENANT TABLES
-- Expectation: rls_enabled and rls_forced should be TRUE for all 14 tenant business tables.
SELECT 
    c.relname AS table_name,
    c.relrowsecurity AS rls_enabled,
    c.relforcerowsecurity AS rls_forced
FROM pg_class c
JOIN pg_namespace n ON n.oid = c.relnamespace
WHERE n.nspname = 'public'
  AND c.relname IN (
    'assets', 'risks', 'controls', 'control_applicability',
    'compliance_items', 'evidence', 'tickets', 'audit_logs',
    'document_analyses', 'risk_control_mappings', 'asset_risk_mapping',
    'ticket_activities', 'ticket_comments', 'evidence_control_matches'
  )
ORDER BY table_name;

-- 5. VERIFY ORG SCOPING OF USERS & TICKETS
-- Expectation: All active users and tickets map to real organization ID
SELECT id, email, role, organization_id 
FROM users 
WHERE is_active = true;

SELECT id, title, status, organization_id 
FROM tickets;
