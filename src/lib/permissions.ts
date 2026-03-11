import { UserRole } from '@/types/user';

// =============================================================================
// Role Display Configuration
// =============================================================================

export const ROLE_DISPLAY_NAMES: Record<UserRole, string> = {
  admin: 'Administrator',
  analyst: 'Risk Analyst',
  control_owner: 'Control Owner',
  risk_owner: 'Risk Owner',
  compliance_officer: 'Compliance Officer',
  department_manager: 'Department Manager',
  executive: 'Executive (CISO/CTO)',
  auditor: 'Auditor',
};

// =============================================================================
// Permission Definitions
// =============================================================================

export const ROLE_PERMISSIONS: Record<UserRole, string[]> = {
  admin: [
    'manage_users',
    'manage_roles',
    'view_all_data',
    'create_risk',
    'edit_risk',
    'delete_risk',
    'create_control',
    'edit_control',
    'delete_control',
    'create_evidence',
    'verify_evidence',
    'delete_evidence',
    'create_compliance',
    'edit_compliance',
    'view_audit_logs',
    'export_reports',
    'configure_system',
    'create_ticket',
    'escalate_ticket',
    'resolve_ticket',
    'assign_ticket',
  ],
  analyst: [
    'create_risk',
    'edit_risk',
    'create_control',
    'edit_control',
    'create_evidence',
    'create_compliance',
    'edit_compliance',
    'view_audit_logs',
    'export_reports',
    'create_ticket',
    'escalate_ticket',
    'resolve_ticket',
  ],
  control_owner: [
    'edit_control',
    'create_evidence',
    'view_audit_logs',
    'create_ticket',
    'escalate_ticket',
    'resolve_ticket',
  ],
  risk_owner: [
    'edit_risk',
    'create_evidence',
    'view_audit_logs',
    'create_ticket',
    'escalate_ticket',
    'resolve_ticket',
  ],
  compliance_officer: [
    'view_all_data',
    'create_compliance',
    'edit_compliance',
    'verify_evidence',
    'view_audit_logs',
    'export_reports',
    'create_ticket',
    'escalate_ticket',
    'resolve_ticket',
    'approve_actions',
  ],
  department_manager: [
    'view_all_data',
    'approve_actions',
    'view_audit_logs',
    'export_reports',
    'create_ticket',
    'escalate_ticket',
    'resolve_ticket',
  ],
  executive: [
    'view_all_data',
    'approve_actions',
    'view_audit_logs',
    'export_reports',
    'escalate_ticket',
    'resolve_ticket',
  ],
  auditor: [
    'view_all_data',
    'view_audit_logs',
    'export_reports',
  ],
};

// =============================================================================
// Permission Helpers
// =============================================================================

export function hasPermission(role: UserRole, permission: string): boolean {
  return ROLE_PERMISSIONS[role]?.includes(permission) ?? false;
}

export function canEditRisk(role: UserRole): boolean {
  return hasPermission(role, 'edit_risk');
}

export function canCreateRisk(role: UserRole): boolean {
  return hasPermission(role, 'create_risk');
}

export function canDeleteRisk(role: UserRole): boolean {
  return hasPermission(role, 'delete_risk');
}

export function canCreateControl(role: UserRole): boolean {
  return hasPermission(role, 'create_control');
}

export function canEditControl(role: UserRole): boolean {
  return hasPermission(role, 'edit_control');
}

export function canUploadEvidence(role: UserRole): boolean {
  return hasPermission(role, 'create_evidence');
}

export function canVerifyEvidence(role: UserRole): boolean {
  return hasPermission(role, 'verify_evidence');
}

export function canApproveActions(role: UserRole): boolean {
  return hasPermission(role, 'approve_actions');
}

export function canViewAuditLogs(role: UserRole): boolean {
  return hasPermission(role, 'view_audit_logs');
}

export function canManageUsers(role: UserRole): boolean {
  return hasPermission(role, 'manage_users');
}

export function isAdmin(role: UserRole): boolean {
  return role === 'admin';
}

export function isAnalyst(role: UserRole): boolean {
  return role === 'analyst';
}

export function isManager(role: UserRole): boolean {
  return role === 'department_manager';
}
