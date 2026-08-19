"use client";

import { useEffect, useCallback } from "react";
import { Risk, Control, Ticket } from "@/types";
import { useAuth } from "@/hooks";
import {
  fetchRisks,
  fetchControls,
  fetchComplianceItems,
  fetchTickets,
  fetchOrganization,
  fetchReadinessScore,
  fetchDashboardSummary,
} from "@/lib";
import { useApiData } from "@/hooks";
import { DashboardSummary } from "@/features/dashboard/DashboardSummary";
import { RiskHighlights } from "@/features/dashboard/RiskHighlights";
import { OverdueItems } from "@/features/dashboard/OverdueItems";
import {
  AlertCircle,
  TrendingUp,
  FileText,
  Shield,
  Clock,
  BarChart3,
  Loader2,
  ArrowRight,
  CheckCircle2,
  AlertTriangle,
  RefreshCw,
} from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import Link from "next/link";
import { formatDistanceToNow, parseISO } from "date-fns";

// =============================================================================
// Helpers
// =============================================================================

function getPriorityColor(priority: string) {
  switch (priority) {
    case "critical": return "bg-red-500";
    case "high": return "bg-orange-500";
    case "medium": return "bg-amber-500";
    default: return "bg-green-500";
  }
}

function getStatusBadge(status: string) {
  switch (status) {
    case "open": return "bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300";
    case "in_review":
    case "pending_evidence": return "bg-indigo-100 text-indigo-700 dark:bg-indigo-900/30 dark:text-indigo-300";
    case "escalated":
    case "overdue": return "bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-300";
    case "resolved": return "bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-300";
    default: return "bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-400";
  }
}

function getDueLabel(dueDate?: string): { label: string; urgent: boolean } {
  if (!dueDate) return { label: "No due date", urgent: false };
  try {
    const due = parseISO(dueDate);
    const now = new Date();
    const diffMs = due.getTime() - now.getTime();
    const diffHours = diffMs / (1000 * 60 * 60);
    if (diffMs < 0) return { label: "Overdue", urgent: true };
    if (diffHours < 24) return { label: `Due in ${Math.round(diffHours)}h`, urgent: true };
    return { label: formatDistanceToNow(due, { addSuffix: true }), urgent: diffHours < 72 };
  } catch {
    return { label: "Unknown", urgent: false };
  }
}

// =============================================================================
// Role-Specific Widget Components — All using real data
// =============================================================================

