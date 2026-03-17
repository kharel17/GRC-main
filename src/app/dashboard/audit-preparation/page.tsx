"use client";

import { useState } from "react";
import { useApiData } from "@/hooks/use-api-data";
import { fetchComplianceItems, fetchEvidence, fetchOrganization, exportAuditReport, exportSoAReport, exportRiskRegister } from "@/lib/data-service";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { ClipboardCheck, ShieldCheck, FileText, CheckCircle2, Circle, AlertCircle, Loader2, Download, FileJson, FileBarChart, Plus } from "lucide-react";
import { Progress } from "@/components/ui/progress";
import { Button } from "@/components/ui/button";
import { toast } from "sonner";
import Link from "next/link";
import { RoleGuard } from "@/components/auth/RoleGuard";

export default function AuditPreparationPage() {
  const { data: compliance, loading: compLoading } = useApiData(fetchComplianceItems);
  const { data: evidence, loading: evLoading } = useApiData(fetchEvidence);
  const { data: org, loading: orgLoading } = useApiData(fetchOrganization);
  
  const [downloading, setDownloading] = useState<string | null>(null);

  const loading = compLoading || evLoading || orgLoading;

  const handleDownload = async (type: 'audit' | 'soa' | 'risks') => {
    if (!org?.id) return;
    setDownloading(type);
    try {
      let blob: Blob;
      let filename: string;
      
      const dateStr = new Date().toISOString().split('T')[0];
      const orgStr = org.name.replace(/\s+/g, '_');

      if (type === 'soa') {
        blob = await exportSoAReport(org.id, 'pdf');
        filename = `ISO27001_SoA_${orgStr}_${dateStr}.pdf`;
      } else if (type === 'risks') {
        blob = await exportRiskRegister(org.id, 'pdf');
        filename = `Risk_Register_${orgStr}_${dateStr}.pdf`;
      } else {
        blob = await exportAuditReport(org.id, 'pdf');
        filename = `Audit_Report_${orgStr}_${dateStr}.pdf`;
      }

      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = filename;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      toast.success(`${type.toUpperCase()} report downloaded successfully`);
    } catch (error) {
      toast.error(`Failed to download ${type} report`);
    } finally {
      setDownloading(null);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center py-24">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
        <span className="ml-3 text-muted-foreground">Preparing audit workspace...</span>
      </div>
    );
  }

  // Calculate readiness
  const totalItems = compliance?.length || 0;
  const verifiedEvidenceCount = evidence?.filter((e: any) => e.verified).length || 0;
  const itemsWithEvidence = compliance?.filter((c: any) => c.evidenceCount && c.evidenceCount > 0).length || 0;
  const readiness = totalItems > 0 ? Math.round((itemsWithEvidence / totalItems) * 100) : 0;

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-end">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Audit Preparation</h1>
          <p className="text-muted-foreground text-sm">Inventory of evidence and control status for external audit readiness.</p>
        </div>
        <div className="flex flex-col items-end gap-3">
          <RoleGuard allowedRoles={['admin', 'manager']}>
            <div className="flex gap-2">
              <Button 
                  onClick={() => handleDownload('soa')} 
                  variant="outline"
                  disabled={!!downloading || !org}
                  className="gap-2"
                >
                  {downloading === 'soa' ? <Loader2 className="h-4 w-4 animate-spin" /> : <FileJson className="h-4 w-4" />}
                  Download SoA
                </Button>
                <Button 
                  onClick={() => handleDownload('risks')} 
                  variant="outline"
                  disabled={!!downloading || !org}
                  className="gap-2"
                >
                  {downloading === 'risks' ? <Loader2 className="h-4 w-4 animate-spin" /> : <FileBarChart className="h-4 w-4" />}
                  Risk Register
                </Button>
              <Button 
                onClick={() => handleDownload('audit')} 
                disabled={!!downloading || !org}
                className="gap-2"
              >
                {downloading === 'audit' ? <Loader2 className="h-4 w-4 animate-spin" /> : <Download className="h-4 w-4" />}
                Full Readiness Report
              </Button>
            </div>
          </RoleGuard>
          <div className="text-right hidden md:block">
            <p className="text-xs font-bold uppercase text-muted-foreground mb-1">Audit Readiness</p>
            <div className="flex items-center gap-3">
              <span className="text-2xl font-bold text-primary">{readiness}%</span>
              <Progress value={readiness} className="w-40 h-2" />
            </div>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <Card className="bg-gradient-to-br from-primary/5 to-primary/10 border-primary/20">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-bold uppercase text-muted-foreground">Framework Coverage</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">ISO 27001:2022</div>
            <p className="text-xs text-muted-foreground mt-1">Phase: Pre-Audit Self-Assessment</p>
          </CardContent>
        </Card>
        
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-bold uppercase text-muted-foreground">Verified Evidence</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{verifiedEvidenceCount} Files</div>
            <p className="text-xs text-muted-foreground mt-1">Ready for auditor inspection</p>
          </CardContent>
        </Card>
 
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-bold uppercase text-muted-foreground">Missing Evidence</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-amber-600">{totalItems - itemsWithEvidence} Controls</div>
            <p className="text-xs text-muted-foreground mt-1">Require documentation uploads</p>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="text-lg flex items-center gap-2">
            <ShieldCheck className="h-5 w-5 text-green-600" />
            Requirement Readiness Tracker
          </CardTitle>
          <CardDescription>Track every requirement and its supporting evidence verified status.</CardDescription>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead className="w-[120px] font-bold">Clause ID</TableHead>
                <TableHead className="font-bold">Control Description</TableHead>
                <TableHead className="font-bold">Status</TableHead>
                <TableHead className="font-bold">Evidence</TableHead>
                <TableHead className="text-right font-bold">Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {(!compliance || compliance.length === 0) ? (
                <TableRow>
                  <TableCell colSpan={5} className="text-center py-20">
                    <ClipboardCheck className="h-12 w-12 text-slate-300 dark:text-slate-600 mx-auto mb-4" />
                    <h3 className="text-sm font-medium text-slate-900 dark:text-slate-100 mb-1">Audit workspace not ready</h3>
                    <p className="text-sm text-slate-500 dark:text-slate-400 mb-6">
                      Upload evidence to your controls to prepare for audit
                    </p>
                    <RoleGuard allowedRoles={['admin', 'manager', 'analyst']}>
                      <Button asChild className="gap-2">
                        <a href="/dashboard/evidence">
                          <Plus className="h-4 w-4" />
                          Go to Evidence
                        </a>
                      </Button>
                    </RoleGuard>
                  </TableCell>
                </TableRow>
              ) : (
                compliance?.map((item: any) => (
                  <TableRow key={item.id} className="hover:bg-slate-50 dark:hover:bg-slate-900/50 transition-colors">
                    <TableCell className="font-mono text-xs font-bold text-primary">
                      {item.iso_clause || item.requirementId || 'A.0.0'}
                    </TableCell>
                    <TableCell className="max-w-[400px]">
                      <div className="font-bold text-sm text-slate-900 dark:text-slate-100">{item.title}</div>
                      <p className="text-[10px] text-muted-foreground line-clamp-1 mt-0.5">{item.description}</p>
                    </TableCell>
                    <TableCell>
                      <Badge 
                        variant={item.status === 'compliant' ? 'secondary' : 'outline'} 
                        className={item.status === 'compliant' ? "bg-emerald-50 text-emerald-700 dark:bg-emerald-950/30 dark:text-emerald-400 border-none uppercase text-[9px]" : "uppercase text-[9px]"}
                      >
                        {item.status.replace('_', ' ')}
                      </Badge>
                    </TableCell>
                    <TableCell>
                      <div className="flex items-center gap-2">
                        <div className="flex -space-x-1.5">
                          {[...Array(Math.min(item.evidenceCount || 0, 3))].map((_, i) => (
                            <div key={i} className="w-5 h-5 rounded-full border-2 border-white dark:border-slate-950 bg-slate-100 dark:bg-slate-800 flex items-center justify-center">
                              <FileText className="h-2.5 w-2.5 text-blue-500" />
                            </div>
                          ))}
                        </div>
                        <span className="text-[10px] font-bold text-slate-500">
                          {item.evidenceCount || 0} items
                        </span>
                      </div>
                    </TableCell>
                    <TableCell className="text-right">
                      <div className="flex items-center justify-end gap-2">
                        {(item.evidenceCount || 0) > 0 ? (
                          <Badge className="bg-emerald-100 text-emerald-700 hover:bg-emerald-100 border-none gap-1 py-1">
                            <CheckCircle2 className="h-3 w-3" />
                            Ready
                          </Badge>
                        ) : (
                          <RoleGuard allowedRoles={['admin', 'manager', 'analyst']}>
                            <Button asChild size="sm" variant="ghost" className="h-8 text-[10px] font-bold uppercase tracking-tight gap-1.5 text-primary hover:bg-primary/5">
                              <Link href={`/dashboard/evidence?controlId=${item.id}`}>
                                <Plus className="h-3 w-3" />
                                Add Evidence
                              </Link>
                            </Button>
                          </RoleGuard>
                        )}
                      </div>
                    </TableCell>
                  </TableRow>
                ))
              )}
            </TableBody>
          </Table>
        </CardContent>
      </Card>
    </div>
  );
}
