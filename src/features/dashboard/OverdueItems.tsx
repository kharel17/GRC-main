import { ComplianceItem } from '@/types/compliance';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Clock, AlertTriangle } from 'lucide-react';

interface OverdueItemsProps {
  complianceItems: ComplianceItem[];
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
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-base font-semibold flex items-center gap-2">
            <Clock className="h-5 w-5 text-slate-400" />
            Upcoming & Overdue
          </CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-slate-500 text-center py-8">
            No upcoming or overdue compliance items
          </p>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader className="pb-3">
        <CardTitle className="text-base font-semibold flex items-center gap-2">
          <Clock className="h-5 w-5 text-slate-600" />
          Upcoming & Overdue ({allItems.length})
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className="space-y-3">
          {allItems.map((item) => {
            const isOverdue = new Date(item.dueDate!) < today;
            return (
              <div key={item.id} className="flex items-start justify-between gap-3 p-3 bg-slate-50 rounded-lg">
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-1">
                    <p className="font-medium text-sm text-slate-900 truncate">{item.title}</p>
                    {isOverdue && <AlertTriangle className="h-4 w-4 text-red-600 flex-shrink-0" />}
                  </div>
                  <p className="text-xs text-slate-500">
                    {item.framework} • {item.requirementId}
                  </p>
                </div>
                <Badge variant={isOverdue ? 'destructive' : 'secondary'} className="flex-shrink-0">
                  {isOverdue ? 'Overdue' : 'Due soon'}
                </Badge>
              </div>
            );
          })}
        </div>
      </CardContent>
    </Card>
  );
}
