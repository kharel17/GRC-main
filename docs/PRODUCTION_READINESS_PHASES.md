# Production Readiness Phased Plan

This plan breaks the production-readiness work into controlled phases. Each phase should be completed, verified, and documented before moving to the next one.

Do not run this whole plan as one implementation prompt. Each phase should be a separate focused Codex session with its own verification pass. This reduces risk, avoids incomplete output, and makes failures recoverable.

## Goal

Make the GRC platform production-ready by:

- Enforcing tenant isolation through `current_user.organization_id`.
- Removing mock and seed data from runtime behavior.
- Completing organization-scoped user and invitation management.
- Updating frontend calls and screens to use scoped backend contracts.
- Providing cleanup SQL and operational documentation.

## Priority Order

1. Phase 0: Remove mock and seed data.
2. Phase 1: Backend multi-tenancy scoping.
3. Phase 1.5: Database RLS and indexes.
4. Phase 2: User invitation and role management.
5. Phase 2.5: Password reset and security hardening.
6. Phase 3: Frontend fixes and empty states.
7. Phase 4: Environment and runtime configuration.
8. Phase 4.5: Docker, nginx, health checks, and deployment readiness.
9. Phase 5: Final documentation.

## Phase 0: Remove Mock and Seed Data

### Scope

- Remove or disable runtime seed data creation.
- Remove hardcoded demo users and organizations from startup behavior.
- Keep ISO 27001 framework library data.
- Provide a Supabase cleanup SQL script.

### Files To Audit Or Change

- `backend/app/main.py`
- `backend/seed.py`
- Any `seed_data.py`, `seed.py`, startup hooks, or scripts that create demo users/orgs.
- `src/lib/mock-data.ts`
- Any frontend fallback that silently displays mock business data.

### Required Fixes

- Delete or disable creation of:
  - `alice@company.com`
  - `bob@company.com`
  - `carol@company.com`
  - `Acme Corporation`
  - `Platform Team`
  - `Test Org`
  - fake risks, controls, tickets, evidence, assets, compliance items.
- Keep framework library data, especially `framework_controls`.
- Keep `control_applicability` rows for real org `24de3639-ee40-4563-a207-dd66436a0da8`.
- Keep user `bcolorc17@gmail.com`.

### Deliverables

- `scripts/cleanup_mock_data.sql`
- File-by-file change summary.
- List of removed/disabled seed entry points.

### Acceptance Checks

- Starting backend does not create demo data.
- Cleanup SQL preserves the real org, real user, framework controls, and real org applicability.
- `python -m py_compile` passes for changed backend files.

## Phase 1: Backend Multi-Tenancy Scoping

### Scope

Every backend API read/write must be scoped to `current_user.organization_id`, except explicitly global reference data.

### Standard Pattern

```python
org_id = current_user.organization_id
if not org_id:
    raise HTTPException(status_code=403, detail="User not associated with any organization")
```

### Files To Fix

- `backend/app/api/organization.py`
- `backend/app/api/control_applicability.py`
- `backend/app/api/risks.py`
- `backend/app/api/controls.py`
- `backend/app/api/evidence.py`
- `backend/app/api/tickets.py`
- `backend/app/api/assets.py`
- `backend/app/api/dashboard.py`
- `backend/app/api/compliance.py`
- `backend/app/api/gap_analysis.py`
- `backend/app/api/audit_logs.py`
- `backend/app/api/notifications.py`

### High-Priority Known Bugs

- `GET /organization/` currently returns the first org found instead of the current user's org.
- `PUT /organization/` currently updates the first org found.
- `GET /control-applicability/compliance-score` currently uses the first org found.
- `GET /control-applicability/soa` and `GET /control-applicability/annex/{annex}` need current-user org scoping.

### Deliverables

- Complete list of endpoints fixed.
- For each endpoint: old behavior, new org-scoped behavior, file path, function name.
- Any endpoint intentionally global must be documented.

### Acceptance Checks

- No `select(models.Organization).limit(1)` remains in request-scoped endpoints.
- Cross-org data cannot be read or updated by another org's user.
- `python -m py_compile` passes for changed backend files.

## Phase 2: User Invitation And Role Management

### Scope

Complete organization-scoped invitation, role update, and user deactivation.

### Backend Work

#### `backend/app/api/invitations.py`

- `POST /invitations/invite-user`
- Generate secure token with `secrets.token_urlsafe(32)`.
- Store hashed token using `hashlib.sha256`.
- Expire invitations after 7 days.
- Send email using SMTP config.
- Return `400` when the email belongs to a user in another org.
- Return `409` for duplicate pending invitation in the same org.

#### `backend/app/api/users.py`

- `GET /users/`: return users only in current user's org.
- `PATCH /users/{user_id}/role`: admin only, same org only.
- `DELETE /users/{user_id}`: admin only, deactivate and clear `organization_id`.

