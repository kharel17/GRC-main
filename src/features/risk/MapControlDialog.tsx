'use client';

import { useState, useEffect } from 'react';
import { fetchControls, mapControlToRisk } from '@/lib/data-service';
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
import { Badge } from '@/components/ui/badge';
import { handleApiError } from '@/lib/handle-api-error';
import { Loader2, ShieldCheck, Check } from 'lucide-react';

interface MapControlDialogProps {
    open: boolean;
    onOpenChange: (open: boolean) => void;
    riskId: string;
    riskTitle: string;
    existingControlIds: string[];
    onSuccess: () => void;
}

export function MapControlDialog({
    open,
    onOpenChange,
    riskId,
    riskTitle,
    existingControlIds,
    onSuccess,
}: MapControlDialogProps) {
    const [controls, setControls] = useState<Control[]>([]);
    const [loading, setLoading] = useState(false);
    const [selectedId, setSelectedId] = useState<string>('');
    const [submitting, setSubmitting] = useState(false);

    useEffect(() => {
        if (open) {
            setLoading(true);
            setSelectedId('');
            fetchControls()
                .then((data) => setControls(data))
                .catch(() => toast.error('Failed to load controls'))
                .finally(() => setLoading(false));
        }
    }, [open]);

    const availableControls = controls.filter(
        (c) => !existingControlIds.includes(c.id)
    );

    const handleMap = async () => {
        if (!selectedId) {
            toast.error('Please select a control to map.');
            return;
        }

        setSubmitting(true);
        try {
            await mapControlToRisk(riskId, selectedId);
            toast.success('Controls mapped successfully!');
            onOpenChange(false);
            onSuccess();
        } catch (err: unknown) {
            toast.error(handleApiError(err));
        } finally {
            setSubmitting(false);
        }
    };

    const getStatusColor = (status: string) => {
        switch (status) {
            case 'implemented':
                return 'bg-green-100 text-green-700';
            case 'planned':
                return 'bg-blue-100 text-blue-700';
            case 'under_review':
                return 'bg-amber-100 text-amber-700';
            default:
                return 'bg-slate-100 text-slate-700';
        }
    };

    const getTypeColor = (type: string) => {
        switch (type) {
            case 'preventive':
                return 'bg-purple-100 text-purple-700';
            case 'detective':
                return 'bg-cyan-100 text-cyan-700';
            case 'corrective':
                return 'bg-orange-100 text-orange-700';
            default:
                return 'bg-slate-100 text-slate-700';
        }
    };

    return (
        <Dialog open={open} onOpenChange={onOpenChange}>
            <DialogContent className="sm:max-w-[550px] max-h-[85vh] overflow-y-auto">
                <DialogHeader>
                    <DialogTitle>Map Control to Risk</DialogTitle>
                    <DialogDescription>
                        Select a control to associate with <strong>"{riskTitle}"</strong>.
                    </DialogDescription>
                </DialogHeader>

                {loading ? (
                    <div className="flex items-center justify-center py-12">
                        <Loader2 className="h-6 w-6 animate-spin text-blue-600" />
                        <span className="ml-2 text-sm text-slate-500">Loading controls...</span>
                    </div>
                ) : availableControls.length === 0 ? (
                    <div className="py-12 text-center">
                        <ShieldCheck className="h-10 w-10 text-slate-300 mx-auto mb-3" />
                        <p className="text-sm text-slate-500">
                            {controls.length === 0
                                ? 'No controls exist yet. Create controls first.'
                                : 'All available controls are already mapped to this risk.'}
                        </p>
                    </div>
                ) : (
                    <div className="space-y-2 py-2">
                        {availableControls.map((control) => (
                            <button
                                key={control.id}
                                onClick={() => setSelectedId(control.id)}
                                className={`w-full text-left p-3 rounded-lg border-2 transition-all ${selectedId === control.id
                                        ? 'border-blue-500 bg-blue-50 dark:bg-blue-950/20'
                                        : 'border-slate-200 dark:border-slate-700 hover:border-slate-300 dark:hover:border-slate-600'
                                    }`}
                            >
                                <div className="flex items-start justify-between gap-2">
                                    <div className="flex-1 min-w-0">
                                        <p className="font-medium text-sm text-slate-900 dark:text-slate-100 truncate">
                                            {control.title}
                                        </p>
                                        <p className="text-xs text-slate-500 dark:text-slate-400 mt-1 line-clamp-2">
                                            {control.description}
                                        </p>
                                        <div className="flex flex-wrap gap-1.5 mt-2">
                                            <Badge className={`text-[10px] ${getTypeColor(control.controlType)}`}>
                                                {control.controlType}
                                            </Badge>
                                            <Badge className={`text-[10px] ${getStatusColor(control.status)}`}>
                                                {control.status}
                                            </Badge>
                                        </div>
                                    </div>
                                    {selectedId === control.id && (
                                        <Check className="h-5 w-5 text-blue-600 shrink-0 mt-0.5" />
                                    )}
                                </div>
                            </button>
                        ))}
                    </div>
                )}

                <div className="flex justify-end gap-3 pt-2 border-t">
                    <Button variant="outline" onClick={() => onOpenChange(false)} disabled={submitting}>
                        Cancel
                    </Button>
                    <Button
                        onClick={handleMap}
                        disabled={submitting || !selectedId}
                    >
                        {submitting ? (
                            <>
                                <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                                Mapping...
                            </>
                        ) : (
                            'Map Control'
                        )}
                    </Button>
                </div>
            </DialogContent>
        </Dialog>
    );
}
