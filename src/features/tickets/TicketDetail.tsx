'use client';

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Switch } from '@/components/ui/switch';
import { Label } from '@/components/ui/label';
import { EscalationBadge } from './EscalationBadge';
import { getPriorityStyles, getStatusStyles, getCategoryLabel } from './TicketCard';
import { useState } from 'react';
import { useAuth } from '@/hooks/useAuth';
import { updateTicket } from '@/lib/data-service';
import { canActOnTicket, isTicketOverdue, getNextEscalationLevel } from '@/lib/ticket-utils';
import { toast } from 'sonner';
import { Ticket, TicketStatus, EscalationHistoryEntry, ActivityLogEntry } from '@/types/ticket';
import { AuditLog } from '@/types/audit';
import {
  ArrowLeft,
  ArrowUpRight,
  AlertTriangle,
  Clock,
  User,
  MessageSquare,
  Shield,
  FileText,
  Activity,
  CheckCircle2,
  XCircle,
  ChevronUp,
  Link as LinkIcon,
} from 'lucide-react';
import Link from 'next/link';

interface TicketDetailProps {
  ticket: Ticket;
  sourceAuditLog?: AuditLog;
}

export function TicketDetail({ ticket: initialTicket, sourceAuditLog }: TicketDetailProps) {
  const { user } = useAuth();
  const [ticket, setTicket] = useState<Ticket>(initialTicket);
  const [isUpdating, setIsUpdating] = useState(false);
  const [showResolveNotes, setShowResolveNotes] = useState(false);
  const [resolveNotes, setResolveNotes] = useState('');

  const priorityStyles = getPriorityStyles(ticket.priority);
  const statusStyles = getStatusStyles(ticket.status);
  
  const canAct = user ? canActOnTicket(ticket, user.id, user.role) : false;
  const isOverdue = isTicketOverdue(ticket);

  const handleEscalate = async () => {
    if (!user) return;
    setIsUpdating(true);
    
    try {
      const nextLevel = getNextEscalationLevel(user.role);
      const newEscalationEntry: EscalationHistoryEntry = {
        escalatedBy: user.id,
        escalatedByRole: user.role,
        escalatedTo: 'Next Tier Queue', // In Step 3, admin will pick this
        escalatedToRole: 'L' + nextLevel,
        level: nextLevel,
        timestamp: new Date().toISOString(),
      };
      
      const newActivityEntry: ActivityLogEntry = {
        action: 'escalated',
        performedBy: user.id,
        performedByRole: user.role,
        timestamp: new Date().toISOString(),
      };

      const updateData = {
        status: 'escalated' as TicketStatus,
        escalationLevel: nextLevel,
        escalationHistory: [...(ticket.escalationHistory || []), newEscalationEntry],
        activityLog: [...(ticket.activityLog || []), newActivityEntry],
        ownerUserId: 'unassigned', // Transfers ownership up
      };

      const updated = await updateTicket(ticket.id, updateData);
      setTicket(updated);
      toast.success('Ticket escalated successfully');
    } catch (error) {
      toast.error('Failed to escalate ticket');
    } finally {
      setIsUpdating(false);
    }
  };

  const handleResolve = async () => {
    if (!user || !resolveNotes.trim()) {
      toast.error('Resolution notes are required');
      return;
    }
    
    setIsUpdating(true);
    try {
      const newActivityEntry: ActivityLogEntry = {
        action: 'resolved',
        performedBy: user.id,
        performedByRole: user.role,
        timestamp: new Date().toISOString(),
        details: resolveNotes,
      };

      const updated = await updateTicket(ticket.id, {
        status: 'resolved',
        resolvedAt: new Date().toISOString(),
        resolutionNotes: resolveNotes,
        activityLog: [...(ticket.activityLog || []), newActivityEntry],
      });
      
      setTicket(updated);
      setShowResolveNotes(false);
      toast.success('Ticket resolved successfully');
    } catch (error) {
      toast.error('Failed to resolve ticket');
    } finally {
      setIsUpdating(false);
    }
  };

  const toggleAutoEscalation = async (enabled: boolean) => {
    setIsUpdating(true);
    try {
      const updated = await updateTicket(ticket.id, { isAutoEscalationEnabled: enabled });
      setTicket(updated);
      toast.success(enabled ? 'Auto-escalation enabled' : 'Auto-escalation disabled');
    } catch (error) {
      toast.error('Failed to update auto-escalation');
    } finally {
      setIsUpdating(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Back Button + Header */}
      <div className="space-y-4">
        <Link
          href="/dashboard/tickets"
          className="inline-flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground transition-colors"
        >
          <ArrowLeft className="h-4 w-4" />
          Back to Tickets
        </Link>

        <div className="flex flex-col lg:flex-row lg:items-start lg:justify-between gap-4">
          <div className="space-y-2 flex-1">
            <div className="flex flex-wrap gap-2">
              <Badge className={`${priorityStyles.badge} text-xs font-semibold uppercase border`}>
                {ticket.priority}
              </Badge>
              <Badge className={`${statusStyles} text-xs capitalize`}>
                {ticket.status.replace('_', ' ')}
              </Badge>
              <Badge variant="outline" className="text-xs">
                {getCategoryLabel(ticket.category)}
              </Badge>
              <EscalationBadge level={ticket.escalationLevel} />
            </div>
            <h1 className="text-xl lg:text-2xl font-bold text-foreground leading-tight">
              {ticket.title}
            </h1>
            <p className="text-sm text-muted-foreground max-w-3xl leading-relaxed">
              {ticket.description}
            </p>
          </div>

          {/* Action Buttons */}
          <div className="flex flex-wrap gap-2 flex-shrink-0">
            {canAct && ticket.status !== 'closed' && ticket.status !== 'resolved' && !showResolveNotes && (
              <>
                <Button
                  size="sm"
                  variant="outline"
                  className="gap-1.5 text-orange-600 border-orange-200 hover:bg-orange-50 dark:hover:bg-orange-900/20"
                  onClick={handleEscalate}
                >
                  <ChevronUp className="h-4 w-4" />
                  Escalate
                </Button>
                <Button 
                  size="sm" 
                  className="gap-1.5 bg-emerald-600 hover:bg-emerald-700 text-white"
                  onClick={() => setShowResolveNotes(true)}
                  disabled={isUpdating}
                >
                  <CheckCircle2 className="h-4 w-4" />
                  Resolve
                </Button>
              </>
            )}
            
            {showResolveNotes && (
              <div className="flex gap-2 items-center bg-muted/50 p-2 rounded-lg border border-border">
                <input
                  type="text"
                  placeholder="Resolution notes..."
                  className="text-sm px-3 py-1.5 rounded-md border border-border bg-background min-w-[200px]"
                  value={resolveNotes}
                  onChange={(e) => setResolveNotes(e.target.value)}
                  autoFocus
                />
                <Button size="sm" onClick={handleResolve} disabled={isUpdating || !resolveNotes.trim()}>
                  Confirm
                </Button>
                <Button size="sm" variant="ghost" onClick={() => setShowResolveNotes(false)} disabled={isUpdating}>
                  Cancel
                </Button>
              </div>
            )}
            
            {canAct && ticket.status === 'resolved' && (
              <Button size="sm" variant="outline" className="gap-1.5">
                <XCircle className="h-4 w-4" />
                Close
              </Button>
            )}
          </div>
        </div>
      </div>

      {/* Detail Cards Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left Column - Main Content */}
        <div className="lg:col-span-2 space-y-6">
          
          {/* Overdue Alert */}
          {isOverdue && ticket.dueDate && (
            <div className="flex items-start gap-3 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-4 shadow-sm animate-pulse-slow">
              <AlertTriangle className="h-5 w-5 text-red-600 flex-shrink-0 mt-0.5" />
              <div>
                <h3 className="font-semibold text-sm text-red-800 dark:text-red-300">
                  SLA Breached: Ticket is Overdue
                </h3>
                <p className="text-xs text-red-700 dark:text-red-400 mt-0.5">
                  Due date was {new Date(ticket.dueDate).toLocaleString()}
                </p>
              </div>
            </div>
          )}
          
          {/* Ownership Lock Alert */}
          {!canAct && user && ticket.status !== 'closed' && ticket.status !== 'resolved' && (
            <div className="flex items-start gap-3 bg-slate-50 dark:bg-slate-900/50 border border-slate-200 dark:border-slate-800 rounded-lg p-4">
              <Shield className="h-5 w-5 text-slate-500 flex-shrink-0 mt-0.5" />
              <div>
                <h3 className="font-semibold text-sm text-slate-700 dark:text-slate-300">
                  Read-Only Mode
                </h3>
                <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
                  This ticket is owned by {ticket.ownerUserId || ticket.assignedTo}. You can view the details and activity, but cannot resolve or escalate it.
                </p>
              </div>
            </div>
          )}

          {/* Escalation Alert */}
          {ticket.escalatedTo && (
            <div className="flex items-start gap-3 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-4">
              <AlertTriangle className="h-5 w-5 text-red-600 dark:text-red-400 flex-shrink-0 mt-0.5" />
              <div>
                <h3 className="font-semibold text-sm text-red-800 dark:text-red-300">
                  Escalated to {ticket.escalatedTo}
                </h3>
                <p className="text-xs text-red-700 dark:text-red-400 mt-0.5">
                  {ticket.escalatedToRole} • Escalated on{' '}
                  {ticket.escalatedAt ? new Date(ticket.escalatedAt).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric', hour: '2-digit', minute: '2-digit' }) : 'N/A'}
                </p>
              </div>
            </div>
          )}

          {/* Source Audit Log */}
          {sourceAuditLog && (
            <Card>
              <CardHeader className="pb-3">
                <CardTitle className="text-sm font-semibold flex items-center gap-2">
                  <Activity className="h-4 w-4 text-muted-foreground" />
                  Source Audit Log
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="bg-muted/50 rounded-lg p-4 space-y-2">
                  <div className="flex items-center justify-between gap-2">
                    <span className="text-sm font-medium text-foreground capitalize">
                      {sourceAuditLog.action} {sourceAuditLog.entityType?.replace('_', ' ')}
                    </span>
                    <time className="text-xs text-muted-foreground">
                      {new Date(sourceAuditLog.timestamp).toLocaleString()}
                    </time>
                  </div>
                  {sourceAuditLog.description && (
                    <p className="text-xs text-muted-foreground">{sourceAuditLog.description}</p>
                  )}
                  <div className="flex flex-wrap gap-2 mt-1">
                    <Badge variant="secondary" className="text-xs">{sourceAuditLog.userName}</Badge>
                    {sourceAuditLog.entityName && (
                      <Badge variant="outline" className="text-xs">{sourceAuditLog.entityName}</Badge>
                    )}
                  </div>
                  {sourceAuditLog.oldValues && sourceAuditLog.newValues && (
                    <div className="mt-3 pt-3 border-t border-border">
                      <p className="text-xs font-medium text-muted-foreground mb-2">Changes:</p>
                      <div className="grid grid-cols-2 gap-2 text-xs">
                        <div className="bg-red-50 dark:bg-red-900/20 rounded p-2">
                          <span className="font-medium text-red-700 dark:text-red-300">Before:</span>
                          <pre className="mt-1 text-red-600 dark:text-red-400 whitespace-pre-wrap">
                            {JSON.stringify(sourceAuditLog.oldValues, null, 2)}
                          </pre>
                        </div>
                        <div className="bg-emerald-50 dark:bg-emerald-900/20 rounded p-2">
                          <span className="font-medium text-emerald-700 dark:text-emerald-300">After:</span>
                          <pre className="mt-1 text-emerald-600 dark:text-emerald-400 whitespace-pre-wrap">
                            {JSON.stringify(sourceAuditLog.newValues, null, 2)}
                          </pre>
                        </div>
                      </div>
                    </div>
                  )}
                </div>
              </CardContent>
            </Card>
          )}

          {/* Escalation Timeline */}
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-sm font-semibold flex items-center gap-2">
                <ArrowUpRight className="h-4 w-4 text-muted-foreground" />
                Escalation Timeline
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="relative">
                <div className="absolute left-4 top-0 bottom-0 w-px bg-border" />
                <div className="space-y-4">
                  {/* Created */}
                  <div className="relative flex gap-3 pl-10">
                    <div className="absolute left-2 p-1.5 rounded-full bg-blue-100 text-blue-600 dark:bg-blue-900/30 dark:text-blue-300">
                      <FileText className="h-3.5 w-3.5" />
                    </div>
                    <div className="bg-muted/50 rounded-lg p-3 flex-1">
                      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-1">
                        <span className="text-sm font-medium text-foreground">Ticket Created</span>
                        <time className="text-xs text-muted-foreground">
                          {new Date(ticket.createdAt).toLocaleString()}
                        </time>
                      </div>
                      <p className="text-xs text-muted-foreground mt-1">
                        Created by {ticket.createdByName} • Assigned to {ticket.assignedTo} ({ticket.assignedToRole})
                      </p>
                    </div>
                  </div>

                  {/* Escalated */}
                  {ticket.escalationHistory?.map((entry, idx) => (
                    <div key={`esc-${idx}`} className="relative flex gap-3 pl-10">
                      <div className="absolute left-2 p-1.5 rounded-full bg-orange-100 text-orange-600 dark:bg-orange-900/30 dark:text-orange-300">
                        <ChevronUp className="h-3.5 w-3.5" />
                      </div>
                      <div className="bg-muted/50 rounded-lg p-3 flex-1 border border-orange-100 dark:border-orange-900/30">
                        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-1">
                          <span className="text-sm font-medium text-foreground">Escalated</span>
                          <time className="text-xs text-muted-foreground">
                            {new Date(entry.timestamp).toLocaleString()}
                          </time>
                        </div>
                        <p className="text-xs text-muted-foreground mt-1 text-orange-700 dark:text-orange-400">
                          Escalated by {entry.escalatedByRole} to Level {entry.level} ({entry.escalatedToRole})
                        </p>
                        {entry.note && (
                          <div className="mt-2 text-xs bg-orange-50 dark:bg-black/20 p-2 rounded">
                            <span className="font-medium">Note:</span> {entry.note}
                          </div>
                        )}
                      </div>
                    </div>
                  ))}

                  {/* Activity Log Entries */}
                  {ticket.activityLog?.map((entry, idx) => {
                    if (entry.action === 'escalated' || entry.action === 'created' || entry.action === 'resolved') {
                      return null; // Handled separately
                    }
                    return (
                      <div key={`act-${idx}`} className="relative flex gap-3 pl-10">
                        <div className="absolute left-2 p-1.5 rounded-full bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-400">
                          <Activity className="h-3.5 w-3.5" />
                        </div>
                        <div className="bg-muted/50 rounded-lg p-3 flex-1">
                          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-1">
                            <span className="text-sm font-medium text-foreground capitalize">
                              Ticket {entry.action}
                            </span>
                            <time className="text-xs text-muted-foreground">
                              {new Date(entry.timestamp).toLocaleString()}
                            </time>
                          </div>
                          <p className="text-xs text-muted-foreground mt-1">
                            By {entry.performedByRole}
                          </p>
                          {entry.details && (
                            <p className="text-xs mt-1 text-slate-600 dark:text-slate-400 italic">
                              &quot;{entry.details}&quot;
                            </p>
                          )}
                        </div>
                      </div>
                    );
                  })}

                  {/* Resolved */}
                  {ticket.resolvedAt && (
                    <div className="relative flex gap-3 pl-10">
                      <div className="absolute left-2 p-1.5 rounded-full bg-emerald-100 text-emerald-600 dark:bg-emerald-900/30 dark:text-emerald-300">
                        <CheckCircle2 className="h-3.5 w-3.5" />
                      </div>
                      <div className="bg-emerald-50/50 dark:bg-emerald-900/10 rounded-lg p-3 flex-1 border border-emerald-100 dark:border-emerald-900/30">
                        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-1">
                          <span className="text-sm font-medium text-emerald-800 dark:text-emerald-300">Resolved</span>
                          <time className="text-xs text-emerald-600/70 dark:text-emerald-400/70">
                            {new Date(ticket.resolvedAt).toLocaleString()}
                          </time>
                        </div>
                        {ticket.resolutionNotes && (
                          <div className="mt-2 text-sm text-emerald-700 dark:text-emerald-400">
                            <strong className="block text-xs uppercase tracking-wider mb-1 opacity-80">Resolution Notes</strong>
                            {ticket.resolutionNotes}
                          </div>
                        )}
                      </div>
                    </div>
                  )}
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Comments */}
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-sm font-semibold flex items-center gap-2">
                <MessageSquare className="h-4 w-4 text-muted-foreground" />
                Comments ({ticket.comments.length})
              </CardTitle>
            </CardHeader>
            <CardContent>
              {ticket.comments.length === 0 ? (
                <div className="text-center py-8">
                  <MessageSquare className="h-10 w-10 text-muted-foreground/30 mx-auto mb-2" />
                  <p className="text-sm text-muted-foreground">No comments yet</p>
                </div>
              ) : (
                <div className="space-y-3">
                  {ticket.comments.map((comment, idx) => (
                    <div key={`comm-${idx}`} className="bg-muted/50 rounded-lg p-4">
                      <div className="flex items-center justify-between gap-2 mb-2">
                        <div className="flex items-center gap-2">
                          <div className="w-7 h-7 rounded-full bg-primary/10 flex items-center justify-center">
                            <span className="text-xs font-semibold text-primary">
                              {comment.authorName.split(' ').map(n => n[0]).join('')}
                            </span>
                          </div>
                          <div>
                            <span className="text-sm font-medium text-foreground">{comment.authorName}</span>
                            <span className="text-xs text-muted-foreground ml-1.5">({comment.authorRole})</span>
                          </div>
                        </div>
                        <time className="text-xs text-muted-foreground">
                          {new Date(comment.timestamp).toLocaleString()}
                        </time>
                      </div>
                      <p className="text-sm text-muted-foreground leading-relaxed pl-9">
                        {comment.text}
                      </p>
                    </div>
                  ))}
                </div>
              )}

              {/* Add Comment (UI only) */}
              {canAct && ticket.status !== 'closed' && (
                <div className="mt-4 pt-4 border-t border-border">
                  <textarea
                    placeholder="Add a comment..."
                    className="w-full rounded-lg border border-border bg-background px-3 py-2 text-sm placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary resize-none"
                    rows={3}
                  />
                  <div className="flex justify-end mt-2">
                    <Button size="sm">Post Comment</Button>
                  </div>
                </div>
              )}
            </CardContent>
          </Card>
        </div>

        {/* Right Column - Sidebar Info */}
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
                  <Badge className={`${priorityStyles.badge} text-xs uppercase border`}>{ticket.priority}</Badge>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-xs text-muted-foreground">Status</span>
                  <Badge className={`${statusStyles} text-xs capitalize`}>{ticket.status.replace('_', ' ')}</Badge>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-xs text-muted-foreground">Escalation</span>
                  <EscalationBadge level={ticket.escalationLevel} />
                </div>

                <div className="border-t border-border pt-3 space-y-3">
                  <div className="flex items-center justify-between">
                    <div className="space-y-0.5">
                      <Label htmlFor="auto-escalate" className="text-xs text-muted-foreground">Auto-Escalation</Label>
                    </div>
                    <Switch
                      id="auto-escalate"
                      defaultChecked={ticket.isAutoEscalationEnabled ?? true}
                      onCheckedChange={toggleAutoEscalation}
                    />
                  </div>

                  <div>
                    <span className="text-xs text-muted-foreground block mb-1">Assigned To</span>
                    <div className="flex items-center gap-1.5">
                      <User className="h-3.5 w-3.5 text-muted-foreground" />
                      <span className="text-sm font-medium text-foreground">{ticket.assignedTo}</span>
                    </div>
                    <span className="text-xs text-muted-foreground ml-5">{ticket.assignedToRole}</span>
                  </div>

                  <div>
                    <span className="text-xs text-muted-foreground block mb-1">Created By</span>
                    <div className="flex items-center gap-1.5">
                      <User className="h-3.5 w-3.5 text-muted-foreground" />
                      <span className="text-sm text-foreground">{ticket.createdByName}</span>
                    </div>
                  </div>
                </div>

                <div className="border-t border-border pt-3 space-y-2">
                  <div className="flex items-center justify-between">
                    <span className="text-xs text-muted-foreground">Created</span>
                    <span className="text-xs text-foreground">
                      {new Date(ticket.createdAt).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })}
                    </span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-xs text-muted-foreground">Updated</span>
                    <span className="text-xs text-foreground">
                      {new Date(ticket.updatedAt).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })}
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
                    <p className="text-sm font-medium text-foreground group-hover:text-primary transition-colors">
                      {ticket.relatedRiskTitle}
                    </p>
                    <p className="text-xs text-muted-foreground mt-0.5 flex items-center gap-1">
                      <LinkIcon className="h-3 w-3" />
                      {ticket.relatedRiskId}
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
      </div>
    </div>
  );
}
