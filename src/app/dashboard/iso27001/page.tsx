
"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { 
  FileText, 
  ShieldCheck, 
  Upload, 
  Download, 
  ArrowRight 
} from "lucide-react";
import Link from "next/link";
import { useAuth } from "@/hooks/useAuth";
import dynamic from "next/dynamic";

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
  const role = user?.role || 'manager';

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-slate-900 mb-1">ISO 27001 Overview</h1>
        <p className="text-sm text-slate-600">
          Monitor your ISO 27001 compliance status and manage controls.
        </p>
      </div>

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
