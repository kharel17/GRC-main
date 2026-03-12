from fastapi import APIRouter
from app.api import auth, risks, audit_logs, controls, compliance, evidence, tickets, reports, users, notifications

api_router = APIRouter()
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(risks.router, prefix="/risks", tags=["risks"])
api_router.include_router(audit_logs.router, prefix="/audit-logs", tags=["audit-logs"])
api_router.include_router(controls.router, prefix="/controls", tags=["controls"])
api_router.include_router(compliance.router, prefix="/compliance", tags=["compliance"])
api_router.include_router(evidence.router, prefix="/evidence", tags=["evidence"])
api_router.include_router(tickets.router, prefix="/tickets", tags=["tickets"])
api_router.include_router(notifications.router, prefix="/notifications", tags=["notifications"])
api_router.include_router(reports.router, prefix="/reports", tags=["reports"])
