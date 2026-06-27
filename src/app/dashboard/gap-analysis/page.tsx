"use client";

import { useApiData } from "@/hooks/use-api-data";
import { fetchComplianceItems,fetchGapReport } from "@/lib/data-service";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { toast } from "sonner";
import { PieChart, Pie, Cell, ResponsiveContainer, Legend, Tooltip } from "recharts";
import { 
  PieChart as PieChartIcon, 
  CheckCircle2 as CheckCircleIcon, 
  AlertCircle as AlertIcon, 
  Clock as ClockIcon, 
  Ban as BanIcon,
  Search as SearchIcon,
  ListFilter as FilterIcon,
  ExternalLink as LinkIcon,
  Zap as ZapIcon,
  ShieldAlert as ShieldIcon,
  Loader2,
  Plus
} from "lucide-react";
import { RoleGuard } from "@/components/auth/RoleGuard";
import { Progress } from "@/components/ui/progress";
import { useState, useMemo } from "react";
import { Input } from "@/components/ui/input";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { ComplianceItem } from "@/types";
import Link from "next/link";

export default function GapAnalysisPage() {
  // Bug 7: keep a refetch handle so "Regenerate" doesn't hard-reload the page
  const { data: report, loading, refetch } = useApiData(fetchGapReport);
  const [statusFilter, setStatusFilter] = useState<string>('all');
  const [searchQuery, setSearchQuery] = useState('');

  const stats = useMemo(() => ({
    compliant: report?.implemented || 0,
    inProgress: report?.partially_implemented || 0,
    nonCompliant: report?.summary?.critical || 0, // Maps to critical gaps
    notStarted: report?.missing || 0,
  }), [report]);

  const total = report?.applicable_controls || 1;
  const compliantPercentage = report?.compliance_percentage || 0;

  const filteredItems = useMemo(() => {
    if (!report?.gaps) return [];
    return report.gaps.filter(item => {
      const matchesStatus = statusFilter === 'all' || item.current_status === statusFilter;
      const matchesSearch = item.control_title?.toLowerCase().includes(searchQuery.toLowerCase()) || 
                           item.control_annex?.toLowerCase().includes(searchQuery.toLowerCase());
      return matchesStatus && matchesSearch;
    });
  }, [report, statusFilter, searchQuery]);

  const priorityActions = useMemo(() => {
    if (!report?.gaps) return [];
    return report.gaps
      .filter(i => i.severity === 'critical' || i.severity === 'high')
      .slice(0, 3);
  }, [report]);

  if (loading) {
    return (
      <div className="flex items-center justify-center py-24">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
        <span className="ml-3 text-muted-foreground">Running assessment...</span>
      </div>
    );
  }

  const chartData = [
    { name: 'Compliant', value: stats.compliant, color: '#22c55e' },
    { name: 'In Progress', value: stats.inProgress, color: '#eab308' },
    { name: 'Gap (Critical)', value: stats.nonCompliant, color: '#ef4444' },
    { name: 'Not Started', value: stats.notStarted, color: '#94a3b8' },
  ].filter(d => d.value > 0);

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'implemented': return <Badge className="bg-green-100 text-green-700 hover:bg-green-200 border-none">Compliant</Badge>;
      case 'in_progress': return <Badge className="bg-amber-100 text-amber-700 hover:bg-amber-200 border-none">In Progress</Badge>;
      case 'not_started': return <Badge className="bg-red-100 text-red-700 hover:bg-red-200 border-none">Gap</Badge>;
      default: return <Badge className="bg-slate-100 text-slate-700 hover:bg-slate-200 border-none">Not Started</Badge>;
    }
  };

  const getPriorityBadge = (priority?: string) => {
    switch (priority?.toLowerCase()) {
      case 'critical': return <Badge variant="destructive" className="uppercase font-bold text-[10px]">Critical</Badge>;
      case 'high': return <Badge className="bg-orange-100 text-orange-700 hover:bg-orange-200 uppercase font-bold text-[10px] border-none">High</Badge>;
      case 'medium': return <Badge className="bg-blue-100 text-blue-700 hover:bg-blue-200 uppercase font-bold text-[10px] border-none">Medium</Badge>;
      default: return <Badge variant="outline" className="uppercase font-bold text-[10px]">Low</Badge>;
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Gap Analysis</h1>
          <p className="text-muted-foreground text-sm">Real-time breakdown of control implementation gaps across compliance frameworks.</p>
        </div>
        <RoleGuard allowedRoles={['admin', 'manager']}>
          <Button 
            className="gap-2" 
            onClick={async () => {
              try {
                const toastId = toast.loading("Recalculating compliance...");
                await (await import('@/lib/data-service')).recalculateCompliance();
                // Bug 7: use refetch() instead of page reload
                await refetch();
                toast.success("Compliance recalculated successfully", { id: toastId });
              } catch (err) {
                toast.error("Failed to recalculate compliance");
              }
            }}
          >
            <ZapIcon className="h-4 w-4" />
            Regenerate Report
          </Button>
        </RoleGuard>
      </div>

      {(!report || report.applicable_controls === 0) ? (
        <Card className="border-dashed">
          <CardContent className="py-24 text-center">
            <PieChartIcon className="h-12 w-12 text-slate-300 dark:text-slate-600 mx-auto mb-4" />
            <h3 className="text-sm font-medium text-slate-900 dark:text-slate-100 mb-1">Create controls first to see gap analysis</h3>
            <p className="text-sm text-slate-500 dark:text-slate-400 mb-6">
              Link controls to your risks to see implementation gaps
            </p>
            <Button asChild className="gap-2">
              <a href="/dashboard/risks">
                <Plus className="h-4 w-4" />
                Go to Risks
              </a>
            </Button>
          </CardContent>
        </Card>
      ) : (
        <>
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            <Card className="lg:col-span-1">
              <CardHeader>
                <CardTitle className="text-lg flex items-center gap-2">
                  <PieChartIcon className="h-5 w-5 text-primary" />
                  Compliance Posture
                </CardTitle>
                <CardDescription>Overall item distribution</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="h-[250px] w-full">
                  <ResponsiveContainer width="100%" height="100%">
                    <PieChart>
                      <Pie
                        data={chartData}
                        cx="50%"
                        cy="50%"
                        innerRadius={60}
                        outerRadius={80}
                        paddingAngle={5}
                        dataKey="value"
                      >
                        {chartData.map((entry, index) => (
                          <Cell key={`cell-${index}`} fill={entry.color} />
                        ))}
                      </Pie>
                      <Tooltip />
                      <Legend verticalAlign="bottom" height={36} />
                    </PieChart>
                  </ResponsiveContainer>
                </div>
                <div className="mt-4 space-y-2">
                  <div className="flex justify-between items-center text-sm">
                    <span className="font-medium text-muted-foreground">Overall Compliance</span>
                    <span className="font-bold text-lg">{compliantPercentage}%</span>
                  </div>
                  <Progress value={compliantPercentage} className="h-2 bg-slate-100" />
                </div>
              </CardContent>
            </Card>

            <div className="lg:col-span-2 space-y-6">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <Card className="bg-green-50/30 border-green-100 dark:bg-green-900/10 dark:border-green-900/30">
                  <CardContent className="p-6">
                    <div className="flex items-center gap-2 text-xs font-bold text-green-700 dark:text-green-400 uppercase mb-2">
                      <CheckCircleIcon className="h-4 w-4" />
                      Compliant Items
                    </div>
                    <div className="text-3xl font-bold">{stats.compliant}</div>
                    <p className="text-xs text-slate-500 mt-1">Controls verified as effective</p>
                  </CardContent>
                </Card>
                
                <Card className="bg-amber-50/30 border-amber-100 dark:bg-amber-900/10 dark:border-amber-900/30">
                  <CardContent className="p-6">
                    <div className="flex items-center gap-2 text-xs font-bold text-amber-700 dark:text-amber-400 uppercase mb-2">
                      <ClockIcon className="h-4 w-4" />
                      In Remediation
                    </div>
                    <div className="text-3xl font-bold">{stats.inProgress}</div>
                    <p className="text-xs text-slate-500 mt-1">Controls in progress</p>
                  </CardContent>
                </Card>

                <Card className="bg-red-50/30 border-red-100 dark:bg-red-900/10 dark:border-red-900/30">
                  <CardContent className="p-6">
                    <div className="flex items-center gap-2 text-xs font-bold text-red-700 dark:text-red-400 uppercase mb-2">
                      <BanIcon className="h-4 w-4" />
                      Critical Gaps
                    </div>
                    <div className="text-3xl font-bold text-red-600">{stats.nonCompliant}</div>
                    <p className="text-xs text-slate-500 mt-1">Requires immediate attention</p>
                  </CardContent>
                </Card>

                <Card className="bg-slate-50/30 border-slate-100 dark:bg-slate-900/10 dark:border-slate-900/30">
                  <CardContent className="p-6">
                    <div className="flex items-center gap-2 text-xs font-bold text-slate-700 dark:text-slate-400 uppercase mb-2">
                      <AlertIcon className="h-4 w-4" />
                      Not Addressed
                    </div>
                    <div className="text-3xl font-bold">{stats.notStarted}</div>
                    <p className="text-xs text-slate-500 mt-1">Not yet assessed</p>
                  </CardContent>
                </Card>
              </div>

              {/* Priority Actions */}
              <Card className="border-primary/20 bg-primary/5">
                <CardHeader className="py-4">
                  <CardTitle className="text-sm flex items-center gap-2 uppercase tracking-wider">
                    <ZapIcon className="h-4 w-4 text-primary" />
                    Priority Actions
                  </CardTitle>
                </CardHeader>
                <CardContent className="pb-4 space-y-3">
                  {priorityActions.map((action, idx) => (
                    // Bug 8: wrap each action in a Link to the ISO 27001 control detail page
                    <Link
                      key={action.control_annex}
                      href={`/dashboard/iso27001/${action.control_annex}`}
                      className="block"
                    >
                      <div className="flex items-center justify-between p-3 bg-white dark:bg-slate-950 rounded-lg border shadow-sm group hover:border-primary transition-colors cursor-pointer">
                        <div className="flex items-center gap-3">
                          <div className="w-6 h-6 rounded-full bg-slate-100 dark:bg-slate-800 flex items-center justify-center text-[10px] font-bold">
                            {idx + 1}
                          </div>
                          <div>
                            <p className="text-sm font-semibold truncate max-w-[300px]">{action.control_title}</p>
                            <p className="text-[10px] text-muted-foreground">{action.control_annex || 'Unmapped'}</p>
                          </div>
                        </div>
                        <div className="flex items-center gap-2">
                          {getPriorityBadge(action.severity)}
                          <LinkIcon className="h-3.5 w-3.5 text-muted-foreground group-hover:text-primary" />
                        </div>
                      </div>
                    </Link>
                  ))}
                </CardContent>
              </Card>
            </div>
          </div>

          <Separator className="my-8" />

          {/* Gap Details Table */}
          <div className="space-y-4">
            <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
              <h2 className="text-lg font-bold flex items-center gap-2">
                <ShieldIcon className="h-5 w-5 text-primary" />
                Gap Register Details
              </h2>
              <div className="flex flex-wrap items-center gap-3">
                <div className="relative">
                  <SearchIcon className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                  <Input 
                    placeholder="Filter by title or ID..." 
                    className="pl-9 w-full md:w-64"
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                  />
                </div>
                <Select value={statusFilter} onValueChange={setStatusFilter}>
                  <SelectTrigger className="w-[180px]">
                    <div className="flex items-center gap-2">
                      <FilterIcon className="h-4 w-4" />
                      <SelectValue placeholder="All Statuses" />
                    </div>
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="all">All Items</SelectItem>
                    <SelectItem value="non_compliant">Critical Gaps</SelectItem>
                    <SelectItem value="in_progress">In Remediation</SelectItem>
                    <SelectItem value="compliant">Compliant</SelectItem>
                    <SelectItem value="not_started">Not Addressed</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>

            <div className="rounded-xl border bg-card overflow-hidden shadow-sm">
              <Table>
                <TableHeader>
                  <TableRow className="bg-slate-50/50 dark:bg-slate-900/50">
                    <TableHead className="font-bold">Requirement ID</TableHead>
                    <TableHead className="font-bold">Title & Description</TableHead>
                    <TableHead className="font-bold text-center">Priority</TableHead>
                    <TableHead className="font-bold text-center">Status</TableHead>
                    <TableHead className="font-bold">Assigned Owner</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {filteredItems.map((item) => (
                    <TableRow key={item.control_annex} className="hover:bg-slate-50 dark:hover:bg-slate-900/50 transition-colors">
                      <TableCell className="font-mono text-xs text-primary font-bold">
                        {item.control_annex}
                      </TableCell>
                      <TableCell className="max-w-[300px]">
                        <p className="font-bold text-sm leading-none mb-1">{item.control_title}</p>
                        <p className="text-xs text-muted-foreground line-clamp-1">{item.reason}</p>
                      </TableCell>
                      <TableCell className="text-center">
                        {getPriorityBadge(item.severity)}
                      </TableCell>
                      <TableCell className="text-center">
                        {getStatusBadge(item.current_status)}
                      </TableCell>
                      <TableCell>
                        <div className="flex items-center gap-2 text-xs text-muted-foreground italic">
                           AI Score: {(item.best_evidence_score || 0).toFixed(0)}%
                        </div>
                      </TableCell>
                    </TableRow>
                  ))}
                  {filteredItems.length === 0 && (
                    <TableRow>
                      <TableCell colSpan={5} className="py-8 text-center text-muted-foreground">
                        No gap analysis items found matching your filters.
                      </TableCell>
                    </TableRow>
                  )}
                </TableBody>
              </Table>
            </div>
          </div>
        </>
      )}
    </div>
  );
}
