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
  Loader2,
} from "lucide-react";
import { RoleGuard } from "@/components/auth/RoleGuard";
import { api } from "@/lib/api-client";
import { useState } from "react";
import { toast } from "sonner";
import { supabase } from "@/lib/supabase";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Checkbox } from "@/components/ui/checkbox";
import { Label } from "@/components/ui/label";
import { Input } from "@/components/ui/input";

const reportTypes = [
  {
    id: "risk-summary",
    title: "Risk Summary Report",
    description: "Overview of all identified risks with scores and status distribution",
    icon: AlertTriangle,
    color: "text-red-600 bg-red-100",
    format: "PDF",
    active: true,
  },
  {
    id: "compliance-status",
    title: "Compliance Status Report",
    description: "Current compliance standing across all frameworks",
    icon: CheckCircle2,
    color: "text-green-600 bg-green-100",
    format: "PDF",
    active: true,
  },
  {
    id: "control-effectiveness",
    title: "Control Effectiveness",
    description: "Analysis of control implementation and effectiveness across ISO 27001 controls",
    icon: Shield,
    color: "text-blue-600 bg-blue-100",
    format: "PDF",
    active: true,
  },
  {
    id: "audit-trail",
    title: "Audit Trail Export",
    description: "Complete audit log of all user actions and system events (last 500 entries)",
    icon: Clock,
    color: "text-purple-600 bg-purple-100",
    format: "PDF",
    active: true,
  },
  {
    id: "evidence-inventory",
    title: "Evidence Inventory",
    description: "List of all uploaded evidence with verification status and AI categorization",
    icon: FileCheck,
    color: "text-amber-600 bg-amber-100",
    format: "PDF",
    active: true,
  },
  {
    id: "trend-analysis",
    title: "Risk Trend Analysis",
    description: "Historical trends, score distributions and category breakdown for risk metrics",
    icon: TrendingUp,
    color: "text-indigo-600 bg-indigo-100",
    format: "PDF",
    active: true,
  },
];

