'use client';

import { useState, useEffect, useCallback } from 'react';
import { api } from '@/lib/api-client';
import { useAuth } from '@/hooks';
import { Evidence } from '@/types';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import {
    Table,
    TableBody,
    TableCell,
    TableHead,
    TableHeader,
    TableRow,
} from '@/components/ui/table';
import {
    Dialog,
    DialogContent,
    DialogHeader,
    DialogTitle,
    DialogFooter,
} from '@/components/ui/dialog';
import { Textarea } from '@/components/ui/textarea';
import {
    FileText,
    ExternalLink,
    ShieldCheck,
    XCircle,
    Loader2,
} from 'lucide-react';
import { toast } from 'sonner';
import { EvidenceDetailSheet } from './EvidenceDetailSheet';
import { deleteEvidence } from '@/lib/data-service';

// ── Types ───────────────────────────────────────────────────

type EvidenceItem = Evidence;

interface EvidenceListProps {
    relatedTo?: 'control' | 'risk';
    relatedId?: string;
    refreshKey?: number; // increment to trigger re-fetch
    items?: EvidenceItem[];           // external data, overrides internal fetch
    viewMode?: 'table' | 'cards';     // default: 'table'
    showRelated?: boolean;            // show "Related To" column, default: false
    onRefresh?: () => void;           // callback after status update
}

// ── Status helpers ──────────────────────────────────────────

const STATUS_CONFIG: Record<string, { label: string; color: string }> = {
    pending: { label: 'Pending Review', color: 'bg-blue-100 text-blue-700 dark:bg-blue-900/40 dark:text-blue-300' },
    verified: { label: 'Verified', color: 'bg-emerald-100 text-emerald-700 dark:bg-emerald-900/40 dark:text-emerald-300' },
    expired: { label: 'Expired', color: 'bg-gray-100 text-gray-600 dark:bg-gray-800 dark:text-gray-400' },
    rejected: { label: 'Rejected', color: 'bg-red-100 text-red-700 dark:bg-red-900/40 dark:text-red-300' },
};

function getStatusBadge(status?: string, validUntil?: string): { label: string; color: string } {
    // Check for expiry
    if (validUntil && new Date(validUntil) < new Date()) {
        return STATUS_CONFIG.expired;
    }
    return STATUS_CONFIG[status || 'pending'] || STATUS_CONFIG.pending;
}

function formatDate(iso?: string): string {
    if (!iso) return '—';
    return new Date(iso).toLocaleDateString(undefined, {
        year: 'numeric',
        month: 'short',
        day: 'numeric',
    });
}

// ── Component ───────────────────────────────────────────────

