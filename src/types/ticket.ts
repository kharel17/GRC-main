export type TicketPriority = 'critical' | 'high' | 'medium' | 'low';
export type TicketStatus = 'open' | 'in_progress' | 'escalated' | 'resolved' | 'closed';
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

export interface ActivityLogEntry {
  action: 'created' | 'assigned' | 'escalated' | 'resolved' | 'closed' | 'commented' | 'reopened';
  performedBy: string;
  performedByRole: string;
  timestamp: string;
  details?: string;
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
  assignedTo: string;
  assignedToRole: string;
  ownerUserId?: string; // The current acting owner
  
  // Escalation
  escalatedTo?: string;
  escalatedToRole?: string;
  escalationLevel: EscalationLevel;
  escalationHistory?: EscalationHistoryEntry[];
  
  // Context
  relatedRiskId?: string;
  relatedRiskTitle?: string;
  relatedEntityType?: string;
  relatedEntityId?: string;
  
  // Metadata & Audit
  createdBy: string;
  createdByName: string;
  createdAt: string;
  updatedAt: string;
  resolvedAt?: string;
  escalatedAt?: string;
  dueDate?: string; // SLA deadline
  resolutionNotes?: string;
  activityLog?: ActivityLogEntry[];
  
  isAutoEscalationEnabled?: boolean;
  comments: TicketComment[];
}
