'use client';

import { useState } from 'react';
import { useApiData } from '@/hooks/use-api-data';
import { fetchRisks, fetchControls } from '@/lib/data-service';
import { EvidenceDropzone } from '@/components/evidence/EvidenceDropzone';
import {
    Dialog,
    DialogContent,
    DialogDescription,
    DialogHeader,
    DialogTitle,
} from '@/components/ui/dialog';
import {
    Select,
    SelectContent,
    SelectItem,
    SelectTrigger,
    SelectValue,
} from '@/components/ui/select';
import { Label } from '@/components/ui/label';

interface EvidenceUploadDialogProps {
    open: boolean;
    onOpenChange: (open: boolean) => void;
    onSuccess: () => void;
}

export function EvidenceUploadDialog({ open, onOpenChange, onSuccess }: EvidenceUploadDialogProps) {
    const [relatedType, setRelatedType] = useState<'risk' | 'control' | ''>('');
    const [relatedId, setRelatedId] = useState<string>('');

    const { data: risks, loading: risksLoading } = useApiData(fetchRisks);
    const { data: controls, loading: controlsLoading } = useApiData(fetchControls);

    const handleOpenChange = (isOpen: boolean) => {
        onOpenChange(isOpen);
        if (!isOpen) {
            // Reset state when strictly closing
            setTimeout(() => {
                setRelatedType('');
                setRelatedId('');
            }, 300);
        }
    };

    const handleSuccess = () => {
        onSuccess();
        handleOpenChange(false);
    };

    return (
        <Dialog open={open} onOpenChange={handleOpenChange}>
            <DialogContent className="sm:max-w-[500px]">
                <DialogHeader>
                    <DialogTitle>Upload Evidence</DialogTitle>
                    <DialogDescription>
                        Upload supporting documentation and link it directly to a specific Risk or Control.
                    </DialogDescription>
                </DialogHeader>

                <div className="grid gap-6 py-4">
                    <div className="space-y-4">
                        <div className="space-y-2">
                            <Label>Link Evidence To</Label>
                            <Select
                                value={relatedType}
                                onValueChange={(val: any) => {
                                    setRelatedType(val);
                                    setRelatedId(''); // Reset specific selection when type changes
                                }}
                            >
                                <SelectTrigger>
                                    <SelectValue placeholder="Select type (Risk or Control)" />
                                </SelectTrigger>
                                <SelectContent>
                                    <SelectItem value="risk">Risk</SelectItem>
                                    <SelectItem value="control">Control</SelectItem>
                                </SelectContent>
                            </Select>
                        </div>

                        {relatedType === 'risk' && (
                            <div className="space-y-2">
                                <Label>Select Risk</Label>
                                <Select value={relatedId} onValueChange={setRelatedId}>
                                    <SelectTrigger>
                                        <SelectValue placeholder={risksLoading ? 'Loading risks...' : 'Select a risk...'} />
                                    </SelectTrigger>
                                    <SelectContent>
                                        {risks?.map((risk) => (
                                            <SelectItem key={risk.id} value={risk.id}>
                                                {risk.id} - {risk.title}
                                            </SelectItem>
                                        ))}
                                    </SelectContent>
                                </Select>
                            </div>
                        )}

                        {relatedType === 'control' && (
                            <div className="space-y-2">
                                <Label>Select Control</Label>
                                <Select value={relatedId} onValueChange={setRelatedId}>
                                    <SelectTrigger>
                                        <SelectValue placeholder={controlsLoading ? 'Loading controls...' : 'Select a control...'} />
                                    </SelectTrigger>
                                    <SelectContent>
                                        {controls?.map((control) => (
                                            <SelectItem key={control.id} value={control.id}>
                                                {control.id} - {control.title}
                                            </SelectItem>
                                        ))}
                                    </SelectContent>
                                </Select>
                            </div>
                        )}
                    </div>

                    {/* Render the Dropzone only when a specific ID is selected */}
                    {relatedType && relatedId ? (
                        <div className="pt-2 border-t border-border">
                            <Label className="block mb-2">File Upload</Label>
                            <EvidenceDropzone
                                relatedTo={relatedType as 'risk' | 'control'}
                                relatedId={relatedId}
                                onUploadSuccess={handleSuccess}
                            />
                        </div>
                    ) : (
                        <div className="pt-2 border-t border-border opacity-50 cursor-not-allowed pointer-events-none pb-2">
                            <Label className="block mb-2">File Upload</Label>
                            <div className="border-2 border-dashed rounded-xl p-8 text-center bg-muted/30">
                                <p className="text-sm text-muted-foreground">Please select a {relatedType || 'Risk or Control'} first to enable uploading.</p>
                            </div>
                        </div>
                    )}
                </div>
            </DialogContent>
        </Dialog>
    );
}
