'use client';

import { useState } from 'react';
import {
  fetchRisks,
  fetchEvidence,
  fetchAuditLogs,
  fetchControlApplicabilityComplianceScore,
} from '@/lib/data-service';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Switch } from '@/components/ui/switch';
import { Label } from '@/components/ui/label';
import {
  Calendar,
  TrendingUp,
  FileText,
  Activity,
} from 'lucide-react';
import { toast } from 'sonner';

interface DigestStats {
  totalRisks: number;
  highRisks: number;
  complianceScore: number;
  totalEvidence: number;
  verifiedEvidence: number;
  recentActivity: number;
}

interface WeeklyDigestToggleProps {
  /** Optional callback when digest is toggled */
  onToggle?: (enabled: boolean) => void;
}

export function WeeklyDigestToggle({ onToggle }: WeeklyDigestToggleProps) {
  const [weeklyDigestEnabled, setWeeklyDigestEnabled] = useState<boolean>(() => {
    if (typeof window !== 'undefined') {
      return localStorage.getItem('weekly_digest') === 'true';
    }
    return false;
  });
  const [digestPreviewOpen, setDigestPreviewOpen] = useState(false);
  const [digestStats, setDigestStats] = useState<DigestStats | null>(null);
  const [loadingDigest, setLoadingDigest] = useState(false);

  const handleWeeklyDigestToggle = async (checked: boolean) => {
    setWeeklyDigestEnabled(checked);
    if (typeof window !== 'undefined') {
      localStorage.setItem('weekly_digest', String(checked));
    }
    onToggle?.(checked);

    if (checked) {
      setLoadingDigest(true);
      try {
        const [risks, evidence, auditLogs, compliance] = await Promise.all([
          fetchRisks(),
          fetchEvidence(),
          fetchAuditLogs(),
          fetchControlApplicabilityComplianceScore(),
        ]);
        const highRisks = risks.filter((r: any) => (r.risk_score || 0) >= 15).length;
        const verified = evidence.filter((e: any) => e.status === 'verified').length;
        const weekAgo = new Date();
        weekAgo.setDate(weekAgo.getDate() - 7);
        const recentActivity = auditLogs.filter((l: any) => {
          const ts = l.timestamp ? new Date(l.timestamp) : null;
          return ts && ts >= weekAgo;
        }).length;
        setDigestStats({
          totalRisks: risks.length,
          highRisks,
          complianceScore: compliance.compliance_percentage,
          totalEvidence: evidence.length,
          verifiedEvidence: verified,
          recentActivity,
        });
        setDigestPreviewOpen(true);
        toast.success('Weekly Digest enabled. Preview your first report below.');
      } catch {
        toast.error('Failed to load digest preview. Digest is still enabled.');
      } finally {
        setLoadingDigest(false);
      }
    } else {
      toast.info('Weekly Digest disabled.');
    }
  };

  return (
    <>
      <div className="flex items-center justify-between">
        <div className="space-y-0.5">
          <Label>Weekly Digest</Label>
          <p className="text-xs text-muted-foreground">Summary of all activities sent weekly</p>
        </div>
        <Switch
          checked={weeklyDigestEnabled}
          onCheckedChange={handleWeeklyDigestToggle}
          disabled={loadingDigest}
        />
      </div>

      {/* Weekly Digest Preview Dialog */}
      <Dialog open={digestPreviewOpen} onOpenChange={setDigestPreviewOpen}>
        <DialogContent className="sm:max-w-[560px]">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <Calendar className="h-5 w-5 text-primary" />
              Weekly Activity Digest
            </DialogTitle>
            <DialogDescription>
              Here's a preview of what your weekly digest email will look like.
            </DialogDescription>
          </DialogHeader>

          {digestStats && (
            <div className="space-y-4 py-2">
              {/* Header banner */}
              <div className="rounded-lg bg-gradient-to-r from-primary/10 to-blue-50 border border-primary/20 p-4">
                <p className="text-xs font-semibold text-primary uppercase tracking-wider">GRC Platform</p>
                <p className="text-base font-bold text-foreground mt-0.5">Weekly Security & Compliance Report</p>
                <p className="text-xs text-muted-foreground mt-1">
                  Week of {new Date(Date.now() - 7 * 24 * 60 * 60 * 1000).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })} – {new Date().toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })}
                </p>
              </div>

              {/* KPI blocks */}
              <div className="grid grid-cols-2 gap-3">
                <div className="rounded-lg border p-3.5 bg-card space-y-1">
                  <div className="flex items-center justify-between">
                    <p className="text-xs text-muted-foreground">Total Risks</p>
                    <TrendingUp className="h-3.5 w-3.5 text-amber-500" />
                  </div>
                  <p className="text-2xl font-bold text-foreground">{digestStats.totalRisks}</p>
                  <p className="text-[11px] text-red-500 font-medium">{digestStats.highRisks} high-severity</p>
                </div>

                <div className="rounded-lg border p-3.5 bg-card space-y-1">
                  <div className="flex items-center justify-between">
                    <p className="text-xs text-muted-foreground">Compliance Score</p>
                    <TrendingUp className="h-3.5 w-3.5 text-emerald-500" />
                  </div>
                  <p className="text-2xl font-bold text-foreground">{digestStats.complianceScore}%</p>
                  <div className="w-full bg-muted rounded-full h-1.5 mt-1">
                    <div
                      className="bg-emerald-500 h-1.5 rounded-full transition-all"
                      style={{ width: `${digestStats.complianceScore}%` }}
                    />
                  </div>
                </div>

                <div className="rounded-lg border p-3.5 bg-card space-y-1">
                  <div className="flex items-center justify-between">
                    <p className="text-xs text-muted-foreground">Evidence</p>
                    <FileText className="h-3.5 w-3.5 text-blue-500" />
                  </div>
                  <p className="text-2xl font-bold text-foreground">{digestStats.totalEvidence}</p>
                  <p className="text-[11px] text-emerald-600 font-medium">{digestStats.verifiedEvidence} verified</p>
                </div>

                <div className="rounded-lg border p-3.5 bg-card space-y-1">
                  <div className="flex items-center justify-between">
                    <p className="text-xs text-muted-foreground">Activity This Week</p>
                    <Activity className="h-3.5 w-3.5 text-purple-500" />
                  </div>
                  <p className="text-2xl font-bold text-foreground">{digestStats.recentActivity}</p>
                  <p className="text-[11px] text-muted-foreground">audit log entries</p>
                </div>
              </div>

              <p className="text-xs text-center text-muted-foreground border-t pt-3">
                📧 This summary will be emailed every Monday at 9:00 AM to your registered email.
              </p>
            </div>
          )}

          <DialogFooter>
            <Button variant="outline" onClick={() => setDigestPreviewOpen(false)}>Close</Button>
            <Button onClick={() => { setDigestPreviewOpen(false); toast.success('Weekly digest scheduled!'); }}>
              <Calendar className="h-4 w-4 mr-1.5" />
              Confirm Schedule
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  );
}
