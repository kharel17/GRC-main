'use client';

import { Evidence } from '@/types';
import {
    Sheet,
    SheetContent,
    SheetDescription,
    SheetHeader,
    SheetTitle,
    SheetFooter,
} from '@/components/ui/sheet';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Separator } from '@/components/ui/separator';
import { Progress } from '@/components/ui/progress';
import {
    FileText,
    Download,
    Trash2,
    ExternalLink,
    Clock,
    User,
    ShieldCheck,
    AlertCircle,
    CheckCircle2,
    XCircle,
    BrainCircuit,
    Calendar,
    CheckSquare
} from 'lucide-react';
import { format } from 'date-fns';

interface EvidenceDetailSheetProps {
    evidence: Evidence | null;
    open: boolean;
    onOpenChange: (open: boolean) => void;
    onDelete?: (id: string) => void;
    onStatusUpdate?: (id: string, status: string) => void;
}

export function EvidenceDetailSheet({
    evidence,
    open,
    onOpenChange,
    onDelete,
    onStatusUpdate
}: EvidenceDetailSheetProps) {
    if (!evidence) return null;

    const getConfidenceColor = (score: number) => {
        if (score >= 80) return 'text-emerald-500';
        if (score >= 60) return 'text-amber-500';
        return 'text-red-500';
    };

    const getConfidenceBg = (score: number) => {
        if (score >= 80) return 'bg-emerald-50 dark:bg-emerald-900/20';
        if (score >= 60) return 'bg-amber-50 dark:bg-amber-900/20';
        return 'bg-red-50 dark:bg-red-900/20';
    };

    const getStatusIcon = (status: string) => {
        switch (status) {
            case 'verified': return <CheckCircle2 className="h-4 w-4 text-emerald-500" />;
            case 'rejected': return <XCircle className="h-4 w-4 text-red-500" />;
            case 'pending': return <Clock className="h-4 w-4 text-blue-500" />;
            default: return <AlertCircle className="h-4 w-4 text-slate-400" />;
        }
    };

    return (
        <Sheet open={open} onOpenChange={onOpenChange}>
            <SheetContent className="sm:max-w-md md:max-w-lg overflow-hidden flex flex-col p-0">
                <SheetHeader className="p-6 border-b">
                    <div className="flex items-center justify-between mb-2">
                        <Badge variant="outline" className="text-[10px] uppercase tracking-wider font-bold">
                            Evidence Detail
                        </Badge>
                        <div className="flex items-center gap-2">
                            {getStatusIcon(evidence.status)}
                            <span className="text-xs font-semibold uppercase">{evidence.status?.replace('_', ' ') || 'Pending'}</span>
                        </div>
                    </div>
                    <SheetTitle className="text-xl flex items-center gap-2">
                        <FileText className="h-5 w-5 text-blue-600" />
                        {evidence.file_name || evidence.title}
                    </SheetTitle>
                    <SheetDescription className="line-clamp-2">
                        {evidence.description || 'No description provided for this evidence.'}
                    </SheetDescription>
                </SheetHeader>

                <ScrollArea className="flex-1 p-6">
                    <div className="space-y-8">
                        {/* AI ANALYSIS SECTION */}
                        <div className="space-y-4">
                            <div className="flex items-center gap-2 text-sm font-bold text-slate-900 dark:text-slate-100 uppercase tracking-tight">
                                <BrainCircuit className="h-4 w-4 text-purple-500" />
                                AI Engine Analysis
                            </div>

                            <div className={`p-4 rounded-xl border-2 ${getConfidenceBg(evidence.confidence_score || 0)} border-white dark:border-slate-800 shadow-sm`}>
                                <div className="flex justify-between items-center mb-3">
                                    <span className="text-sm font-medium">Matching Confidence</span>
                                    <span className={`text-xl font-bold ${getConfidenceColor(evidence.confidence_score || 0)}`}>
                                        {evidence.confidence_score || 0}%
                                    </span>
                                </div>
                                <Progress value={evidence.confidence_score || 0} className="h-2 mb-4" />
                                
                                <div className="space-y-4">
                                    <div>
                                        <div className="text-[10px] font-bold text-slate-500 uppercase mb-1">AI Findings Summary</div>
                                        <p className="text-sm text-slate-700 dark:text-slate-300 italic leading-relaxed">
                                            "{evidence.ai_summary || "AI analysis is pending for this document."}"
                                        </p>
                                    </div>
                                    
                                    <div className="flex items-center justify-between p-2 bg-white/50 dark:bg-black/20 rounded-lg">
                                        <div className="flex items-center gap-2">
                                            <ShieldCheck className="h-4 w-4 text-blue-600" />
                                            <span className="text-xs font-medium uppercase text-slate-500">Matched ISO Clause</span>
                                        </div>
                                        <Badge variant="secondary" className="font-mono text-xs">
                                            {evidence.matched_iso_clause || 'None Detected'}
                                        </Badge>
                                    </div>
                                </div>
                            </div>
                        </div>

                        {/* METADATA SECTION */}
                        <div className="space-y-4 pt-4">
                            <div className="flex items-center gap-2 text-sm font-bold text-slate-900 dark:text-slate-100 uppercase tracking-tight">
                                <FileText className="h-4 w-4 text-blue-500" />
                                Metadata & History
                            </div>
                            
                            <div className="grid grid-cols-2 gap-y-6 gap-4 text-sm">
                                <div className="space-y-1">
                                    <div className="flex items-center gap-1.5 text-xs text-muted-foreground">
                                        <User className="h-3 w-3" />
                                        Uploaded By
                                    </div>
                                    <p className="font-medium truncate">{evidence.uploadedByName || 'System'}</p>
                                </div>
                                <div className="space-y-1">
                                    <div className="flex items-center gap-1.5 text-xs text-muted-foreground">
                                        <Calendar className="h-3 w-3" />
                                        Upload Date
                                    </div>
                                    <p className="font-medium">{evidence.uploaded_at ? format(new Date(evidence.uploaded_at), 'PPP') : '—'}</p>
                                </div>
                                <div className="space-y-1">
                                    <div className="flex items-center gap-1.5 text-xs text-muted-foreground">
                                        <Clock className="h-3 w-3" />
                                        Retention Expiry
                                    </div>
                                    <p className="font-medium">{evidence.valid_until ? format(new Date(evidence.valid_until), 'PPP') : 'None set'}</p>
                                </div>
                                <div className="space-y-1">
                                    <div className="flex items-center gap-1.5 text-xs text-muted-foreground">
                                        <CheckSquare className="h-3 w-3" />
                                        Control ID
                                    </div>
                                    <p className="font-mono text-xs font-medium uppercase">
                                        {evidence.control_id ? evidence.control_id.slice(0, 8) : 'Unlinked'}
                                    </p>
                                </div>
                            </div>
                        </div>

                        <Separator />

                        {/* FILE ACTIONS */}
                        <div className="grid grid-cols-2 gap-3">
                            <Button variant="outline" className="gap-2" asChild>
                                <a href={evidence.file_url} target="_blank" rel="noopener noreferrer">
                                    <ExternalLink className="h-4 w-4" />
                                    View File
                                </a>
                            </Button>
                            <Button variant="outline" className="gap-2">
                                <Download className="h-4 w-4" />
                                Download
                            </Button>
                        </div>
                    </div>
                </ScrollArea>

                <SheetFooter className="p-6 bg-slate-50 dark:bg-slate-900 border-t flex-row gap-2 justify-end">
                    <Button 
                        variant="destructive" 
                        size="sm" 
                        className="gap-2"
                        onClick={() => onDelete?.(evidence.id)}
                    >
                        <Trash2 className="h-4 w-4" />
                        Delete Evidence
                    </Button>
                </SheetFooter>
            </SheetContent>
        </Sheet>
    );
}
