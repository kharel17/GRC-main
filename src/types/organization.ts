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
  employee_count?: number;
  risk_appetite?: Record<string, any>;
  compliance_target_date?: string;
  createdAt: string;
  updatedAt: string;
}
