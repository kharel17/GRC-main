from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, ConfigDict, computed_field
from pydantic.alias_generators import to_camel
from uuid import UUID
from app.models.ticket import TicketPriority, TicketStatus, TicketCategory
from app.models.ticket_activity import TicketActivityType

# Ticket Comment
class TicketCommentBase(BaseModel):
    ticket_id: UUID
    author_id: UUID
    text: str

class TicketCommentCreate(BaseModel):
    text: str

class TicketCommentInDBBase(TicketCommentBase):
    id: UUID
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True, alias_generator=to_camel, populate_by_name=True)

    @computed_field
    def author_name(self) -> str:
        author = getattr(self, "author", None)
        return author.full_name if author else "Unknown"

    @computed_field
    def author_role(self) -> str:
        author = getattr(self, "author", None)
        return author.role if author else "analyst"

class TicketComment(TicketCommentInDBBase):
    pass

# Ticket Activity
class TicketActivityBase(BaseModel):
    ticket_id: UUID
    user_id: Optional[UUID] = None
    activity_type: TicketActivityType
    old_value: Optional[str] = None
    new_value: Optional[str] = None
    description: Optional[str] = None

class TicketActivity(TicketActivityBase):
    id: UUID
    timestamp: datetime

    model_config = ConfigDict(from_attributes=True, alias_generator=to_camel, populate_by_name=True)

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
    is_auto_escalation_enabled: bool = True
    is_repeat_finding: bool = False
    iso_clause: Optional[str] = None
    risk_score: Optional[int] = None
    related_risk_id: Optional[UUID] = None
    related_entity_type: Optional[str] = None
    related_entity_id: Optional[UUID] = None
    created_by: UUID
    due_date: Optional[datetime] = None
    previous_ticket_id: Optional[UUID] = None
    status_updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True, alias_generator=to_camel, populate_by_name=True)

    @computed_field
    def manager_id(self) -> Optional[UUID]:
        assignee = getattr(self, "assignee", None)
        return assignee.manager_id if assignee else None

    @computed_field
    def assigned_to_name(self) -> str:
        assignee = getattr(self, "assignee", None)
        return assignee.full_name if assignee else "Unassigned"

    @computed_field
    def escalated_to_name(self) -> Optional[str]:
        escalated_to = getattr(self, "escalated_to", None)
        return escalated_to.full_name if escalated_to else None

    @computed_field
    def creator_name(self) -> str:
        creator = getattr(self, "creator", None)
        return creator.full_name if creator else "System"

class AITicketCreate(BaseModel):
    criticalityScore: str
    findingsText: str
    controlId: Optional[UUID] = None
    riskId: Optional[UUID] = None
    source_audit_log_id: UUID

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
    is_auto_escalation_enabled: Optional[bool] = None
    resolved_at: Optional[datetime] = None
    escalated_at: Optional[datetime] = None

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

class TicketResolution(BaseModel):
    resolution_notes: str

class EvidenceRequest(BaseModel):
    comment_text: str

class TicketInDBBase(TicketBase):
    source_audit_log_id: Optional[UUID] = None
    id: UUID
    created_at: datetime
    updated_at: datetime
    resolved_at: Optional[datetime] = None
    escalated_at: Optional[datetime] = None
    due_date: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True, alias_generator=to_camel, populate_by_name=True)

class Ticket(TicketInDBBase):
    comments: List[TicketComment] = []
    activities: List[TicketActivity] = []
