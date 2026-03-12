'use client';

import { useState } from 'react';
import { createControl } from '@/lib/data-service';
import { useAuth } from '@/hooks/useAuth';
import { toast } from 'sonner';
import {
    Dialog,
    DialogContent,
    DialogDescription,
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
import { Loader2 } from 'lucide-react';

interface NewControlDialogProps {
    open: boolean;
    onOpenChange: (open: boolean) => void;
    onSuccess: () => void;
}

export function NewControlDialog({ open, onOpenChange, onSuccess }: NewControlDialogProps) {
    const { user } = useAuth();

    const [title, setTitle] = useState('');
    const [description, setDescription] = useState('');
    const [controlType, setControlType] = useState('preventive');
    const [effectiveness, setEffectiveness] = useState('medium');
    const [status, setStatus] = useState('planned');
    const [submitting, setSubmitting] = useState(false);

    const resetForm = () => {
        setTitle('');
        setDescription('');
        setControlType('preventive');
        setEffectiveness('medium');
        setStatus('planned');
    };

    const handleSubmit = async () => {
        if (!title.trim() || !description.trim()) {
            toast.error('Please fill in title and description.');
            return;
        }

        setSubmitting(true);
        try {
            await createControl({
                title: title.trim(),
                description: description.trim(),
                control_type: controlType,
                effectiveness,
                status,
                owner_id: user?.id,
            } as any);

            toast.success('Control created successfully!');
            resetForm();
            onSuccess();
            onOpenChange(false);
        } catch (err: any) {
            toast.error(err?.message || 'Failed to create control.');
        } finally {
            setSubmitting(false);
        }
    };

    return (
        <Dialog open={open} onOpenChange={onOpenChange}>
            <DialogContent className="sm:max-w-[500px] max-h-[90vh] overflow-y-auto">
                <DialogHeader>
                    <DialogTitle>Create New Control</DialogTitle>
                    <DialogDescription>
                        Define a new risk mitigation control for your organization.
                    </DialogDescription>
                </DialogHeader>

                <div className="grid gap-4 py-4">
                    <div className="space-y-2">
                        <Label htmlFor="ctrl-title">Title *</Label>
                        <Input
                            id="ctrl-title"
                            placeholder="e.g. Multi-Factor Authentication"
                            value={title}
                            onChange={(e) => setTitle(e.target.value)}
                        />
                    </div>

                    <div className="space-y-2">
                        <Label htmlFor="ctrl-desc">Description *</Label>
                        <Textarea
                            id="ctrl-desc"
                            placeholder="Describe the control and how it mitigates risk..."
                            value={description}
                            onChange={(e) => setDescription(e.target.value)}
                            rows={3}
                        />
                    </div>

                    <div className="space-y-2">
                        <Label>Control Type</Label>
                        <Select value={controlType} onValueChange={setControlType}>
                            <SelectTrigger>
                                <SelectValue />
                            </SelectTrigger>
                            <SelectContent>
                                <SelectItem value="preventive">
                                    Preventive — Stops risks before they occur
                                </SelectItem>
                                <SelectItem value="detective">
                                    Detective — Identifies risks when they happen
                                </SelectItem>
                                <SelectItem value="corrective">
                                    Corrective — Addresses risks after they occur
                                </SelectItem>
                            </SelectContent>
                        </Select>
                    </div>

                    <div className="grid grid-cols-2 gap-4">
                        <div className="space-y-2">
                            <Label>Effectiveness</Label>
                            <Select value={effectiveness} onValueChange={setEffectiveness}>
                                <SelectTrigger>
                                    <SelectValue />
                                </SelectTrigger>
                                <SelectContent>
                                    <SelectItem value="high">High</SelectItem>
                                    <SelectItem value="medium">Medium</SelectItem>
                                    <SelectItem value="low">Low</SelectItem>
                                </SelectContent>
                            </Select>
                        </div>

                        <div className="space-y-2">
                            <Label>Initial Status</Label>
                            <Select value={status} onValueChange={setStatus}>
                                <SelectTrigger>
                                    <SelectValue />
                                </SelectTrigger>
                                <SelectContent>
                                    <SelectItem value="planned">Planned</SelectItem>
                                    <SelectItem value="implemented">Implemented</SelectItem>
                                    <SelectItem value="under_review">Under Review</SelectItem>
                                </SelectContent>
                            </Select>
                        </div>
                    </div>
                </div>

                <div className="flex justify-end gap-3 pt-2">
                    <Button variant="outline" onClick={() => onOpenChange(false)} disabled={submitting}>
                        Cancel
                    </Button>
                    <Button onClick={handleSubmit} disabled={submitting}>
                        {submitting ? (
                            <>
                                <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                                Creating...
                            </>
                        ) : (
                            'Create Control'
                        )}
                    </Button>
                </div>
            </DialogContent>
        </Dialog>
    );
}
