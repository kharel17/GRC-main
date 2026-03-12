"use client";

import { useApiData } from "@/hooks/use-api-data";
import { fetchComplianceItems, fetchEvidence } from "@/lib/data-service";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { ClipboardCheck, ShieldCheck, FileText, CheckCircle2, Circle, AlertCircle, Loader2 } from "lucide-react";
import { Progress } from "@/components/ui/progress";

export default function AuditPreparationPage() {
  const { data: compliance, loading: compLoading } = useApiData(fetchComplianceItems);
  const { data: evidence, loading: evLoading } = useApiData(fetchEvidence);

  const loading = compLoading || evLoading;

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
  const verifiedEvidenceCount = evidence?.filter(e => e.verified).length || 0;
  const itemsWithEvidence = compliance?.filter(c => c.evidenceCount && c.evidenceCount > 0).length || 0;
  const readiness = totalItems > 0 ? Math.round((itemsWithEvidence / totalItems) * 100) : 0;

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-end">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Audit Preparation</h1>
          <p className="text-muted-foreground text-sm">Inventory of evidence and control status for external audit readiness.</p>
        </div>
        <div className="text-right hidden md:block">
          <p className="text-xs font-bold uppercase text-muted-foreground mb-1">Audit Readiness</p>
          <div className="flex items-center gap-3">
            <span className="text-2xl font-bold text-primary">{readiness}%</span>
            <Progress value={readiness} className="w-40 h-2" />
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
                <TableHead className="w-[100px]">ID</TableHead>
                <TableHead>Requirement</TableHead>
                <TableHead>Status</TableHead>
                <TableHead>Evidence</TableHead>
                <TableHead className="text-right">Readiness</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {compliance?.map((item) => (
                <TableRow key={item.id}>
                  <TableCell className="font-mono text-xs">{item.requirementId}</TableCell>
                  <TableCell>
                    <div className="font-medium text-sm">{item.title}</div>
                    <p className="text-[10px] text-muted-foreground line-clamp-1">{item.description}</p>
                  </TableCell>
                  <TableCell>
                    <Badge variant={item.status === 'compliant' ? 'outline' : 'secondary'} className="text-[10px]">
                      {item.status.replace('_', ' ')}
                    </Badge>
                  </TableCell>
                  <TableCell>
                    <div className="flex items-center gap-1.5">
                      <FileText className="h-3.5 w-3.5 text-muted-foreground" />
                      <span className="text-xs">{item.evidenceCount || 0} items</span>
                    </div>
                  </TableCell>
                  <TableCell className="text-right">
                    {(item.evidenceCount || 0) > 0 ? (
                      <div className="flex items-center justify-end gap-1.5 text-green-600 font-bold text-xs">
                        <CheckCircle2 className="h-3.5 w-3.5" />
                        Ready
                      </div>
                    ) : (
                      <div className="flex items-center justify-end gap-1.5 text-slate-400 text-xs">
                        <Circle className="h-3.5 w-3.5" />
                        Missing
                      </div>
                    )}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </CardContent>
      </Card>
    </div>
  );
}
