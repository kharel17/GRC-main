import { Risk, RiskSeverity } from '@/types';

export interface RiskScoreExplanation {
  likelihood: {
    value: number;
    label: string;
    description: string;
  };
  impact: {
    value: number;
    label: string;
    description: string;
  };
  score: {
    value: number;
    label: string;
    severity: string;
    color: string;
  };
  recommendation: string;
}

const SEVERITY_LABELS: Record<RiskSeverity, string> = {
  1: 'Minimal',
  2: 'Low',
  3: 'Medium',
  4: 'High',
  5: 'Critical',
};

const SEVERITY_DESCRIPTIONS: Record<RiskSeverity, string> = {
  1: 'Almost no probability of occurrence',
  2: 'Low probability of occurrence',
  3: 'Moderate probability of occurrence',
  4: 'High probability of occurrence',
  5: 'Very likely to occur',
};

export function calculateRiskScore(likelihood: RiskSeverity, impact: RiskSeverity): number {
  return likelihood * impact;
}

export function getRiskSeverity(score: number): string {
  if (score <= 4) return 'Low';
  if (score <= 9) return 'Medium';
  if (score <= 16) return 'High';
  return 'Critical';
}

export function getRiskColor(score: number): string {
  if (score <= 4) return '#10b981';
  if (score <= 9) return '#f59e0b';
  if (score <= 16) return '#f97316';
  return '#ef4444';
}

export function getScoreLabel(score: number): string {
  if (score <= 4) return 'Low Risk';
  if (score <= 9) return 'Medium Risk';
  if (score <= 16) return 'High Risk';
  return 'Critical Risk';
}

export function explainRiskScore(risk: Risk): RiskScoreExplanation {
  return {
    likelihood: {
      value: risk.likelihood,
      label: SEVERITY_LABELS[risk.likelihood],
      description: SEVERITY_DESCRIPTIONS[risk.likelihood],
    },
    impact: {
      value: risk.impact,
      label: SEVERITY_LABELS[risk.impact],
      description: SEVERITY_DESCRIPTIONS[risk.impact],
    },
    score: {
      value: risk.riskScore || 0,
      label: getScoreLabel(risk.riskScore || 0),
      severity: getRiskSeverity(risk.riskScore || 0),
      color: getRiskColor(risk.riskScore || 0),
    },
    recommendation: getRecommendation(risk.riskScore || 0, risk.status || 'open'),
  };
}

export function getRecommendation(score: number, status: string): string {
  if (status === 'accepted') {
    return 'This risk has been accepted. Monitor for changes in business context.';
  }

  if (score <= 4) {
    return 'Low risk. Continue standard monitoring. Document in risk register.';
  }

  if (score <= 9) {
    return 'Medium risk. Develop mitigation strategy and assign owner. Review quarterly.';
  }

  if (score <= 16) {
    return 'High risk. Implement controls immediately. Review monthly for effectiveness.';
  }

  return 'Critical risk. Escalate to leadership. Implement emergency mitigation measures.';
}

export function residualRiskScore(
  originalLikelihood: RiskSeverity,
  originalImpact: RiskSeverity,
  controlEffectiveness: 'low' | 'medium' | 'high'
): { likelihood: number; impact: number; score: number } {
  const effectivenessMultiplier = {
    low: 0.7,
    medium: 0.5,
    high: 0.2,
  };

  const multiplier = effectivenessMultiplier[controlEffectiveness];

  const residualLikelihood = Math.ceil(originalLikelihood * multiplier);
  const residualImpact = Math.ceil(originalImpact * multiplier);
  const residualScore = residualLikelihood * residualImpact;

  return {
    likelihood: Math.max(1, residualLikelihood),
    impact: Math.max(1, residualImpact),
    score: Math.max(1, residualScore),
  };
}
