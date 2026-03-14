import { UserRole, Ticket, TicketStatus, TicketPriority, EscalationLevel } from '@/types';
import { addDays, addHours, isPast, parseISO } from 'date-fns';

// ============================================================================
// Config: Escalation Hierarchy
// ============================================================================

export const ROLE_ESCALATION_LEVEL: Record<UserRole, EscalationLevel | null> = {
  analyst: 1,
  control_owner: 1,
  risk_owner: 1,
  
  compliance_officer: 2,
  department_manager: 2,
  manager: 2,
  
  executive: 3,
  
  admin: 4,
  
  // Auditor is read-only, cannot be escalated to
  auditor: null,
  superadmin: 4,
};

// ============================================================================
// Config: SLA / Due Dates
// ============================================================================

export function getDefaultDueDate(priority: TicketPriority): Date {
  const now = new Date();
  switch (priority) {
    case 'critical':
      return addHours(now, 24); // 24 hours
    case 'high':
      return addDays(now, 3);   // 3 days
    case 'medium':
      return addDays(now, 7);   // 7 days
    case 'low':
      return addDays(now, 14);  // 14 days
    default:
      return addDays(now, 7);
  }
}

// ============================================================================
// Config: Status State Machine
// ============================================================================

export const VALID_STATUS_TRANSITIONS: Record<TicketStatus, TicketStatus[]> = {
  open: ['in_review', 'escalated', 'closed'],
  in_review: ['pending_evidence', 'resolved', 'escalated', 'rejected'],
  pending_evidence: ['in_review', 'escalated'],
  escalated: ['in_review', 'resolved', 'closed', 'escalated'],
  resolved: ['pending_l2_review', 'pending_l1_signoff', 'closed', 'in_review'],
  pending_l2_review: ['resolved', 'pending_l1_signoff', 'rejected'],
  pending_l1_signoff: ['closed', 'rejected'],
  rejected: ['in_review', 'open'],
  closed: ['open'],
  archived: [],
  overdue: ['escalated', 'in_review'],
};

// ============================================================================
// Helpers
// ============================================================================

export function getNextEscalationLevel(currentRole: UserRole): EscalationLevel {
  const currentLevel = ROLE_ESCALATION_LEVEL[currentRole] || 1;
  const nextLevel = Math.min(currentLevel + 1, 4) as EscalationLevel;
  return nextLevel;
}

export function canActOnTicket(ticket: Ticket, userId: string, userRole: UserRole): boolean {
  // Admins can always act
  if (userRole === 'admin') return true;
  
  // If the ticket is escalated, special roles can act
  if (ticket.status === 'escalated') {
    return ticket.escalatedToId === userId || userRole === 'department_manager' || userRole === 'executive';
  }
  
  // Default: Assigned user can act
  return ticket.assignedToId === userId;
}

export function isTicketOverdue(ticket: Ticket): boolean {
  if (ticket.status === 'resolved' || ticket.status === 'closed') return false;
  if (!ticket.dueDate) return false;
  
  // backend provides ISO string
  return isPast(parseISO(ticket.dueDate));
}

export function canTransitionTo(currentStatus: TicketStatus, targetStatus: TicketStatus): boolean {
  return VALID_STATUS_TRANSITIONS[currentStatus]?.includes(targetStatus) ?? false;
}
