"use client";

import { useState } from 'react';
import { Risk } from '@/types/risk';
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
    return getRiskLevel(risk.riskScore) === filter;
  });

  // Sort by risk score descending and take top 5
  const topRisks = [...filteredRisks]
    .sort((a, b) => b.riskScore - a.riskScore)
    .slice(0, 5);

  const filterButtons: { label: string; value: FilterType; count: number }[] = [
    { label: 'All', value: 'all', count: risks.length },
    { label: 'High', value: 'high', count: risks.filter(r => getRiskLevel(r.riskScore) === 'high').length },
    { label: 'Medium', value: 'medium', count: risks.filter(r => getRiskLevel(r.riskScore) === 'medium').length },
    { label: 'Low', value: 'low', count: risks.filter(r => getRiskLevel(r.riskScore) === 'low').length },
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
        <div className="flex flex-wrap gap-2 mt-3">
          {filterButtons.map((btn) => (
            <button
              key={btn.value}
              onClick={() => setFilter(btn.value)}
              className={`px-3 py-1.5 text-xs font-medium rounded-full transition-colors ${
                filter === btn.value
                  ? 'bg-blue-600 text-white dark:bg-blue-500'
                  : 'bg-muted text-muted-foreground hover:bg-muted/80'
              }`}
            >
              {btn.label} ({btn.count})
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
                className="block p-3 rounded-lg bg-muted/50 hover:bg-muted transition-colors group"
              >
                <div className="flex items-start justify-between gap-3">
                  <div className="flex-1 min-w-0">
                    <p className="font-medium text-sm text-foreground truncate group-hover:text-blue-600 dark:group-hover:text-blue-400 transition-colors">
                      {risk.title}
                    </p>
                    <div className="flex items-center gap-2 mt-1">
                      {risk.category && (
                        <span
                          className="text-xs px-2 py-0.5 rounded-full font-medium"
                          style={{
                            backgroundColor: risk.category.color + '15',
                            color: risk.category.color,
                          }}
                        >
                          {risk.category.name}
                        </span>
                      )}
                      <span className="text-xs text-muted-foreground">
                        L:{risk.likelihood} × I:{risk.impact}
                      </span>
                    </div>
                  </div>
                  <Badge 
                    className={`font-semibold text-xs px-2 py-1 border ${getScoreStyles(risk.riskScore)}`}
                  >
                    {risk.riskScore}
                  </Badge>
                </div>
              </Link>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
