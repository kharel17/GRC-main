'use client';

import { useState } from 'react';
import { fetchAuditLogs, fetchUsers } from '@/lib/data-service';
import { useApiData } from '@/hooks';
import { AuditLog } from '@/types';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Clock, FileText, Shield, Activity, Filter, AlertTriangle, Edit, Loader2 } from 'lucide-react';

type ActionTypeFilter = 'all' | 'created' | 'updated' | 'deleted';

function getActionIcon(action: string) {
  switch (action) {
    case 'created': return <FileText className="h-4 w-4" />;
    case 'updated': return <Edit className="h-4 w-4" />;
    case 'deleted': return <AlertTriangle className="h-4 w-4" />;
    case 'approved': return <Shield className="h-4 w-4" />;
    default: return <Activity className="h-4 w-4" />;
  }
}

function getActionColor(action: string) {
  switch (action) {
    case 'created': return 'bg-green-100 text-green-600';
    case 'updated': return 'bg-blue-100 text-blue-600';
    case 'deleted': return 'bg-red-100 text-red-600';
    case 'approved': return 'bg-emerald-100 text-emerald-600';
    case 'reviewed': return 'bg-purple-100 text-purple-600';
    default: return 'bg-slate-100 text-slate-600';
  }
}

export default function AuditPage() {
  const { data: auditLogs, loading: logsLoading, error: logsError } = useApiData<AuditLog[]>(fetchAuditLogs);
  const { data: users, loading: usersLoading } = useApiData<any[]>(fetchUsers);
  const [actionFilter, setActionFilter] = useState<ActionTypeFilter>('all');
  const [userFilter, setUserFilter] = useState<string>('all');

  const allLogs = auditLogs ?? [];
  const allUsers = users ?? [];
  const loading = logsLoading || usersLoading;
  const error = logsError;

  const filteredLogs = allLogs.filter((log) => {
    if (actionFilter !== 'all' && log.action !== actionFilter) return false;
    // Support filtering by actor_id
    if (userFilter !== 'all' && log.actor_id !== userFilter) return false;
    return true;
  });

  const filterButtons: { label: string; value: ActionTypeFilter; count: number }[] = [
    { label: 'All', value: 'all', count: allLogs.length },
    { label: 'Created', value: 'created', count: allLogs.filter(l => l.action === 'created').length },
    { label: 'Updated', value: 'updated', count: allLogs.filter(l => l.action === 'updated').length },
    { label: 'Deleted', value: 'deleted', count: allLogs.filter(l => l.action === 'deleted').length },
  ];

  if (loading) {
    return (
      <div className="flex items-center justify-center py-24">
        <Loader2 className="h-8 w-8 animate-spin text-blue-600" />
        <span className="ml-3 text-slate-600">Loading audit logs…</span>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex flex-col items-center justify-center py-24 text-center">
        <Clock className="h-12 w-12 text-red-400 mb-4" />
        <h3 className="text-sm font-medium text-slate-900 mb-1">Failed to load audit logs</h3>
        <p className="text-sm text-slate-500">{error.message}</p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-slate-900 mb-1">Audit Log</h1>
        <p className="text-sm text-slate-600">
          Track all system activities and changes
        </p>
      </div>

      {/* Filter Bar */}
      <div className="flex flex-col sm:flex-row gap-4 items-start sm:items-center justify-between">
        <div className="flex flex-wrap gap-2">
          {filterButtons.map((btn) => (
            <button
              key={btn.value}
              onClick={() => setActionFilter(btn.value)}
              className={`px-3 py-1.5 text-xs font-medium rounded-full transition-colors ${
                actionFilter === btn.value
                  ? 'bg-blue-600 text-white'
                  : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
              }`}
            >
              {btn.label} ({btn.count})
            </button>
          ))}
        </div>

        <div className="flex items-center gap-2">
          <Filter className="h-4 w-4 text-slate-500" />
          <Select value={userFilter} onValueChange={setUserFilter}>
            <SelectTrigger className="w-[180px] h-9">
              <SelectValue placeholder="Filter by user" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All Users</SelectItem>
              {allUsers.map((u) => (
                <SelectItem key={u.id} value={u.id}>
                  {u.full_name || u.email}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
      </div>

      {/* Results Count */}
      <div className="text-sm text-slate-500">
        Showing {filteredLogs.length} of {allLogs.length} entries
      </div>

      {/* Empty State */}
      {filteredLogs.length === 0 ? (
        <Card className="border-dashed">
          <CardContent className="py-12 text-center">
            <Clock className="h-12 w-12 text-slate-300 mx-auto mb-4" />
            <h3 className="text-sm font-medium text-slate-900 mb-1">No audit entries found</h3>
            <p className="text-sm text-slate-500">
              Try adjusting your filters to see more results.
            </p>
          </CardContent>
        </Card>
      ) : (
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-base font-semibold flex items-center gap-2">
              <Clock className="h-5 w-5 text-slate-600" />
              Activity Timeline
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="relative">
              {/* Timeline line */}
              <div className="absolute left-5 top-0 bottom-0 w-px bg-slate-200" />
              
              <div className="space-y-4">
                {filteredLogs.map((log) => (
                  <div key={log.id} className="relative flex gap-4 pl-12">
                    {/* Timeline dot */}
                    <div className={`absolute left-3 p-1.5 rounded-full ${getActionColor(log.action)}`}>
                      {getActionIcon(log.action)}
                    </div>
                    
                    <div className="flex-1 bg-slate-50 rounded-lg p-4 hover:bg-slate-100 transition-colors">
                      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2">
                        <p className="text-sm font-medium text-slate-900 capitalize">
                          {log.action} {log.entityType?.replace('_', ' ')}
                        </p>
                        <time className="text-xs text-slate-500">
                          {new Date(log.timestamp || log.created_at || '').toLocaleString()}
                        </time>
                      </div>
                      {log.description && (
                        <p className="text-xs text-slate-600 mt-1">{log.description}</p>
                      )}
                      <div className="flex flex-wrap gap-2 mt-2">
                        <Badge variant="secondary" className="text-xs">
                          {log.userName}
                        </Badge>
                        {log.entityName && (
                          <Badge variant="outline" className="text-xs">
                            {log.entityName}
                          </Badge>
                        )}
                        {log.ipAddress && (
                          <Badge variant="outline" className="text-xs text-slate-500">
                            IP: {log.ipAddress}
                          </Badge>
                        )}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
