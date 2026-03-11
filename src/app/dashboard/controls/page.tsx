'use client';

import { useState } from 'react';
import { fetchControls } from '@/lib/data-service';
import { useApiData } from '@/hooks/use-api-data';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Plus, Shield, Filter, Loader2 } from 'lucide-react';
import Link from 'next/link';
import { RoleGuard } from '@/components/auth/RoleGuard';
import { NewControlDialog } from '@/features/control/NewControlDialog';

type ControlType = 'all' | 'preventive' | 'detective' | 'corrective';

function getEffectivenessStyles(effectiveness: string) {
  switch (effectiveness) {
    case 'high':
      return 'bg-green-100 dark:bg-green-900 text-green-700 dark:text-green-200';
    case 'medium':
      return 'bg-amber-100 dark:bg-amber-900 text-amber-700 dark:text-amber-200';
    case 'low':
      return 'bg-red-100 dark:bg-red-900 text-red-700 dark:text-red-200';
    default:
      return 'bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300';
  }
}

function getStatusStyles(status: string) {
  switch (status) {
    case 'implemented':
      return 'bg-green-100 dark:bg-green-900 text-green-700 dark:text-green-200';
    case 'under_review':
      return 'bg-blue-100 dark:bg-blue-900 text-blue-700 dark:text-blue-200';
    case 'planned':
      return 'bg-amber-100 dark:bg-amber-900 text-amber-700 dark:text-amber-200';
    default:
      return 'bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300';
  }
}

function getTypeColor(type: string) {
  switch (type) {
    case 'preventive':
      return 'border-blue-200 dark:border-blue-700 bg-blue-50 dark:bg-blue-900';
    case 'detective':
      return 'border-purple-200 dark:border-purple-700 bg-purple-50 dark:bg-purple-900';
    case 'corrective':
      return 'border-amber-200 dark:border-amber-700 bg-amber-50 dark:bg-amber-900';
    default:
      return 'border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-950';
  }
}

export default function ControlsPage() {
  const { data: controls, loading, error, refetch } = useApiData(fetchControls);
  const [typeFilter, setTypeFilter] = useState<ControlType>('all');
  const [statusFilter, setStatusFilter] = useState<string>('all');
  const [newControlOpen, setNewControlOpen] = useState(false);

  const allControls = controls ?? [];

  const filteredControls = allControls.filter((control) => {
    if (typeFilter !== 'all' && control.controlType !== typeFilter) return false;
    if (statusFilter !== 'all' && control.status !== statusFilter) return false;
    return true;
  });

  const typeButtons: { label: string; value: ControlType; count: number }[] = [
    { label: 'All', value: 'all', count: allControls.length },
    { label: 'Preventive', value: 'preventive', count: allControls.filter(c => c.controlType === 'preventive').length },
    { label: 'Detective', value: 'detective', count: allControls.filter(c => c.controlType === 'detective').length },
    { label: 'Corrective', value: 'corrective', count: allControls.filter(c => c.controlType === 'corrective').length },
  ];

  if (loading) {
    return (
      <div className="flex items-center justify-center py-24">
        <Loader2 className="h-8 w-8 animate-spin text-blue-600" />
        <span className="ml-3 text-slate-600">Loading controls…</span>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex flex-col items-center justify-center py-24 text-center">
        <Shield className="h-12 w-12 text-red-400 dark:text-red-500 mb-4" />
        <h3 className="text-sm font-medium text-slate-900 dark:text-slate-100 mb-1">Failed to load controls</h3>
        <p className="text-sm text-slate-500 dark:text-slate-400">{error.message}</p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 dark:text-slate-100 mb-1">Controls</h1>
          <p className="text-sm text-slate-600 dark:text-slate-400">Manage risk mitigation controls</p>
        </div>
        <RoleGuard allowedRoles={['admin', 'analyst']}>
          <Button className="gap-2 w-full sm:w-auto" onClick={() => setNewControlOpen(true)}>
            <Plus className="h-4 w-4" />
            New Control
          </Button>
        </RoleGuard>
      </div>

      {/* Filter Bar */}
      <div className="flex flex-col sm:flex-row gap-4 items-start sm:items-center justify-between">
        {/* Type Filter Tabs */}
        <div className="flex flex-wrap gap-2">
          {typeButtons.map((btn) => (
            <button
              key={btn.value}
              onClick={() => setTypeFilter(btn.value)}
              className={`px-3 py-1.5 text-xs font-medium rounded-full transition-colors ${typeFilter === btn.value
                  ? 'bg-blue-600 dark:bg-blue-500 text-white dark:text-white'
                  : 'bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-400 hover:bg-slate-200 dark:hover:bg-slate-700'
                }`}
            >
              {btn.label} ({btn.count})
            </button>
          ))}
        </div>

        {/* Status Filter */}
        <div className="flex items-center gap-2">
          <Filter className="h-4 w-4 text-slate-500" />
          <Select value={statusFilter} onValueChange={setStatusFilter}>
            <SelectTrigger className="w-[140px] h-9">
              <SelectValue placeholder="Status" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All Status</SelectItem>
              <SelectItem value="implemented">Implemented</SelectItem>
              <SelectItem value="under_review">Under Review</SelectItem>
              <SelectItem value="planned">Planned</SelectItem>
            </SelectContent>
          </Select>
        </div>
      </div>

      {/* Results Count */}
      <div className="text-sm text-slate-500 dark:text-slate-400">
        Showing {filteredControls.length} of {allControls.length} controls
      </div>

      {/* Empty State */}
      {filteredControls.length === 0 ? (
        <Card className="border-dashed">
          <CardContent className="py-12 text-center">
            <Shield className="h-12 w-12 text-slate-300 dark:text-slate-600 mx-auto mb-4" />
            <h3 className="text-sm font-medium text-slate-900 dark:text-slate-100 mb-1">No controls found</h3>
            <p className="text-sm text-slate-500 dark:text-slate-400">
              Try adjusting your filters to see more results.
            </p>
          </CardContent>
        </Card>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {filteredControls.map((control) => (
            <Link key={control.id} href={`/dashboard/controls/${control.id}`}>
              <Card
                className={`h-full hover:shadow-md transition-shadow border-l-4 cursor-pointer group ${getTypeColor(control.controlType)}`}
              >
                <CardHeader className="pb-2">
                  <CardTitle className="text-sm font-medium line-clamp-2 group-hover:text-blue-600 transition-colors">{control.title}</CardTitle>
                </CardHeader>
                <CardContent className="space-y-3">
                  <p className="text-xs text-slate-600 dark:text-slate-400 line-clamp-2">{control.description}</p>
                  <div className="flex flex-wrap gap-2">
                    <Badge variant="outline" className="text-xs capitalize">
                      {control.controlType}
                    </Badge>
                    <Badge className={`text-xs capitalize ${getEffectivenessStyles(control.effectiveness)}`}>
                      {control.effectiveness}
                    </Badge>
                    <Badge variant="secondary" className={`text-xs capitalize ${getStatusStyles(control.status)}`}>
                      {control.status.replace('_', ' ')}
                    </Badge>
                  </div>
                  <div className="pt-2 border-t text-xs text-slate-500 dark:text-slate-400 flex items-center justify-between">
                    <span>Owner: {control.ownerName}</span>
                  </div>
                </CardContent>
              </Card>
            </Link>
          ))}
        </div>
      )}

      <NewControlDialog
        open={newControlOpen}
        onOpenChange={setNewControlOpen}
        onSuccess={() => refetch()}
      />
    </div>
  );
}