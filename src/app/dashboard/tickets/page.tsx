'use client';

import { useState } from 'react';
import { fetchTickets } from '@/lib/data-service';
import { useApiData } from '@/hooks/use-api-data';
import { TicketCard } from '@/features/tickets/TicketCard';
import { Card, CardContent } from '@/components/ui/card';
import { Switch } from '@/components/ui/switch';
import { Label } from '@/components/ui/label';
import { useAuth } from '@/hooks/useAuth';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import {
  AlertTriangle,
  ArrowUpRight,
  CheckCircle2,
  Clock,
  Filter,
  Loader2,
  Plus,
  Ticket,
  XCircle,
} from 'lucide-react';
import { RoleGuard } from '@/components/auth/RoleGuard';
import { TicketStatus, TicketPriority, TicketCategory } from '@/types/ticket';

export default function TicketsPage() {
  const { user } = useAuth();
  const { data: tickets, loading, error, refetch } = useApiData(fetchTickets);
  
  const [statusFilter, setStatusFilter] = useState<string>('all');
  const [priorityFilter, setPriorityFilter] = useState<string>('all');
  const [categoryFilter, setCategoryFilter] = useState<string>('all');
  const [showMyTickets, setShowMyTickets] = useState(false);

  const allTickets = tickets ?? [];

  const filteredTickets = allTickets.filter((ticket) => {
    if (statusFilter !== 'all' && ticket.status !== statusFilter) return false;
    if (priorityFilter !== 'all' && ticket.priority !== priorityFilter) return false;
    if (categoryFilter !== 'all' && ticket.category !== categoryFilter) return false;
    
    if (showMyTickets && user) {
      const isAssignedTo = ticket.assignedToId === user.id || ticket.assignedToName === user.email;
      const isOwner = ticket.createdBy === user.id;
      const isEscalatedToRole = ticket.escalatedToRole === user.role;
      return isAssignedTo || isOwner || isEscalatedToRole;
    }
    
    return true;
  });

  const clearFilters = () => {
    setStatusFilter('all');
    setPriorityFilter('all');
    setCategoryFilter('all');
    setShowMyTickets(false);
  };


  const hasActiveFilters = statusFilter !== 'all' || priorityFilter !== 'all' || categoryFilter !== 'all';

  // Stats
  const openCount = allTickets.filter(t => t.status === 'open' || t.status === 'in_review').length;
  const escalatedCount = allTickets.filter(t => t.status === 'escalated').length;
  const resolvedCount = allTickets.filter(t => t.status === 'resolved' || t.status === 'closed').length;
  const criticalCount = allTickets.filter(t => t.priority === 'critical' && t.status !== 'resolved' && t.status !== 'closed').length;

  const stats = [
    {
      label: 'Open',
      value: openCount,
      icon: Clock,
      color: 'text-blue-600 dark:text-blue-400',
      bgColor: 'bg-blue-50 dark:bg-blue-900/20',
      borderColor: 'border-blue-200 dark:border-blue-800',
    },
    {
      label: 'Escalated',
      value: escalatedCount,
      icon: ArrowUpRight,
      color: 'text-red-600 dark:text-red-400',
      bgColor: 'bg-red-50 dark:bg-red-900/20',
      borderColor: 'border-red-200 dark:border-red-800',
    },
    {
      label: 'Resolved',
      value: resolvedCount,
      icon: CheckCircle2,
      color: 'text-emerald-600 dark:text-emerald-400',
      bgColor: 'bg-emerald-50 dark:bg-emerald-900/20',
      borderColor: 'border-emerald-200 dark:border-emerald-800',
    },
    {
      label: 'Critical Active',
      value: criticalCount,
      icon: AlertTriangle,
      color: 'text-orange-600 dark:text-orange-400',
      bgColor: 'bg-orange-50 dark:bg-orange-900/20',
      borderColor: 'border-orange-200 dark:border-orange-800',
    },
  ];

  if (loading) {
    return (
      <div className="flex items-center justify-center py-24">
        <Loader2 className="h-8 w-8 animate-spin text-blue-600" />
        <span className="ml-3 text-slate-600">Loading tickets…</span>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex flex-col items-center justify-center py-24 text-center">
        <Ticket className="h-12 w-12 text-red-400 mb-4" />
        <h3 className="text-sm font-medium text-slate-900 mb-1">Failed to load tickets</h3>
        <p className="text-sm text-slate-500">{error.message}</p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-foreground mb-1">Ticket Escalation</h1>
          <p className="text-sm text-muted-foreground">
            Track, escalate, and share risk findings with stakeholders
          </p>
        </div>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        {stats.map((stat) => {
          const Icon = stat.icon;
          return (
            <Card key={stat.label} className={`border ${stat.borderColor}`}>
              <CardContent className="pt-5 pb-4">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-xs font-medium text-muted-foreground uppercase tracking-wide">{stat.label}</p>
                    <p className={`text-2xl font-bold mt-1 ${stat.color}`}>{stat.value}</p>
                  </div>
                  <div className={`p-2.5 rounded-lg ${stat.bgColor}`}>
                    <Icon className={`h-5 w-5 ${stat.color}`} />
                  </div>
                </div>
              </CardContent>
            </Card>
          );
        })}
      </div>

      {/* Filter Bar */}
      <div className="flex flex-col sm:flex-row gap-3 items-start sm:items-center justify-between">
        <div className="flex flex-wrap gap-2 items-center w-full sm:w-auto">
          <div className="flex items-center gap-2">
            <Filter className="h-4 w-4 text-muted-foreground" />
            <span className="text-sm text-muted-foreground hidden sm:inline">Filters:</span>
          </div>
          
          <div className="flex items-center gap-2 mr-2 pr-2 border-r border-border">
            <Switch
              id="my-tickets"
              checked={showMyTickets}
              onCheckedChange={setShowMyTickets}
            />
            <Label htmlFor="my-tickets" className="text-sm cursor-pointer py-1">
              My Tickets
            </Label>
          </div>

          <Select value={statusFilter} onValueChange={setStatusFilter}>
            <SelectTrigger className="w-[130px] h-9">
              <SelectValue placeholder="Status" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All Status</SelectItem>
              <SelectItem value="open">Open</SelectItem>
              <SelectItem value="in_review">In Review</SelectItem>
              <SelectItem value="pending_evidence">Pending Evidence</SelectItem>
              <SelectItem value="escalated">Escalated</SelectItem>
              <SelectItem value="resolved">Resolved</SelectItem>
              <SelectItem value="closed">Closed</SelectItem>
            </SelectContent>
          </Select>

          <Select value={priorityFilter} onValueChange={setPriorityFilter}>
            <SelectTrigger className="w-[130px] h-9">
              <SelectValue placeholder="Priority" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All Priority</SelectItem>
              <SelectItem value="critical">Critical</SelectItem>
              <SelectItem value="high">High</SelectItem>
              <SelectItem value="medium">Medium</SelectItem>
              <SelectItem value="low">Low</SelectItem>
            </SelectContent>
          </Select>

          <Select value={categoryFilter} onValueChange={setCategoryFilter}>
            <SelectTrigger className="w-[150px] h-9">
              <SelectValue placeholder="Category" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All Categories</SelectItem>
              <SelectItem value="risk_identified">Risk Identified</SelectItem>
              <SelectItem value="risk_mitigated">Risk Mitigated</SelectItem>
              <SelectItem value="compliance_gap">Compliance Gap</SelectItem>
              <SelectItem value="security_incident">Security Incident</SelectItem>
              <SelectItem value="audit_finding">Audit Finding</SelectItem>
              <SelectItem value="policy_violation">Policy Violation</SelectItem>
            </SelectContent>
          </Select>

          {hasActiveFilters && (
            <Button variant="ghost" size="sm" onClick={clearFilters} className="text-muted-foreground">
              Clear
            </Button>
          )}
        </div>
      </div>

      {/* Results Count */}
      <div className="text-sm text-muted-foreground">
        Showing {filteredTickets.length} of {allTickets.length} tickets
      </div>

      {/* Tickets Grid or Empty State */}
      {filteredTickets.length === 0 ? (
        <Card className="border-dashed">
          <CardContent className="py-12 text-center">
            <Ticket className="h-12 w-12 text-muted-foreground/30 mx-auto mb-4" />
            <h3 className="text-sm font-medium text-foreground mb-1">No tickets found</h3>
            <p className="text-sm text-muted-foreground mb-4">
              {hasActiveFilters
                ? 'Try adjusting your filters to see more results.'
                : 'Create your first escalation ticket to get started.'}
            </p>
            {hasActiveFilters && (
              <Button variant="outline" size="sm" onClick={clearFilters}>
                Clear Filters
              </Button>
            )}
          </CardContent>
        </Card>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
          {filteredTickets.map((ticket) => (
            <TicketCard key={ticket.id} ticket={ticket} />
          ))}
        </div>
      )}
    </div>
  );
}
