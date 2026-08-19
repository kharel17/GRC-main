"use client";

import { useState, useEffect } from "react";
import { fetchEvidence } from "@/lib/data-service";
import { useApiData } from "@/hooks";
import { Button } from "@/components/ui/button";
import { Plus, LayoutGrid, List, Loader2, FileText } from "lucide-react";
import { RoleGuard } from "@/components/auth/RoleGuard";
import { EvidenceUploadDialog } from "@/components/evidence/EvidenceUploadDialog";
import { EvidenceList } from "@/components/evidence/EvidenceList";

type ViewMode = 'table' | 'cards';
type VerificationFilter = 'all' | 'verified' | 'pending';

export default function EvidencePage() {
  const { data: evidence, loading, error, refetch } = useApiData(fetchEvidence);
  const [verificationFilter, setVerificationFilter] = useState<VerificationFilter>('all');
  const [viewMode, setViewMode] = useState<ViewMode>('table');
  const [isMobile, setIsMobile] = useState(false);
  const [uploadDialogOpen, setUploadDialogOpen] = useState(false);

  useEffect(() => {
    const checkMobile = () => setIsMobile(window.innerWidth < 768);
    checkMobile();
    window.addEventListener('resize', checkMobile);
    return () => window.removeEventListener('resize', checkMobile);
  }, []);

  const allEvidence = evidence ?? [];

  const filteredEvidence = allEvidence.filter((item) => {
    if (verificationFilter === 'verified') return item.status === 'verified';
    if (verificationFilter === 'pending') return item.status !== 'verified';
    return true;
  });

  const filterButtons: { label: string; value: VerificationFilter; count: number }[] = [
    { label: 'All', value: 'all', count: allEvidence.length },
    { label: 'Verified', value: 'verified', count: allEvidence.filter(e => e.status === 'verified').length },
    { label: 'Pending', value: 'pending', count: allEvidence.filter(e => e.status !== 'verified').length },
  ];

  // Auto-switch to cards on mobile
  const effectiveViewMode = isMobile ? 'cards' : viewMode;

  if (loading) {
    return (
      <div className="flex items-center justify-center py-24">
        <Loader2 className="h-8 w-8 animate-spin text-blue-600" />
        <span className="ml-3 text-slate-600">Loading evidence…</span>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex flex-col items-center justify-center py-24 text-center">
        <FileText className="h-12 w-12 text-red-400 mb-4" />
        <h3 className="text-sm font-medium text-slate-900 mb-1">Failed to load evidence</h3>
        <p className="text-sm text-slate-500">{error.message}</p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 mb-1">Evidence</h1>
          <p className="text-sm text-slate-600">
            Supporting documentation for risks and controls
          </p>
        </div>
        <RoleGuard allowedRoles={['admin', 'manager', 'analyst', 'control_owner', 'risk_owner', 'compliance_officer']}>
          <Button className="gap-2 w-full sm:w-auto" onClick={() => setUploadDialogOpen(true)}>
            <Plus className="h-4 w-4" />
            Upload Evidence
          </Button>
        </RoleGuard>
      </div>

      {/* Filter Bar */}
      <div className="flex flex-col sm:flex-row gap-4 items-start sm:items-center justify-between">
        <div className="flex flex-wrap gap-2">
          {filterButtons.map((btn) => (
            <button
              key={btn.value}
              onClick={() => setVerificationFilter(btn.value)}
              className={`px-3 py-1.5 text-xs font-medium rounded-full transition-colors ${verificationFilter === btn.value
                ? 'bg-blue-600 text-white'
                : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
                }`}
            >
              {btn.label} ({btn.count})
            </button>
          ))}
        </div>

        {/* View Toggle (hidden on mobile) */}
        <div className="hidden md:flex items-center gap-1 bg-slate-100 rounded-lg p-1">
          <Button
            variant={viewMode === 'table' ? 'secondary' : 'ghost'}
            size="sm"
            className="h-8 px-3"
            onClick={() => setViewMode('table')}
          >
            <List className="h-4 w-4" />
          </Button>
          <Button
            variant={viewMode === 'cards' ? 'secondary' : 'ghost'}
            size="sm"
            className="h-8 px-3"
            onClick={() => setViewMode('cards')}
          >
            <LayoutGrid className="h-4 w-4" />
          </Button>
        </div>
      </div>

      {/* Results Count */}
      <div className="text-sm text-slate-500">
        Showing {filteredEvidence.length} of {allEvidence.length} items
      </div>

      {/* Results View */}
      {filteredEvidence.length === 0 ? (
        <div className="bg-card border-2 border-dashed border-slate-200 dark:border-slate-800 rounded-xl py-16 text-center">
          <FileText className="h-12 w-12 text-slate-300 dark:text-slate-600 mx-auto mb-4" />
          <h3 className="text-sm font-medium text-slate-900 dark:text-slate-100 mb-1">No evidence uploaded yet</h3>
          <p className="text-sm text-slate-500 dark:text-slate-400 mb-6">
            Upload documents to prove your controls are working
          </p>
          <RoleGuard allowedRoles={['admin', 'manager', 'analyst']}>
            <Button onClick={() => setUploadDialogOpen(true)} className="gap-2">
              <Plus className="h-4 w-4" />
              Upload Evidence
            </Button>
          </RoleGuard>
        </div>
      ) : (
        <EvidenceList
          items={filteredEvidence}
          viewMode={effectiveViewMode}
          showRelated={true}
          onRefresh={() => refetch()}
        />
      )}

      <EvidenceUploadDialog
        open={uploadDialogOpen}
        onOpenChange={setUploadDialogOpen}
        onSuccess={() => refetch()}
      />
    </div>
  );
}
