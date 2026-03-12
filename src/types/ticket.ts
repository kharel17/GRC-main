export type TicketPriority = 'critical' | 'high' | 'medium' | 'low';
export type TicketStatus = 
  | 'open' 
  | 'in_review' 
  | 'pending_evidence' 
  | 'escalated' 
  | 'rejected' 
  | 'resolved' 
  | 'pending_l2_review' 
  | 'pending_l1_signoff' 
  | 'closed' 
  | 'archived'
  | 'overdue';
export type TicketCategory =
  | 'risk_identified'
  | 'risk_mitigated'
  | 'compliance_gap'
  | 'security_incident'
  | 'audit_finding'
  | 'policy_violation';

export type EscalationLevel = 1 | 2 | 3 | 4;

export interface TicketComment {
  id: string;
  authorId: string;
  authorName: string;
  authorRole: string;
  text: string;
  timestamp: string;
}

export interface EscalationHistoryEntry {
  escalatedBy: string;
  escalatedByRole: string;
  escalatedTo: string;
  escalatedToRole: string;
  level: EscalationLevel;
  timestamp: string;
  note?: string;
}

export type TicketActivityType =
  | 'status_change'
  | 'priority_change'
  | 'assignment_change'
  | 'escalation'
  | 'resolution'
  | 'comment_added'
  | 'sla_missed'
  | 'other';

export interface TicketActivity {
  id: string;
  ticketId: string;
  userId?: string;
  activityType: TicketActivityType;
  oldValue?: string;
  newValue?: string;
  description?: string;
  timestamp: string;
}

export interface Ticket {
  id: string;
  title: string;
  description: string;
  priority: TicketPriority;
  status: TicketStatus;
  category: TicketCategory;
  sourceAuditLogId: string;
  
  // Ownership and Assignment
  assignedToId: string;
  assignedToRole: string;
  assignedToName: string;
  managerId?: string;
  isActingAdmin?: boolean;
  
  // Escalation
  escalatedToId?: string;
  escalatedToRole?: string;
  escalatedToName?: string;
  escalationLevel: EscalationLevel;
  isAutoEscalationEnabled: boolean;
  
  // Context
  relatedRiskId?: string;
  relatedEntityType?: string;
  relatedEntityId?: string;
  isRepeatFinding: boolean;
  isoClause?: string;
  riskScore?: number;
  previousTicketId?: string;
  
  // Metadata & Audit
  createdBy: string;
  creatorName: string;
  createdAt: string;
  updatedAt: string;
  statusUpdatedAt: string;
  resolvedAt?: string;
  escalatedAt?: string;
  dueDate?: string; // SLA deadline
  resolutionNotes?: string;
  
  activities: TicketActivity[];
  comments: TicketComment[];
}
