"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  FileText,
  Download,
  RefreshCw,
  BarChart3,
  Shield,
  AlertTriangle,
  CheckCircle2,
  Clock,
  TrendingUp,
  FileCheck,
} from "lucide-react";
import { RoleGuard } from "@/components/auth/RoleGuard";

const reportTypes = [
  {
    id: "risk-summary",
    title: "Risk Summary Report",
    description: "Overview of all identified risks with scores and status distribution",
    icon: AlertTriangle,
    color: "text-red-600 bg-red-100",
    lastGenerated: "2024-01-20",
    format: "PDF",
  },
  {
    id: "compliance-status",
    title: "Compliance Status Report",
    description: "Current compliance standing across all frameworks",
    icon: CheckCircle2,
    color: "text-green-600 bg-green-100",
    lastGenerated: "2024-01-19",
    format: "PDF",
  },
  {
    id: "control-effectiveness",
    title: "Control Effectiveness",
    description: "Analysis of control implementation and effectiveness",
    icon: Shield,
    color: "text-blue-600 bg-blue-100",
    lastGenerated: "2024-01-18",
    format: "XLSX",
  },
  {
    id: "audit-trail",
    title: "Audit Trail Export",
    description: "Complete audit log for a specified time period",
    icon: Clock,
    color: "text-purple-600 bg-purple-100",
    lastGenerated: "2024-01-17",
    format: "CSV",
  },
  {
    id: "evidence-inventory",
    title: "Evidence Inventory",
    description: "List of all uploaded evidence with verification status",
    icon: FileCheck,
    color: "text-amber-600 bg-amber-100",
    lastGenerated: "2024-01-15",
    format: "XLSX",
  },
  {
    id: "trend-analysis",
    title: "Risk Trend Analysis",
    description: "Historical trends and projections for risk metrics",
    icon: TrendingUp,
    color: "text-indigo-600 bg-indigo-100",
    lastGenerated: "2024-01-10",
    format: "PDF",
  },
];

export default function ReportsPage() {
  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 mb-1">Reports</h1>
          <p className="text-sm text-slate-600">
            Generate and download compliance reports
          </p>
        </div>
        <RoleGuard allowedRoles={['admin']}>
          <Button className="gap-2 w-full sm:w-auto">
            <BarChart3 className="h-4 w-4" />
            Custom Report
          </Button>
        </RoleGuard>
      </div>

      {/* Report Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {reportTypes.map((report) => {
          const Icon = report.icon;
          return (
            <Card
              key={report.id}
              className="hover:shadow-md transition-shadow group"
            >
              <CardHeader className="pb-3">
                <div className="flex items-start gap-3">
                  <div className={`p-2 rounded-lg ${report.color}`}>
                    <Icon className="h-5 w-5" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <CardTitle className="text-sm font-medium line-clamp-1">
                      {report.title}
                    </CardTitle>
                    <Badge variant="outline" className="text-xs mt-1">
                      {report.format}
                    </Badge>
                  </div>
                </div>
              </CardHeader>
              <CardContent className="space-y-4">
                <p className="text-xs text-slate-600 line-clamp-2">
                  {report.description}
                </p>
                
                <div className="text-xs text-slate-500">
                  Last generated: {new Date(report.lastGenerated).toLocaleDateString()}
                </div>

                <div className="flex gap-2 pt-2 border-t">
                  <Button variant="outline" size="sm" className="flex-1 gap-1 text-xs">
                    <Download className="h-3 w-3" />
                    Download
                  </Button>
                  <Button size="sm" className="flex-1 gap-1 text-xs">
                    <RefreshCw className="h-3 w-3" />
                    Generate
                  </Button>
                </div>
              </CardContent>
            </Card>
          );
        })}
      </div>

      {/* Quick Stats */}
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-base font-semibold flex items-center gap-2">
            <FileText className="h-5 w-5 text-slate-600" />
            Report Generation Statistics
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div className="text-center p-4 bg-slate-50 rounded-lg">
              <p className="text-2xl font-bold text-slate-900">47</p>
              <p className="text-xs text-slate-500">Reports This Month</p>
            </div>
            <div className="text-center p-4 bg-slate-50 rounded-lg">
              <p className="text-2xl font-bold text-slate-900">12</p>
              <p className="text-xs text-slate-500">Scheduled Reports</p>
            </div>
            <div className="text-center p-4 bg-slate-50 rounded-lg">
              <p className="text-2xl font-bold text-slate-900">234</p>
              <p className="text-xs text-slate-500">Total Downloads</p>
            </div>
            <div className="text-center p-4 bg-slate-50 rounded-lg">
              <p className="text-2xl font-bold text-slate-900">6</p>
              <p className="text-xs text-slate-500">Custom Templates</p>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
