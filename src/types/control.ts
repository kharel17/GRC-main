export type ControlType = 'preventive' | 'detective' | 'corrective';
export type ControlStatus = 'planned' | 'implemented' | 'under_review';
export type ControlEffectiveness = 'low' | 'medium' | 'high';

export interface Control {
  id: string;
  title: string;
  description: string;
  controlType: ControlType;
  effectiveness: ControlEffectiveness;
  status: ControlStatus;
  ownerId: string;
  ownerName?: string;
  createdBy: string;
  createdAt: string;
  updatedAt: string;
}

export interface RiskControlMapping {
  id: string;
  riskId: string;
  controlId: string;
  residualLikelihood?: number;
  residualImpact?: number;
  residualRiskScore?: number;
  mappedBy: string;
  mappedAt: string;
}
