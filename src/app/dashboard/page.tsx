"use client";

import { useAuth } from "@/hooks/useAuth";
import { mockRisks, mockControls, mockComplianceItems } from "@/lib/mock-data";
import { DashboardSummary } from "@/features/dashboard/DashboardSummary";
import { RiskHighlights } from "@/features/dashboard/RiskHighlights";
import { OverdueItems } from "@/features/dashboard/OverdueItems";
import { AlertCircle, TrendingUp, FileText, Shield, Clock, BarChart3 } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

// =============================================================================
// Role-Specific Widget Components
// =============================================================================

function AdminSystemOverview() {
  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
      <Card className="bg-gradient-to-br from-blue-50 to-blue-100 border-blue-200 dark:from-blue-950/40 dark:to-blue-900/40 dark:border-blue-800">
        <CardContent className="p-4">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-blue-600 rounded-lg">
              <Shield className="h-5 w-5 text-white" />
            </div>
            <div>
              <p className="text-2xl font-bold text-blue-900 dark:text-blue-100">{mockControls.length}</p>
              <p className="text-sm text-blue-700 dark:text-blue-300">Active Controls</p>
            </div>
          </div>
        </CardContent>
      </Card>
      <Card className="bg-gradient-to-br from-amber-50 to-amber-100 border-amber-200 dark:from-amber-950/40 dark:to-amber-900/40 dark:border-amber-800">
        <CardContent className="p-4">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-amber-600 rounded-lg">
              <AlertCircle className="h-5 w-5 text-white" />
            </div>
            <div>
              <p className="text-2xl font-bold text-amber-900 dark:text-amber-100">
                {mockRisks.filter(r => r.status === 'identified').length}
              </p>
              <p className="text-sm text-amber-700 dark:text-amber-300">Open Risks</p>
            </div>
          </div>
        </CardContent>
      </Card>
      <Card className="bg-gradient-to-br from-green-50 to-green-100 border-green-200 dark:from-green-950/40 dark:to-green-900/40 dark:border-green-800">
        <CardContent className="p-4">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-green-600 rounded-lg">
              <TrendingUp className="h-5 w-5 text-white" />
            </div>
            <div>
              <p className="text-2xl font-bold text-green-900 dark:text-green-100">87%</p>
              <p className="text-sm text-green-700 dark:text-green-300">Compliance Rate</p>
            </div>
          </div>
        </CardContent>
      </Card>
      <Card className="bg-gradient-to-br from-purple-50 to-purple-100 border-purple-200 dark:from-purple-950/40 dark:to-purple-900/40 dark:border-purple-800">
        <CardContent className="p-4">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-purple-600 rounded-lg">
              <Clock className="h-5 w-5 text-white" />
            </div>
            <div>
              <p className="text-2xl font-bold text-purple-900 dark:text-purple-100">12</p>
              <p className="text-sm text-purple-700 dark:text-purple-300">Pending Reviews</p>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

function AnalystTaskWidget() {
  const pendingTasks = [
    { id: 1, title: "Review Q4 Risk Assessment", priority: "high", due: "Today" },
    { id: 2, title: "Update Control Documentation", priority: "medium", due: "Tomorrow" },
    { id: 3, title: "Collect Evidence for SOC2", priority: "high", due: "3 days" },
    { id: 4, title: "Assess New Vendor Risk", priority: "low", due: "1 week" },
  ];

  return (
    <Card className="mb-6">
      <CardHeader className="pb-3">
        <CardTitle className="text-lg flex items-center gap-2">
          <FileText className="h-5 w-5 text-green-600" />
          My Tasks
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className="space-y-3">
          {pendingTasks.map((task) => (
            <div 
              key={task.id} 
              className="flex items-center justify-between p-3 bg-muted/50 rounded-lg hover:bg-muted transition-colors"
            >
              <div className="flex items-center gap-3">
                <div className={`w-2 h-2 rounded-full ${
                  task.priority === 'high' ? 'bg-red-500' : 
                  task.priority === 'medium' ? 'bg-amber-500' : 'bg-green-500'
                }`} />
                <span className="text-sm font-medium text-foreground">{task.title}</span>
              </div>
              <span className="text-xs text-muted-foreground">{task.due}</span>
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}

function ManagerReportsWidget() {
  const reports = [
    { id: 1, title: "Monthly Risk Summary", date: "Jan 2026", status: "Ready" },
    { id: 2, title: "Compliance Dashboard", date: "Q4 2025", status: "Ready" },
    { id: 3, title: "Audit Findings Report", date: "Dec 2025", status: "Pending" },
  ];

  return (
    <Card className="mb-6">
      <CardHeader className="pb-3">
        <CardTitle className="text-lg flex items-center gap-2">
          <BarChart3 className="h-5 w-5 text-purple-600" />
          Executive Reports
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className="space-y-3">
          {reports.map((report) => (
            <div 
              key={report.id} 
              className="flex items-center justify-between p-3 bg-muted/50 rounded-lg hover:bg-muted transition-colors cursor-pointer"
            >
              <div>
                <p className="text-sm font-medium text-foreground">{report.title}</p>
                <p className="text-xs text-muted-foreground">{report.date}</p>
              </div>
              <span className={`text-xs px-2 py-1 rounded-full ${
                report.status === 'Ready' 
                  ? 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-300' 
                  : 'bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-300'
              }`}>
                {report.status}
              </span>
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}

// =============================================================================
// Main Dashboard Component
// =============================================================================

export default function DashboardPage() {
  const { user } = useAuth();
  const role = user?.role || 'manager';

  // Role-specific greeting
  const getGreeting = () => {
    switch (role) {
      case 'admin':
        return { title: 'System Overview', subtitle: 'Complete platform visibility and control' };
      case 'analyst':
        return { title: 'Risk & Compliance Dashboard', subtitle: 'Track your tasks and assessments' };
      case 'manager':
        return { title: 'Executive Dashboard', subtitle: 'High-level reports and insights' };
      default:
        return { title: 'Dashboard', subtitle: 'Risk and compliance overview' };
    }
  };

  const greeting = getGreeting();

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-foreground mb-1">{greeting.title}</h1>
        <p className="text-sm text-muted-foreground">{greeting.subtitle}</p>
      </div>

      {/* Admin-specific system overview */}
      {role === 'admin' && <AdminSystemOverview />}

      {/* Analyst-specific task widget */}
      {role === 'analyst' && <AnalystTaskWidget />}

      {/* Manager-specific reports widget */}
      {role === 'manager' && <ManagerReportsWidget />}

      {/* Common summary component - visible to all */}
      <DashboardSummary
        risks={mockRisks}
        controls={mockControls}
        complianceItems={mockComplianceItems}
      />

      {/* Risk highlights and overdue items - visibility based on role */}
      {(role === 'admin' || role === 'analyst') && (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <div className="lg:col-span-2">
            <RiskHighlights risks={mockRisks} />
          </div>
          <div>
            <OverdueItems complianceItems={mockComplianceItems} />
          </div>
        </div>
      )}

      {/* Manager sees only reports-focused content */}
      {role === 'manager' && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <OverdueItems complianceItems={mockComplianceItems} />
          <Card>
            <CardHeader>
              <CardTitle className="text-lg">Quick Actions</CardTitle>
            </CardHeader>
            <CardContent className="space-y-2">
              <button className="w-full text-left p-3 rounded-lg bg-muted/50 hover:bg-muted transition-colors text-sm text-foreground">
                View Latest Audit Report →
              </button>
              <button className="w-full text-left p-3 rounded-lg bg-muted/50 hover:bg-muted transition-colors text-sm text-foreground">
                Download Compliance Summary →
              </button>
              <button className="w-full text-left p-3 rounded-lg bg-muted/50 hover:bg-muted transition-colors text-sm text-foreground">
                Schedule Review Meeting →
              </button>
            </CardContent>
          </Card>
        </div>
      )}
    </div>
  );
}
