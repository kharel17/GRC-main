
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
  evidenceIds?: string[];
  riskIds?: string[];
  createdAt: string;
  updatedAt: string;
}

export interface ISOEvidence {
  id: string;
  title: string;
  description?: string;
  fileUrl: string;
  fileName: string;
  fileType: string;
  fileSize: number;
  controlId: string;
  uploadedBy: string;
  uploadedByName?: string;
  uploadedAt: string;
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
