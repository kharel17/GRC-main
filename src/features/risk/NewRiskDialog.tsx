'use client';

import { useState } from 'react';
import { createRisk, getRiskCategories } from '@/lib/data-service';
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

interface NewRiskDialogProps {
    open: boolean;
    onOpenChange: (open: boolean) => void;
    onSuccess: () => void;
}

export function NewRiskDialog({ open, onOpenChange, onSuccess }: NewRiskDialogProps) {
    const { user } = useAuth();
    const categories = getRiskCategories();

    const [title, setTitle] = useState('');
    const [description, setDescription] = useState('');
    const [categoryId, setCategoryId] = useState('');
    const [likelihood, setLikelihood] = useState('3');
    const [impact, setImpact] = useState('3');
    const [status, setStatus] = useState('identified');
    const [submitting, setSubmitting] = useState(false);

    const riskScore = parseInt(likelihood) * parseInt(impact);

    const resetForm = () => {
        setTitle('');
        setDescription('');
        setCategoryId('');
        setLikelihood('3');
        setImpact('3');
        setStatus('identified');
    };

    const handleSubmit = async () => {
        if (!title.trim() || !description.trim() || !categoryId) {
            toast.error('Please fill in all required fields.');
            return;
        }

        setSubmitting(true);
        try {
            await createRisk({
                title: title.trim(),
                description: description.trim(),
                category_id: categoryId,
                likelihood: parseInt(likelihood),
                impact: parseInt(impact),
                risk_score: riskScore,
                status,
                owner_id: user?.id,
            } as any);

            toast.success('Risk created successfully!');
            resetForm();
            onSuccess();
            onOpenChange(false);
        } catch (err: any) {
            toast.error(err?.message || 'Failed to create risk.');
        } finally {
            setSubmitting(false);
        }
    };

    return (
        <Dialog open={open} onOpenChange={onOpenChange}>
            <DialogContent className="sm:max-w-[520px] max-h-[90vh] overflow-y-auto">
                <DialogHeader>
                    <DialogTitle>Create New Risk</DialogTitle>
                    <DialogDescription>
                        Identify and document a new organizational risk.
                    </DialogDescription>
                </DialogHeader>

                <div className="grid gap-4 py-4">
                    <div className="space-y-2">
                        <Label htmlFor="risk-title">Title *</Label>
                        <Input
                            id="risk-title"
                            placeholder="e.g. Data Breach via Phishing"
                            value={title}
                            onChange={(e) => setTitle(e.target.value)}
                        />
                    </div>

                    <div className="space-y-2">
                        <Label htmlFor="risk-desc">Description *</Label>
                        <Textarea
                            id="risk-desc"
                            placeholder="Describe the risk and its potential consequences..."
                            value={description}
                            onChange={(e) => setDescription(e.target.value)}
                            rows={3}
                        />
                    </div>

                    <div className="space-y-2">
                        <Label>Category *</Label>
                        <Select value={categoryId} onValueChange={setCategoryId}>
                            <SelectTrigger>
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
                        <Label>Initial Status</Label>
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
                                Creating...
                            </>
                        ) : (
                            'Create Risk'
                        )}
                    </Button>
                </div>
            </DialogContent>
        </Dialog>
    );
}
