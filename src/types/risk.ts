export type RiskStatus = 'identified' | 'assessed' | 'mitigated' | 'accepted';
export type RiskSeverity = 1 | 2 | 3 | 4 | 5;

export interface RiskCategory {
  id: string;
  name: string;
  description: string;
  color: string;
}

export interface Risk {
  id: string;
  title: string;
  description: string;
  categoryId: string;
  category?: RiskCategory;
  likelihood: RiskSeverity;
  impact: RiskSeverity;
  riskScore: number;
  status: RiskStatus;
  ownerId: string;
  ownerName?: string;
  createdBy: string;
  createdAt: string;
  updatedAt: string;
}

export interface RiskAssessment {
  id: string;
  riskId: string;
  assessmentDate: string;
  likelihood: RiskSeverity;
  impact: RiskSeverity;
  riskScore: number;
  notes?: string;
  assessorId: string;
  assessorName?: string;
  reviewedBy?: string;
  reviewedAt?: string;
  createdAt: string;
}
