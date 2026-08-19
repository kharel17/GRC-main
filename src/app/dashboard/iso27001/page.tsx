
"use client";

import { useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { 
  FileText, 
  ShieldCheck, 
  Upload, 
  ArrowRight,
  Loader2,
} from "lucide-react";
import Link from "next/link";
import { useAuth, useApiData } from "@/hooks";
import { api } from "@/lib/api-client";
import { fetchOrganization, initializeControlApplicability } from "@/lib/data-service";
import dynamic from "next/dynamic";
import { toast } from "sonner";

const ISOComplianceWidget = dynamic(
  () => import("@/features/iso27001/ISOComplianceWidget").then(mod => mod.ISOComplianceWidget),
  { ssr: false }
);

const ISOControlsStatusWidget = dynamic(
  () => import("@/features/iso27001/ISOControlsStatusWidget").then(mod => mod.ISOControlsStatusWidget),
  { ssr: false }
);

export default function ISODashboardPage() {
  const { user } = useAuth();
  const role = user?.role || 'analyst';
  const [initializing, setInitializing] = useState(false);
  const { data: complianceStats, loading: statsLoading } = useApiData(() =>
    api.get<{ totalControls: number }>('/compliance/stats')
  );
  const canInitialize = role === 'admin' || role === 'manager';
  const shouldShowInitializePrompt = !statsLoading && (complianceStats?.totalControls ?? 0) === 0;

  const handleInitializeIso = async () => {
    setInitializing(true);
    try {
      const org = await fetchOrganization();
      if (!org?.id) {
        throw new Error('Organization not found');
      }
      const result = await initializeControlApplicability(org.id, 'iso27001');
      toast.success(`ISO 27001 controls initialized: ${result.initialized_count}`);
      window.location.reload();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Failed to initialize ISO 27001 controls');
    } finally {
      setInitializing(false);
    }
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-slate-900 mb-1">ISO 27001 Overview</h1>
        <p className="text-sm text-slate-600">
          Monitor your ISO 27001 compliance status and manage controls.
        </p>
      </div>

      {shouldShowInitializePrompt && (
        <Card className="border-dashed">
          <CardContent className="py-8 flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
            <div>
              <p className="font-semibold text-slate-900">ISO 27001 controls not yet initialized for your organization.</p>
              <p className="text-sm text-slate-600 mt-1">Initialize the 93 Annex A controls to start tracking applicability.</p>
            </div>
            {canInitialize && (
              <Button onClick={handleInitializeIso} disabled={initializing} className="gap-2 shrink-0">
                {initializing ? <Loader2 className="h-4 w-4 animate-spin" /> : <ShieldCheck className="h-4 w-4" />}
                Initialize ISO 27001 Controls
              </Button>
            )}
          </CardContent>
        </Card>
      )}

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {/* Compliance Score Widget */}
        <div className="lg:col-span-2">
          <ISOComplianceWidget />
        </div>

        {/* Status Breakdown Widget */}
        <div>
          <ISOControlsStatusWidget />
        </div>
      </div>

      {/* Quick Actions & Navigation */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <Card className="hover:shadow-md transition-shadow cursor-pointer group">
          <Link href="/dashboard/iso27001/controls">
            <CardHeader className="pb-2">
              <CardTitle className="text-lg flex items-center gap-2 group-hover:text-blue-600 transition-colors">
                <ShieldCheck className="h-5 w-5" />
                Manage Controls
              </CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-sm text-slate-600 mb-4">
                View and update status for all 93 Annex A controls.
              </p>
              <div className="flex items-center text-sm font-medium text-blue-600">
                Go to Controls <ArrowRight className="h-4 w-4 ml-1 group-hover:translate-x-1 transition-transform" />
              </div>
            </CardContent>
          </Link>
        </Card>

        <Card className="hover:shadow-md transition-shadow cursor-pointer group">
          <Link href="/dashboard/iso27001/evidence">
            <CardHeader className="pb-2">
              <CardTitle className="text-lg flex items-center gap-2 group-hover:text-blue-600 transition-colors">
                <Upload className="h-5 w-5" />
                Evidence Repository
              </CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-sm text-slate-600 mb-4">
                Upload and manage evidence files linked to controls.
              </p>
              <div className="flex items-center text-sm font-medium text-blue-600">
                Manage Evidence <ArrowRight className="h-4 w-4 ml-1 group-hover:translate-x-1 transition-transform" />
              </div>
            </CardContent>
          </Link>
        </Card>

        <Card className="hover:shadow-md transition-shadow cursor-pointer group">
          <Link href="/dashboard/iso27001/reports">
            <CardHeader className="pb-2">
              <CardTitle className="text-lg flex items-center gap-2 group-hover:text-blue-600 transition-colors">
                <FileText className="h-5 w-5" />
                Compliance Reports
              </CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-sm text-slate-600 mb-4">
                Generate and download compliance status reports.
              </p>
              <div className="flex items-center text-sm font-medium text-blue-600">
                View Reports <ArrowRight className="h-4 w-4 ml-1 group-hover:translate-x-1 transition-transform" />
              </div>
            </CardContent>
          </Link>
        </Card>
      </div>

      {/* Recent Activity / Audit Log Preview could go here */}
    </div>
  );
}
