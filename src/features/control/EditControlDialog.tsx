'use client';

import { useState, useEffect } from 'react';
import { updateControl } from '@/lib/data-service';
import { toast } from 'sonner';
import type { Control } from '@/types/control';
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

interface EditControlDialogProps {
    open: boolean;
    onOpenChange: (open: boolean) => void;
    control: Control;
    onSuccess: () => void;
}

export function EditControlDialog({ open, onOpenChange, control, onSuccess }: EditControlDialogProps) {
    const [title, setTitle] = useState(control.title);
    const [description, setDescription] = useState(control.description);
    const [controlType, setControlType] = useState(control.controlType);
    const [effectiveness, setEffectiveness] = useState(control.effectiveness);
    const [status, setStatus] = useState<string>(control.status);
    const [submitting, setSubmitting] = useState(false);

    useEffect(() => {
        if (open && control) {
            setTitle(control.title);
            setDescription(control.description);
            setControlType(control.controlType);
            setEffectiveness(control.effectiveness);
            setStatus(control.status);
        }
    }, [open, control]);

    const handleSubmit = async () => {
        if (!title.trim() || !description.trim()) {
            toast.error('Title and description are required.');
            return;
        }

        setSubmitting(true);
        try {
            await updateControl(control.id, {
                title: title.trim(),
                description: description.trim(),
                control_type: controlType,
                effectiveness,
                status,
            } as any);

            toast.success('Control updated successfully!');
            onSuccess();
            onOpenChange(false);
        } catch (err: any) {
            toast.error(err?.message || 'Failed to update control.');
        } finally {
            setSubmitting(false);
        }
    };

    return (
        <Dialog open={open} onOpenChange={onOpenChange}>
            <DialogContent className="sm:max-w-[500px] max-h-[90vh] overflow-y-auto">
                <DialogHeader>
                    <DialogTitle>Edit Control</DialogTitle>
                    <DialogDescription>
                        Update the details of this control.
                    </DialogDescription>
                </DialogHeader>

                <div className="grid gap-4 py-4">
                    <div className="space-y-2">
                        <Label htmlFor="edit-ctrl-title">Title *</Label>
                        <Input
                            id="edit-ctrl-title"
                            value={title}
                            onChange={(e) => setTitle(e.target.value)}
                        />
                    </div>

                    <div className="space-y-2">
                        <Label htmlFor="edit-ctrl-desc">Description *</Label>
                        <Textarea
                            id="edit-ctrl-desc"
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
                                <SelectItem value="preventive">Preventive</SelectItem>
                                <SelectItem value="detective">Detective</SelectItem>
                                <SelectItem value="corrective">Corrective</SelectItem>
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
                            <Label>Status</Label>
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
                                Saving...
                            </>
                        ) : (
                            'Save Changes'
                        )}
                    </Button>
                </div>
            </DialogContent>
        </Dialog>
    );
}
