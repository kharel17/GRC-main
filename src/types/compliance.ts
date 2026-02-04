export type ComplianceStatus = 'not_started' | 'in_progress' | 'compliant' | 'non_compliant';
export type CompliancePriority = 'low' | 'medium' | 'high' | 'critical';

export interface ComplianceItem {
  id: string;
  framework: string;
  requirementId: string;
  title: string;
  description: string;
  status: ComplianceStatus;
  priority: CompliancePriority;
  dueDate?: string;
  ownerId: string;
  ownerName?: string;
  createdAt: string;
  updatedAt: string;
  evidenceCount?: number;
}
