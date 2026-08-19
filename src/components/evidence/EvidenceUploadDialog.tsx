import React, { useState } from 'react';
import { useApiData } from '@/hooks';
import { fetchRisks, fetchControls } from '@/lib/data-service';
import { EvidenceDropzone } from '@/components/evidence';
import { toast } from 'sonner';
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
    const [selectedRisk, setSelectedRisk] = useState<string>('');
    const [selectedControl, setSelectedControl] = useState<string>('');
    const [errors, setErrors] = useState<Record<string, string>>({});
    const [attempted, setAttempted] = useState(false);

    const { data: risksData, loading: risksLoading } = useApiData(fetchRisks);
    const { data: controlsData, loading: controlsLoading } = useApiData(fetchControls);

    // Ensure risks and controls are arrays, even if data is null/undefined
    const risks = risksData || [];
    const controls = controlsData || [];

    // Filter controls based on selected risk
    const relatedControls = React.useMemo(() => {
        // Fallback: Currently the API does not embed risk IDs in controls directly, 
        // so we just return all controls for now
        return controls;
    }, [controls]);

    const targetType = selectedControl ? 'control' : (selectedRisk ? 'risk' : '');
    const targetId = selectedControl || selectedRisk;
    const isReady = !!targetId;

    const handleOpenChange = (isOpen: boolean) => {
        onOpenChange(isOpen);
        if (!isOpen) {
            // Reset state when strictly closing
            setTimeout(() => {
                setSelectedRisk('');
                setSelectedControl('');
                setErrors({});
                setAttempted(false);
            }, 300);
        }
    };

    const handleUploadComplete = () => {
        toast.success(`Evidence uploaded and linked to ${selectedControl ? 'Control' : 'Risk'}.`);
        onSuccess();
        handleOpenChange(false);
    };

    const validateSelection = () => {
        setAttempted(true);
        if (!isReady) {
            setErrors({ selection: 'Please select a Risk or Control to attach evidence.' });
            return false;
        }
        setErrors({});
        return true;
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
                    {/* Select Risk */}
                    <div className="space-y-2">
                        <Label>Link to Risk (Optional if Control is selected)</Label>
                        <Select
                            value={selectedRisk}
                            onValueChange={(val) => {
                                setSelectedRisk(val);
                                setSelectedControl(''); // Reset control when risk changes
                                if (errors.selection) setErrors({});
                            }}
                            disabled={risksLoading}
                        >
                            <SelectTrigger className={attempted && !isReady ? "border-red-500" : undefined}>
                                <SelectValue placeholder={risksLoading ? 'Loading risks...' : "Select a risk..."} />
                            </SelectTrigger>
                            <SelectContent>
                                {risks.map((risk) => (
                                    <SelectItem key={risk.id} value={risk.id}>
                                        {risk.id} - {risk.title}
                                    </SelectItem>
                                ))}
                            </SelectContent>
                        </Select>
                    </div>

                    {/* Select Control */}
                    <div className="space-y-2">
                        <Label>Link to Control (Optional if Risk is selected)</Label>
                        <Select
                            value={selectedControl}
                            onValueChange={(val) => {
                                setSelectedControl(val);
                                if (errors.selection) setErrors({});
                            }}
                            disabled={controlsLoading || (selectedRisk !== '' && relatedControls.length === 0)}
                        >
                            <SelectTrigger className={attempted && !isReady ? "border-red-500" : undefined}>
                                <SelectValue placeholder={controlsLoading ? 'Loading controls...' : (selectedRisk ? "Select a related control..." : "Select any control...")} />
                            </SelectTrigger>
                            <SelectContent>
                                {relatedControls.length === 0 ? (
                                    <SelectItem value="none" disabled>
                                        {selectedRisk ? "No controls related to this risk" : "No controls available"}
                                    </SelectItem>
                                ) : (
                                    relatedControls.map((control) => (
                                        <SelectItem key={control.id} value={control.id}>
                                            {control.id} - {control.title}
                                        </SelectItem>
                                    ))
                                )}
                            </SelectContent>
                        </Select>
                    </div>

                    {errors.selection && <p className="text-xs text-red-500 mt-1">{errors.selection}</p>}
                </div>

                {isReady ? (
                    <div className="pt-2 border-t border-border">
                        <Label className="block mb-2">File Upload</Label>
                        <EvidenceDropzone
                            relatedTo={targetType as 'risk' | 'control'}
                            relatedId={targetId}
                            onUploadSuccess={handleUploadComplete}
                        />
                    </div>
                ) : (
                    <div
                        className="pt-2 border-t border-border opacity-50 cursor-pointer pb-2"
                        onClick={validateSelection} 
                    >
                        <Label className="block mb-2">File Upload</Label>
                        <div className="border-2 border-dashed rounded-xl p-8 text-center bg-muted/30">
                            <p className="text-sm text-muted-foreground">Please select a Risk or Control first to enable uploading.</p>
                        </div>
                    </div>
                )}
            </DialogContent>
        </Dialog>
    );
}
