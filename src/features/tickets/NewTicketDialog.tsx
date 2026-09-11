'use client';

import { useState } from 'react';
import { createTicket, fetchUsers } from '@/lib/data-service';
import { useAuth, useApiData } from '@/hooks';
import { toast } from 'sonner';
import { handleApiError } from '@/lib/handle-api-error';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { Label } from '@/components/ui/label';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Loader2, Ticket as TicketIcon } from 'lucide-react';
import { TicketPriority } from '@/types';

interface NewTicketDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSuccess: () => void;
}

export function NewTicketDialog({ open, onOpenChange, onSuccess }: NewTicketDialogProps) {
  const { user } = useAuth();
  const { data: users, loading: loadingUsers } = useApiData(fetchUsers);

  const [title, setTitle] = useState('');
  const [description, setDescription] = useState('');
  const [priority, setPriority] = useState<TicketPriority>('medium');
  const [assignedToId, setAssignedToId] = useState<string>('');
  const [dueDate, setDueDate] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [errors, setErrors] = useState<Record<string, string>>({});

  const resetForm = () => {
    setTitle('');
    setDescription('');
    setPriority('medium');
    setAssignedToId('');
    setDueDate('');
    setErrors({});
  };

  const handleClose = (newOpen: boolean) => {
    if (!newOpen) {
      resetForm();
    }
    onOpenChange(newOpen);
  };

  const validateForm = () => {
    const newErrors: Record<string, string> = {};

    if (!title.trim()) {
      newErrors.title = 'Title is required.';
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (submitting) return;

    if (!validateForm()) {
      toast.error('Please fill in all required fields.');
      return;
    }

    setSubmitting(true);
    try {
      const payload: any = {
        title: title.trim(),
        description: description.trim(),
        priority,
      };

      if (assignedToId && assignedToId !== 'unassigned') {
        payload.assigned_to_id = assignedToId;
        payload.assignedToId = assignedToId;
      }

      if (dueDate) {
        payload.due_date = new Date(dueDate).toISOString();
        payload.dueDate = payload.due_date;
      }

      await createTicket(payload);
      toast.success('Ticket created successfully');
      resetForm();
      onOpenChange(false);
      onSuccess();
    } catch (err: any) {
      toast.error(handleApiError(err) || 'Failed to create ticket');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={handleClose}>
      <DialogContent className="sm:max-w-[540px]">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2 text-xl font-semibold">
            <TicketIcon className="h-5 w-5 text-indigo-600" />
            Create Remediation Ticket
          </DialogTitle>
          <DialogDescription>
            Log an issue, security finding, or action item for escalation and tracking.
          </DialogDescription>
        </DialogHeader>

        <form onSubmit={handleSubmit} className="space-y-4 py-2">
          {/* Title */}
          <div className="space-y-1.5">
            <Label htmlFor="ticket-title" className="text-sm font-medium">
              Title <span className="text-red-500">*</span>
            </Label>
            <Input
              id="ticket-title"
              placeholder="e.g., Remediate open SSH port on production bastion"
              value={title}
              onChange={(e) => {
                setTitle(e.target.value);
                if (errors.title) setErrors((prev) => ({ ...prev, title: '' }));
              }}
              className={errors.title ? 'border-red-500' : ''}
              disabled={submitting}
              autoFocus
            />
            {errors.title && <p className="text-xs text-red-500">{errors.title}</p>}
          </div>

          {/* Description */}
          <div className="space-y-1.5">
            <Label htmlFor="ticket-description" className="text-sm font-medium">
              Description
            </Label>
            <Textarea
              id="ticket-description"
              placeholder="Provide background context, reproduction steps, or compliance requirement details..."
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              rows={3}
              disabled={submitting}
            />
          </div>

          {/* Priority & Assignee Grid */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            {/* Priority */}
            <div className="space-y-1.5">
              <Label htmlFor="ticket-priority" className="text-sm font-medium">
                Priority
              </Label>
              <Select
                value={priority}
                onValueChange={(val: TicketPriority) => setPriority(val)}
                disabled={submitting}
              >
                <SelectTrigger id="ticket-priority">
                  <SelectValue placeholder="Select priority" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="low">Low (Routine)</SelectItem>
                  <SelectItem value="medium">Medium (Standard)</SelectItem>
                  <SelectItem value="high">High (Urgent)</SelectItem>
                  <SelectItem value="critical">Critical (Immediate)</SelectItem>
                </SelectContent>
              </Select>
            </div>

            {/* Assignee */}
            <div className="space-y-1.5">
              <Label htmlFor="ticket-assignee" className="text-sm font-medium">
                Assignee
              </Label>
              <Select
                value={assignedToId}
                onValueChange={setAssignedToId}
                disabled={submitting || loadingUsers}
              >
                <SelectTrigger id="ticket-assignee">
                  <SelectValue placeholder={loadingUsers ? "Loading users..." : "Select assignee"} />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="unassigned">Unassigned (Self)</SelectItem>
                  {users?.map((u: any) => (
                    <SelectItem key={u.id} value={u.id}>
                      {u.full_name || u.email} ({u.role})
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>

          {/* Due Date */}
          <div className="space-y-1.5">
            <Label htmlFor="ticket-due-date" className="text-sm font-medium">
              Due Date
            </Label>
            <Input
              id="ticket-due-date"
              type="date"
              value={dueDate}
              onChange={(e) => setDueDate(e.target.value)}
              disabled={submitting}
            />
            <p className="text-[11px] text-muted-foreground">
              Leave blank to automatically calculate based on SLA policy.
            </p>
          </div>

          <DialogFooter className="pt-2">
            <Button
              type="button"
              variant="outline"
              onClick={() => handleClose(false)}
              disabled={submitting}
            >
              Cancel
            </Button>
            <Button type="submit" disabled={submitting} className="gap-2">
              {submitting && <Loader2 className="h-4 w-4 animate-spin" />}
              Create Ticket
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
