"use client";

import { ComplianceItem } from '@/types';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Clock, AlertTriangle, ArrowRight, Calendar, CheckCircle2 } from 'lucide-react';
import Link from 'next/link';

interface OverdueItemsProps {
  complianceItems: ComplianceItem[];
}

function getDaysText(dueDate: string, today: Date): string {
  const due = new Date(dueDate);
  const diff = Math.floor((due.getTime() - today.getTime()) / (1000 * 60 * 60 * 24));
  
  if (diff < 0) {
    const absDiff = Math.abs(diff);
    return `${absDiff} day${absDiff !== 1 ? 's' : ''} overdue`;
  } else if (diff === 0) {
    return 'Due today';
  } else {
    return `${diff} day${diff !== 1 ? 's' : ''} left`;
  }
}

export function OverdueItems({ complianceItems }: OverdueItemsProps) {
  const today = new Date();
  const overdueItems = complianceItems.filter((item) => {
    if (!item.dueDate) return false;
    return new Date(item.dueDate) < today && item.status !== 'compliant';
  });

  const upcomingItems = complianceItems.filter((item) => {
    if (!item.dueDate) return false;
    const dueDate = new Date(item.dueDate);
    const daysUntilDue = Math.floor((dueDate.getTime() - today.getTime()) / (1000 * 60 * 60 * 24));
    return daysUntilDue >= 0 && daysUntilDue <= 30 && item.status !== 'compliant';
  });

  const allItems = [...overdueItems, ...upcomingItems].slice(0, 5);

  if (allItems.length === 0) {
    return (
      <Card className="h-full">
        <CardHeader className="pb-3">
          <CardTitle className="text-base font-semibold flex items-center gap-2">
            <Clock className="h-5 w-5 text-muted-foreground" />
            Upcoming & Overdue
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="text-center py-12 px-6">
            <div className="w-16 h-16 bg-green-50 dark:bg-green-900/20 rounded-full flex items-center justify-center mx-auto mb-4 border border-green-100 dark:border-green-900/30">
              <CheckCircle2 className="h-8 w-8 text-green-500" />
            </div>
            <h4 className="text-sm font-bold text-slate-900 dark:text-slate-100 mb-1 leading-tight">All Operations Clear</h4>
            <p className="text-xs text-slate-500 dark:text-slate-400">
              No upcoming or overdue compliance tasks identified.
            </p>
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className="h-full">
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <CardTitle className="text-base font-semibold flex items-center gap-2">
            <Clock className="h-5 w-5 text-muted-foreground" />
            <span className="hidden sm:inline">Upcoming & Overdue</span>
            <span className="sm:hidden">Due Items</span>
            <Badge variant="secondary" className="ml-1">{allItems.length}</Badge>
          </CardTitle>
          <Link href="/dashboard/evidence">
            <Button variant="ghost" size="sm" className="gap-1 text-blue-600 hover:text-blue-700 hover:bg-blue-50 dark:text-blue-400 dark:hover:text-blue-300 dark:hover:bg-blue-900/20 text-xs">
              View All
              <ArrowRight className="h-3 w-3" />
            </Button>
          </Link>
        </div>
      </CardHeader>
      <CardContent>
        <div className="space-y-3">
          {allItems.map((item) => {
            const isOverdue = new Date(item.dueDate!) < today;
            const daysText = getDaysText(item.dueDate!, today);
            
            return (
              <div 
                key={item.id} 
                className={`flex items-center gap-4 p-3.5 rounded-xl border transition-all hover:shadow-sm group ${
                  isOverdue 
                    ? 'bg-red-50/50 border-red-100 dark:bg-red-950/10 dark:border-red-900/30 hover:bg-red-100/50' 
                    : 'bg-white dark:bg-slate-950 border-slate-100 dark:border-slate-800 hover:border-primary/30'
                }`}
              >
                <div className={`p-2.5 rounded-lg shrink-0 ${
                  isOverdue ? 'bg-red-100 text-red-600' : 'bg-slate-100 text-slate-600 dark:bg-slate-800'
                }`}>
                  <Clock className="h-4 w-4" />
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <p className="font-bold text-sm text-slate-900 dark:text-slate-100 truncate group-hover:text-primary transition-colors">
                      {item.title}
                    </p>
                    {isOverdue && <AlertTriangle className="h-3.5 w-3.5 text-red-600 animate-pulse" />}
                  </div>
                  <div className="flex items-center gap-2 mt-0.5">
                    <Badge variant="outline" className="text-[9px] font-bold uppercase tracking-tight py-0 h-4 border-slate-200">
                      {item.requirementId || 'G-001'}
                    </Badge>
                    <span className="text-[10px] text-muted-foreground font-medium truncate">
                      {item.framework}
                    </span>
                  </div>
                </div>
                <div className="flex flex-col items-end gap-1 shrink-0">
                  <span className={`text-[10px] font-black uppercase tracking-tighter ${
                    isOverdue ? 'text-red-600' : 'text-slate-500'
                  }`}>
                    {daysText}
                  </span>
                  <div className={`h-1.5 w-12 rounded-full overflow-hidden bg-slate-100 dark:bg-slate-800`}>
                    <div className={`h-full ${isOverdue ? 'bg-red-500' : 'bg-amber-500'}`} style={{ width: isOverdue ? '100%' : '30%' }} />
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      </CardContent>
    </Card>
  );
}
