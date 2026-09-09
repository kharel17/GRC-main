'use client';

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Switch } from '@/components/ui/switch';
import { Label } from '@/components/ui/label';
import { EscalationBadge } from './EscalationBadge';
import { getPriorityStyles, getStatusStyles } from './TicketCard';
import {
  AlertTriangle,
  User,
  Shield,
  ArrowUpRight,
  Link as LinkIcon,
} from 'lucide-react';
import Link from 'next/link';
import { Ticket, EscalationLevel } from '@/types';
import { updateTicket } from '@/lib/data-service';
import { toast } from 'sonner';

interface TicketSidebarProps {
  ticket: Ticket;
  userRole?: string;
  isUpdating: boolean;
  onTicketUpdate: (ticket: Ticket) => void;
  onUpdatingChange: (updating: boolean) => void;
}

export function TicketSidebar({
  ticket,
  userRole,
  isUpdating,
  onTicketUpdate,
  onUpdatingChange,
}: TicketSidebarProps) {
  const priorityStyles = getPriorityStyles(ticket.priority);
  const statusStyles = getStatusStyles(ticket.status);

  const toggleAutoEscalation = async (enabled: boolean) => {
    onUpdatingChange(true);
    try {
      const updated = await updateTicket(ticket.id, { isAutoEscalationEnabled: enabled });
      onTicketUpdate(updated);
      if (!enabled) {
        toast.success('Auto-escalation disabled for this ticket');
      } else {
        toast.success('Auto-escalation enabled');
      }
    } catch (error) {
      toast.error('Failed to update auto-escalation');
    } finally {
      onUpdatingChange(false);
    }
  };

  return (
    <div className="space-y-4">
      {/* Ticket Info */}
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-sm font-semibold">Ticket Details</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-xs text-muted-foreground">Ticket ID</span>
              <span className="text-xs font-mono text-foreground">{ticket.id.toUpperCase()}</span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-xs text-muted-foreground">Priority</span>
              <Badge className={`${priorityStyles?.badge || ''} text-xs uppercase border`}>{ticket.priority}</Badge>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-xs text-muted-foreground">Status</span>
              <Badge className={`${statusStyles} text-xs capitalize`}>{ticket.status.replace('_', ' ')}</Badge>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-xs text-muted-foreground">Escalation</span>
              <EscalationBadge level={ticket.escalationLevel as EscalationLevel} />
            </div>

            <div className="border-t border-border pt-3 space-y-3">
            {(userRole === 'admin' || userRole === 'manager') && (
              <div className="flex items-center justify-between">
                <div className="space-y-0.5">
                  <Label htmlFor="auto-escalate" className="text-xs text-muted-foreground">Auto-Escalation</Label>
                </div>
                <Switch
                  id="auto-escalate"
                  checked={ticket.isAutoEscalationEnabled ?? true}
                  onCheckedChange={toggleAutoEscalation}
                  disabled={isUpdating}
                />
              </div>
            )}

              <div>
                <span className="text-xs text-muted-foreground block mb-1">Assigned To</span>
                <div className="flex items-center gap-1.5">
                  <User className="h-3.5 w-3.5 text-muted-foreground" />
                  <span className="text-sm font-medium text-foreground">{ticket.assignedToName || ticket.assignedToId}</span>
                </div>
                <span className="text-xs text-muted-foreground ml-5">{ticket.assignedToRole}</span>
              </div>

              <div>
                <span className="text-xs text-muted-foreground block mb-1">Created By</span>
                <div className="flex items-center gap-1.5">
                  <User className="h-3.5 w-3.5 text-muted-foreground" />
                  <span className="text-sm text-foreground">{ticket.creatorName || ticket.createdBy}</span>
                </div>
              </div>
            </div>

            <div className="border-t border-border pt-3 space-y-2">
              <div className="flex items-center justify-between">
                <span className="text-xs text-muted-foreground">Created</span>
                <span className="text-xs text-foreground">
                  {new Date(ticket.createdAt || ticket.created_at || '').toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })}
                </span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-xs text-muted-foreground">Updated</span>
                <span className="text-xs text-foreground">
                  {new Date(ticket.updatedAt || ticket.updated_at || '').toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })}
                </span>
              </div>
              {ticket.resolvedAt && (
                <div className="flex items-center justify-between">
                  <span className="text-xs text-muted-foreground">Resolved</span>
                  <span className="text-xs text-emerald-600 dark:text-emerald-400">
                    {new Date(ticket.resolvedAt).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })}
                  </span>
                </div>
              )}
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Related Risk */}
      {ticket.relatedRiskId && (
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-sm font-semibold flex items-center gap-2">
              <AlertTriangle className="h-4 w-4 text-muted-foreground" />
              Related Risk
            </CardTitle>
          </CardHeader>
          <CardContent>
            <Link
              href={`/dashboard/risks/${ticket.relatedRiskId}`}
              className="flex items-center gap-2 bg-muted/50 hover:bg-muted rounded-lg p-3 transition-colors group"
            >
              <div className="flex-1">
                <p className="text-sm font-medium text-foreground group-hover:text-primary transition-colors line-clamp-1">
                  Risk ID: {ticket.relatedRiskId}
                </p>
                <p className="text-xs text-muted-foreground mt-0.5 flex items-center gap-1">
                  <LinkIcon className="h-3 w-3" />
                  View Impact Analysis
                </p>
              </div>
              <ArrowUpRight className="h-4 w-4 text-muted-foreground group-hover:text-primary transition-colors" />
            </Link>
          </CardContent>
        </Card>
      )}

      {/* Related Entity (non-risk) */}
      {!ticket.relatedRiskId && ticket.relatedEntityType && (
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-sm font-semibold flex items-center gap-2">
              <Shield className="h-4 w-4 text-muted-foreground" />
              Related {ticket.relatedEntityType.charAt(0).toUpperCase() + ticket.relatedEntityType.slice(1)}
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="bg-muted/50 rounded-lg p-3">
              <p className="text-xs text-muted-foreground flex items-center gap-1">
                <LinkIcon className="h-3 w-3" />
                {ticket.relatedEntityType}: {ticket.relatedEntityId}
              </p>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