#### `backend/app/api/auth.py`

- Add `POST /auth/accept-invite`.
- Accept `token` and `password`.
- Hash token and find invitation.
- Check expiry.
- Set password and activate user.
- Assign `organization_id`.
- Mark invitation used or delete it.
- Return JWT tokens using existing auth logic.

### Environment Variables

```env
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-app-password
FRONTEND_URL=http://localhost:3000
```

### Deliverables

- Invitation flow documentation.
- Email template/link format.
- Endpoint summaries.
- Any DB migration requirement. If token/expiry fields do not exist, document the migration needed before coding.

### Acceptance Checks

- Admin can invite within own org.
- Existing user in another org cannot be invited.
- Pending duplicate invite returns `409`.
- Invite link lets user set password and land on dashboard.
- Deactivated users cannot access org data.

## Phase 1.5: Database RLS And Indexes

### Scope

Add database-level tenant isolation and performance indexes. App-level scoping is required, but it is not enough for production. Supabase Row Level Security should be the safety net if an endpoint has a bug.

### RLS Requirements

Enable RLS for every tenant-scoped table, including at minimum:

- `risks`
- `controls`
- `evidence`
- `tickets`
- `assets`
- `compliance_items`
- `control_applicability`
- `audit_logs`
- tenant-scoped notification or invitation tables, if present

Example pattern:

```sql
ALTER TABLE risks ENABLE ROW LEVEL SECURITY;

CREATE POLICY org_isolation ON risks
  USING (organization_id = current_setting('app.org_id')::uuid);
```

The application must set the request org context before queries if this policy pattern is used:

```sql
SELECT set_config('app.org_id', '<current_user.organization_id>', true);
```

If the app cannot reliably set `app.org_id`, use Supabase JWT claims or another production-safe RLS strategy instead. Document the chosen strategy.

### Index Requirements

Every table queried by `organization_id` needs an index.

Example:

```sql
CREATE INDEX IF NOT EXISTS idx_risks_org ON risks(organization_id);
CREATE INDEX IF NOT EXISTS idx_tickets_org ON tickets(organization_id);
CREATE INDEX IF NOT EXISTS idx_evidence_org ON evidence(organization_id);
CREATE INDEX IF NOT EXISTS idx_assets_org ON assets(organization_id);
CREATE INDEX IF NOT EXISTS idx_controls_org ON controls(organization_id);
CREATE INDEX IF NOT EXISTS idx_compliance_items_org ON compliance_items(organization_id);
CREATE INDEX IF NOT EXISTS idx_control_applicability_org ON control_applicability(organization_id);
```

Add compound indexes where query patterns require them, for example:

```sql
CREATE INDEX IF NOT EXISTS idx_control_applicability_org_annex
  ON control_applicability(organization_id, control_annex);
```

### Deliverables

- `scripts/enable_rls_and_indexes.sql`
- List of tenant-scoped tables.
- RLS policy strategy.
- Index list and rationale.

### Acceptance Checks

- RLS is enabled on all tenant-scoped tables.
- Cross-org SQL reads fail when `app.org_id` does not match.
- Indexed query plans use organization indexes for large tables.

## Phase 3: Frontend Fixes

### Scope

Update frontend API calls and screens to match scoped backend contracts.

### Files To Fix

#### `src/lib/data-service.ts`

- Change `updateOrganization(id, data)` to `updateOrganization(data)`.
- Use `PUT /organization/`.
- Add:
  - `inviteUser(email: string, role: string)`
  - `updateUserRole(userId: string, role: string)`
  - `removeUser(userId: string)`

#### `src/app/dashboard/organization/page.tsx`

- Remove org ID argument from `updateOrganization`.
- Read frameworks from:

```ts
const frameworks = org.compliance_frameworks ?? org.complianceFrameworks ?? [];
```

#### `src/app/dashboard/users/page.tsx`

- Add Invite User modal.
- Show pending invitations.
- Allow cancel pending invitation.
- Allow admin role changes.
- Allow admin remove/deactivate user.

#### `src/app/accept-invite/page.tsx`

- New page.
- Read `token` from query string.
- Show password and confirm password form.
- Submit to `POST /auth/accept-invite`.
- Redirect to `/dashboard` on success.

#### `src/app/dashboard/settings/page.tsx`

- Ensure framework management uses scoped endpoints.
- Add org details edit form if missing.

### Deliverables

- Frontend API contract summary.
- Page-level behavior summary.
- Error state handling notes.

### Acceptance Checks

- `yarn typecheck` passes.
- Organization update uses scoped `PUT /organization/`.
- User page works using current org only.
- Accept invite works from emailed link.

## Phase 2.5: Password Reset And Security Hardening

### Scope

Close security gaps that would block production readiness.

### JWT Secret Management

- Verify `SECRET_KEY` is not hardcoded.
- Production must require `SECRET_KEY` from environment.
- Document secret rotation procedure.
- Rotation should invalidate or version old sessions deliberately.