export default function ReportsPage() {
  const [downloading, setDownloading] = useState<string | null>(null);
  const [customDialogOpen, setCustomDialogOpen] = useState(false);
  const [generatingCustom, setGeneratingCustom] = useState(false);
  const [downloadCount, setDownloadCount] = useState(0);
  const [lastGenerated, setLastGenerated] = useState<string | null>(null);

  const activeReports = reportTypes.filter((r) => r.active).length;

  const [customConfig, setCustomConfig] = useState({
    title: "Combined Q1 GRC Report",
    date_range: "last_30_days",
    framework: "iso27001",
    include_risks: true,
    include_controls: true,
    include_compliance: true,
    include_tickets: false,
    include_audit_logs: false,
  });

  const handleDownload = async (reportId: string, _format: string, openInTab = false) => {
    try {
      setDownloading(reportId);

      const { data: { session } } = await supabase.auth.getSession();
      const token = session?.access_token;

      if (!token) {
        toast.error("Authentication session expired. Please log in again.");
        return;
      }

      const response = await fetch(`${api.baseUrl}/reports/${reportId}/export`, {
        method: "GET",
        headers: {
          "Authorization": `Bearer ${token}`
        }
      });

      if (!response.ok) {
        if (response.status === 401) throw new Error("Unauthorized");
        const errText = await response.text().catch(() => '');
        throw new Error(errText || "Failed to generate report");
      }

      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);

      if (openInTab) {
        // Open in new tab for preview
        window.open(url, '_blank');
      } else {
        // Trigger file download
        const a = document.createElement('a');
        a.href = url;
        a.download = `${reportId}-${new Date().toISOString().split('T')[0]}.pdf`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
      }

      window.URL.revokeObjectURL(url);
      setDownloadCount((prev) => prev + 1);
      setLastGenerated(new Date().toLocaleTimeString());
      toast.success(`${openInTab ? 'Report opened in new tab' : 'Report downloaded'} successfully`);
    } catch (error: any) {
      console.error(error);
      toast.error(error.message === "Unauthorized" ? "Session expired" : `Error: ${error.message}`);
    } finally {
      setDownloading(null);
    }
  };

  const handleCustomReport = async () => {
    try {
      setGeneratingCustom(true);

      const { data: { session } } = await supabase.auth.getSession();
      const token = session?.access_token;

      if (!token) {
        toast.error("Not authenticated");
        return;
      }

      const response = await fetch(`${api.baseUrl}/reports/custom/export`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "Authorization": `Bearer ${token}`
        },
        body: JSON.stringify(customConfig)
      });

      if (!response.ok) throw new Error("Failed to generate custom report");

      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `custom-report-${new Date().toISOString().split('T')[0]}.html`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);

      setCustomDialogOpen(false);
      toast.success("Custom report generated");
    } catch (error) {
      console.error(error);
      toast.error("Error generating custom report");
    } finally {
      setGeneratingCustom(false);
    }
  };

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
          <Button 
            className="gap-2 w-full sm:w-auto"
            onClick={() => setCustomDialogOpen(true)}
          >
            <BarChart3 className="h-4 w-4" />
            Custom Report Builder
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
              className={`hover:shadow-md transition-shadow group ${!report.active ? 'opacity-70' : ''}`}
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
                    <Badge variant={report.active ? "secondary" : "outline"} className="text-[10px] mt-1 uppercase">
                      {report.active ? report.format : "Coming Soon"}
                    </Badge>
                  </div>
                </div>
              </CardHeader>
              <CardContent className="space-y-4">
                <p className="text-xs text-slate-600 line-clamp-2">
                  {report.description}
                </p>

                <div className="flex gap-2 pt-2 border-t">
                  <Button
                    variant="outline"
                    size="sm"
                    className="flex-1 gap-1 text-xs"
                    onClick={() => handleDownload(report.id, report.format, false)}
                    disabled={downloading === report.id || !report.active}
                  >
                    {downloading === report.id ? (
                      <RefreshCw className="h-3 w-3 animate-spin" />
                    ) : (
                      <Download className="h-3 w-3" />
                    )}
                    Download
                  </Button>
                  <Button 
                    size="sm" 
                    className="flex-1 gap-1 text-xs" 
                    disabled={!report.active || downloading === report.id}
                    onClick={() => handleDownload(report.id, report.format, true)}
                  >
                    {downloading === report.id ? (
                      <RefreshCw className="h-3 w-3 animate-spin" />
                    ) : (
                      <RefreshCw className="h-3 w-3" />
                    )}
                    Preview
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
            Platform Reporting Overview
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div className="text-center p-4 bg-slate-50 rounded-lg">
              <p className="text-2xl font-bold text-slate-900">{activeReports}</p>
              <p className="text-xs text-slate-500">Available Reports</p>
            </div>
            <div className="text-center p-4 bg-slate-50 rounded-lg">
              <p className="text-2xl font-bold text-slate-900">{downloadCount}</p>
              <p className="text-xs text-slate-500">Generated This Session</p>
            </div>
            <div className="text-center p-4 bg-slate-50 rounded-lg">
              <p className="text-2xl font-bold text-slate-900">PDF</p>
              <p className="text-xs text-slate-500">Export Format</p>
            </div>
            <div className="text-center p-4 bg-slate-50 rounded-lg">
              <p className="text-2xl font-bold text-slate-900 text-sm truncate">
                {lastGenerated ?? '—'}
              </p>
              <p className="text-xs text-slate-500">Last Generated At</p>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Custom Report Dialog */}
      <Dialog open={customDialogOpen} onOpenChange={setCustomDialogOpen}>
        <DialogContent className="sm:max-w-[500px]">
          <DialogHeader>
            <DialogTitle>Custom Report Builder</DialogTitle>
            <DialogDescription>
              Configure a comprehensive report across multiple GRC modules.
            </DialogDescription>
          </DialogHeader>

          <div className="grid gap-4 py-4">
            <div className="grid gap-2">
              <Label htmlFor="title">Report Title</Label>
              <Input 
                id="title" 
                value={customConfig.title}
                onChange={(e) => setCustomConfig({...customConfig, title: e.target.value})}
              />
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div className="grid gap-2">
                <Label>Date Range</Label>
                <Select 
                  value={customConfig.date_range}
                  onValueChange={(val) => setCustomConfig({...customConfig, date_range: val})}
                >
                  <SelectTrigger>
                    <SelectValue placeholder="Select range" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="last_7_days">Last 7 Days</SelectItem>
                    <SelectItem value="last_30_days">Last 30 Days</SelectItem>
                    <SelectItem value="last_quarter">Last Quarter</SelectItem>
                    <SelectItem value="all_time">All Time</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div className="grid gap-2">
                <Label>Framework</Label>
                <Select 
                  value={customConfig.framework}
                  onValueChange={(val) => setCustomConfig({...customConfig, framework: val})}
                >
                  <SelectTrigger>
                    <SelectValue placeholder="Select range" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="iso27001">ISO 27001</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>

            <div className="space-y-3 pt-2">
              <Label className="text-sm font-semibold text-slate-500">INCLUDED SECTIONS</Label>
              <div className="grid grid-cols-2 gap-4">
                <div className="flex items-center space-x-2">
                  <Checkbox 
                    id="include_risks" 
                    checked={customConfig.include_risks}
                    onCheckedChange={(val) => setCustomConfig({...customConfig, include_risks: !!val})}
                  />
                  <Label htmlFor="include_risks" className="text-xs cursor-pointer">Risk Summary</Label>
                </div>
                <div className="flex items-center space-x-2">
                  <Checkbox 
                    id="include_controls" 
                    checked={customConfig.include_controls}
                    onCheckedChange={(val) => setCustomConfig({...customConfig, include_controls: !!val})}
                  />
                  <Label htmlFor="include_controls" className="text-xs cursor-pointer">Control Status</Label>
                </div>
                <div className="flex items-center space-x-2">
                  <Checkbox 
                    id="include_compliance" 
                    checked={customConfig.include_compliance}
                    onCheckedChange={(val) => setCustomConfig({...customConfig, include_compliance: !!val})}
                  />
                  <Label htmlFor="include_compliance" className="text-xs cursor-pointer">Compliance Health</Label>
                </div>
                <div className="flex items-center space-x-2">
                  <Checkbox 
                    id="include_tickets" 
                    checked={customConfig.include_tickets}
                    onCheckedChange={(val) => setCustomConfig({...customConfig, include_tickets: !!val})}
                  />
                  <Label htmlFor="include_tickets" className="text-xs cursor-pointer">Ticket Summary</Label>
                </div>
                <div className="flex items-center space-x-2">
                  <Checkbox 
                    id="include_audit_logs" 
                    checked={customConfig.include_audit_logs}
                    onCheckedChange={(val) => setCustomConfig({...customConfig, include_audit_logs: !!val})}
                  />
                  <Label htmlFor="include_audit_logs" className="text-xs cursor-pointer">Audit Trail</Label>
                </div>
              </div>
            </div>
          </div>

          <DialogFooter>
            <Button variant="outline" onClick={() => setCustomDialogOpen(false)}>Cancel</Button>
            <Button 
              onClick={handleCustomReport}
              disabled={generatingCustom}
            >
              {generatingCustom ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Generating...
                </>
              ) : (
                "Build Report"
              )}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
