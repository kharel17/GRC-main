'use client';

import { useState, useEffect } from 'react';
import { DocumentAnalysis, RemediationCandidate, CommitRemediationItem } from '@/types';
import {
    Dialog,
    DialogContent,
    DialogDescription,
    DialogHeader,
    DialogTitle,
} from '@/components/ui/dialog';
import {
    Sheet,
    SheetContent,
    SheetDescription,
    SheetHeader,
    SheetTitle,
} from '@/components/ui/sheet';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Separator } from '@/components/ui/separator';
import { Checkbox } from '@/components/ui/checkbox';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import {
    Select,
    SelectContent,
    SelectItem,
    SelectTrigger,
    SelectValue,
} from '@/components/ui/select';
import {
    FileText,
    CheckCircle2,
    AlertCircle,
    BrainCircuit,
    ArrowRight,
    ShieldCheck,
    Calendar,
    Tag,
    Sparkles,
    AlertTriangle,
    Layers,
    Loader2,
    CheckCheck,
    HelpCircle,
} from 'lucide-react';
import { format } from 'date-fns';
import { fetchRemediationPreview, commitRemediations } from '@/lib/data-service';
import { useToast } from '@/hooks/use-toast';

interface DocumentAnalysisDetailsDialogProps {
    analysis: DocumentAnalysis | null;
    open: boolean;
    onOpenChange: (open: boolean) => void;
    onRemediationCommitted?: () => void;
}

interface CandidateEditState {
    risk_title: string;
    risk_description: string;
    likelihood: number;
    impact: number;
    control_title: string;
    control_description: string;
    control_type: string;
}

