import { UserRole } from '@/types/user';
import { Ticket, TicketStatus, TicketPriority, EscalationLevel } from '@/types/ticket';
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
  
  executive: 3,
  
  admin: 4,
  
  // Auditor is read-only, cannot be escalated to
  auditor: null,
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
  open: ['in_progress', 'escalated', 'closed'],
  in_progress: ['escalated', 'resolved', 'closed'],
  escalated: ['in_progress', 'resolved', 'closed', 'escalated'], // Can escalate further
  resolved: ['closed', 'in_progress'], // Can be reopened
  closed: ['in_progress'], // Can be reopened
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
  
  // Determine who the current acting owner is
  // If ownerUserId is set, they are the sole owner
  if (ticket.ownerUserId) {
    return ticket.ownerUserId === userId;
  }
  
  // Fallback to legacy assignment checking
  if (ticket.status === 'escalated') {
    return ticket.escalatedTo === userId;
  }
  
  return ticket.assignedTo === userId;
}

export function isTicketOverdue(ticket: Ticket): boolean {
  if (ticket.status === 'resolved' || ticket.status === 'closed') return false;
  if (!ticket.dueDate) return false;
  
  return isPast(parseISO(ticket.dueDate));
}

export function canTransitionTo(currentStatus: TicketStatus, targetStatus: TicketStatus): boolean {
  return VALID_STATUS_TRANSITIONS[currentStatus]?.includes(targetStatus) ?? false;
}
