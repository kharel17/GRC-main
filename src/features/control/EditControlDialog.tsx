'use client';

import { useState, useEffect } from 'react';
import { updateControl, fetchUsers } from '@/lib/data-service';
import { useApiData } from '@/hooks';
import { toast } from 'sonner';
import { handleApiError } from '@/lib/handle-api-error';
import { Control } from '@/types';
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
    const { data: users, loading: loadingUsers } = useApiData(fetchUsers);
    
    const [title, setTitle] = useState(control.title || '');
    const [description, setDescription] = useState(control.description || '');
    const [ownerId, setOwnerId] = useState<string>(control.owner_id || '');
    const [controlType, setControlType] = useState<'preventive' | 'detective' | 'corrective'>((control.type || 'preventive') as any);
    const [effectiveness, setEffectiveness] = useState<'high' | 'medium' | 'low'>((control.effectiveness || 'medium') as any);
    const [status, setStatus] = useState<string>(control.status || 'planned');
    const [submitting, setSubmitting] = useState(false);
    const [errors, setErrors] = useState<Record<string, string>>({});
    const [attempted, setAttempted] = useState(false);

    useEffect(() => {
        if (open && control) {
            setTitle(control.title || '');
            setDescription(control.description || '');
            setOwnerId(control.owner_id || '');
            setControlType((control.type || 'preventive') as any);
            setEffectiveness((control.effectiveness || 'medium') as any);
            setStatus(control.status || 'planned');
            setErrors({});
            setAttempted(false);
        }
    }, [open, control]);

    const validateForm = () => {
        const newErrors: Record<string, string> = {};
        
        if (!title.trim()) {
            newErrors.title = 'Title is required.';
        }
        
        if (!description.trim()) {
            newErrors.description = 'Description is required.';
        } else if (description.trim().length < 10) {
            newErrors.description = 'Description must be at least 10 characters.';
        }

        setErrors(newErrors);
        return Object.keys(newErrors).length === 0;
    };

    const handleSubmit = async () => {
        setAttempted(true);
        if (!validateForm()) return;

        setSubmitting(true);
        try {
            await updateControl(control.id, {
                title: title.trim(),
                description: description.trim(),
                control_type: controlType,
                effectiveness,
                status,
                owner_id: ownerId,
            } as any);

            toast.success('Control updated successfully!');
            onSuccess();
            onOpenChange(false);
        } catch (err: unknown) {
            toast.error(handleApiError(err));
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
                        <Label htmlFor="edit-ctrl-title" className={errors.title && attempted ? "text-red-500" : ""}>Title *</Label>
                        <Input
                            id="edit-ctrl-title"
                            value={title}
                            onChange={(e) => {
                                setTitle(e.target.value);
                                if (attempted) validateForm();
                            }}
                            className={errors.title && attempted ? "border-red-500 focus-visible:ring-red-500" : ""}
                        />
                        {attempted && errors.title && <p className="text-xs text-red-500">{errors.title}</p>}
                    </div>

                    <div className="space-y-2">
                        <Label htmlFor="edit-ctrl-desc" className={errors.description && attempted ? "text-red-500" : ""}>Description *</Label>
                        <Textarea
                            id="edit-ctrl-desc"
                            value={description}
                            onChange={(e) => {
                                setDescription(e.target.value);
                                if (attempted) validateForm();
                            }}
                            rows={3}
                            className={errors.description && attempted ? "border-red-500 focus-visible:ring-red-500" : ""}
                        />
                        {attempted && errors.description && <p className="text-xs text-red-500">{errors.description}</p>}
                        <div className="flex justify-between mt-1">
                            {attempted && errors.description ? (
                                <p className="text-xs text-red-500">{errors.description}</p>
                            ) : (
                                <span />
                            )}
                            <p className="text-xs text-muted-foreground">{description.length} chars</p>
                        </div>
                    </div>

                    <div className="space-y-2">
                        <Label>Assigned Owner *</Label>
                        <Select value={ownerId} onValueChange={setOwnerId}>
                            <SelectTrigger>
                                <SelectValue placeholder={loadingUsers ? "Loading users..." : "Select owner..."} />
                            </SelectTrigger>
                            <SelectContent>
                                {users?.filter(u => ['admin', 'manager', 'analyst'].includes(u.role)).map((u) => (
                                    <SelectItem key={u.id} value={u.id}>
                                        <div className="flex flex-col">
                                            <span className="text-sm font-medium">{u.full_name || u.email}</span>
                                            <span className="text-[10px] text-muted-foreground uppercase">{u.role}</span>
                                        </div>
                                    </SelectItem>
                                ))}
                            </SelectContent>
                        </Select>
                    </div>

                    <div className="space-y-2">
                        <Label>Control Type</Label>
                        <Select value={controlType} onValueChange={(val: 'preventive' | 'detective' | 'corrective') => setControlType(val)}>
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
                            <Select value={effectiveness} onValueChange={(val: 'high' | 'medium' | 'low') => setEffectiveness(val)}>
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
