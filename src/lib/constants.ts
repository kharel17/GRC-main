import { RiskCategory } from '@/types/risk';

export const RISK_CATEGORIES: RiskCategory[] = [
  { id: '1', name: 'Operational', description: 'Day-to-day operational risks', color: '#3b82f6' },
  { id: '2', name: 'Financial', description: 'Financial stability risks', color: '#10b981' },
  { id: '3', name: 'Compliance', description: 'Regulatory compliance risks', color: '#f59e0b' },
  { id: '4', name: 'Strategic', description: 'Long-term strategy risks', color: '#8b5cf6' },
  { id: '5', name: 'Reputational', description: 'Brand and reputation risks', color: '#ef4444' },
  { id: '6', name: 'Technology', description: 'IT and cybersecurity risks', color: '#06b6d4' },
];

export const RISK_SEVERITY_LEVELS = {
  1: 'Minimal',
  2: 'Low',
  3: 'Medium',
  4: 'High',
  5: 'Critical',
} as const;

export const RISK_SCORE_MATRIX = {
  1: { min: 1, max: 4, severity: 'Low' },
  2: { min: 5, max: 9, severity: 'Medium' },
  3: { min: 10, max: 16, severity: 'High' },
  4: { min: 17, max: 25, severity: 'Critical' },
} as const;

export const CONTROL_TYPES = ['preventive', 'detective', 'corrective'] as const;

export const CONTROL_EFFECTIVENESS = ['low', 'medium', 'high'] as const;

export const CONTROL_STATUS = ['planned', 'implemented', 'under_review'] as const;

export const COMPLIANCE_FRAMEWORKS = ['SOC2', 'ISO27001', 'GDPR', 'HIPAA', 'PCI-DSS'] as const;

export const COMPLIANCE_STATUS = ['not_started', 'in_progress', 'compliant', 'non_compliant'] as const;

export const COMPLIANCE_PRIORITY = ['low', 'medium', 'high', 'critical'] as const;

export const USER_ROLES = ['admin', 'analyst', 'manager'] as const;
