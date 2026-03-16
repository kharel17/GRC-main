"use client";

import { useState } from 'react';
import { Risk } from '@/types';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { AlertTriangle, ArrowRight, TrendingUp } from 'lucide-react';
import Link from 'next/link';

interface RiskHighlightsProps {
  risks: Risk[];
}

type FilterType = 'all' | 'high' | 'medium' | 'low';

function getRiskLevel(score: number): 'high' | 'medium' | 'low' {
  if (score >= 12) return 'high';
  if (score >= 6) return 'medium';
  return 'low';
}

function getScoreStyles(score: number) {
  const level = getRiskLevel(score);
  switch (level) {
    case 'high':
      return 'bg-red-100 text-red-700 border-red-200 dark:bg-red-900/30 dark:text-red-400 dark:border-red-900/30';
    case 'medium':
      return 'bg-amber-100 text-amber-700 border-amber-200 dark:bg-amber-900/30 dark:text-amber-400 dark:border-amber-900/30';
    case 'low':
      return 'bg-green-100 text-green-700 border-green-200 dark:bg-green-900/30 dark:text-green-400 dark:border-green-900/30';
  }
}

export function RiskHighlights({ risks }: RiskHighlightsProps) {
  const [filter, setFilter] = useState<FilterType>('all');

  const filteredRisks = risks.filter((risk) => {
    if (filter === 'all') return true;
    return getRiskLevel(risk.score) === filter;
  });

  // Sort by risk score descending and take top 5
  const topRisks = [...filteredRisks]
    .sort((a, b) => (b.score || 0) - (a.score || 0))
    .slice(0, 5);

  const filterButtons: { label: string; value: FilterType; count: number }[] = [
    { label: 'All', value: 'all', count: risks.length },
    { label: 'High', value: 'high', count: risks.filter(r => getRiskLevel(r.score) === 'high').length },
    { label: 'Medium', value: 'medium', count: risks.filter(r => getRiskLevel(r.score) === 'medium').length },
    { label: 'Low', value: 'low', count: risks.filter(r => getRiskLevel(r.score) === 'low').length },
  ];

  return (
    <Card className="h-full">
      <CardHeader className="pb-3">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
          <CardTitle className="text-base font-semibold flex items-center gap-2">
            <TrendingUp className="h-5 w-5 text-muted-foreground" />
            Risk Highlights
          </CardTitle>
          <Link href="/dashboard/risks">
            <Button variant="ghost" size="sm" className="gap-1 text-blue-600 hover:text-blue-700 hover:bg-blue-50 dark:text-blue-400 dark:hover:text-blue-300 dark:hover:bg-blue-900/20">
              View All
              <ArrowRight className="h-4 w-4" />
            </Button>
          </Link>
        </div>
        
        {/* Filter Tabs */}
        <div className="flex flex-wrap gap-2 mt-4">
          {filterButtons.map((btn) => (
            <button
              key={btn.value}
              onClick={() => setFilter(btn.value)}
              className={`px-4 py-1.5 text-[10px] font-black uppercase tracking-widest rounded-full transition-all border ${
                filter === btn.value
                  ? 'bg-primary text-white border-primary shadow-md scale-105'
                  : 'bg-white dark:bg-slate-900 text-slate-500 border-slate-200 dark:border-slate-800 hover:border-primary/50'
              }`}
            >
              {btn.label} <span className="opacity-50 ml-1">{btn.count}</span>
            </button>
          ))}
        </div>
      </CardHeader>
      <CardContent>
        {topRisks.length === 0 ? (
          <div className="text-center py-8">
            <AlertTriangle className="h-8 w-8 text-muted-foreground mx-auto mb-2" />
            <p className="text-sm text-muted-foreground">No risks match the selected filter</p>
          </div>
        ) : (
          <div className="space-y-3">
            {topRisks.map((risk) => (
              <Link
                key={risk.id}
                href={`/dashboard/risks/${risk.id}`}
                className="block p-4 rounded-xl border border-slate-100 dark:border-slate-800 bg-white dark:bg-slate-950/50 hover:border-primary/30 hover:shadow-md transition-all group"
              >
                <div className="flex items-center justify-between gap-4">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1.5">
                      <p className="font-bold text-sm text-slate-900 dark:text-slate-100 truncate group-hover:text-primary transition-colors">
                        {risk.title}
                      </p>
                    </div>
                    <div className="flex items-center gap-3">
                      {risk.category && (
                        <span className="text-[10px] font-black uppercase tracking-tighter text-muted-foreground bg-slate-100 dark:bg-slate-800 px-2 py-0.5 rounded">
                          {risk.category.name}
                        </span>
                      )}
                      <div className="flex items-center gap-1.5">
                        <div className="flex items-center -space-x-1">
                          <div className={`w-2 h-2 rounded-full border border-white dark:border-slate-950 ${risk.likelihood > 3 ? 'bg-red-500' : 'bg-amber-500'}`} />
                          <div className={`w-2 h-2 rounded-full border border-white dark:border-slate-950 ${risk.impact > 3 ? 'bg-red-500' : 'bg-amber-500'}`} />
                        </div>
                        <span className="text-[10px] font-bold text-slate-500 uppercase tracking-tighter">
                          L:{risk.likelihood || risk.probability} × I:{risk.impact}
                        </span>
                      </div>
                    </div>
                  </div>
                  <div className={`flex items-center justify-center w-10 h-10 rounded-xl border-2 font-black text-sm shrink-0 shadow-sm ${getScoreStyles(risk.score)}`}>
                    {risk.score}
                  </div>
                </div>
              </Link>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