### Password Policy

Apply policy to invitation acceptance and password reset:

- Minimum length.
- Complexity requirements.
- Confirmation match on frontend.
- Backend validation regardless of frontend validation.

### Rate Limiting

Add rate limiting for:

- `POST /auth/login`
- `POST /auth/accept-invite`
- password reset request endpoint

Document whether rate limiting is implemented in app middleware, nginx, or deployment platform.

### CORS And HTTPS

- Replace broad/local-only CORS assumptions with explicit production domains.
- Document production `FRONTEND_URL`.
- Document HTTPS enforcement at proxy/platform level.

### Password Reset

Add forgot-password flow before go-live:

- Request reset email.
- Generate secure reset token.
- Store hashed token.
- Expire token.
- Set new password.

### Session Management

- Add ability to force logout all sessions for a user.
- Ensure user removal/deactivation invalidates existing tokens.

### Audit Logging

Admin actions must be audit logged:

- invite sent
- invite cancelled
- role changed
- user removed/deactivated
- framework added/deactivated

### Framework Deactivation

Add a safe framework deactivation workflow:

- Remove framework from org active framework list.
- Decide whether existing `control_applicability` rows are archived, soft-deactivated, or preserved.
- Never silently delete audit-relevant control history.

### Deliverables

- Security checklist.
- Password policy documentation.
- Rate limiting strategy.
- Session invalidation strategy.
- Audit log event list.

### Acceptance Checks

- Login cannot be brute-forced without throttling.
- Password acceptance rejects weak passwords.
- Removed users cannot keep using old sessions.
- Admin changes are visible in audit logs.

## Phase 3: Frontend Fixes And Empty States

### Additional Scope

After mock data removal, pages must not look broken when there is no data.

### Required UX Work

- Add explicit loading states where pages currently flash blank content.
- Add error states with retry actions for API failures.
- Add empty states for:
  - risks
  - controls
  - evidence
  - tickets
  - assets
  - compliance items
  - audit logs
- Ensure token expiry redirects to login instead of silent failures.

### Acceptance Checks

- Empty production tenant has useful first-run screens.
- API errors are visible and actionable.
- Expired token path is tested.

## Phase 4: Environment And Runtime Configuration

### Scope

Add required SMTP and frontend URL configuration.

### Files

- `backend/.env`
- Existing backend config module, currently `backend/app/config.py` unless the project is moved to `backend/app/core/config.py`.

### Required Settings

```python
SMTP_HOST: str = ""
SMTP_PORT: int = 587
SMTP_USER: str = ""
SMTP_PASSWORD: str = ""
FRONTEND_URL: str = "http://localhost:3000"
```

### Deliverables

- Environment variable list.
- Local development setup notes.
- Production deployment notes for SMTP secrets.

### Acceptance Checks

- Missing SMTP config fails gracefully.
- Email sending works with configured SMTP.
- No secrets are committed.

## Phase 4.5: Docker, Nginx, Health Checks, And Deployment Readiness

### Scope

Prepare the runtime environment for production deployment.

### Environment Separation

- Document `.env.development` and `.env.production` expectations.
- Ensure production secrets are not committed.
- Document required frontend and backend env vars separately.

### Docker And Nginx

- Review `Dockerfile`.
- Review `docker-compose.yaml`.
- Review `nginx` config.
- Ensure production config supports:
  - HTTPS termination or proxy integration.
  - correct frontend/backend routing.
  - request size limits for evidence uploads.
  - CORS alignment.
  - static asset caching.

### Health Checks

The health endpoint must check:

- app is running
- database connectivity
- optionally Supabase/storage connectivity if critical

### Graceful Shutdown

Document uvicorn/gunicorn signal handling and deployment strategy for graceful shutdown and zero-downtime deploys.

### Deliverables

- Deployment checklist.
- Health check behavior.
- Docker/nginx production notes.

### Acceptance Checks

- Health check fails when DB is unreachable.
- Container can start with production env only.
- Evidence upload size limits are documented and tested.

## Phase 5: Final Documentation Update

After all phases are implemented, update:

- `DOCUMENTATION.md`
- `docs/PRODUCTION_READINESS_PHASES.md`
- `scripts/cleanup_mock_data.sql`

The final documentation must include:

- Complete SQL cleanup script.
- Complete list of endpoints fixed for org scoping.
- Invitation flow sequence:
  1. Admin invites user.
  2. Email is sent.
  3. User clicks invitation link.
  4. User sets password.
  5. User lands on dashboard.
- Environment variable list.
- Security checklist.
- RLS and index SQL.
- Deployment checklist.
- Migration status.
- Verification results:
  - `python -m py_compile ...`
  - `yarn typecheck`

## Execution Rule

Do not mix phases in a single change unless required by a dependency. Complete and verify each phase before starting the next phase.
