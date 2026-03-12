"use client";

import { useApiData } from "@/hooks/use-api-data";
import { fetchComplianceItems } from "@/lib/data-service";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { PieChart, Pie, Cell, ResponsiveContainer, Legend, Tooltip } from "recharts";
import { PieChart as PieChartIcon, CheckCircle2, AlertCircle, Clock, Ban, Loader2 } from "lucide-react";
import { Progress } from "@/components/ui/progress";

export default function GapAnalysisPage() {
  const { data: compliance, loading } = useApiData(fetchComplianceItems);

  if (loading) {
    return (
      <div className="flex items-center justify-center py-24">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
        <span className="ml-3 text-muted-foreground">Running assessment...</span>
      </div>
    );
  }

  const stats = {
    compliant: compliance?.filter(i => i.status === 'compliant').length || 0,
    inProgress: compliance?.filter(i => i.status === 'in_progress').length || 0,
    nonCompliant: compliance?.filter(i => i.status === 'non_compliant').length || 0,
    notStarted: compliance?.filter(i => i.status === 'not_started').length || 0,
  };

  const total = (stats.compliant + stats.inProgress + stats.nonCompliant + stats.notStarted) || 1;
  const compliantPercentage = Math.round((stats.compliant / total) * 100);

  const chartData = [
    { name: 'Compliant', value: stats.compliant, color: '#22c55e' },
    { name: 'In Progress', value: stats.inProgress, color: '#eab308' },
    { name: 'Non Compliant', value: stats.nonCompliant, color: '#ef4444' },
    { name: 'Not Started', value: stats.notStarted, color: '#94a3b8' },
  ].filter(d => d.value > 0);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Gap Analysis</h1>
        <p className="text-muted-foreground text-sm">Real-time breakdown of control implementation gaps across compliance frameworks.</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <Card className="lg:col-span-1">
          <CardHeader>
            <CardTitle className="text-lg flex items-center gap-2">
              <PieChartIcon className="h-5 w-5 text-primary" />
              Compliance Posture
            </CardTitle>
            <CardDescription>Overall item distribution</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="h-[300px] w-full">
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={chartData}
                    cx="50%"
                    cy="50%"
                    innerRadius={60}
                    outerRadius={80}
                    paddingAngle={5}
                    dataKey="value"
                  >
                    {chartData.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={entry.color} />
                    ))}
                  </Pie>
                  <Tooltip />
                  <Legend verticalAlign="bottom" height={36} />
                </PieChart>
              </ResponsiveContainer>
            </div>
            <div className="mt-4 space-y-2">
              <div className="flex justify-between items-center text-sm">
                <span className="font-medium">Total Compliance Score</span>
                <span className="font-bold text-primary">{compliantPercentage}%</span>
              </div>
              <Progress value={compliantPercentage} className="h-2" />
            </div>
          </CardContent>
        </Card>

        <div className="lg:col-span-2 grid grid-cols-1 md:grid-cols-2 gap-4">
          <Card>
            <CardHeader className="pb-3 px-4">
              <CardTitle className="text-sm font-bold uppercase text-muted-foreground flex items-center gap-2">
                <CheckCircle2 className="h-4 w-4 text-green-500" />
                Compliant Items
              </CardTitle>
            </CardHeader>
            <CardContent className="px-4">
              <div className="text-3xl font-bold">{stats.compliant}</div>
              <p className="text-xs text-muted-foreground mt-1">Successfully implemented and verified controls.</p>
            </CardContent>
          </Card>
          
          <Card>
            <CardHeader className="pb-3 px-4">
              <CardTitle className="text-sm font-bold uppercase text-muted-foreground flex items-center gap-2">
                <Clock className="h-4 w-4 text-amber-500" />
                In Remediation
              </CardTitle>
            </CardHeader>
            <CardContent className="px-4">
              <div className="text-3xl font-bold">{stats.inProgress}</div>
              <p className="text-xs text-muted-foreground mt-1">Controls currently under implementation or review.</p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="pb-3 px-4">
              <CardTitle className="text-sm font-bold uppercase text-muted-foreground flex items-center gap-2">
                <Ban className="h-4 w-4 text-red-500" />
                Critical Gaps
              </CardTitle>
            </CardHeader>
            <CardContent className="px-4">
              <div className="text-3xl font-bold">{stats.nonCompliant}</div>
              <p className="text-xs text-muted-foreground mt-1">Identified failures requiring immediate attention.</p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="pb-3 px-4">
              <CardTitle className="text-sm font-bold uppercase text-muted-foreground flex items-center gap-2">
                <AlertCircle className="h-4 w-4 text-slate-400" />
                Not Addressed
              </CardTitle>
            </CardHeader>
            <CardContent className="px-4">
              <div className="text-3xl font-bold">{stats.notStarted}</div>
              <p className="text-xs text-muted-foreground mt-1">Items that have not yet been assessed or acted upon.</p>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
