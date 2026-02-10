'use client';

import { Risk } from '@/types/risk';
import { ComplianceItem } from '@/types/compliance';
import { Control } from '@/types/control';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { TrendingUp, TrendingDown, Minus, AlertTriangle, Shield, CheckCircle2, BarChart3 } from 'lucide-react';

interface DashboardSummaryProps {
  risks: Risk[];
  controls: Control[];
  complianceItems: ComplianceItem[];
  isLoading?: boolean;
}

function MetricSkeleton() {
  return (
    <Card className="animate-pulse">
      <CardHeader className="pb-3">
        <div className="h-4 bg-muted rounded w-24" />
      </CardHeader>
      <CardContent className="space-y-2">
        <div className="h-8 bg-muted rounded w-16" />
        <div className="h-3 bg-muted rounded w-20" />
      </CardContent>
    </Card>
  );
}

export function DashboardSummary({ risks, controls, complianceItems, isLoading }: DashboardSummaryProps) {
  if (isLoading) {
    return (
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        {Array.from({ length: 4 }).map((_, i) => (
          <MetricSkeleton key={i} />
        ))}
      </div>
    );
  }

  const avgRiskScore =
    risks.length > 0 ? Math.round(risks.reduce((sum, r) => sum + r.riskScore, 0) / risks.length) : 0;

  const openRisks = risks.filter((r) => r.status !== 'mitigated' && r.status !== 'accepted').length;

  const compliantItems = complianceItems.filter((c) => c.status === 'compliant').length;
  const complianceRate = Math.round((compliantItems / complianceItems.length) * 100) || 0;

  const implementedControls = controls.filter((c) => c.status === 'implemented').length;

  const getTrendIcon = (trend: string) => {
    switch (trend) {
      case 'positive':
        return <TrendingUp className="h-4 w-4 text-green-600 dark:text-green-400" />;
      case 'negative':
        return <TrendingDown className="h-4 w-4 text-red-600 dark:text-red-400" />;
      default:
        return <Minus className="h-4 w-4 text-muted-foreground" />;
    }
  };

  const getMetricIcon = (type: string) => {
    switch (type) {
      case 'risk':
        return <AlertTriangle className="h-5 w-5" />;
      case 'open':
        return <BarChart3 className="h-5 w-5" />;
      case 'compliance':
        return <CheckCircle2 className="h-5 w-5" />;
      case 'controls':
        return <Shield className="h-5 w-5" />;
      default:
        return null;
    }
  };

  const metrics = [
    {
      label: 'Average Risk Score',
      value: avgRiskScore,
      trend: avgRiskScore > 10 ? 'negative' : avgRiskScore > 5 ? 'neutral' : 'positive',
      trendLabel: 'Risk level',
      type: 'risk',
      color: avgRiskScore > 10 
        ? 'text-red-700 bg-red-50 dark:bg-red-900/30 dark:text-red-400' 
        : avgRiskScore > 5 
          ? 'text-amber-700 bg-amber-50 dark:bg-amber-900/30 dark:text-amber-400' 
          : 'text-green-700 bg-green-50 dark:bg-green-900/30 dark:text-green-400',
    },
    {
      label: 'Open Risks',
      value: openRisks,
      trend: openRisks > 3 ? 'negative' : 'neutral',
      trendLabel: 'Require attention',
      type: 'open',
      color: openRisks > 3 
        ? 'text-red-700 bg-red-50 dark:bg-red-900/30 dark:text-red-400' 
        : 'text-blue-700 bg-blue-50 dark:bg-blue-900/30 dark:text-blue-400',
    },
    {
      label: 'Compliance Rate',
      value: `${complianceRate}%`,
      trend: complianceRate >= 80 ? 'positive' : complianceRate >= 60 ? 'neutral' : 'negative',
      trendLabel: 'On track',
      type: 'compliance',
      color: complianceRate >= 80 
        ? 'text-green-700 bg-green-50 dark:bg-green-900/30 dark:text-green-400' 
        : complianceRate >= 60 
          ? 'text-amber-700 bg-amber-50 dark:bg-amber-900/30 dark:text-amber-400' 
          : 'text-red-700 bg-red-50 dark:bg-red-900/30 dark:text-red-400',
    },
    {
      label: 'Controls Active',
      value: `${implementedControls}/${controls.length}`,
      trend: implementedControls === controls.length ? 'positive' : 'neutral',
      trendLabel: 'Implemented',
      type: 'controls',
      color: 'text-blue-700 bg-blue-50 dark:bg-blue-900/30 dark:text-blue-400',
    },
  ];

  return (
    <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
      {metrics.map((metric) => (
        <Card key={metric.label} className="card-hover group">
          <CardHeader className="pb-2">
            <div className="flex items-center justify-between">
              <CardTitle className="text-xs sm:text-sm font-medium text-muted-foreground">
                {metric.label}
              </CardTitle>
              <span className={`p-1.5 rounded-lg ${metric.color} opacity-80 group-hover:opacity-100 transition-opacity`}>
                {getMetricIcon(metric.type)}
              </span>
            </div>
          </CardHeader>
          <CardContent className="pt-0">
            <div className="flex items-baseline gap-2">
              <span className="text-2xl sm:text-3xl font-bold text-foreground">{metric.value}</span>
              {getTrendIcon(metric.trend)}
            </div>
            <p className="text-xs text-muted-foreground mt-1">{metric.trendLabel}</p>
          </CardContent>
        </Card>
      ))}
    </div>
  );
}
