
"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Cell, Pie, PieChart, ResponsiveContainer, Tooltip } from "recharts";
import { useEffect, useState } from "react";
import { isoService } from "@/lib/iso-service";
import { ISOComplianceStats } from "@/types/iso27001";
import { Skeleton } from "@/components/ui/skeleton";

export function ISOControlsStatusWidget() {
  const [stats, setStats] = useState<ISOComplianceStats | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    isoService.getComplianceStats()
      .then(data => {
        setStats(data);
        setLoading(false);
      })
      .catch(err => {
        console.error("[ISOControlsStatusWidget] Failed to fetch stats:", err);
        setLoading(false);
      });
  }, []);

  if (loading) {
    return <Skeleton className="h-[300px] w-full rounded-xl" />;
  }

  if (!stats) return null;

  const data = [
    { name: 'Implemented', value: stats.implementedControls, color: '#16a34a' }, // green-600
    { name: 'In Progress', value: stats.inProgressControls, color: '#d97706' }, // amber-600
    { name: 'Not Started', value: stats.notStartedControls, color: '#cbd5e1' }, // slate-300
    { name: 'N/A', value: stats.notApplicableControls, color: '#94a3b8' }, // slate-400
  ].filter(item => item.value > 0);

  return (
    <Card className="h-full">
      <CardHeader>
        <CardTitle className="text-lg">Controls Status</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="h-[200px] w-full">
          <ResponsiveContainer width="100%" height="100%">
            <PieChart>
              <Pie
                data={data}
                cx="50%"
                cy="50%"
                innerRadius={60}
                outerRadius={80}
                paddingAngle={2}
                dataKey="value"
              >
                {data.map((entry, index) => (
                  <Cell key={`cell-${index}`} fill={entry.color} />
                ))}
              </Pie>
              <Tooltip />
            </PieChart>
          </ResponsiveContainer>
        </div>
        <div className="flex flex-wrap justify-center gap-4 mt-4">
          {data.map((item) => (
            <div key={item.name} className="flex items-center gap-2">
              <div className="w-3 h-3 rounded-full" style={{ backgroundColor: item.color }} />
              <span className="text-sm text-slate-600">
                {item.name} ({item.value})
              </span>
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}
