'use client';

import { Risk } from '@/types/risk';
import { ComplianceItem } from '@/types/compliance';
import { Control } from '@/types/control';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { TrendingUp, TrendingDown } from 'lucide-react';

interface DashboardSummaryProps {
  risks: Risk[];
  controls: Control[];
  complianceItems: ComplianceItem[];
}

export function DashboardSummary({ risks, controls, complianceItems }: DashboardSummaryProps) {
  const avgRiskScore =
    risks.length > 0 ? Math.round(risks.reduce((sum, r) => sum + r.riskScore, 0) / risks.length) : 0;

  const compliantItems = complianceItems.filter((c) => c.status === 'compliant').length;
  const complianceRate = Math.round((compliantItems / complianceItems.length) * 100) || 0;

  const implementedControls = controls.filter((c) => c.status === 'implemented').length;

  const metrics = [
    {
      label: 'Average Risk Score',
      value: avgRiskScore,
      trend: 'neutral',
      trendLabel: 'vs last month',
    },
    {
      label: 'Compliance Rate',
      value: `${complianceRate}%`,
      trend: 'positive',
      trendLabel: 'on track',
    },
    {
      label: 'Controls Implemented',
      value: `${implementedControls}/${controls.length}`,
      trend: 'positive',
      trendLabel: 'active controls',
    },
  ];

  return (
    <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
      {metrics.map((metric) => (
        <Card key={metric.label}>
          <CardHeader className="pb-3">
            <CardTitle className="text-sm font-medium text-slate-600">{metric.label}</CardTitle>
          </CardHeader>
          <CardContent className="space-y-2">
            <div className="flex items-baseline gap-2">
              <span className="text-3xl font-bold text-slate-900">{metric.value}</span>
              {metric.trend === 'positive' && (
                <TrendingUp className="h-4 w-4 text-green-600" />
              )}
              {metric.trend === 'negative' && (
                <TrendingDown className="h-4 w-4 text-red-600" />
              )}
            </div>
            <p className="text-xs text-slate-500">{metric.trendLabel}</p>
          </CardContent>
        </Card>
      ))}
    </div>
  );
}
