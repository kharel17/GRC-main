from fastapi import APIRouter
from app.api import (
    auth, users, organization, assets, risks, audit_logs, controls, 
    control_applicability, compliance, evidence, document_analysis, 
    gap_analysis, audit_preparation, reports, notifications, ai, 
    dashboard, tickets, invitations, onboarding,
)


api_router = APIRouter()

# Auth & Users
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(users.router, prefix="/users", tags=["users"])

# Step 0 — Dashboard & Monitoring
api_router.include_router(dashboard.router, prefix="/dashboard", tags=["dashboard"])

# Step 1 — Organization Setup
api_router.include_router(organization.router, prefix="/organization", tags=["organization"])

# Step 2 — Asset Identification
api_router.include_router(assets.router, prefix="/assets", tags=["assets"])

# Step 3 — AI Document Analysis
api_router.include_router(document_analysis.router, prefix="/document-analysis", tags=["document-analysis"])

# Step 4 — Control Mapping & SoA
api_router.include_router(controls.router, prefix="/controls", tags=["controls"])
api_router.include_router(control_applicability.router, prefix="/control-applicability", tags=["control-applicability"])

# Step 5 — Gap Analysis
api_router.include_router(gap_analysis.router, prefix="/gap-analysis", tags=["gap-analysis"])

# Step 6 — Ticket Workflow
api_router.include_router(tickets.router, prefix="/tickets", tags=["tickets"])

# Step 7 — Continuous Monitoring
api_router.include_router(risks.router, prefix="/risks", tags=["risks"])
api_router.include_router(compliance.router, prefix="/compliance", tags=["compliance"])

# Step 8 — Audit Preparation
api_router.include_router(audit_preparation.router, prefix="/audit-preparation", tags=["audit-preparation"])
api_router.include_router(reports.router, prefix="/reports", tags=["reports"])

# Supporting
api_router.include_router(evidence.router, prefix="/evidence", tags=["evidence"])
api_router.include_router(audit_logs.router, prefix="/audit-logs", tags=["audit-logs"])
api_router.include_router(notifications.router, prefix="/notifications", tags=["notifications"])
api_router.include_router(ai.router, prefix="/ai", tags=["ai"])
api_router.include_router(invitations.router, prefix="/invitations", tags=["invitations"])
api_router.include_router(onboarding.router, prefix="/onboarding", tags=["onboarding"])