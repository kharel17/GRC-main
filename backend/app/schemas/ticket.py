from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel
from uuid import UUID
from app.models.ticket import TicketPriority, TicketStatus, TicketCategory

# Ticket Comment
class TicketCommentBase(BaseModel):
    ticket_id: UUID
    author_id: UUID
    text: str

class TicketCommentCreate(TicketCommentBase):
    pass

class TicketCommentInDBBase(TicketCommentBase):
    id: UUID
    created_at: datetime
    
    class Config:
        from_attributes = True

class TicketComment(TicketCommentInDBBase):
    pass

# Ticket
class TicketBase(BaseModel):
    title: str
    description: str
    priority: TicketPriority
    status: TicketStatus = TicketStatus.open
    category: TicketCategory
    source_audit_log_id: UUID
    assigned_to_id: UUID
    assigned_to_role: str
    escalated_to_id: Optional[UUID] = None
    escalated_to_role: Optional[str] = None
    escalation_level: int = 1
    related_risk_id: Optional[UUID] = None
    related_entity_type: Optional[str] = None
    related_entity_id: Optional[UUID] = None
    created_by: UUID

class TicketCreate(TicketBase):
    pass

class TicketUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    priority: Optional[TicketPriority] = None
    status: Optional[TicketStatus] = None
    assigned_to_id: Optional[UUID] = None
    escalated_to_id: Optional[UUID] = None
    escalation_level: Optional[int] = None
    resolved_at: Optional[datetime] = None
    escalated_at: Optional[datetime] = None

class TicketInDBBase(TicketBase):
    id: UUID
    created_at: datetime
    updated_at: datetime
    resolved_at: Optional[datetime] = None
    escalated_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class Ticket(TicketInDBBase):
    comments: List[TicketComment] = []
