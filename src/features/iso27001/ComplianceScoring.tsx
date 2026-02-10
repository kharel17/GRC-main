
"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import { useMemo } from "react";
import { ISOControl, ISOControlStatus } from "@/types/iso27001";
import { 
  BarChart, 
  Bar, 
  XAxis, 
  YAxis, 
  CartesianGrid, 
  Tooltip, 
  ResponsiveContainer,
  Cell
} from "recharts";

interface ComplianceScoringProps {
  controls: ISOControl[];
}

export function ComplianceScoring({ controls }: ComplianceScoringProps) {
  const stats = useMemo(() => {
    const total = controls.length;
    const implemented = controls.filter(c => c.status === 'implemented').length;
    const inProgress = controls.filter(c => c.status === 'in_progress').length;
    const notStarted = controls.filter(c => c.status === 'not_started').length;
    const notApplicable = controls.filter(c => c.status === 'not_applicable').length;
    const score = total > 0 ? Math.round((implemented / (total - notApplicable)) * 100) : 0;

    return { total, implemented, inProgress, notStarted, notApplicable, score };
  }, [controls]);

  const clauseStats = useMemo(() => {
    const groups: Record<string, { total: number; implemented: number }> = {};
    controls.forEach(c => {
      if (!groups[c.clauseId]) groups[c.clauseId] = { total: 0, implemented: 0 };
      groups[c.clauseId].total++;
      if (c.status === 'implemented') groups[c.clauseId].implemented++;
    });

    return Object.entries(groups).map(([clause, data]) => ({
      clause: `Clause ${clause}`,
      score: Math.round((data.implemented / data.total) * 100),
      total: data.total
    })).sort((a, b) => a.clause.localeCompare(b.clause));
  }, [controls]);

  const getScoreColor = (score: number) => {
    if (score >= 80) return "text-green-600";
    if (score >= 50) return "text-amber-600";
    return "text-red-600";
  };

  const getBarColor = (score: number) => {
    if (score >= 80) return "#16a34a";
    if (score >= 50) return "#d97706";
    return "#dc2626";
  };

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-slate-500">Compliance Score</CardTitle>
          </CardHeader>
          <CardContent>
            <div className={`text-3xl font-bold ${getScoreColor(stats.score)}`}>{stats.score}%</div>
            <Progress value={stats.score} className="h-2 mt-2" />
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-slate-500">Implemented</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold text-green-600">{stats.implemented}</div>
            <div className="text-xs text-slate-500">controls</div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-slate-500">In Progress</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold text-amber-600">{stats.inProgress}</div>
            <div className="text-xs text-slate-500">controls</div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-slate-500">Gap</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold text-slate-600">{stats.notStarted}</div>
            <div className="text-xs text-slate-500">not started controls</div>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Compliance by Clause</CardTitle>
        </CardHeader>
        <CardContent>
         <div className="h-[300px] w-full">
            <ResponsiveContainer width="100%" height="100%">
               <BarChart data={clauseStats} layout="vertical" margin={{ top: 5, right: 30, left: 40, bottom: 5 }}>
                  <CartesianGrid strokeDasharray="3 3" horizontal={false} stroke="hsl(var(--border))" />
                  <XAxis type="number" domain={[0, 100]} hide />
                  <YAxis 
                    dataKey="clause" 
                    type="category" 
                    width={100} 
                    tick={{ fill: 'hsl(var(--muted-foreground))', fontSize: 12 }} 
                    axisLine={false}
                    tickLine={false}
                  />
                  <Tooltip 
                    cursor={{ fill: 'hsl(var(--muted)/0.2)' }}
                    contentStyle={{ 
                      borderRadius: '8px', 
                      border: '1px solid hsl(var(--border))', 
                      backgroundColor: 'hsl(var(--card))',
                      color: 'hsl(var(--foreground))'
                    }}
                  />
                  <Bar dataKey="score" name="Compliance %" radius={[0, 4, 4, 0]} barSize={32}>
                    {clauseStats.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={
                        entry.score >= 80 ? 'hsl(var(--green-600))' : 
                        entry.score >= 50 ? 'hsl(var(--amber-500))' : 'hsl(var(--destructive))'
                      } />
                    ))}
                  </Bar>
               </BarChart>
            </ResponsiveContainer>
         </div>
         <div className="mt-4 grid grid-cols-2 md:grid-cols-4 gap-4">
             {clauseStats.map(clause => (
               <div key={clause.clause} className="flex flex-col p-3 rounded-lg border border-border bg-card">
                  <span className="text-xs text-muted-foreground mb-1">{clause.clause}</span>
                  <div className="flex items-end gap-2">
                     <span className="text-lg font-bold text-foreground">{Math.round(clause.score)}%</span>
                     <Progress value={clause.score} className="h-1.5 w-16 mb-2" />
                  </div>
               </div>
             ))}
         </div>
      </CardContent>
      </Card>
    </div>
  );
}
