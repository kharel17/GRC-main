'use client';

import { mockRisks } from '@/lib/mock-data';
import { RiskScoreExplanation } from '@/features/risk/RiskScoreExplanation';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { ArrowLeft, Edit } from 'lucide-react';
import Link from 'next/link';
import { getStatusColor, getScoreBadgeColor } from '@/features/risk/risk.logic';

export default function RiskDetailPage({ params }: { params: { id: string } }) {
  const risk = mockRisks.find((r) => r.id === params.id);

  if (!risk) {
    return (
      <div className="space-y-4">
        <Link href="/risks" className="inline-flex items-center gap-2 text-blue-600 hover:underline">
          <ArrowLeft className="h-4 w-4" />
          Back to risks
        </Link>
        <p className="text-slate-600">Risk not found</p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <Link href="/risks" className="inline-flex items-center gap-2 text-slate-600 hover:text-slate-900">
          <ArrowLeft className="h-4 w-4" />
          <span className="text-sm">Back to risks</span>
        </Link>
        <Button variant="outline" className="gap-2">
          <Edit className="h-4 w-4" />
          Edit
        </Button>
      </div>

      <Card>
        <CardHeader className="pb-4">
          <div className="space-y-4">
            <div>
              <h1 className="text-2xl font-bold text-slate-900">{risk.title}</h1>
              <p className="text-slate-600 mt-2">{risk.description}</p>
            </div>

            <div className="flex flex-wrap items-center gap-3">
              <Badge className={getScoreBadgeColor(risk.riskScore)}>
                Score: {risk.riskScore}
              </Badge>
              <Badge className={getStatusColor(risk.status)}>
                {risk.status}
              </Badge>
              <span
                className="inline-block px-2 py-1 rounded text-xs font-medium"
                style={{ backgroundColor: risk.category?.color + '20', color: risk.category?.color }}
              >
                {risk.category?.name}
              </span>
            </div>
          </div>
        </CardHeader>

        <CardContent className="space-y-6 border-t border-slate-200 pt-6">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div className="bg-slate-50 p-4 rounded-lg">
              <p className="text-xs text-slate-600 font-medium mb-2">Likelihood</p>
              <p className="text-2xl font-bold text-slate-900">{risk.likelihood}</p>
              <p className="text-xs text-slate-500 mt-1">out of 5</p>
            </div>
            <div className="bg-slate-50 p-4 rounded-lg">
              <p className="text-xs text-slate-600 font-medium mb-2">Impact</p>
              <p className="text-2xl font-bold text-slate-900">{risk.impact}</p>
              <p className="text-xs text-slate-500 mt-1">out of 5</p>
            </div>
            <div className="bg-slate-50 p-4 rounded-lg">
              <p className="text-xs text-slate-600 font-medium mb-2">Owner</p>
              <p className="font-medium text-slate-900">{risk.ownerName}</p>
              <p className="text-xs text-slate-500 mt-1">assigned</p>
            </div>
            <div className="bg-slate-50 p-4 rounded-lg">
              <p className="text-xs text-slate-600 font-medium mb-2">Created</p>
              <p className="font-medium text-slate-900">{new Date(risk.createdAt).toLocaleDateString()}</p>
              <p className="text-xs text-slate-500 mt-1">in register</p>
            </div>
          </div>
        </CardContent>
      </Card>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2">
          <RiskScoreExplanation risk={risk} />
        </div>

        <div className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle className="text-base">Related Controls</CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-sm text-slate-600">
                No controls mapped yet. Create or map controls to mitigate this risk.
              </p>
              <Button variant="outline" className="w-full mt-4">
                Map Control
              </Button>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="text-base">Supporting Evidence</CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-sm text-slate-600">
                No evidence uploaded yet. Upload documents to support this risk assessment.
              </p>
              <Button variant="outline" className="w-full mt-4">
                Upload Evidence
              </Button>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
