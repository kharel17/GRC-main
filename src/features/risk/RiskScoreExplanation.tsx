'use client';

import { Risk } from '@/types';
import { explainRiskScore } from '@/lib/risk-scoring';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { AlertCircle, Info } from 'lucide-react';

interface RiskScoreExplanationProps {
  risk: Risk;
}

export function RiskScoreExplanation({ risk }: RiskScoreExplanationProps) {
  const explanation = explainRiskScore(risk);

  return (
    <Card>
      <CardHeader className="pb-3">
        <CardTitle className="text-base font-semibold flex items-center gap-2">
          <Info className="h-5 w-5 text-blue-600" />
          Score Breakdown
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="grid grid-cols-3 gap-4">
          <div className="bg-slate-50 p-4 rounded-lg">
            <p className="text-xs text-slate-600 font-medium mb-2">Likelihood</p>
            <p className="text-2xl font-bold text-slate-900 mb-1">{explanation.likelihood.value}</p>
            <p className="text-xs font-medium text-slate-700">{explanation.likelihood.label}</p>
            <p className="text-xs text-slate-500 mt-2">{explanation.likelihood.description}</p>
          </div>

          <div className="bg-slate-50 p-4 rounded-lg flex items-center justify-center">
            <div className="text-center">
              <p className="text-xs text-slate-600 font-medium mb-2">×</p>
              <p className="text-3xl font-bold text-slate-400">=</p>
            </div>
          </div>

          <div className="bg-slate-50 p-4 rounded-lg">
            <p className="text-xs text-slate-600 font-medium mb-2">Impact</p>
            <p className="text-2xl font-bold text-slate-900 mb-1">{explanation.impact.value}</p>
            <p className="text-xs font-medium text-slate-700">{explanation.impact.label}</p>
            <p className="text-xs text-slate-500 mt-2">{explanation.impact.description}</p>
          </div>
        </div>

        <div
          className="p-4 rounded-lg border-2"
          style={{
            borderColor: explanation.score.color,
            backgroundColor: explanation.score.color + '15',
          }}
        >
          <div className="flex items-center justify-between mb-2">
            <p className="text-xs text-slate-600 font-medium">Risk Score</p>
            <span
              className="text-xs font-bold px-2 py-1 rounded"
              style={{
                color: explanation.score.color,
                backgroundColor: explanation.score.color + '30',
              }}
            >
              {explanation.score.severity}
            </span>
          </div>
          <p className="text-3xl font-bold" style={{ color: explanation.score.color }}>
            {explanation.score.value}
          </p>
          <p className="text-sm font-medium mt-3 flex items-start gap-2">
            <AlertCircle className="h-4 w-4 flex-shrink-0 mt-0.5" style={{ color: explanation.score.color }} />
            {explanation.recommendation}
          </p>
        </div>
      </CardContent>
    </Card>
  );
}
