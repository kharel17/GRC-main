'use client';

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import {
  ArrowUpRight,
  CheckCircle2,
  AlertTriangle,
  ChevronUp,
  Activity,
} from 'lucide-react';
import { TicketActivity } from '@/types';

interface TicketTimelineProps {
  activities: TicketActivity[];
}

export function TicketTimeline({ activities }: TicketTimelineProps) {
  const sortedActivities = [...(activities || [])].sort(
    (a, b) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime()
  );

  return (
    <Card>
      <CardHeader className="pb-3">
        <CardTitle className="text-sm font-semibold flex items-center gap-2">
          <ArrowUpRight className="h-4 w-4 text-muted-foreground" />
          Ticket Activity History
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className="relative">
          <div className="absolute left-4 top-0 bottom-0 w-px bg-border" />
          <div className="space-y-4">
            {sortedActivities.map((activity, idx) => (
              <div key={`act-${idx}`} className="relative flex gap-3 pl-10">
                <div className={`absolute left-2 p-1.5 rounded-full z-10 ${
                  activity.activityType === 'escalation' ? 'bg-orange-100 text-orange-600' :
                  activity.activityType === 'resolution' ? 'bg-emerald-100 text-emerald-600' :
                  activity.activityType === 'sla_missed' ? 'bg-red-100 text-red-600' :
                  'bg-slate-100 text-slate-600'
                }`}>
                  {activity.activityType === 'escalation' ? <ChevronUp className="h-3.5 w-3.5" /> : 
                   activity.activityType === 'resolution' ? <CheckCircle2 className="h-3.5 w-3.5" /> :
                   activity.activityType === 'sla_missed' ? <AlertTriangle className="h-3.5 w-3.5" /> :
                   <Activity className="h-3.5 w-3.5" />}
                </div>
                <div className={`bg-muted/50 rounded-lg p-3 flex-1 border ${
                  activity.activityType === 'escalation' ? 'border-orange-100' :
                  activity.activityType === 'resolution' ? 'border-emerald-100' :
                  'border-transparent'
                }`}>
                  <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-1">
                    <span className="text-sm font-medium text-foreground capitalize">
                      {activity.activityType.replace('_', ' ')}
                    </span>
                    <time className="text-xs text-muted-foreground">
                      {new Date(activity.timestamp).toLocaleString()}
                    </time>
                  </div>
                  {activity.description && (
                    <p className="text-xs text-muted-foreground mt-1">
                      {activity.description}
                    </p>
                  )}
                  {activity.newValue && (
                    <div className="mt-2 flex items-center gap-2 text-[10px] uppercase tracking-wider font-semibold text-muted-foreground bg-background/40 p-1.5 rounded">
                      {activity.oldValue && (
                        <>
                          <span className="line-through opacity-50">{activity.oldValue}</span>
                          <span>→</span>
                        </>
                      )}
                      <span className="text-foreground">{activity.newValue}</span>
                    </div>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
