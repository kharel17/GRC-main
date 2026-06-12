"""
Invitation endpoints for the GRC Platform.
Manages admin and user invitations for the invitation-only access system.
"""
from datetime import datetime
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app import models
from app.config import settings
from app.database import get_db
from app.api.deps import get_current_user
from app.utils.notifications import notify
import logging
import uuid
import secrets
import hashlib
from app.utils.emails import send_invitation_email

logger = logging.getLogger("grc.invitations")

router = APIRouter()

# ── Platform team emails (can invite admins) ──────────────────
PLATFORM_TEAM_EMAILS = ["bcolorc17@gmail.com", "grchelios@gmail.com"]

# ── Schemas ───────────────────────────────────────────────────

class InviteAdminRequest(BaseModel):
    email: EmailStr
    full_name: str
    organization_name: str

class InviteUserRequest(BaseModel):
    email: EmailStr
    full_name: str
    role: str  # "manager" or "analyst"
    manager_id: Optional[UUID] = None

class InvitationResponse(BaseModel):
    success: bool
    message: str

class PendingInvitation(BaseModel):
    id: UUID
    email: str
    full_name: str
    role: str
    invited_at: Optional[datetime]
    invited_by_email: Optional[str] = None

    class Config:
        from_attributes = True

# ── Helpers ───────────────────────────────────────────────────

def _get_supabase_admin():
    """Get a Supabase client with the service role key for admin operations."""
    if not settings.SUPABASE_SERVICE_KEY:
        raise HTTPException(
            status_code=500,
            detail="SUPABASE_SERVICE_KEY is not configured. Cannot send invitations."
        )
    from supabase import create_client
    return create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_KEY)


async def _log_audit(
    db: AsyncSession,
    user_id: UUID,
    action: str,
    entity_id: UUID,
    entity_name: str,
    description: str,
):
    """Log an audit event for invitation actions."""
    try:
        audit_log = models.AuditLog(
            id=uuid.uuid4(),
            user_id=user_id,
            action=models.AuditAction.created,
            entity_type=models.AuditEntityType.user,
            entity_id=entity_id,
            entity_name=entity_name,
            description=description,
        )
        db.add(audit_log)
        await db.flush()
    except Exception as e:
        logger.warning(f"Failed to create audit log: {e}")


# ── 1. POST /invite-admin ────────────────────────────────────