export function EvidenceList({
    relatedTo,
    relatedId,
    refreshKey,
    items: externalItems,
    viewMode = 'table',
    showRelated = false,
    onRefresh
}: EvidenceListProps) {
    const { user, hasRole } = useAuth();
    const [internalItems, setInternalItems] = useState<EvidenceItem[]>([]);
    const [loading, setLoading] = useState(!externalItems);

    // Dialog state for verify/reject
    const [reviewDialogOpen, setReviewDialogOpen] = useState(false);
    const [reviewTarget, setReviewTarget] = useState<{ id: string; action: 'verified' | 'rejected' } | null>(null);
    const [reviewNotes, setReviewNotes] = useState('');
    const [reviewing, setReviewing] = useState(false);

    // Detail Sheet state
    const [selectedEvidence, setSelectedEvidence] = useState<EvidenceItem | null>(null);
    const [detailSheetOpen, setDetailSheetOpen] = useState(false);

    const canReview = hasRole(['admin', 'manager']);

    const items = externalItems || internalItems;

    const fetchEvidence = useCallback(async () => {
        if (externalItems || !relatedId) return;
        try {
            setLoading(true);
            const data = await api.get<EvidenceItem[]>(`/evidence/?related_id=${relatedId}`);
            setInternalItems(data);
        } catch (err) {
            console.error('Failed to load evidence', err);
        } finally {
            setLoading(false);
        }
    }, [relatedId, externalItems]);

    useEffect(() => {
        if (relatedId) fetchEvidence();
    }, [relatedId, refreshKey, fetchEvidence]);

    const openReviewDialog = (evidenceId: string, action: 'verified' | 'rejected') => {
        setReviewTarget({ id: evidenceId, action });
        setReviewNotes('');
        setReviewDialogOpen(true);
    };

    const submitReview = async () => {
        if (!reviewTarget) return;
        setReviewing(true);
        try {
            await api.patch(`/evidence/${reviewTarget.id}/status`, {
                status: reviewTarget.action,
                review_notes: reviewNotes || undefined,
            });
            toast.success(reviewTarget.action === 'verified' ? 'Evidence verified' : 'Evidence rejected');
            setReviewDialogOpen(false);
            if (onRefresh) {
                onRefresh();
            } else {
                fetchEvidence();
            }
        } finally {
            setReviewing(false);
        }
    };

    const handleRowClick = (item: EvidenceItem) => {
        setSelectedEvidence(item);
        setDetailSheetOpen(true);
    };

    const handleDelete = async (id: string) => {
        if (!confirm('Are you sure you want to delete this evidence?')) return;
        
        try {
            await deleteEvidence(id);
            toast.success('Evidence deleted successfully');
            setDetailSheetOpen(false);
            if (onRefresh) onRefresh();
            else fetchEvidence();
        } catch (err: any) {
            toast.error(err?.message || 'Failed to delete evidence');
        }
    };

    // ── Render Helpers ──────────────────────────────────────────

    const renderTableView = () => {
        return (
            <div className="rounded-xl border border-border bg-card overflow-hidden">
                <Table>
                    <TableHeader>
                        <TableRow className="hover:bg-muted/50 border-border">
                            <TableHead className="text-muted-foreground">File</TableHead>
                            {showRelated && <TableHead className="text-muted-foreground">Related To</TableHead>}
                            <TableHead className="text-muted-foreground">Uploaded</TableHead>
                            <TableHead className="text-muted-foreground">Status</TableHead>
                            <TableHead className="text-muted-foreground">Valid Until</TableHead>
                            {canReview && <TableHead className="text-right text-muted-foreground">Actions</TableHead>}
                        </TableRow>
                    </TableHeader>
                    <TableBody>
                        {items.map((item) => {
                            const badge = getStatusBadge(item.status, item.valid_until);
                            return (
                                <TableRow 
                                    key={item.id} 
                                    className="hover:bg-muted/50 border-border cursor-pointer group"
                                    onClick={() => handleRowClick(item)}
                                >
                                    <TableCell>
                                        <div className="flex items-center gap-2.5">
                                            <FileText className="h-4 w-4 text-blue-500 shrink-0" />
                                            <div className="min-w-0">
                                                {item.file_url ? (
                                                    <a
                                                        href={item.file_url}
                                                        target="_blank"
                                                        rel="noopener noreferrer"
                                                        className="text-sm font-medium text-foreground hover:text-blue-600 hover:underline inline-flex items-center gap-1"
                                                    >
                                                        {item.file_name || item.title}
                                                        <ExternalLink className="h-3 w-3" />
                                                    </a>
                                                ) : (
                                                    <span className="text-sm font-medium text-foreground">{item.file_name || item.title}</span>
                                                )}
                                                {item.description && (
                                                    <p className="text-xs text-muted-foreground truncate max-w-[200px]">{item.description}</p>
                                                )}
                                            </div>
                                        </div>
                                    </TableCell>
                                    {showRelated && (
                                        <TableCell className="text-sm text-foreground">
                                            {item.relatedName || '—'}
                                        </TableCell>
                                    )}
                                    <TableCell className="text-sm text-muted-foreground whitespace-nowrap">
                                        {formatDate(item.uploaded_at)}
                                    </TableCell>
                                    <TableCell>
                                        <Badge variant="secondary" className={`text-xs font-medium ${badge.color}`}>
                                            {badge.label}
                                        </Badge>
                                    </TableCell>
                                    <TableCell className="text-sm text-muted-foreground whitespace-nowrap">
                                        {formatDate(item.valid_until)}
                                    </TableCell>
                                    {canReview && (
                                        <TableCell className="text-right">
                                            <div className="flex gap-1 justify-end">
                                                {item.status === 'pending' && (
                                                    <Button
                                                        variant="ghost"
                                                        size="sm"
                                                        className="text-emerald-600 hover:text-emerald-700 hover:bg-emerald-50 dark:hover:bg-emerald-950/30 gap-1"
                                                        onClick={(e) => {
                                                            e.stopPropagation();
                                                            openReviewDialog(item.id, 'verified');
                                                        }}
                                                    >
                                                        <ShieldCheck className="h-3.5 w-3.5" />
                                                        Verify
                                                    </Button>
                                                )}
                                                {item.status === 'pending' && (
                                                    <Button
                                                        variant="ghost"
                                                        size="sm"
                                                        className="text-red-600 hover:text-red-700 hover:bg-red-50 dark:hover:bg-red-950/30 gap-1"
                                                        onClick={(e) => {
                                                            e.stopPropagation();
                                                            openReviewDialog(item.id, 'rejected');
                                                        }}
                                                    >
                                                        <XCircle className="h-3.5 w-3.5" />
                                                        Reject
                                                    </Button>
                                                )}
                                            </div>
                                        </TableCell>
                                    )}
                                </TableRow>
                            );
                        })}
                    </TableBody>
                </Table>
            </div>
        );
    };

    const renderCardView = () => {
        return (
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
                {items.map((item) => {
                    const badge = getStatusBadge(item.status, item.valid_until);
                    return (
                        <div 
                            key={item.id} 
                            className="rounded-xl border border-border bg-card p-4 space-y-4 hover:shadow-md transition-shadow cursor-pointer group"
                            onClick={() => handleRowClick(item)}
                        >
                            <div className="flex items-start justify-between gap-2">
                                <div className="flex items-start gap-3 min-w-0">
                                    <div className="p-2 bg-blue-50 dark:bg-blue-900/20 rounded-lg">
                                        <FileText className="h-5 w-5 text-blue-500" />
                                    </div>
                                    <div className="min-w-0">
                                        {item.file_url ? (
                                            <a
                                                href={item.file_url}
                                                target="_blank"
                                                rel="noopener noreferrer"
                                                className="text-sm font-semibold text-foreground hover:text-blue-600 hover:underline block truncate"
                                            >
                                                {item.file_name || item.title}
                                            </a>
                                        ) : (
                                            <span className="text-sm font-semibold text-foreground block truncate">{item.file_name || item.title}</span>
                                        )}
                                        <p className="text-xs text-muted-foreground">{formatDate(item.uploaded_at)}</p>
                                    </div>
                                </div>
                                <Badge variant="secondary" className={`text-[10px] px-1.5 py-0 font-medium whitespace-nowrap ${badge.color}`}>
                                    {badge.label}
                                </Badge>
                            </div>

                            <div className="text-xs space-y-1.5 border-t border-border pt-3">
                                {showRelated && (
                                    <div className="flex justify-between">
                                        <span className="text-muted-foreground">Related:</span>
                                        <span className="text-foreground font-medium">{item.relatedName || '—'}</span>
                                    </div>
                                )}
                                <div className="flex justify-between">
                                    <span className="text-muted-foreground">By:</span>
                                    <span className="text-foreground font-medium">{item.uploadedByName || '—'}</span>
                                </div>
                                <div className="flex justify-between">
                                    <span className="text-muted-foreground">Valid Until:</span>
                                    <span className="text-foreground font-medium">{formatDate(item.valid_until)}</span>
                                </div>
                            </div>

                            {canReview && (
                                <div className="pt-3 border-t border-border flex gap-2">
                                    {item.status === 'pending' && (
                                        <Button
                                            variant="outline"
                                            size="sm"
                                            className="flex-1 text-emerald-600 border-emerald-200 hover:bg-emerald-50 dark:border-emerald-900/30 dark:hover:bg-emerald-950/30 text-xs py-1 h-8"
                                            onClick={(e) => {
                                                e.stopPropagation();
                                                openReviewDialog(item.id, 'verified');
                                            }}
                                        >
                                            <ShieldCheck className="h-3.5 w-3.5 mr-1" />
                                            Verify
                                        </Button>
                                    )}
                                    {item.status === 'pending' && (
                                        <Button
                                            variant="outline"
                                            size="sm"
                                            className="flex-1 text-red-600 border-red-200 hover:bg-red-50 dark:border-red-900/30 dark:hover:bg-red-950/30 text-xs py-1 h-8"
                                            onClick={(e) => {
                                                e.stopPropagation();
                                                openReviewDialog(item.id, 'rejected');
                                            }}
                                        >
                                            <XCircle className="h-3.5 w-3.5 mr-1" />
                                            Reject
                                        </Button>
                                    )}
                                </div>
                            )}
                        </div>
                    );
                })}
            </div>
        );
    };

    // ── Render ──────────────────────────────────────────────────

    if (loading) {
        return (
            <div className="flex items-center justify-center py-12">
                <Loader2 className="h-6 w-6 animate-spin text-blue-600" />
                <span className="ml-2 text-sm text-muted-foreground">Loading evidence…</span>
            </div>
        );
    }

    if (items.length === 0) {
        return (
            <div className="text-center py-10 text-muted-foreground border border-dashed border-border rounded-xl">
                <FileText className="h-8 w-8 mx-auto mb-2 opacity-40" />
                <p className="text-sm">No evidence found</p>
            </div>
        );
    }

    return (
        <>
            {viewMode === 'table' ? renderTableView() : renderCardView()}

            {/* Detail Sheet */}
            <EvidenceDetailSheet
                evidence={selectedEvidence}
                open={detailSheetOpen}
                onOpenChange={setDetailSheetOpen}
                onDelete={handleDelete}
            />

            {/* Review Dialog */}
            <Dialog open={reviewDialogOpen} onOpenChange={setReviewDialogOpen}>
                <DialogContent>
                    <DialogHeader>
                        <DialogTitle>
                            {reviewTarget?.action === 'verified' ? 'Verify Evidence' : 'Reject Evidence'}
                        </DialogTitle>
                    </DialogHeader>
                    <div className="space-y-3 py-2">
                        <Textarea
                            placeholder="Add review notes (optional)…"
                            value={reviewNotes}
                            onChange={(e) => setReviewNotes(e.target.value)}
                            className="min-h-[100px]"
                        />
                    </div>
                    <DialogFooter>
                        <Button variant="outline" onClick={() => setReviewDialogOpen(false)}>
                            Cancel
                        </Button>
                        <Button
                            onClick={submitReview}
                            disabled={reviewing}
                            className={
                                reviewTarget?.action === 'verified'
                                    ? 'bg-emerald-600 hover:bg-emerald-700'
                                    : 'bg-red-600 hover:bg-red-700'
                            }
                        >
                            {reviewing
                                ? 'Submitting…'
                                : reviewTarget?.action === 'verified'
                                    ? 'Confirm Verify'
                                    : 'Confirm Reject'}
                        </Button>
                    </DialogFooter>
                </DialogContent>
            </Dialog>
        </>
    );
}
