
export type ISOControlStatus = 'not_started' | 'in_progress' | 'implemented' | 'not_applicable';

export interface ISOClause {
  id: string;
  title: string;
  description?: string;
  order: number;
}

export interface ISOControl {
  id: string;
  clauseId: string;
  annex: string; // e.g., "5.1"
  title: string;
  description: string;
  guidance?: string;
  status: ISOControlStatus;
  ownerId?: string;
  ownerName?: string;
  lastReviewDate?: string;
  nextReviewDate?: string;
  notes?: string;
  evidenceCount?: number;
  createdAt: string;
  updatedAt: string;
}

export interface ISOEvidence {
  id: string;
  title: string;
  description?: string;
  file_url?: string;
  fileUrl: string; // Keep for compatibility
  file_name?: string;
  fileName: string; // Keep for compatibility
  file_type?: string;
  fileType: string; // Keep for compatibility
  file_size?: number;
  fileSize: number; // Keep for compatibility
  control_id?: string;
  controlId: string; // Keep for compatibility
  uploaded_by?: string;
  uploadedBy: string; // Keep for compatibility
  uploaded_by_name?: string;
  uploadedByName?: string;
  uploaded_at: string;
  uploadedAt?: string; // Change to optional if not usually used as alias
  version: number;
  previousVersionId?: string;
}

export interface ISOComplianceStats {
  totalControls: number;
  implementedControls: number;
  inProgressControls: number;
  notStartedControls: number;
  notApplicableControls: number;
  complianceScore: number; // 0-100
}

export interface ISOAuditLog {
  id: string;
  action: 'create' | 'update' | 'delete' | 'upload_evidence' | 'delete_evidence' | 'link_risk';
  entityId: string;
  entityType: 'control' | 'evidence';
  userId: string;
  userName: string;
  timestamp: string;
  details: string;
  changes?: {
    field: string;
    oldValue: any;
    newValue: any;
  }[];
}