@router.post("/invite-admin", response_model=InvitationResponse)
async def invite_admin(
    body: InviteAdminRequest,
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """
    Invite a new customer admin. Only callable by platform team emails.
    Creates an organization and user row, then sends a Supabase invite email.
    """
    # Guard: only platform team
    if current_user.email not in PLATFORM_TEAM_EMAILS:
        raise HTTPException(status_code=403, detail="Only platform team can invite admins")

    # Check if email already exists
    existing = await db.execute(
        select(models.User).where(models.User.email == body.email)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail=f"User with email {body.email} already exists")

    # Create organization
    org = models.Organization(
        id=uuid.uuid4(),
        name=body.organization_name,
        onboarding_completed=False,
        created_by=current_user.id,
    )
    db.add(org)
    await db.flush()

    # Generate secure token
    raw_token = secrets.token_urlsafe(32)
    token_hash = hashlib.sha256(raw_token.encode()).hexdigest()
    expires_at = datetime.utcnow() + timedelta(days=7)

    # Create user row
    new_user = models.User(
        id=uuid.uuid4(),
        email=body.email,
        full_name=body.full_name,
        hashed_password="PENDING_INVITATION",
        role=models.UserRole.admin,
        invitation_status="pending",
        invitation_token_hash=token_hash,
        invitation_expires_at=expires_at,
        invited_by=current_user.id,
        invited_at=datetime.utcnow(),
        organization_id=org.id,
        organization_name=body.organization_name,
        is_active=True,
    )
    db.add(new_user)
    await db.flush()

    # Send invite email via Custom SMTP
    await send_invitation_email(
        email_to=body.email,
        token=raw_token,
        full_name=body.full_name,
        org_name=body.organization_name
    )

    # Audit log
    await _log_audit(
        db, current_user.id, "ADMIN_INVITED", new_user.id,
        body.email, f"Admin invited: {body.email} for org {body.organization_name}"
    )

    await db.commit()

    # 4. Notifications
    # Notify New Admin (Welcome)
    await notify(
        db=db,
        user_id=new_user.id,
        title="Welcome to the platform",
        message=f"Welcome! You have been invited as admin to {body.organization_name}",
        entity_type="user",
        entity_id=new_user.id,
        link_url="/dashboard",
        notification_type="WELCOME"
    )

    return InvitationResponse(success=True, message=f"Invitation sent to {body.email}")


# ── 2. POST /invite-user ─────────────────────────────────────

@router.post("/invite-user", response_model=InvitationResponse)
async def invite_user(
    body: InviteUserRequest,
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """
    Invite a new user (manager or analyst). Only callable by admin or manager.
    Guards: Admin can invite manager/analyst. Manager can invite analyst only.
    """
    # Validate role
    if body.role not in ("manager", "analyst"):
        raise HTTPException(status_code=400, detail="Role must be 'manager' or 'analyst'")

    # Guard: role hierarchy
    user_role = str(current_user.role.value) if hasattr(current_user.role, 'value') else str(current_user.role)
    if user_role == "manager" and body.role != "analyst":
        raise HTTPException(status_code=403, detail="Managers can only invite analysts")
    if user_role not in ("admin", "manager"):
        raise HTTPException(status_code=403, detail="Only admins and managers can invite users")

    # Analyst requires manager_id
    if body.role == "analyst" and not body.manager_id:
        raise HTTPException(status_code=400, detail="manager_id is required when inviting an analyst")

    # Check if email already exists
    existing = await db.execute(
        select(models.User).where(models.User.email == body.email)
    )
    # Check if duplicate pending invitation exists in the SAME org
    duplicate = await db.execute(
        select(models.User).where(
            models.User.email == body.email,
            models.User.organization_id == current_user.organization_id,
            models.User.invitation_status == "pending"
        )
    )
    if duplicate.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="A pending invitation already exists for this email in your organization.")

    # Generate secure token
    raw_token = secrets.token_urlsafe(32)
    token_hash = hashlib.sha256(raw_token.encode()).hexdigest()
    expires_at = datetime.utcnow() + timedelta(days=7)

    # Resolve role enum
    try:
        role_enum = models.UserRole(body.role)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid role: {body.role}")

    # Create user row
    new_user = models.User(
        id=uuid.uuid4(),
        email=body.email,
        full_name=body.full_name,
        hashed_password="PENDING_INVITATION", # Placeholder until password set
        role=role_enum,
        invitation_status="pending",
        invitation_token_hash=token_hash,
        invitation_expires_at=expires_at,
        invited_by=current_user.id,
        invited_at=datetime.utcnow(),
        organization_id=current_user.organization_id,
        manager_id=body.manager_id,
        is_active=True,
    )
    db.add(new_user)
    await db.flush()

    # Send invite email via Custom SMTP
    org_name = current_user.organization_name or "GRC Platform"
    await send_invitation_email(
        email_to=body.email,
        token=raw_token,
        full_name=body.full_name,
        org_name=org_name
    )

    # Audit log
    await _log_audit(
        db, current_user.id, "USER_INVITED", new_user.id,
        body.email, f"{body.role} invited: {body.email}"
    )

    await db.commit()

    # 4. Notifications
    # Notify New User (Welcome)
    await notify(
        db=db,
        user_id=new_user.id,
        title="Welcome to the platform",
        message=f"Welcome! You have been invited as {body.role} to {org_name}",
        entity_type="user",
        entity_id=new_user.id,
        link_url="/dashboard",
        notification_type="WELCOME"
    )

    # Notify Admin (New team member joined)
    admin_res = await db.execute(
        select(models.User).where(
            models.User.organization_id == current_user.organization_id, 
            models.User.role == models.UserRole.admin
        )
    )
    admins = admin_res.scalars().all()
    for admin in admins:
        await notify(
            db=db,
            user_id=admin.id,
            title="New team member joined",
            message=f"👋 {body.full_name} joined as {body.role}",
            entity_type="user",
            entity_id=new_user.id,
            link_url="/dashboard/users",
            notification_type="USER_JOINED"
        )

    return InvitationResponse(success=True, message=f"Invitation sent to {body.email}")


# ── 3. GET /pending ───────────────────────────────────────────

@router.get("/pending")
async def get_pending_invitations(
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """
    Returns all pending invitations for the current user's organization.
    Only admin and manager can see this.
    """
    user_role = str(current_user.role.value) if hasattr(current_user.role, 'value') else str(current_user.role)
    if user_role not in ("admin", "manager"):
        raise HTTPException(status_code=403, detail="Only admins and managers can view pending invitations")

    query = select(models.User).where(
        models.User.invitation_status == "pending",
        models.User.organization_id == current_user.organization_id,
    )
    result = await db.execute(query)
    pending_users = result.scalars().all()

    invitations = []
    for u in pending_users:
        # Get inviter email
        inviter_email = None
        if u.invited_by:
            inviter = await db.get(models.User, u.invited_by)
            inviter_email = inviter.email if inviter else None

        invitations.append({
            "id": str(u.id),
            "email": u.email,
            "full_name": u.full_name,
            "role": str(u.role.value) if hasattr(u.role, 'value') else str(u.role),
            "invited_at": u.invited_at.isoformat() if u.invited_at else None,
            "invited_by_email": inviter_email,
        })

    return invitations


# ── 4. DELETE /{user_id} ──────────────────────────────────────

@router.delete("/{user_id}")
async def cancel_invitation(
    user_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """
    Cancels a pending invitation by deleting the user row.
    Only admin can cancel invitations.
    """
    user_role = str(current_user.role.value) if hasattr(current_user.role, 'value') else str(current_user.role)
    if user_role != "admin":
        raise HTTPException(status_code=403, detail="Only admins can cancel invitations")

    user_to_cancel = await db.get(models.User, user_id)
    if not user_to_cancel:
        raise HTTPException(status_code=404, detail="User not found")

    if user_to_cancel.invitation_status != "pending":
        raise HTTPException(status_code=400, detail="Can only cancel pending invitations")

    await db.delete(user_to_cancel)
    await db.commit()

    return {"success": True, "message": f"Invitation for {user_to_cancel.email} cancelled"}
