'use client';

import { useState, useEffect } from 'react';
import { updateRisk, fetchRiskCategories, fetchUsers } from '@/lib/data-service';
import { useApiData } from '@/hooks';
import { toast } from 'sonner';
import { handleApiError } from '@/lib/handle-api-error';
import { Risk } from '@/types';
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

interface EditRiskDialogProps {
    open: boolean;
    onOpenChange: (open: boolean) => void;
    risk: Risk;
    onSuccess: () => void;
}

export function EditRiskDialog({ open, onOpenChange, risk, onSuccess }: EditRiskDialogProps) {
    const [categories, setCategories] = useState<any[]>([]);

    const { data: users, loading: loadingUsers } = useApiData(fetchUsers);
    
    const [title, setTitle] = useState(risk.title);
    const [description, setDescription] = useState(risk.description);
    const [categoryId, setCategoryId] = useState(risk.categoryId || risk.category?.id || '');
    const [ownerId, setOwnerId] = useState<string>(risk.owner_id || '');
    const [likelihood, setLikelihood] = useState(String(risk.likelihood));
    const [impact, setImpact] = useState(String(risk.impact));
    const [status, setStatus] = useState<string>(risk.status);
    const [submitting, setSubmitting] = useState(false);
    const [errors, setErrors] = useState<Record<string, string>>({});
    const [attempted, setAttempted] = useState(false);

    useEffect(() => {
        const loadCategories = async () => {
            try {
                const data = await fetchRiskCategories();
                setCategories(data);
            } catch (err) {
                console.error('Failed to load categories:', err);
            }
        };
        loadCategories();
    }, []);

    // Re-sync form when opening with a different risk
    useEffect(() => {
        if (open && risk) {
            setTitle(risk.title);
            setDescription(risk.description);
            setCategoryId(risk.categoryId || risk.category?.id || '');
            setOwnerId(risk.owner_id || '');
            setLikelihood(String(risk.likelihood));
            setImpact(String(risk.impact));
            setStatus(risk.status);
            setErrors({});
            setAttempted(false);
        }
    }, [open, risk]);

    const riskScore = parseInt(likelihood) * parseInt(impact);

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
        
        if (!categoryId) {
            newErrors.category = 'Please select a category.';
        }

        setErrors(newErrors);
        return Object.keys(newErrors).length === 0;
    };

    const handleSubmit = async () => {
        setAttempted(true);
        if (!validateForm()) return;

        setSubmitting(true);
        try {
            await updateRisk(risk.id, {
                title: title.trim(),
                description: description.trim(),
                category_id: categoryId,
                likelihood: parseInt(likelihood),
                impact: parseInt(impact),
                risk_score: riskScore,
                status,
                owner_id: ownerId,
            } as any);

            toast.success('Risk updated successfully!');
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
            <DialogContent className="sm:max-w-[520px] max-h-[90vh] overflow-y-auto">
                <DialogHeader>
                    <DialogTitle>Edit Risk</DialogTitle>
                    <DialogDescription>
                        Update the details of this risk assessment.
                    </DialogDescription>
                </DialogHeader>

                <div className="grid gap-4 py-4">
                    <div className="space-y-2">
                        <Label htmlFor="edit-risk-title" className={errors.title && attempted ? "text-red-500" : ""}>Title *</Label>
                        <Input
                            id="edit-risk-title"
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
                        <Label htmlFor="edit-risk-desc" className={errors.description && attempted ? "text-red-500" : ""}>Description *</Label>
                        <Textarea
                            id="edit-risk-desc"
                            value={description}
                            onChange={(e) => {
                                setDescription(e.target.value);
                                if (attempted) validateForm();
                            }}
                            rows={3}
                            className={errors.description && attempted ? "border-red-500 focus-visible:ring-red-500" : ""}
                        />
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
                        <Label className={errors.category && attempted ? "text-red-500" : ""}>Category *</Label>
                        <Select value={categoryId} onValueChange={(val) => {
                            setCategoryId(val);
                            if (attempted) validateForm();
                        }}>
                            <SelectTrigger className={errors.category && attempted ? "border-red-500 focus:ring-red-500" : ""}>
                                <SelectValue placeholder="Select category..." />
                            </SelectTrigger>
                            <SelectContent>
                                {categories.map((cat) => (
                                    <SelectItem key={cat.id} value={cat.id}>
                                        <span className="flex items-center gap-2">
                                            <span
                                                className="w-2.5 h-2.5 rounded-full inline-block"
                                                style={{ backgroundColor: cat.color }}
                                            />
                                            {cat.name}
                                        </span>
                                    </SelectItem>
                                ))}
                            </SelectContent>
                        </Select>
                        {attempted && errors.category && <p className="text-xs text-red-500">{errors.category}</p>}
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

                    <div className="grid grid-cols-2 gap-4">
                        <div className="space-y-2">
                            <Label>Likelihood (1-5)</Label>
                            <Select value={likelihood} onValueChange={setLikelihood}>
                                <SelectTrigger>
                                    <SelectValue />
                                </SelectTrigger>
                                <SelectContent>
                                    {[1, 2, 3, 4, 5].map((v) => (
                                        <SelectItem key={v} value={String(v)}>
                                            {v} — {['Rare', 'Unlikely', 'Possible', 'Likely', 'Almost Certain'][v - 1]}
                                        </SelectItem>
                                    ))}
                                </SelectContent>
                            </Select>
                        </div>

                        <div className="space-y-2">
                            <Label>Impact (1-5)</Label>
                            <Select value={impact} onValueChange={setImpact}>
                                <SelectTrigger>
                                    <SelectValue />
                                </SelectTrigger>
                                <SelectContent>
                                    {[1, 2, 3, 4, 5].map((v) => (
                                        <SelectItem key={v} value={String(v)}>
                                            {v} — {['Negligible', 'Minor', 'Moderate', 'Major', 'Severe'][v - 1]}
                                        </SelectItem>
                                    ))}
                                </SelectContent>
                            </Select>
                        </div>
                    </div>

                    <div className="flex items-center justify-between bg-slate-50 dark:bg-slate-800 rounded-lg p-3">
                        <span className="text-sm font-medium text-slate-700 dark:text-slate-300">
                            Calculated Risk Score
                        </span>
                        <span
                            className={`text-lg font-bold ${riskScore >= 12
                                ? 'text-red-600'
                                : riskScore >= 6
                                    ? 'text-amber-600'
                                    : 'text-green-600'
                                }`}
                        >
                            {riskScore}
                        </span>
                    </div>

                    <div className="space-y-2">
                        <Label>Status</Label>
                        <Select value={status} onValueChange={setStatus}>
                            <SelectTrigger>
                                <SelectValue />
                            </SelectTrigger>
                            <SelectContent>
                                <SelectItem value="identified">Identified</SelectItem>
                                <SelectItem value="assessed">Assessed</SelectItem>
                                <SelectItem value="mitigated">Mitigated</SelectItem>
                                <SelectItem value="accepted">Accepted</SelectItem>
                            </SelectContent>
                        </Select>
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
