'use client';

import { Risk, ComplianceItem, Control } from '@/types';
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

  const rawAvgRiskScore =
    risks.length > 0 
      ? Math.round(risks.reduce((sum, r) => sum + (r.score ?? 0), 0) / risks.length) 
      : 0;
  const avgRiskScore = isNaN(rawAvgRiskScore) ? 0 : rawAvgRiskScore;

  const openRisks = risks.filter((r) => r.status !== 'mitigated' && r.status !== 'accepted').length;

  const compliantItems = complianceItems.filter((c) => c.status === 'compliant').length;
  const rawComplianceRate = complianceItems.length > 0 ? Math.round((compliantItems / complianceItems.length) * 100) : 0;
  const complianceRate = isNaN(rawComplianceRate) ? 0 : rawComplianceRate;

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
      value: `${implementedControls ?? 0}/${controls.length ?? 0}`,
      trend: implementedControls === controls.length ? 'positive' : 'neutral',
      trendLabel: 'Implemented',
      type: 'controls',
      color: 'text-blue-700 bg-blue-50 dark:bg-blue-900/30 dark:text-blue-400',
    },
  ];

  return (
    <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
      {metrics.map((metric) => (
        <Card key={metric.label} className="relative overflow-hidden border-slate-200/60 dark:border-slate-800/60 bg-white/50 dark:bg-slate-950/50 backdrop-blur-sm transition-all hover:shadow-lg hover:-translate-y-1 group">
          <div className="absolute top-0 right-0 w-24 h-24 bg-gradient-to-br from-primary/5 to-transparent rounded-full -mr-12 -mt-12 transition-transform group-hover:scale-150" />
          <CardHeader className="pb-2">
            <div className="flex items-center justify-between">
              <CardTitle className="text-xs sm:text-[10px] font-bold uppercase tracking-widest text-muted-foreground/80">
                {metric.label}
              </CardTitle>
              <div className={`p-2 rounded-xl ${metric.color} shadow-sm group-hover:scale-110 transition-transform`}>
                {getMetricIcon(metric.type)}
              </div>
            </div>
          </CardHeader>
          <CardContent className="pt-0">
            <div className="flex items-baseline gap-2">
              <span className="text-2xl sm:text-3xl font-black tracking-tight text-slate-900 dark:text-slate-100">
                {metric.value}
              </span>
              <div className="flex items-center group-hover:translate-x-0.5 transition-transform">
                {getTrendIcon(metric.trend)}
              </div>
            </div>
            <div className="flex items-center gap-1.5 mt-2">
              <div className={`w-1.5 h-1.5 rounded-full ${
                metric.trend === 'positive' ? 'bg-green-500' : 
                metric.trend === 'negative' ? 'bg-red-500' : 'bg-amber-500'
              }`} />
              <p className="text-[10px] font-bold text-muted-foreground/70 uppercase tracking-tighter">{metric.trendLabel}</p>
            </div>
          </CardContent>
        </Card>
      ))}
    </div>
  );
}
