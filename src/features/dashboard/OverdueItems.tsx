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
          <div className="text-center py-8">
            <CheckCircle2 className="h-8 w-8 text-green-400 mx-auto mb-2" />
            <p className="text-sm text-muted-foreground">
              No upcoming or overdue items
            </p>
            <p className="text-xs text-muted-foreground mt-1">All compliance items are on track</p>
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
        <div className="space-y-2.5">
          {allItems.map((item) => {
            const isOverdue = new Date(item.dueDate!) < today;
            const daysText = getDaysText(item.dueDate!, today);
            
            return (
              <div 
                key={item.id} 
                className={`flex flex-col sm:flex-row sm:items-center gap-2 p-3 rounded-lg transition-colors ${
                  isOverdue 
                    ? 'bg-red-50 hover:bg-red-100 dark:bg-red-900/20 dark:hover:bg-red-900/30' 
                    : 'bg-muted/50 hover:bg-muted'
                }`}
              >
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-1">
                    <p className="font-medium text-sm text-foreground truncate">{item.title}</p>
                    {isOverdue && <AlertTriangle className="h-3.5 w-3.5 text-red-600 dark:text-red-400 flex-shrink-0" />}
                  </div>
                  <div className="flex flex-wrap items-center gap-x-2 gap-y-1 text-xs text-muted-foreground">
                    <span className="font-medium">{item.framework}</span>
                    <span>•</span>
                    <span>{item.requirementId}</span>
                    <span className="hidden sm:inline">•</span>
                    <span className={`hidden sm:inline ${isOverdue ? 'text-red-600 dark:text-red-400 font-medium' : ''}`}>
                      <Calendar className="h-3 w-3 inline mr-1" />
                      {daysText}
                    </span>
                  </div>
                </div>
                <div className="flex items-center gap-2 mt-2 sm:mt-0">
                  <Badge 
                    variant={isOverdue ? 'destructive' : 'secondary'} 
                    className="flex-shrink-0 text-xs"
                  >
                    {daysText}
                  </Badge>
                </div>
              </div>
            );
          })}
        </div>
      </CardContent>
    </Card>
  );
}
