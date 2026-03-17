"use client";

import { useApiData } from "@/hooks/use-api-data";
import { fetchComplianceItems } from "@/lib/data-service";
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

export default function GapAnalysisPage() {
  const { data: compliance, loading } = useApiData(fetchComplianceItems);
  const [statusFilter, setStatusFilter] = useState<string>('all');
  const [searchQuery, setSearchQuery] = useState('');

  const stats = useMemo(() => ({
    compliant: compliance?.filter(i => i.status === 'compliant').length || 0,
    inProgress: compliance?.filter(i => i.status === 'in_progress').length || 0,
    nonCompliant: compliance?.filter(i => i.status === 'non_compliant').length || 0,
    notStarted: compliance?.filter(i => i.status === 'not_started').length || 0,
  }), [compliance]);

  const total = (stats.compliant + stats.inProgress + stats.nonCompliant + stats.notStarted) || 1;
  const compliantPercentage = Math.round((stats.compliant / total) * 100);

  const filteredItems = useMemo(() => {
    if (!compliance) return [];
    return compliance.filter(item => {
      const matchesStatus = statusFilter === 'all' || item.status === statusFilter;
      const matchesSearch = item.title?.toLowerCase().includes(searchQuery.toLowerCase()) || 
                           item.requirementId?.toLowerCase().includes(searchQuery.toLowerCase());
      return matchesStatus && matchesSearch;
    });
  }, [compliance, statusFilter, searchQuery]);

  const priorityActions = useMemo(() => {
    if (!compliance) return [];
    return compliance
      .filter(i => i.status === 'non_compliant' || i.status === 'not_started')
      .sort((a, b) => {
        const priorityScore: Record<string, number> = { critical: 4, high: 3, medium: 2, low: 1 };
        return (priorityScore[b.priority || 'low'] || 0) - (priorityScore[a.priority || 'low'] || 0);
      })
      .slice(0, 3);
  }, [compliance]);

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
    { name: 'Non Compliant', value: stats.nonCompliant, color: '#ef4444' },
    { name: 'Not Started', value: stats.notStarted, color: '#94a3b8' },
  ].filter(d => d.value > 0);

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'compliant': return <Badge className="bg-green-100 text-green-700 hover:bg-green-200 border-none">Compliant</Badge>;
      case 'in_progress': return <Badge className="bg-amber-100 text-amber-700 hover:bg-amber-200 border-none">In Progress</Badge>;
      case 'non_compliant': return <Badge className="bg-red-100 text-red-700 hover:bg-red-200 border-none">Gap</Badge>;
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
                toast.success("Compliance recalculated successfully", { id: toastId });
                window.location.reload(); // Refresh to see updated data
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

      {(!compliance || compliance.length === 0) ? (
        <Card className="border-dashed">
          <CardContent className="py-24 text-center">
            <PieChartIcon className="h-12 w-12 text-slate-300 dark:text-slate-600 mx-auto mb-4" />
            <h3 className="text-sm font-medium text-slate-900 dark:text-slate-100 mb-1">No data for Gap Analysis</h3>
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
                    <div key={action.id} className="flex items-center justify-between p-3 bg-white dark:bg-slate-950 rounded-lg border shadow-sm group hover:border-primary transition-colors cursor-pointer">
                      <div className="flex items-center gap-3">
                        <div className="w-6 h-6 rounded-full bg-slate-100 dark:bg-slate-800 flex items-center justify-center text-[10px] font-bold">
                          {idx + 1}
                        </div>
                        <div>
                          <p className="text-sm font-semibold truncate max-w-[300px]">{action.title}</p>
                          <p className="text-[10px] text-muted-foreground">{action.requirementId || 'Unmapped'}</p>
                        </div>
                      </div>
                      <div className="flex items-center gap-2">
                        {getPriorityBadge(action.priority)}
                        <LinkIcon className="h-3.5 w-3.5 text-muted-foreground group-hover:text-primary" />
                      </div>
                    </div>
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
                    <TableRow key={item.id} className="hover:bg-slate-50 dark:hover:bg-slate-900/50 transition-colors">
                      <TableCell className="font-mono text-xs text-primary font-bold">
                        {item.requirementId || item.iso_clause || 'G-001'}
                      </TableCell>
                      <TableCell className="max-w-[300px]">
                        <p className="font-bold text-sm leading-none mb-1">{item.title || 'Untitled Requirement'}</p>
                        <p className="text-xs text-muted-foreground line-clamp-1">{item.description || 'No description provided.'}</p>
                      </TableCell>
                      <TableCell className="text-center">
                        {getPriorityBadge(item.priority)}
                      </TableCell>
                      <TableCell className="text-center">
                        {getStatusBadge(item.status)}
                      </TableCell>
                      <TableCell>
                        <div className="flex items-center gap-2">
                          <div className="w-6 h-6 rounded-full bg-blue-100 dark:bg-blue-900/30 flex items-center justify-center text-[10px] font-bold text-blue-700 dark:text-blue-400">
                            {(item.ownerName || 'U')[0]}
                          </div>
                          <span className="text-xs font-medium">{item.ownerName || 'Unassigned'}</span>
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