function AdminSystemOverview({
  controls,
  risks,
  readiness,
  dashboardStats,
}: {
  controls: Control[];
  risks: Risk[];
  readiness: any;
  dashboardStats: any;
}) {
  const totalControls = controls.length;
  const openRisks = risks.filter(
    (r) => r.status !== "mitigated" && r.status !== "accepted"
  ).length;
  const compliancePercentage =
    readiness?.compliance_percentage ?? readiness?.weighted_readiness ?? 0;
  const openTickets = dashboardStats?.tickets?.open ?? 0;

  const cards = [
    {
      value: totalControls,
      label: "Active Controls",
      icon: Shield,
      gradient: "from-blue-50 to-blue-100 border-blue-200 dark:from-blue-950/40 dark:to-blue-900/40 dark:border-blue-800",
      iconBg: "bg-blue-600",
      textColor: "text-blue-900 dark:text-blue-100",
      subColor: "text-blue-700 dark:text-blue-300",
      href: "/dashboard/controls",
    },
    {
      value: openRisks,
      label: "Open Risks",
      icon: AlertCircle,
      gradient: "from-amber-50 to-amber-100 border-amber-200 dark:from-amber-950/40 dark:to-amber-900/40 dark:border-amber-800",
      iconBg: "bg-amber-600",
      textColor: "text-amber-900 dark:text-amber-100",
      subColor: "text-amber-700 dark:text-amber-300",
      href: "/dashboard/risks",
    },
    {
      value: `${compliancePercentage}%`,
      label: "Overall Compliance",
      icon: TrendingUp,
      gradient: "from-green-50 to-green-100 border-green-200 dark:from-green-950/40 dark:to-green-900/40 dark:border-green-800",
      iconBg: "bg-green-600",
      textColor: "text-green-900 dark:text-green-100",
      subColor: "text-green-700 dark:text-green-300",
      href: "/dashboard/iso27001",
    },
    {
      value: openTickets,
      label: "Open Tickets",
      icon: BarChart3,
      gradient: "from-purple-50 to-purple-100 border-purple-200 dark:from-purple-950/40 dark:to-purple-900/40 dark:border-purple-800",
      iconBg: "bg-purple-600",
      textColor: "text-purple-900 dark:text-purple-100",
      subColor: "text-purple-700 dark:text-purple-300",
      href: "/dashboard/tickets",
    },
  ];

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
      {cards.map((card) => (
        <Link key={card.label} href={card.href}>
          <Card className={`bg-gradient-to-br ${card.gradient} cursor-pointer hover:shadow-lg transition-all hover:-translate-y-0.5`}>
            <CardContent className="p-4">
              <div className="flex items-center gap-3">
                <div className={`p-2 ${card.iconBg} rounded-lg flex-shrink-0`}>
                  <card.icon className="h-5 w-5 text-white" />
                </div>
                <div>
                  <p className={`text-2xl font-bold ${card.textColor}`}>{card.value}</p>
                  <p className={`text-sm ${card.subColor}`}>{card.label}</p>
                </div>
              </div>
            </CardContent>
          </Card>
        </Link>
      ))}
    </div>
  );
}

// Real ticket-based task widget for Analysts / Control Owners / Risk Owners
function AnalystTaskWidget({ tickets, userId }: { tickets: Ticket[]; userId?: string }) {
  const myTickets = tickets
    .filter((t) => {
      const assignedId = t.assignedToId || (t as any).assigned_to_id;
      const isOpen = !["resolved", "closed", "archived"].includes(t.status);
      return isOpen && (assignedId === userId || !userId);
    })
    .slice(0, 5);

  return (
    <Card className="mb-6">
      <CardHeader className="pb-3 flex flex-row items-center justify-between">
        <CardTitle className="text-lg flex items-center gap-2">
          <FileText className="h-5 w-5 text-green-600" />
          My Open Tickets
        </CardTitle>
        <Link href="/dashboard/tickets">
          <Button variant="ghost" size="sm" className="text-xs text-muted-foreground gap-1 hover:text-primary">
            View all <ArrowRight className="h-3 w-3" />
          </Button>
        </Link>
      </CardHeader>
      <CardContent>
        {myTickets.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-6 text-center">
            <CheckCircle2 className="h-8 w-8 text-green-500 mb-2" />
            <p className="text-sm font-medium text-foreground">All caught up!</p>
            <p className="text-xs text-muted-foreground">No open tickets assigned to you.</p>
          </div>
        ) : (
          <div className="space-y-2">
            {myTickets.map((ticket) => {
              const due = getDueLabel(ticket.dueDate || (ticket as any).due_date);
              return (
                <Link key={ticket.id} href={`/dashboard/tickets/${ticket.id}`}>
                  <div className="flex items-center justify-between p-3 bg-muted/50 rounded-lg hover:bg-muted transition-colors cursor-pointer group">
                    <div className="flex items-center gap-3 flex-1 min-w-0">
                      <div className={`w-2 h-2 rounded-full flex-shrink-0 ${getPriorityColor(ticket.priority)}`} />
                      <div className="flex-1 min-w-0">
                        <p className="text-sm font-medium text-foreground truncate group-hover:text-primary transition-colors">
                          {ticket.title}
                        </p>
                        <span className={`inline-block text-[10px] px-1.5 py-0.5 rounded-full capitalize mt-0.5 ${getStatusBadge(ticket.status)}`}>
                          {ticket.status.replace(/_/g, " ")}
                        </span>
                      </div>
                    </div>
                    <span className={`text-xs flex-shrink-0 ml-2 font-medium ${due.urgent ? "text-red-600 dark:text-red-400" : "text-muted-foreground"}`}>
                      {due.label}
                    </span>
                  </div>
                </Link>
              );
            })}
          </div>
        )}
      </CardContent>
    </Card>
  );
}

