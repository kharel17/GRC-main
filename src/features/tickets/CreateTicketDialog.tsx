'use client';

import { useState } from 'react';
import { useAuth } from '@/hooks/useAuth';
import { Button } from '@/components/ui/button';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { TicketPriority, TicketCategory } from '@/types/ticket';
import { useApiData } from '@/hooks/use-api-data';
import { fetchUsers } from '@/lib/data-service';

interface CreateTicketDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSubmit: (data: any) => Promise<void>;
}

export function CreateTicketDialog({ open, onOpenChange, onSubmit }: CreateTicketDialogProps) {
  const { user } = useAuth();
  const { data: users, loading: usersLoading } = useApiData(fetchUsers);
  
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [formData, setFormData] = useState({
    title: '',
    description: '',
    priority: 'medium' as TicketPriority,
    category: 'risk_identified' as TicketCategory,
    assignedToId: '', // Default down below based on role
  });

  const isAdmin = user?.role === 'admin';

  const resetForm = () => {
    setFormData({
      title: '',
      description: '',
      priority: 'medium',
      category: 'risk_identified',
      assignedToId: '',
    });
  };

  const handleOpenChange = (newOpen: boolean) => {
    if (!newOpen) resetForm();
    onOpenChange(newOpen);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!user) return;
    
    setIsSubmitting(true);
    
    try {
      // If admin and they selected someone, use that. Otherwise assign to self (lowest tier)
      let ownerId = user.id;
      let assignedToName = user.email;
      let assignedToRole = user.role;
      
      if (isAdmin && formData.assignedToId && users) {
        const selectedUser = users.find(u => u.id === formData.assignedToId);
        if (selectedUser) {
          ownerId = selectedUser.id;
          assignedToName = selectedUser.fullName;
          assignedToRole = selectedUser.role;
        }
      }

      await onSubmit({
        ...formData,
        ownerUserId: ownerId,
        assignedTo: assignedToName,
        assignedToRole: assignedToRole,
        createdBy: user.id,
        createdByName: user.email,
        escalationLevel: 1, // Start at level 1
      });
      
      handleOpenChange(false);
    } catch (error) {
      console.error('Failed to create ticket', error);
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogContent className="sm:max-w-[550px]">
        <form onSubmit={handleSubmit}>
          <DialogHeader>
            <DialogTitle>Raise a Ticket</DialogTitle>
            <DialogDescription>
              Create a new GRC ticket. By default, you will be assigned as the ticket owner.
            </DialogDescription>
          </DialogHeader>
          <div className="grid gap-4 py-4">
            <div className="space-y-2">
              <Label htmlFor="title">Title <span className="text-red-500">*</span></Label>
              <Input
                id="title"
                placeholder="Brief summary of the issue..."
                value={formData.title}
                onChange={(e) => setFormData({ ...formData, title: e.target.value })}
                required
              />
            </div>
            
            <div className="space-y-2">
              <Label htmlFor="description">Description <span className="text-red-500">*</span></Label>
              <Textarea
                id="description"
                placeholder="Detailed explanation, including relevant context or next steps..."
                value={formData.description}
                onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                required
                rows={4}
              />
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor="priority">Priority</Label>
                <Select
                  value={formData.priority}
                  onValueChange={(value: TicketPriority) => setFormData({ ...formData, priority: value })}
                >
                  <SelectTrigger id="priority">
                    <SelectValue placeholder="Select priority" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="low">Low</SelectItem>
                    <SelectItem value="medium">Medium</SelectItem>
                    <SelectItem value="high">High</SelectItem>
                    <SelectItem value="critical">Critical</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              
              <div className="space-y-2">
                <Label htmlFor="category">Category</Label>
                <Select
                  value={formData.category}
                  onValueChange={(value: TicketCategory) => setFormData({ ...formData, category: value })}
                >
                  <SelectTrigger id="category">
                    <SelectValue placeholder="Select category" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="risk_identified">Risk Identified</SelectItem>
                    <SelectItem value="risk_mitigated">Risk Mitigated</SelectItem>
                    <SelectItem value="compliance_gap">Compliance Gap</SelectItem>
                    <SelectItem value="security_incident">Security Incident</SelectItem>
                    <SelectItem value="audit_finding">Audit Finding</SelectItem>
                    <SelectItem value="policy_violation">Policy Violation</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>

            {isAdmin && !usersLoading && users && (
              <div className="space-y-2 mt-2 pt-4 border-t border-border">
                <Label htmlFor="assignee" className="flex items-center gap-2">
                  Assign To <span className="text-xs text-muted-foreground font-normal">(Admin Only)</span>
                </Label>
                <Select
                  value={formData.assignedToId}
                  onValueChange={(value) => setFormData({ ...formData, assignedToId: value })}
                >
                  <SelectTrigger id="assignee">
                    <SelectValue placeholder="Select assignee (Default: Self)" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="self" className="italic font-medium text-primary">-- Assign to Self --</SelectItem>
                    {users.map(u => (
                      <SelectItem key={u.id} value={u.id}>
                        {u.fullName} ({u.role.replace('_', ' ')})
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
                <p className="text-xs text-muted-foreground">
                  As an admin, you can assign this ticket to someone else immediately. 
                  Otherwise, it will be assigned to you as the creator.
                </p>
              </div>
            )}
          </div>
          <DialogFooter>
            <Button
              type="button"
              variant="outline"
              onClick={() => handleOpenChange(false)}
              disabled={isSubmitting}
            >
              Cancel
            </Button>
            <Button type="submit" disabled={isSubmitting || !formData.title.trim() || !formData.description.trim()}>
              {isSubmitting ? 'Raising Ticket...' : 'Raise Ticket'}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
