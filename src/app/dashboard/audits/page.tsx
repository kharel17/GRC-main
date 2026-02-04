"use client";

import { mockAuditLogs } from "@/lib/mock-data";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Clock } from "lucide-react";

export default function AuditsPage() {
  const getActionColor = (action: string) => {
    const colors: Record<string, string> = {
      created: "bg-blue-100 text-blue-700",
      updated: "bg-purple-100 text-purple-700",
      deleted: "bg-red-100 text-red-700",
      approved: "bg-green-100 text-green-700",
      reviewed: "bg-amber-100 text-amber-700",
    };
    return colors[action] || "bg-slate-100 text-slate-700";
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-slate-900 mb-1">Audit Log</h1>
        <p className="text-sm text-slate-600">
          System activity and change tracking
        </p>
      </div>

      <div className="space-y-3">
        {mockAuditLogs.map((log) => (
          <Card key={log.id}>
            <CardContent className="pt-6">
              <div className="flex items-start justify-between gap-4">
                <div className="flex-1">
                  <div className="flex items-center gap-2 mb-2">
                    <Badge className={getActionColor(log.action)}>
                      {log.action}
                    </Badge>
                    <span className="text-sm font-medium text-slate-900">
                      {log.entityName || log.entityType}
                    </span>
                  </div>
                  <p className="text-sm text-slate-600 mb-2">
                    {log.description}
                  </p>
                  <div className="flex items-center gap-4 text-xs text-slate-500">
                    <span>By: {log.userName}</span>
                    <div className="flex items-center gap-1">
                      <Clock className="h-3 w-3" />
                      {new Date(log.timestamp).toLocaleString()}
                    </div>
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  );
}
