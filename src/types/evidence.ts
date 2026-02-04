export type EvidenceRelatedTo = 'risk' | 'control' | 'compliance_item';

export interface Evidence {
  id: string;
  title: string;
  description?: string;
  fileUrl?: string;
  fileName?: string;
  fileType?: string;
  fileSize?: number;
  relatedTo: EvidenceRelatedTo;
  relatedId: string;
  relatedName?: string;
  uploadedBy: string;
  uploadedByName?: string;
  uploadedAt: string;
  verified: boolean;
  verifiedBy?: string;
  verifiedByName?: string;
  verifiedAt?: string;
}
