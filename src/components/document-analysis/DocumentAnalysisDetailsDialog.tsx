'use client';

import { DocumentAnalysis } from '@/types';
import {
    Dialog,
    DialogContent,
    DialogDescription,
    DialogHeader,
    DialogTitle,
} from '@/components/ui/dialog';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Separator } from '@/components/ui/separator';
import {
    FileText,
    CheckCircle2,
    AlertCircle,
    BrainCircuit,
    ArrowRight,
    ShieldCheck,
    Calendar,
    Tag
} from 'lucide-react';
import { format } from 'date-fns';

interface DocumentAnalysisDetailsDialogProps {
    analysis: DocumentAnalysis | null;
    open: boolean;
    onOpenChange: (open: boolean) => void;
}

export function DocumentAnalysisDetailsDialog({
    analysis,
    open,
    onOpenChange
}: DocumentAnalysisDetailsDialogProps) {
    if (!analysis) return null;

    return (
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
                                "{analysis.summary || "AI analysis of this document has identified several key compliance indicators and potential gaps in implementation."}"
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
                                    analysis.implemented_controls.map((control: any, i: number) => (
                                        <div key={i} className="flex items-start gap-3 p-3 rounded-lg border border-green-100 bg-green-50/20 dark:border-green-900/20 dark:bg-green-900/5">
                                            <div className="mt-0.5 px-1.5 py-0.5 rounded bg-green-100 dark:bg-green-900/40 text-[10px] font-mono font-bold text-green-700 dark:text-green-300">
                                                {control.annex}
                                            </div>
                                            <div>
                                                <p className="text-sm font-semibold text-green-900 dark:text-green-100">{control.title}</p>
                                                <p className="text-xs text-green-700/70 dark:text-green-400/70 mt-0.5 line-clamp-2">{control.evidence_found || 'Evidence identified in document contents.'}</p>
                                            </div>
                                        </div>
                                    ))
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
                                <Badge variant="outline" className="text-amber-600 border-amber-200 bg-amber-50/50">
                                    {analysis.missing_controls?.length || 0} Identified
                                </Badge>
                            </div>
                            <div className="grid gap-3">
                                {analysis.missing_controls && analysis.missing_controls.length > 0 ? (
                                    analysis.missing_controls.map((control: any, i: number) => (
                                        <div key={i} className="flex items-start gap-3 p-3 rounded-lg border border-amber-100 bg-amber-50/20 dark:border-amber-900/20 dark:bg-amber-900/5">
                                            <div className="mt-0.5 px-1.5 py-0.5 rounded bg-amber-100 dark:bg-amber-900/40 text-[10px] font-mono font-bold text-amber-700 dark:text-amber-300">
                                                {control.annex}
                                            </div>
                                            <div>
                                                <p className="text-sm font-semibold text-amber-900 dark:text-amber-100">{control.title}</p>
                                                <p className="text-xs text-amber-700/70 dark:text-amber-400/70 mt-0.5 line-clamp-2">{control.reason || 'Requirement not sufficiently addressed in current document.'}</p>
                                            </div>
                                        </div>
                                    ))
                                ) : (
                                    <p className="text-sm text-muted-foreground italic pl-6">No gaps identified.</p>
                                )}
                            </div>
                        </div>

                        <Separator />

                        {/* NEXT STEPS */}
                        <div className="space-y-3">
                            <div className="flex items-center gap-2 text-sm font-bold uppercase tracking-tight text-blue-700 dark:text-blue-400">
                                <ShieldCheck className="h-4 w-4" />
                                Remediation Recommendation
                            </div>
                            <div className="p-4 rounded-xl border-2 border-dashed border-blue-100 dark:border-blue-900/30 bg-blue-50/30 dark:bg-blue-900/5">
                                <ul className="space-y-3">
                                    <li className="flex items-start gap-2 text-sm">
                                        <ArrowRight className="h-4 w-4 text-blue-500 mt-0.5 shrink-0" />
                                        <span>Update document to include <strong>{analysis.missing_controls?.[0]?.title || 'missing sections'}</strong> as identified by the AI engine.</span>
                                    </li>
                                    <li className="flex items-start gap-2 text-sm">
                                        <ArrowRight className="h-4 w-4 text-blue-500 mt-0.5 shrink-0" />
                                        <span>Link this policy as evidence for Control <strong>{analysis.implemented_controls?.[0]?.annex || 'ISO-27001'}</strong>.</span>
                                    </li>
                                </ul>
                            </div>
                        </div>
                    </div>
                </ScrollArea>
                <div className="p-6 border-t bg-slate-50 dark:bg-slate-900 flex justify-end">
                    <Button onClick={() => onOpenChange(false)}>Close Review</Button>
                </div>
            </DialogContent>
        </Dialog>
    );
}
