export type AssetType = 'data' | 'software' | 'hardware' | 'service' | 'personnel' | 'physical' | 'server' | 'db' | 'app';
export type AssetClassification = 'public' | 'internal' | 'confidential' | 'restricted';
export type AssetCriticality = 'low' | 'medium' | 'high' | 'critical';
export type AssetStatus = 'active' | 'decommissioned' | 'under_review';

export interface Asset {
  id: string;
  organizationId: string;
  name: string;
  description?: string;
  assetType: AssetType;
  classification: AssetClassification;
  criticality: AssetCriticality;
  location?: string;
  status: AssetStatus;
  ownerId: string;
  related_risks?: string[];
  createdAt: string;
  updatedAt: string;
}