export function DocumentAnalysisDetailsDialog({
    analysis,
    open,
    onOpenChange,
    onRemediationCommitted,
}: DocumentAnalysisDetailsDialogProps) {
    const { toast } = useToast();
    const [drawerOpen, setDrawerOpen] = useState(false);
    const [isLoadingPreview, setIsLoadingPreview] = useState(false);
    const [isSubmittingCommit, setIsSubmittingCommit] = useState(false);
    const [candidates, setCandidates] = useState<RemediationCandidate[]>([]);
    const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
    const [edits, setEdits] = useState<Record<string, CandidateEditState>>({});

    // Reset drawer state when dialog closes
    useEffect(() => {
        if (!open) {
            setDrawerOpen(false);
        }
    }, [open]);

    // Fetch remediation preview when opening the staging drawer
    const handleOpenDrawer = async () => {
        if (!analysis?.id) return;
        setDrawerOpen(true);
        setIsLoadingPreview(true);
        try {
            const data = await fetchRemediationPreview(String(analysis.id));
            setCandidates(data);

            // By default: check all unregistered items; uncheck items that already exist in register
            const initialSelected = new Set<string>();
            const initialEdits: Record<string, CandidateEditState> = {};

            data.forEach((item) => {
                if (!item.already_registered) {
                    initialSelected.add(item.candidate_id);
                }
                initialEdits[item.candidate_id] = {
                    risk_title: item.suggested_risk_title,
                    risk_description: item.suggested_risk_description,
                    likelihood: item.suggested_risk_likelihood || 3,
                    impact: item.suggested_risk_impact || 3,
                    control_title: item.suggested_control_title,
                    control_description: item.suggested_control_description,
                    control_type: item.control_type || 'preventive',
                };
            });

            setSelectedIds(initialSelected);
            setEdits(initialEdits);
        } catch (err: any) {
            console.error('[HITL Drawer] Failed to fetch remediation preview:', err);
            toast({
                title: 'Failed to load preview',
                description: err?.message || 'Could not retrieve suggested remediation candidates.',
                variant: 'destructive',
            });
        } finally {
            setIsLoadingPreview(false);
        }
    };

    const toggleCandidateSelection = (id: string) => {
        setSelectedIds((prev) => {
            const next = new Set(prev);
            if (next.has(id)) {
                next.delete(id);
            } else {
                next.add(id);
            }
            return next;
        });
    };

    const selectAllUnregistered = () => {
        const next = new Set<string>();
        candidates.forEach((c) => {
            if (!c.already_registered) next.add(c.candidate_id);
        });
        setSelectedIds(next);
    };

    const selectAll = () => {
        const next = new Set<string>(candidates.map((c) => c.candidate_id));
        setSelectedIds(next);
    };

    const deselectAll = () => {
        setSelectedIds(new Set());
    };

    const updateCandidateField = (
        id: string,
        field: keyof CandidateEditState,
        value: any
    ) => {
        setEdits((prev) => ({
            ...prev,
            [id]: {
                ...prev[id],
                [field]: value,
            },
        }));
    };

    const handleCommitBatch = async () => {
        if (!analysis?.id || selectedIds.size === 0) return;

        setIsSubmittingCommit(true);
        try {
            const itemsToCommit: CommitRemediationItem[] = [];

            for (const c of candidates) {
                if (selectedIds.has(c.candidate_id)) {
                    const edited = edits[c.candidate_id] || {
                        risk_title: c.suggested_risk_title,
                        risk_description: c.suggested_risk_description,
                        likelihood: c.suggested_risk_likelihood,
                        impact: c.suggested_risk_impact,
                        control_title: c.suggested_control_title,
                        control_description: c.suggested_control_description,
                        control_type: c.control_type,
                    };

                    itemsToCommit.push({
                        candidate_id: c.candidate_id,
                        framework_id: c.framework_id,
                        framework_control_id: c.framework_control_id,
                        risk_title: edited.risk_title,
                        risk_description: edited.risk_description,
                        likelihood: Number(edited.likelihood),
                        impact: Number(edited.impact),
                        control_title: edited.control_title,
                        control_description: edited.control_description,
                        control_type: edited.control_type,
                        owner_id: c.owner_id,
                    });
                }
            }

            const response = await commitRemediations(String(analysis.id), {
                items: itemsToCommit,
            });

            toast({
                title: 'Remediation Action Plan Committed',
                description: `Successfully registered ${response.committed_count} controls & risks tagged as 'ai_suggested'.`,
            });

            setDrawerOpen(false);
            if (onRemediationCommitted) {
                onRemediationCommitted();
            }
        } catch (err: any) {
            console.error('[HITL Drawer] Failed to commit remediations:', err);
            toast({
                title: 'Commit Failed',
                description: err?.message || 'Database transaction rolled back cleanly. No changes were committed.',
                variant: 'destructive',
            });
        } finally {
            setIsSubmittingCommit(false);
        }
    };

    if (!analysis) return null;

    const hasGaps = (analysis.missing_controls?.length || 0) > 0;

    return (
        <>
            <Dialog open={open} onOpenChange={onOpenChange}>
                <DialogContent className="sm:max-w-2xl max-h-[90vh] overflow-hidden flex flex-col p-0">
                    <DialogHeader className="p-6 border-b">
                        <div className="flex items-center gap-2 mb-2">
                            <Badge variant="outline" className="text-[10px] uppercase font-bold tracking-wider">
                                AI Analysis Results
                            </Badge>
                            <Badge variant={analysis.status === 'completed' ? 'secondary' : 'outline'} className="text-[10px] uppercase">
                                {analysis.status}
                            </Badge>
                        </div>
                        <DialogTitle className="text-xl flex items-center gap-2">
                            <FileText className="h-5 w-5 text-blue-600" />
                            {analysis.file_name || analysis.fileName || analysis.document_name || 'Untitled Document'}
                        </DialogTitle>
                        <DialogDescription className="flex items-center gap-4 mt-2">
                            <span className="flex items-center gap-1.5 text-xs">
                                <Calendar className="h-3 w-3" />
                                {analysis.analyzedAt || analysis.createdAt ? format(new Date(analysis.analyzedAt || analysis.createdAt!), 'PPP') : '—'}
                            </span>
                            <span className="flex items-center gap-1.5 text-xs">
                                <Tag className="h-3 w-3" />
                                {analysis.documentCategory || 'General Security Document'}
                            </span>
                        </DialogDescription>
                    </DialogHeader>

                    <ScrollArea className="flex-1 p-6">
                        <div className="space-y-8">
                            {/* EXECUTIVE SUMMARY */}
                            <div className="space-y-3">
                                <div className="flex items-center gap-2 text-sm font-bold uppercase tracking-tight text-slate-900 dark:text-slate-100">
                                    <BrainCircuit className="h-4 w-4 text-purple-500" />
                                    Executive Discovery
                                </div>
                                <div className="p-4 rounded-xl bg-slate-50 dark:bg-slate-900 border border-slate-100 dark:border-slate-800 italic text-sm text-slate-700 dark:text-slate-300 leading-relaxed shadow-sm">
                                    "{analysis.summary || 'AI analysis of this document has identified several key compliance indicators and potential gaps in implementation.'}"
                                </div>
                            </div>

                            {/* COMPLIANT CONTROLS */}
                            <div className="space-y-4">
                                <div className="flex items-center justify-between">
                                    <div className="flex items-center gap-2 text-sm font-bold uppercase tracking-tight text-green-700 dark:text-green-400">
                                        <CheckCircle2 className="h-4 w-4" />
                                        Implemented Controls
                                    </div>
                                    <Badge variant="outline" className="text-green-600 border-green-200 bg-green-50/50">
                                        {analysis.implemented_controls?.length || 0} Found
                                    </Badge>
                                </div>
                                <div className="grid gap-3">
                                    {analysis.implemented_controls && analysis.implemented_controls.length > 0 ? (
                                        analysis.implemented_controls.map((control: any, i: number) => {
                                            const annexLabel = control.control_annex || control.annex || control.control_id || 'Control';
                                            const confidenceVal = control.confidence ?? (control.confidence_score ? control.confidence_score / 100 : null);
                                            const confidencePct = confidenceVal != null ? Math.round(confidenceVal > 1 ? confidenceVal : confidenceVal * 100) : null;
                                            return (
                                                <div key={i} className="flex items-start gap-3 p-3 rounded-lg border border-green-100 bg-green-50/20 dark:border-green-900/20 dark:bg-green-900/5">
                                                    <div className="flex flex-col items-start gap-1">
                                                        <div className="mt-0.5 px-1.5 py-0.5 rounded bg-green-100 dark:bg-green-900/40 text-[10px] font-mono font-bold text-green-700 dark:text-green-300">
                                                            {annexLabel}
                                                        </div>
                                                        {confidencePct != null && (
                                                            <Badge variant="outline" className="text-[9px] py-0 px-1 border-green-300 text-green-700 dark:text-green-300">
                                                                {confidencePct}%
                                                            </Badge>
                                                        )}
                                                    </div>
                                                    <div className="flex-1">
                                                        <p className="text-sm font-semibold text-green-900 dark:text-green-100">{control.title}</p>
                                                        <p className="text-xs text-green-700/70 dark:text-green-400/70 mt-0.5 line-clamp-2">{control.excerpt || control.evidence_found || 'Evidence identified in document contents.'}</p>
                                                    </div>
                                                </div>
                                            );
                                        })
                                    ) : (
                                        <p className="text-sm text-muted-foreground italic pl-6">No matches identified.</p>
                                    )}
                                </div>
                            </div>

                            {/* IDENTIFIED GAPS */}
                            <div className="space-y-4">
                                <div className="flex items-center justify-between">
                                    <div className="flex items-center gap-2 text-sm font-bold uppercase tracking-tight text-amber-700 dark:text-amber-400">
                                        <AlertCircle className="h-4 w-4" />
                                        Compliance Gaps
                                    </div>
                                    <div className="flex items-center gap-2">
                                        <Badge variant="outline" className="text-amber-600 border-amber-200 bg-amber-50/50">
                                            {analysis.missing_controls?.length || 0} Identified
                                        </Badge>
                                        {hasGaps && (
                                            <Button
                                                size="sm"
                                                variant="outline"
                                                onClick={handleOpenDrawer}
                                                className="h-7 text-xs border-amber-300 text-amber-800 bg-amber-50 hover:bg-amber-100 dark:border-amber-700 dark:text-amber-300 dark:bg-amber-950/40 gap-1 font-semibold"
                                            >
                                                <Sparkles className="h-3 w-3 text-amber-600" />
                                                Review Plan
                                            </Button>
                                        )}
                                    </div>
                                </div>
                                <div className="grid gap-3">
                                    {analysis.missing_controls && analysis.missing_controls.length > 0 ? (
                                        analysis.missing_controls.map((control: any, i: number) => {
                                            const annexLabel = control.control_annex || control.annex || control.control_id || 'Gap';
                                            return (
                                                <div key={i} className="flex items-start gap-3 p-3 rounded-lg border border-amber-100 bg-amber-50/20 dark:border-amber-900/20 dark:bg-amber-900/5">
                                                    <div className="mt-0.5 px-1.5 py-0.5 rounded bg-amber-100 dark:bg-amber-900/40 text-[10px] font-mono font-bold text-amber-700 dark:text-amber-300">
                                                        {annexLabel}
                                                    </div>
                                                    <div className="flex-1">
                                                        <p className="text-sm font-semibold text-amber-900 dark:text-amber-100">{control.title}</p>
                                                        <p className="text-xs text-amber-700/70 dark:text-amber-400/70 mt-0.5 line-clamp-2">{control.reason || 'Requirement not sufficiently addressed in current document.'}</p>
                                                    </div>
                                                </div>
                                            );
                                        })
                                    ) : (
                                        <p className="text-sm text-muted-foreground italic pl-6">No gaps identified.</p>
                                    )}
                                </div>
                            </div>

                            <Separator />

                            {/* REMEDIATION RECOMMENDATION CTA */}
                            <div className="space-y-3">
                                <div className="flex items-center justify-between">
                                    <div className="flex items-center gap-2 text-sm font-bold uppercase tracking-tight text-blue-700 dark:text-blue-400">
                                        <ShieldCheck className="h-4 w-4" />
                                        Remediation Recommendation
                                    </div>
                                    {hasGaps && (
                                        <Button
                                            size="sm"
                                            onClick={handleOpenDrawer}
                                            className="bg-blue-600 hover:bg-blue-700 text-white gap-1.5 text-xs font-semibold shadow-sm"
                                        >
                                            <Sparkles className="h-3.5 w-3.5" />
                                            Review Suggested Action Plan
                                        </Button>
                                    )}
                                </div>
                                <div className="p-4 rounded-xl border-2 border-dashed border-blue-100 dark:border-blue-900/30 bg-blue-50/30 dark:bg-blue-900/5">
                                    <ul className="space-y-3">
                                        <li className="flex items-start gap-2 text-sm">
                                            <ArrowRight className="h-4 w-4 text-blue-500 mt-0.5 shrink-0" />
                                            <span>Update document to include <strong>{analysis.missing_controls?.[0]?.title || 'missing sections'}</strong> as identified by the AI engine.</span>
                                        </li>
                                        <li className="flex items-start gap-2 text-sm">
                                            <ArrowRight className="h-4 w-4 text-blue-500 mt-0.5 shrink-0" />
                                            <span>Stage and approve missing controls into official Risk and Control registers.</span>
                                        </li>
                                    </ul>
                                </div>
                            </div>
                        </div>
                    </ScrollArea>
                    <div className="p-6 border-t bg-slate-50 dark:bg-slate-900 flex justify-between items-center">
                        <div>
                            {hasGaps && (
                                <Button
                                    variant="default"
                                    onClick={handleOpenDrawer}
                                    className="bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-700 hover:to-indigo-700 text-white gap-2 text-sm font-semibold shadow"
                                >
                                    <Sparkles className="h-4 w-4" />
                                    Review Suggested Action Plan ({analysis.missing_controls?.length})
                                </Button>
                            )}
                        </div>
                        <Button variant="outline" onClick={() => onOpenChange(false)}>
                            Close Review
                        </Button>
                    </div>
                </DialogContent>
            </Dialog>

            {/* HITL STAGING REVIEW DRAWER */}
            <Sheet open={drawerOpen} onOpenChange={setDrawerOpen}>
                <SheetContent side="right" className="w-full sm:max-w-3xl flex flex-col p-0 overflow-hidden bg-background border-l shadow-2xl">
                    <SheetHeader className="p-6 border-b bg-slate-50 dark:bg-slate-900/60">
                        <div className="flex items-center justify-between">
                            <div className="flex items-center gap-2">
                                <Badge className="bg-purple-600/10 text-purple-700 dark:text-purple-300 border-purple-200 gap-1 text-xs">
                                    <BrainCircuit className="h-3 w-3" />
                                    HITL Remediation Pipeline
                                </Badge>
                                <Badge variant="outline" className="border-amber-300 text-amber-700 dark:text-amber-400 bg-amber-50 dark:bg-amber-950/30 gap-1 text-xs font-semibold">
                                    <AlertTriangle className="h-3 w-3" />
                                    AI Suggested (Requires Verification)
                                </Badge>
                            </div>
                        </div>
                        <SheetTitle className="text-xl font-bold tracking-tight text-foreground mt-2">
                            Remediation Action Plan Review
                        </SheetTitle>
                        <SheetDescription className="text-xs text-muted-foreground mt-1">
                            Review and refine candidate controls and risks synthesized from document gap findings before registering them into your enterprise catalog.
                        </SheetDescription>
                    </SheetHeader>

                    {isLoadingPreview ? (
                        <div className="flex-1 flex flex-col items-center justify-center gap-3 p-12">
                            <Loader2 className="h-8 w-8 animate-spin text-blue-600" />
                            <p className="text-sm font-medium text-muted-foreground">Synthesizing multi-framework candidate controls...</p>
                        </div>
                    ) : (
                        <>
                            {/* BATCH CONTROLS BAR */}
                            <div className="px-6 py-3 border-b bg-slate-100/60 dark:bg-slate-900/30 flex items-center justify-between text-xs">
                                <div className="flex items-center gap-3">
                                    <span className="font-semibold text-slate-700 dark:text-slate-300">
                                        Selected: <span className="text-blue-600 dark:text-blue-400 font-bold">{selectedIds.size}</span> of {candidates.length}
                                    </span>
                                    <Separator orientation="vertical" className="h-4" />
                                    <Button variant="ghost" size="sm" onClick={selectAllUnregistered} className="h-6 text-[11px] px-2">
                                        Select Unregistered
                                    </Button>
                                    <Button variant="ghost" size="sm" onClick={selectAll} className="h-6 text-[11px] px-2">
                                        Select All
                                    </Button>
                                    <Button variant="ghost" size="sm" onClick={deselectAll} className="h-6 text-[11px] px-2">
                                        Deselect All
                                    </Button>
                                </div>
                                <div className="text-muted-foreground italic flex items-center gap-1">
                                    <HelpCircle className="h-3 w-3" />
                                    <span>Unregistered items are checked by default</span>
                                </div>
                            </div>

                            {/* CANDIDATE ITEMS LIST */}
                            <ScrollArea className="flex-1 p-6">
                                <div className="space-y-4">
                                    {candidates.map((c) => {
                                        const isSelected = selectedIds.has(c.candidate_id);
                                        const edit = edits[c.candidate_id] || {
                                            risk_title: c.suggested_risk_title,
                                            risk_description: c.suggested_risk_description,
                                            likelihood: c.suggested_risk_likelihood,
                                            impact: c.suggested_risk_impact,
                                            control_title: c.suggested_control_title,
                                            control_description: c.suggested_control_description,
                                            control_type: c.control_type,
                                        };

                                        return (
                                            <div
                                                key={c.candidate_id}
                                                className={`p-4 rounded-xl border transition-all ${
                                                    isSelected
                                                        ? 'border-blue-300 dark:border-blue-800 bg-blue-50/15 dark:bg-blue-950/10 shadow-sm'
                                                        : 'border-slate-200 dark:border-slate-800 bg-card opacity-80'
                                                }`}
                                            >
                                                {/* TOP HEADER */}
                                                <div className="flex items-start justify-between gap-3">
                                                    <div className="flex items-start gap-3">
                                                        <Checkbox
                                                            checked={isSelected}
                                                            onCheckedChange={() => toggleCandidateSelection(c.candidate_id)}
                                                            className="mt-1"
                                                        />
                                                        <div>
                                                            <div className="flex items-center gap-2 flex-wrap mb-1">
                                                                <span className="font-mono text-xs px-2 py-0.5 rounded bg-slate-200 dark:bg-slate-800 text-slate-800 dark:text-slate-200 font-bold">
                                                                    {c.gap_annex}
                                                                </span>
                                                                <Badge variant="outline" className="text-[10px] font-semibold border-blue-300 text-blue-700 dark:text-blue-300 bg-blue-50/40">
                                                                    <Layers className="h-2.5 w-2.5 mr-1" />
                                                                    {c.framework_name || 'Standard Framework'}
                                                                </Badge>
                                                                {c.already_registered ? (
                                                                    <Badge className="bg-amber-100 dark:bg-amber-900/40 text-amber-800 dark:text-amber-200 border-amber-300 text-[10px]">
                                                                        Already in Register
                                                                    </Badge>
                                                                ) : (
                                                                    <Badge variant="outline" className="text-green-700 dark:text-green-300 border-green-300 text-[10px]">
                                                                        New Gap Entry
                                                                    </Badge>
                                                                )}
                                                                <Badge variant="secondary" className="text-[9px] uppercase tracking-wider text-purple-700 dark:text-purple-300">
                                                                    AI Suggested
                                                                </Badge>
                                                            </div>
                                                            <h4 className="text-sm font-semibold text-foreground">
                                                                {c.gap_title}
                                                            </h4>
                                                            {c.gap_reason && (
                                                                <p className="text-xs text-muted-foreground mt-0.5">
                                                                    {c.gap_reason}
                                                                </p>
                                                            )}
                                                        </div>
                                                    </div>
                                                </div>

                                                {/* EDITABLE FIELDS CONTAINER */}
                                                {isSelected && (
                                                    <div className="mt-4 pt-3 border-t border-slate-100 dark:border-slate-800/80 grid grid-cols-1 md:grid-cols-2 gap-4 text-xs">
                                                        {/* RISK SIDE */}
                                                        <div className="p-3 rounded-lg bg-slate-50 dark:bg-slate-900/60 border border-slate-200/70 dark:border-slate-800 space-y-2">
                                                            <div className="flex items-center justify-between">
                                                                <span className="font-bold uppercase tracking-tight text-red-700 dark:text-red-400">
                                                                    Suggested Risk
                                                                </span>
                                                                <span className="text-[10px] font-mono text-muted-foreground">
                                                                    Score: {edit.likelihood * edit.impact} / 25
                                                                </span>
                                                            </div>
                                                            <div>
                                                                <label className="text-[10px] text-muted-foreground block mb-0.5">Title</label>
                                                                <Input
                                                                    value={edit.risk_title}
                                                                    onChange={(e) => updateCandidateField(c.candidate_id, 'risk_title', e.target.value)}
                                                                    className="h-7 text-xs"
                                                                />
                                                            </div>
                                                            <div className="grid grid-cols-2 gap-2">
                                                                <div>
                                                                    <label className="text-[10px] text-muted-foreground block mb-0.5">Likelihood (1-5)</label>
                                                                    <Select
                                                                        value={String(edit.likelihood)}
                                                                        onValueChange={(val) => updateCandidateField(c.candidate_id, 'likelihood', Number(val))}
                                                                    >
                                                                        <SelectTrigger className="h-7 text-xs">
                                                                            <SelectValue />
                                                                        </SelectTrigger>
                                                                        <SelectContent>
                                                                            <SelectItem value="1">1 - Rare</SelectItem>
                                                                            <SelectItem value="2">2 - Unlikely</SelectItem>
                                                                            <SelectItem value="3">3 - Moderate</SelectItem>
                                                                            <SelectItem value="4">4 - Likely</SelectItem>
                                                                            <SelectItem value="5">5 - Frequent</SelectItem>
                                                                        </SelectContent>
                                                                    </Select>
                                                                </div>
                                                                <div>
                                                                    <label className="text-[10px] text-muted-foreground block mb-0.5">Impact (1-5)</label>
                                                                    <Select
                                                                        value={String(edit.impact)}
                                                                        onValueChange={(val) => updateCandidateField(c.candidate_id, 'impact', Number(val))}
                                                                    >
                                                                        <SelectTrigger className="h-7 text-xs">
                                                                            <SelectValue />
                                                                        </SelectTrigger>
                                                                        <SelectContent>
                                                                            <SelectItem value="1">1 - Negligible</SelectItem>
                                                                            <SelectItem value="2">2 - Minor</SelectItem>
                                                                            <SelectItem value="3">3 - Moderate</SelectItem>
                                                                            <SelectItem value="4">4 - Major</SelectItem>
                                                                            <SelectItem value="5">5 - Critical</SelectItem>
                                                                        </SelectContent>
                                                                    </Select>
                                                                </div>
                                                            </div>
                                                        </div>

                                                        {/* CONTROL SIDE */}
                                                        <div className="p-3 rounded-lg bg-slate-50 dark:bg-slate-900/60 border border-slate-200/70 dark:border-slate-800 space-y-2">
                                                            <div className="flex items-center justify-between">
                                                                <span className="font-bold uppercase tracking-tight text-blue-700 dark:text-blue-400">
                                                                    Suggested Control
                                                                </span>
                                                                <Badge variant="outline" className="text-[9px] capitalize py-0">
                                                                    {edit.control_type}
                                                                </Badge>
                                                            </div>
                                                            <div>
                                                                <label className="text-[10px] text-muted-foreground block mb-0.5">Title</label>
                                                                <Input
                                                                    value={edit.control_title}
                                                                    onChange={(e) => updateCandidateField(c.candidate_id, 'control_title', e.target.value)}
                                                                    className="h-7 text-xs"
                                                                />
                                                            </div>
                                                            <div>
                                                                <label className="text-[10px] text-muted-foreground block mb-0.5">Control Type</label>
                                                                <Select
                                                                    value={edit.control_type}
                                                                    onValueChange={(val) => updateCandidateField(c.candidate_id, 'control_type', val)}
                                                                >
                                                                    <SelectTrigger className="h-7 text-xs">
                                                                        <SelectValue />
                                                                    </SelectTrigger>
                                                                    <SelectContent>
                                                                        <SelectItem value="preventive">Preventive</SelectItem>
                                                                        <SelectItem value="detective">Detective</SelectItem>
                                                                        <SelectItem value="corrective">Corrective</SelectItem>
                                                                    </SelectContent>
                                                                </Select>
                                                            </div>
                                                        </div>
                                                    </div>
                                                )}
                                            </div>
                                        );
                                    })}
                                </div>
                            </ScrollArea>

                            {/* DRAWER FOOTER */}
                            <div className="p-4 border-t bg-slate-50 dark:bg-slate-900 flex items-center justify-between">
                                <div className="text-xs text-muted-foreground">
                                    Ready to commit: <strong className="text-foreground">{selectedIds.size} items</strong>
                                </div>
                                <div className="flex items-center gap-2">
                                    <Button variant="outline" size="sm" onClick={() => setDrawerOpen(false)} disabled={isSubmittingCommit}>
                                        Cancel
                                    </Button>
                                    <Button
                                        size="sm"
                                        disabled={selectedIds.size === 0 || isSubmittingCommit}
                                        onClick={handleCommitBatch}
                                        className="bg-blue-600 hover:bg-blue-700 text-white gap-2 font-semibold shadow"
                                    >
                                        {isSubmittingCommit ? (
                                            <>
                                                <Loader2 className="h-3.5 w-3.5 animate-spin" />
                                                Committing Batch...
                                            </>
                                        ) : (
                                            <>
                                                <CheckCheck className="h-3.5 w-3.5" />
                                                Approve & Add to Registers ({selectedIds.size} items)
                                            </>
                                        )}
                                    </Button>
                                </div>
                            </div>
                        </>
                    )}
                </SheetContent>
            </Sheet>
        </>
    );
}