// Real report links for Managers / Executives / Compliance Officers
function ManagerReportsWidget({ orgId, readiness }: { orgId?: string; readiness: any }) {
  const compliancePct = readiness?.compliance_percentage ?? readiness?.weighted_readiness ?? 0;
  const criticalGaps = readiness?.critical_gaps ?? 0;
  const highGaps = readiness?.high_gaps ?? 0;

  const reports = [
    {
      title: "Audit Readiness Report",
      description: `${compliancePct}% compliance · ${criticalGaps} critical gaps`,
      href: "/dashboard/audit-preparation",
      status: compliancePct >= 80 ? "Ready" : compliancePct >= 60 ? "In Progress" : "Needs Attention",
      statusColor: compliancePct >= 80
        ? "bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-300"
        : compliancePct >= 60
        ? "bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-300"
        : "bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-300",
    },
    {
      title: "ISO 27001 Compliance Report",
      description: "Statement of Applicability & Gap Analysis",
      href: "/dashboard/iso27001/reports",
      status: "Available",
      statusColor: "bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300",
    },
    {
      title: "Risk Register",
      description: `${highGaps} high-priority gaps requiring attention`,
      href: "/dashboard/risks",
      status: highGaps > 0 ? "Action Required" : "Clean",
      statusColor: highGaps > 0
        ? "bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-300"
        : "bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-300",
    },
  ];

  return (
    <Card className="mb-6">
      <CardHeader className="pb-3 flex flex-row items-center justify-between">
        <CardTitle className="text-lg flex items-center gap-2">
          <BarChart3 className="h-5 w-5 text-purple-600" />
          Reports & Readiness
        </CardTitle>
        <Link href="/dashboard/audit-preparation">
          <Button variant="ghost" size="sm" className="text-xs text-muted-foreground gap-1 hover:text-primary">
            Audit Prep <ArrowRight className="h-3 w-3" />
          </Button>
        </Link>
      </CardHeader>
      <CardContent>
        <div className="space-y-3">
          {reports.map((report) => (
            <Link key={report.title} href={report.href}>
              <div className="flex items-center justify-between p-3 bg-muted/50 rounded-lg hover:bg-muted transition-colors cursor-pointer group">
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium text-foreground group-hover:text-primary transition-colors truncate">
                    {report.title}
                  </p>
                  <p className="text-xs text-muted-foreground mt-0.5">{report.description}</p>
                </div>
                <span className={`text-xs px-2 py-1 rounded-full flex-shrink-0 ml-2 font-medium ${report.statusColor}`}>
                  {report.status}
                </span>
              </div>
            </Link>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}

// Recent Activity Feed from backend dashboard summary
function RecentActivityFeed({ activities }: { activities: any[] }) {
  if (!activities || activities.length === 0) return null;

  const actionIcon = (action: string) => {
    switch (action) {
      case "created": return <span className="text-green-600">+</span>;
      case "updated": return <span className="text-blue-600">~</span>;
      case "deleted": return <span className="text-red-600">-</span>;
      default: return <span className="text-muted-foreground">•</span>;
    }
  };

  return (
    <Card>
      <CardHeader className="pb-3">
        <CardTitle className="text-base flex items-center gap-2">
          <Clock className="h-4 w-4 text-muted-foreground" />
          Recent Activity
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className="space-y-3">
          {activities.map((log) => (
            <div key={log.id} className="flex items-start gap-3">
              <div className="w-5 h-5 rounded-full bg-muted flex items-center justify-center text-xs flex-shrink-0 mt-0.5 font-bold">
                {actionIcon(log.action)}
              </div>
              <div className="flex-1 min-w-0">
                <p className="text-sm text-foreground">
                  <span className="font-medium capitalize">{log.action}</span>{" "}
                  <span className="text-muted-foreground capitalize">{log.entity_type?.replace(/_/g, " ")}</span>
                  {log.entity_name && <span className="font-medium"> · {log.entity_name}</span>}
                </p>
                {log.description && (
                  <p className="text-xs text-muted-foreground truncate">{log.description}</p>
                )}
                {log.timestamp && (
                  <p className="text-[10px] text-muted-foreground/70 mt-0.5">
                    {formatDistanceToNow(parseISO(log.timestamp), { addSuffix: true })}
                  </p>
                )}
              </div>
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}

// =============================================================================
// Role-specific greeting helper
// =============================================================================

const getGreeting = (role: string) => {
  switch (role) {
    case "admin":
      return { title: "System Overview", subtitle: "Complete platform visibility and control" };
    case "analyst":
    case "control_owner":
    case "risk_owner":
      return { title: "Risk & Compliance Dashboard", subtitle: "Track your assigned tasks and assessments" };
    case "compliance_officer":
      return { title: "Compliance Dashboard", subtitle: "Monitor compliance posture and findings" };
    case "department_manager":
    case "executive":
      return { title: "Executive Dashboard", subtitle: "High-level reports and insights" };
    case "auditor":
      return { title: "Audit Dashboard", subtitle: "Review compliance and risk data (read-only)" };
    default:
      return { title: "Dashboard", subtitle: "Risk and compliance overview" };
  }
};

// =============================================================================
// Main Dashboard Page
// =============================================================================

const POLL_INTERVAL_MS = 60_000; // 60 seconds

export default function DashboardPage() {
  const { user } = useAuth();
  const role = user?.role || "analyst";

  // Core data
  const { data: fetchedRisks, loading: risksLoading, refetch: refetchRisks } = useApiData(fetchRisks);
  const risks = fetchedRisks ?? [];

  const { data: fetchedControls, loading: controlsLoading, refetch: refetchControls } = useApiData(fetchControls);
  const controls = fetchedControls ?? [];

  const { data: fetchedCompliance, loading: complianceLoading, refetch: refetchCompliance } = useApiData(fetchComplianceItems);
  const compliance = fetchedCompliance ?? [];

  const { data: fetchedTickets, loading: ticketsLoading, refetch: refetchTickets } = useApiData(fetchTickets);
  const tickets = fetchedTickets ?? [];

  const { data: org, loading: orgLoading } = useApiData(fetchOrganization);
  const orgId = org?.id || "";

  const { data: readiness, loading: readinessLoading, refetch: refetchReadiness } = useApiData(
    () => (orgId ? fetchReadinessScore(orgId) : Promise.resolve(null)),
    [orgId]
  );

  // Aggregated backend dashboard summary (for admin overview stats + recent activity)
  const { data: dashboardStats, loading: statsLoading, refetch: refetchStats } = useApiData(fetchDashboardSummary);

  const loading =
    risksLoading ||
    controlsLoading ||
    complianceLoading ||
    ticketsLoading ||
    orgLoading ||
    (!!orgId && readinessLoading);

  // Auto-refresh every 60 seconds
  const refetchAll = useCallback(() => {
    refetchRisks();
    refetchControls();
    refetchCompliance();
    refetchTickets();
    refetchStats();
    if (orgId) refetchReadiness();
  }, [orgId, refetchRisks, refetchControls, refetchCompliance, refetchTickets, refetchStats, refetchReadiness]);

  useEffect(() => {
    const interval = setInterval(refetchAll, POLL_INTERVAL_MS);
    return () => clearInterval(interval);
  }, [refetchAll]);

  const greeting = getGreeting(role);
  const recentActivity = (dashboardStats as any)?.recent_activity ?? [];

  if (loading) {
    return (
      <div className="space-y-6">
        <div>
          <h1 className="text-2xl font-bold text-foreground mb-1">{greeting.title}</h1>
          <p className="text-sm text-muted-foreground">{greeting.subtitle}</p>
        </div>
        <div className="flex items-center justify-center py-24">
          <Loader2 className="h-8 w-8 animate-spin text-blue-600" />
          <span className="ml-3 text-slate-600">Syncing dashboard...</span>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header + manual refresh */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-foreground mb-1">{greeting.title}</h1>
          <p className="text-sm text-muted-foreground">{greeting.subtitle}</p>
        </div>
        <Button variant="ghost" size="sm" onClick={refetchAll} className="gap-1.5 text-muted-foreground hover:text-foreground">
          <RefreshCw className="h-3.5 w-3.5" />
          Refresh
        </Button>
      </div>

      {/* Admin — full system overview with real stats */}
      {role === "admin" && (
        <AdminSystemOverview
          controls={controls}
          risks={risks}
          readiness={readiness}
          dashboardStats={dashboardStats}
        />
      )}

      {/* Analyst/Owner — real ticket task list */}
      {(role === "analyst" || role === "control_owner" || role === "risk_owner") && (
        <AnalystTaskWidget tickets={tickets} userId={user?.id} />
      )}

      {/* Manager/Executive/Compliance — real readiness-driven reports */}
      {(role === "department_manager" || role === "executive" || role === "compliance_officer") && (
        <ManagerReportsWidget orgId={orgId} readiness={readiness} />
      )}

      {/* Metric summary cards — all roles */}
      <DashboardSummary risks={risks} controls={controls} complianceItems={compliance} />

      {/* Risk highlights + overdue compliance items */}
      {(role === "admin" ||
        role === "analyst" ||
        role === "risk_owner" ||
        role === "control_owner" ||
        role === "compliance_officer") && (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <div className="lg:col-span-2">
            <RiskHighlights risks={risks} />
          </div>
          <div className="space-y-6">
            <OverdueItems complianceItems={compliance} />
            {recentActivity.length > 0 && (
              <RecentActivityFeed activities={recentActivity} />
            )}
          </div>
        </div>
      )}

      {/* Manager/Executive — overdue + quick actions + recent activity */}
      {(role === "department_manager" || role === "executive") && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <OverdueItems complianceItems={compliance} />
          <div className="space-y-4">
            <Card>
              <CardHeader>
                <CardTitle className="text-base">Quick Actions</CardTitle>
              </CardHeader>
              <CardContent className="space-y-2">
                <Link href="/dashboard/audit-preparation">
                  <button className="w-full text-left p-3 rounded-lg bg-muted/50 hover:bg-muted transition-colors text-sm text-foreground flex items-center justify-between group">
                    View Audit Readiness Report
                    <ArrowRight className="h-4 w-4 opacity-0 group-hover:opacity-100 transition-opacity" />
                  </button>
                </Link>
                <Link href="/dashboard/iso27001/reports">
                  <button className="w-full text-left p-3 rounded-lg bg-muted/50 hover:bg-muted transition-colors text-sm text-foreground flex items-center justify-between group">
                    Download Compliance PDF
                    <ArrowRight className="h-4 w-4 opacity-0 group-hover:opacity-100 transition-opacity" />
                  </button>
                </Link>
                <Link href="/dashboard/risks">
                  <button className="w-full text-left p-3 rounded-lg bg-muted/50 hover:bg-muted transition-colors text-sm text-foreground flex items-center justify-between group">
                    Review Risk Register
                    <ArrowRight className="h-4 w-4 opacity-0 group-hover:opacity-100 transition-opacity" />
                  </button>
                </Link>
              </CardContent>
            </Card>
            {recentActivity.length > 0 && <RecentActivityFeed activities={recentActivity} />}
          </div>
        </div>
      )}
    </div>
  );
}
