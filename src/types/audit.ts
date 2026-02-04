export type AuditAction = 'created' | 'updated' | 'deleted' | 'approved' | 'rejected' | 'reviewed';
export type AuditEntityType = 'risk' | 'control' | 'evidence' | 'compliance_item' | 'user';

export interface AuditLog {
  id: string;
  userId: string;
  userName: string;
  action: AuditAction;
  entityType: AuditEntityType;
  entityId: string;
  entityName?: string;
  oldValues?: Record<string, any>;
  newValues?: Record<string, any>;
  timestamp: string;
  ipAddress?: string;
  description?: string;
}
