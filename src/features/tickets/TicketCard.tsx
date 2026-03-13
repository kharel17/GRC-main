'use client';

import Link from 'next/link';
import { Card, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { EscalationBadge } from './EscalationBadge';
import { Ticket, TicketPriority, TicketStatus } from '@/types/ticket';
import {
  ArrowUpRight,
  Clock,
  User,
  AlertTriangle,
  MessageSquare,
} from 'lucide-react';

// Priority styles
export function getPriorityStyles(priority: TicketPriority) {
  switch (priority) {
    case 'critical':
      return {
        badge: 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-300 border-red-200',
        dot: 'bg-red-500',
        border: 'border-l-red-500',
      };
    case 'high':
      return {
        badge: 'bg-orange-100 text-orange-700 dark:bg-orange-900/30 dark:text-orange-300 border-orange-200',
        dot: 'bg-orange-500',
        border: 'border-l-orange-500',
      };
    case 'medium':
      return {
        badge: 'bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-300 border-amber-200',
        dot: 'bg-amber-500',
        border: 'border-l-amber-500',
      };
    case 'low':
      return {
        badge: 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-300 border-green-200',
        dot: 'bg-green-500',
        border: 'border-l-green-500',
      };
  }
}

// Status styles
export function getStatusStyles(status: TicketStatus) {
  switch (status) {
    case 'open':
      return 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300';
    case 'in_review':
    case 'pending_evidence':
    case 'pending_l2_review':
    case 'pending_l1_signoff':
      return 'bg-indigo-100 text-indigo-700 dark:bg-indigo-900/30 dark:text-indigo-300';
    case 'escalated':
    case 'overdue':
      return 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-300';
    case 'resolved':
      return 'bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-300';
    case 'closed':
    case 'archived':
    case 'rejected':
      return 'bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-400';
    default:
      return 'bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-400';
  }
}

// Category display labels
export function getCategoryLabel(category: string) {
  const labels: Record<string, string> = {
    risk_identified: 'Risk Identified',
    risk_mitigated: 'Risk Mitigated',
    compliance_gap: 'Compliance Gap',
    security_incident: 'Security Incident',
    audit_finding: 'Audit Finding',
    policy_violation: 'Policy Violation',
  };
  return labels[category] || category;
}

function getTimeAgo(timestamp: string) {
  const now = new Date();
  const date = new Date(timestamp);
  const diffMs = now.getTime() - date.getTime();
  const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));
  if (diffDays === 0) return 'Today';
  if (diffDays === 1) return 'Yesterday';
  if (diffDays < 7) return `${diffDays}d ago`;
  if (diffDays < 30) return `${Math.floor(diffDays / 7)}w ago`;
  return `${Math.floor(diffDays / 30)}mo ago`;
}

interface TicketCardProps {
  ticket: Ticket;
}

export function TicketCard({ ticket }: TicketCardProps) {
  const priorityStyles = getPriorityStyles(ticket.priority);
  const statusStyles = getStatusStyles(ticket.status);

  return (
    <Link href={`/dashboard/tickets/${ticket.id}`}>
      <Card className={`h-full border-l-4 ${priorityStyles.border} hover:shadow-lg transition-all duration-200 cursor-pointer group`}>
        <CardContent className="pt-5 pb-4 space-y-3">
          {/* Header: Priority + Status */}
          <div className="flex items-start justify-between gap-2">
            <div className="flex flex-wrap gap-1.5">
              <Badge className={`${priorityStyles.badge} text-xs font-semibold uppercase border`}>
                {ticket.priority}
              </Badge>
              <Badge className={`${statusStyles} text-xs capitalize`}>
                {ticket.status.replace('_', ' ')}
              </Badge>
            </div>
            <ArrowUpRight className="h-4 w-4 text-muted-foreground opacity-0 group-hover:opacity-100 transition-opacity flex-shrink-0" />
          </div>

          {/* Title */}
          <h3 className="font-semibold text-sm text-foreground group-hover:text-primary transition-colors line-clamp-2 leading-snug">
            {ticket.title}
          </h3>

          {/* Description */}
          <p className="text-xs text-muted-foreground line-clamp-2 leading-relaxed">
            {ticket.description}
          </p>

          {/* Category + Escalation */}
          <div className="flex flex-wrap gap-1.5">
            <Badge variant="outline" className="text-xs">
              {getCategoryLabel(ticket.category)}
            </Badge>
            <EscalationBadge level={ticket.escalationLevel} />
          </div>

          {/* Footer: Assignee, Time, Comments */}
          <div className="flex items-center justify-between text-xs text-muted-foreground pt-2 border-t border-border">
            <div className="flex items-center gap-1.5">
              <User className="h-3.5 w-3.5" />
              <span className="truncate max-w-[120px]">{ticket.assignedToName}</span>
            </div>
            <div className="flex items-center gap-3">
              {ticket.comments.length > 0 && (
                <div className="flex items-center gap-1">
                  <MessageSquare className="h-3.5 w-3.5" />
                  <span>{ticket.comments.length}</span>
                </div>
              )}
              <div className="flex items-center gap-1">
                <Clock className="h-3.5 w-3.5" />
                <span>{getTimeAgo(ticket.createdAt)}</span>
              </div>
            </div>
          </div>

          {/* Escalation info */}
          {ticket.escalatedToName && (
            <div className="flex items-center gap-1.5 text-xs bg-red-50 dark:bg-red-900/20 text-red-700 dark:text-red-300 px-2.5 py-1.5 rounded-md">
              <AlertTriangle className="h-3.5 w-3.5 flex-shrink-0" />
              <span>Escalated to <strong>{ticket.escalatedToName}</strong> ({ticket.escalatedToRole})</span>
            </div>
          )}
        </CardContent>
      </Card>
    </Link>
  );
}
