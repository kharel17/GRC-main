'use client';

import { useState } from 'react';
import { Button } from '@/components/ui/button';
import {
  FileText,
  CheckCircle2,
  ChevronUp,
} from 'lucide-react';
import { Ticket } from '@/types';
import { escalateTicket, resolveTicket, requestEvidence } from '@/lib/data-service';
import { toast } from 'sonner';

interface TicketActionsProps {
  ticket: Ticket;
  canAct: boolean;
  userRole?: string;
  isUpdating: boolean;
  onTicketUpdate: (ticket: Ticket) => void;
  onUpdatingChange: (updating: boolean) => void;
}

export function TicketActions({
  ticket,
  canAct,
  userRole,
  isUpdating,
  onTicketUpdate,
  onUpdatingChange,
}: TicketActionsProps) {
  const [showResolveNotes, setShowResolveNotes] = useState(false);
  const [resolveNotes, setResolveNotes] = useState('');
  const [showEvidenceRequest, setShowEvidenceRequest] = useState(false);
  const [evidenceRequestComment, setEvidenceRequestComment] = useState('');

  const handleEscalate = async () => {
    if (!ticket.managerId) {
      toast.error('Cannot escalate: No manager assigned to current owner');
      return;
    }
    onUpdatingChange(true);
    try {
      const updated = await escalateTicket(ticket.id, ticket.managerId);
      onTicketUpdate(updated);
      toast.success('Ticket escalated successfully to manager');
    } catch (error) {
      const errorMsg = (error as any)?.response?.data?.detail || 'Failed to escalate ticket';
      toast.error(errorMsg);
    } finally {
      onUpdatingChange(false);
    }
  };

  const handleResolve = async () => {
    if (!resolveNotes.trim()) {
      toast.error('Resolution notes are required');
      return;
    }
    onUpdatingChange(true);
    try {
      const updated = await resolveTicket(ticket.id, resolveNotes);
      onTicketUpdate(updated);
      setShowResolveNotes(false);
      toast.success('Ticket resolved successfully');
    } catch (error) {
      toast.error('Failed to resolve ticket');
    } finally {
      onUpdatingChange(false);
    }
  };

  const handleRequestEvidence = async () => {
    if (!evidenceRequestComment.trim()) {
      toast.error('Reason for evidence request is required');
      return;
    }
    onUpdatingChange(true);
    try {
      const updated = await requestEvidence(ticket.id, evidenceRequestComment);
      onTicketUpdate(updated);
      setShowEvidenceRequest(false);
      setEvidenceRequestComment('');
      toast.success('Evidence request sent');
    } catch (error) {
      toast.error('Failed to request evidence');
    } finally {
      onUpdatingChange(false);
    }
  };

  if (!canAct || ticket.status === 'closed' || ticket.status === 'resolved') {
    return null;
  }

  if (showEvidenceRequest) {
    return (
      <div className="flex gap-2 items-center bg-blue-50/50 p-2 rounded-lg border border-blue-100">
        <input
          type="text"
          placeholder="Why is evidence needed?..."
          className="text-sm px-3 py-1.5 rounded-md border border-border bg-background min-w-[250px]"
          value={evidenceRequestComment}
          onChange={(e) => setEvidenceRequestComment(e.target.value)}
          autoFocus
        />
        <Button size="sm" onClick={handleRequestEvidence} disabled={isUpdating || !evidenceRequestComment.trim()}>
          Send Request
        </Button>
        <Button size="sm" variant="ghost" onClick={() => setShowEvidenceRequest(false)} disabled={isUpdating}>
          Cancel
        </Button>
      </div>
    );
  }

  if (showResolveNotes) {
    return (
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
    );
  }

  return (
    <div className="flex flex-wrap gap-2 flex-shrink-0">
      {(userRole === 'admin' || userRole === 'manager') && (
        <Button
          size="sm"
          variant="outline"
          className="gap-1.5 text-blue-600 border-blue-200 hover:bg-blue-50 dark:hover:bg-blue-900/20"
          onClick={() => setShowEvidenceRequest(true)}
        >
          <FileText className="h-4 w-4" />
          Request Evidence
        </Button>
      )}
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
    </div>
  );
}
