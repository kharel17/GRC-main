export interface Organization {
  id: string;
  name: string;
  industry?: string;
  size?: string;
  description?: string;
  website?: string;
  country?: string;
  complianceFrameworks: string[];
  primaryContactId?: string;
  createdAt: string;
  updatedAt: string;
}
