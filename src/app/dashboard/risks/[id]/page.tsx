'use client';

import { fetchRisk, fetchRiskControls } from '@/lib/data-service';
import { useApiData } from '@/hooks';
import { RiskScoreExplanation } from '@/features/risk/RiskScoreExplanation';
import { EditRiskDialog } from '@/features/risk/EditRiskDialog';
import { MapControlDialog } from '@/features/risk/MapControlDialog';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { ArrowLeft, Edit, Loader2, ShieldCheck } from 'lucide-react';
import Link from 'next/link';
import { getStatusColor, getScoreBadgeColor } from '@/features/risk/risk.logic';
import { useCallback, useState, useEffect } from 'react';
import { EvidenceDropzone } from '@/components/evidence/EvidenceDropzone';
import { EvidenceList } from '@/components/evidence/EvidenceList';

export default function RiskDetailPage({ params }: { params: { id: string } }) {
  const fetcher = useCallback(() => fetchRisk(params.id), [params.id]);
  const { data: risk, loading, error, refetch } = useApiData(fetcher, [params.id]);
  const [evidenceRefresh, setEvidenceRefresh] = useState(0);
  const [editOpen, setEditOpen] = useState(false);
  const [mapControlOpen, setMapControlOpen] = useState(false);
  const [mappedControls, setMappedControls] = useState<any[]>([]);

  // Fetch mapped controls
  const loadControls = useCallback(async () => {
    const data = await fetchRiskControls(params.id);
    setMappedControls(data);
  }, [params.id]);

  useEffect(() => {
    loadControls();
  }, [loadControls]);

  if (loading) {
    return (
      <div className="flex items-center justify-center py-24">
        <Loader2 className="h-8 w-8 animate-spin text-blue-600" />
        <span className="ml-3 text-slate-600">Loading risk…</span>
      </div>
    );
  }

  if (error || !risk) {
    return (
      <div className="space-y-4">
        <Link href="/dashboard/risks" className="inline-flex items-center gap-2 text-blue-600 hover:underline">
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
        <Link href="/dashboard/risks" className="inline-flex items-center gap-2 text-slate-600 hover:text-slate-900">
          <ArrowLeft className="h-4 w-4" />
          <span className="text-sm">Back to risks</span>
        </Link>
        <Button variant="outline" className="gap-2" onClick={() => setEditOpen(true)}>
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
              <Badge className={getScoreBadgeColor(risk.riskScore || risk.score)}>
                Score: {risk.riskScore || risk.score}
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
                <p className="font-medium text-slate-900">{new Date(risk.created_at || '').toLocaleDateString()}</p>
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
              {mappedControls.length === 0 ? (
                <p className="text-sm text-slate-600">
                  No controls mapped yet. Create or map controls to mitigate this risk.
                </p>
              ) : (
                <div className="space-y-2 mb-4">
                  {mappedControls.map((mc: any) => (
                    <div
                      key={mc.id}
                      className="flex items-center gap-2 p-2 rounded-lg bg-slate-50 dark:bg-slate-800"
                    >
                      <ShieldCheck className="h-4 w-4 text-blue-500 shrink-0" />
                      <div className="min-w-0 flex-1">
                        <p className="text-sm font-medium text-slate-900 dark:text-slate-100 truncate">
                          {mc.control_title || mc.controlTitle || 'Control'}
                        </p>
                        <p className="text-xs text-slate-500">
                          {mc.control_status || mc.controlStatus || 'Unknown'}
                        </p>
                      </div>
                    </div>
                  ))}
                </div>
              )}
              <Button
                variant="outline"
                className="w-full mt-2"
                onClick={() => setMapControlOpen(true)}
              >
                Map Control
              </Button>
            </CardContent>
          </Card>
        </div>
      </div>

      {/* ── Mitigating Evidence ─────────────────────────── */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Mitigating Evidence</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <EvidenceDropzone
            relatedTo="risk"
            relatedId={params.id}
            onUploadSuccess={() => setEvidenceRefresh((k) => k + 1)}
          />
          <EvidenceList
            relatedTo="risk"
            relatedId={params.id}
            refreshKey={evidenceRefresh}
          />
        </CardContent>
      </Card>

      {/* ── Dialogs ─────────────────────────────────────── */}
      <EditRiskDialog
        open={editOpen}
        onOpenChange={setEditOpen}
        risk={risk}
        onSuccess={() => refetch()}
      />
      <MapControlDialog
        open={mapControlOpen}
        onOpenChange={setMapControlOpen}
        riskId={params.id}
        riskTitle={risk.title}
        existingControlIds={mappedControls.map((mc: any) => mc.control_id || mc.controlId)}
        onSuccess={() => loadControls()}
      />
    </div>
  );
}
