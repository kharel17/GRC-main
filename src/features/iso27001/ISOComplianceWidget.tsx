
"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import { CheckCircle2, AlertCircle, Clock } from "lucide-react";
import { useEffect, useState } from "react";
import { isoService, getIsUsingFallback } from "@/lib";
import { ISOComplianceStats } from "@/types";
import { Skeleton } from "@/components/ui/skeleton";
import { Badge } from "@/components/ui/badge";


export function ISOComplianceWidget() {
  const [stats, setStats] = useState<ISOComplianceStats | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    isoService.getComplianceStats()
      .then(data => {
        setStats(data);
        setLoading(false);
      });
  }, []);


  if (loading) {
    return <Skeleton className="h-[200px] w-full rounded-xl" />;
  }

  if (!stats) return null;

  const isFallback = getIsUsingFallback();



  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="text-lg font-semibold flex items-center justify-between">
          <div className="flex items-center gap-2">
            <span>Overall Compliance</span>
            {isFallback && (
              <Badge variant="outline" className="text-[10px] h-5 bg-amber-50 text-amber-600 border-amber-200 animate-pulse">
                Offline Mode
              </Badge>
            )}
          </div>
          <span className={`text-2xl font-bold ${stats.complianceScore >= 80 ? 'text-green-600' :
            stats.complianceScore >= 50 ? 'text-amber-600' : 'text-red-600'
            }`}>
            {stats.complianceScore}%
          </span>
        </CardTitle>
      </CardHeader>
      <CardContent>
        <Progress value={stats.complianceScore} className="h-2 mb-4" />
        <div className="grid grid-cols-3 gap-4 pt-2">
          <div className="flex flex-col items-center p-2 bg-green-500/10 rounded-lg">
            <CheckCircle2 className="h-5 w-5 text-green-600 mb-1" />
            <span className="text-xl font-bold text-green-700 dark:text-green-500">{stats.implementedControls}</span>
            <span className="text-xs text-green-600/80 text-center">Implemented</span>
          </div>
          <div className="flex flex-col items-center p-2 bg-amber-500/10 rounded-lg">
            <Clock className="h-5 w-5 text-amber-600 mb-1" />
            <span className="text-xl font-bold text-amber-700 dark:text-amber-500">{stats.inProgressControls}</span>
            <span className="text-xs text-amber-600/80 text-center">In Progress</span>
          </div>
          <div className="flex flex-col items-center p-2 bg-muted rounded-lg">
            <AlertCircle className="h-5 w-5 text-muted-foreground mb-1" />
            <span className="text-xl font-bold text-foreground">{stats.notStartedControls}</span>
            <span className="text-xs text-muted-foreground text-center">Not Started</span>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
