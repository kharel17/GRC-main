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

export interface Ticket {
  id: string;
  title: string;
  description: string;
  priority: TicketPriority;
  status: TicketStatus;
  category: TicketCategory;
  sourceAuditLogId: string;
  assignedTo: string;
  assignedToRole: string;
  escalatedTo?: string;
  escalatedToRole?: string;
  escalationLevel: EscalationLevel;
  relatedRiskId?: string;
  relatedRiskTitle?: string;
  relatedEntityType?: string;
  relatedEntityId?: string;
  createdBy: string;
  createdByName: string;
  createdAt: string;
  updatedAt: string;
  resolvedAt?: string;
  escalatedAt?: string;
  isAutoEscalationEnabled?: boolean;
  comments: TicketComment[];
}
