"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Download, FileText } from "lucide-react";

export default function ReportsPage() {
  const reports = [
    {
      title: "Risk Assessment Report",
      description: "Comprehensive risk register with scores and trends",
      lastGenerated: "2024-01-28",
    },
    {
      title: "Compliance Status Report",
      description: "Framework compliance rates and pending requirements",
      lastGenerated: "2024-01-25",
    },
    {
      title: "Control Effectiveness Report",
      description: "Assessment of control implementation and effectiveness",
      lastGenerated: "2024-01-22",
    },
  ];

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-slate-900 mb-1">Reports</h1>
        <p className="text-sm text-slate-600">
          Generate and export compliance reports
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {reports.map((report) => (
          <Card key={report.title}>
            <CardHeader>
              <CardTitle className="text-base flex items-center gap-2">
                <FileText className="h-5 w-5 text-blue-600" />
                {report.title}
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <p className="text-sm text-slate-600">{report.description}</p>
              <div className="flex items-center justify-between">
                <p className="text-xs text-slate-500">
                  Last generated:{" "}
                  {new Date(report.lastGenerated).toLocaleDateString()}
                </p>
                <Button size="sm" className="gap-2">
                  <Download className="h-4 w-4" />
                  Export
                </Button>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  );
}
