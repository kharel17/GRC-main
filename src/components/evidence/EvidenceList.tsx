'use client';

import { useState, useEffect, useCallback } from 'react';
import { api } from '@/lib/api-client';
import { useAuth } from '@/hooks/useAuth';
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
    Clock,
    Loader2,
} from 'lucide-react';
import { toast } from 'sonner';

// ── Types ───────────────────────────────────────────────────

interface EvidenceItem {
    id: string;
    title: string;
    description?: string;
    file_url?: string;
    file_name?: string;
    file_type?: string;
    file_size?: number;
    uploaded_by: string;
    uploaded_at: string;
    status?: string;
    valid_until?: string;
    verified?: boolean;
    verified_by?: string;
    verified_at?: string;
    related_to: string;
    related_id: string;
}

interface EvidenceListProps {
    relatedTo: 'control' | 'risk';
    relatedId: string;
    refreshKey?: number; // increment to trigger re-fetch
}

// ── Status helpers ──────────────────────────────────────────

const STATUS_CONFIG: Record<string, { label: string; color: string }> = {
    active: { label: 'Submitted', color: 'bg-blue-100 text-blue-700 dark:bg-blue-900/40 dark:text-blue-300' },
    expired: { label: 'Expired', color: 'bg-gray-100 text-gray-600 dark:bg-gray-800 dark:text-gray-400' },
    rejected: { label: 'Rejected', color: 'bg-red-100 text-red-700 dark:bg-red-900/40 dark:text-red-300' },
};

function getStatusBadge(status?: string, validUntil?: string): { label: string; color: string } {
    // Check for expiry
    if (validUntil && new Date(validUntil) < new Date()) {
        return STATUS_CONFIG.expired;
    }
    return STATUS_CONFIG[status || 'active'] || STATUS_CONFIG.active;
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

export function EvidenceList({ relatedTo, relatedId, refreshKey }: EvidenceListProps) {
    const { user, hasRole } = useAuth();
    const [items, setItems] = useState<EvidenceItem[]>([]);
    const [loading, setLoading] = useState(true);

    // Dialog state for verify/reject
    const [reviewDialogOpen, setReviewDialogOpen] = useState(false);
    const [reviewTarget, setReviewTarget] = useState<{ id: string; action: 'active' | 'rejected' } | null>(null);
    const [reviewNotes, setReviewNotes] = useState('');
    const [reviewing, setReviewing] = useState(false);

    const canReview = hasRole(['admin', 'manager']);

    const fetchEvidence = useCallback(async () => {
        try {
            setLoading(true);
            const data = await api.get<EvidenceItem[]>(`/evidence/?related_id=${relatedId}`);
            setItems(data);
        } catch (err) {
            console.error('Failed to load evidence', err);
        } finally {
            setLoading(false);
        }
    }, [relatedId]);

    useEffect(() => {
        if (relatedId) fetchEvidence();
    }, [relatedId, refreshKey, fetchEvidence]);

    const openReviewDialog = (evidenceId: string, action: 'active' | 'rejected') => {
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
            toast.success(reviewTarget.action === 'active' ? 'Evidence verified' : 'Evidence rejected');
            setReviewDialogOpen(false);
            fetchEvidence();
        } catch (err: any) {
            toast.error(err?.message || 'Failed to update status');
        } finally {
            setReviewing(false);
        }
    };

    // ── Render ──────────────────────────────────────────────

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
                <p className="text-sm">No evidence uploaded yet</p>
            </div>
        );
    }

    return (
        <>
            <div className="rounded-xl border border-border bg-card overflow-hidden">
                <Table>
                    <TableHeader>
                        <TableRow className="hover:bg-muted/50 border-border">
                            <TableHead className="text-muted-foreground">File</TableHead>
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
                                <TableRow key={item.id} className="hover:bg-muted/50 border-border">
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
                                                {item.status !== 'active' && (
                                                    <Button
                                                        variant="ghost"
                                                        size="sm"
                                                        className="text-emerald-600 hover:text-emerald-700 hover:bg-emerald-50 dark:hover:bg-emerald-950/30 gap-1"
                                                        onClick={() => openReviewDialog(item.id, 'active')}
                                                    >
                                                        <ShieldCheck className="h-3.5 w-3.5" />
                                                        Verify
                                                    </Button>
                                                )}
                                                {item.status !== 'rejected' && (
                                                    <Button
                                                        variant="ghost"
                                                        size="sm"
                                                        className="text-red-600 hover:text-red-700 hover:bg-red-50 dark:hover:bg-red-950/30 gap-1"
                                                        onClick={() => openReviewDialog(item.id, 'rejected')}
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

            {/* Review Dialog */}
            <Dialog open={reviewDialogOpen} onOpenChange={setReviewDialogOpen}>
                <DialogContent>
                    <DialogHeader>
                        <DialogTitle>
                            {reviewTarget?.action === 'active' ? 'Verify Evidence' : 'Reject Evidence'}
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
                                reviewTarget?.action === 'active'
                                    ? 'bg-emerald-600 hover:bg-emerald-700'
                                    : 'bg-red-600 hover:bg-red-700'
                            }
                        >
                            {reviewing
                                ? 'Submitting…'
                                : reviewTarget?.action === 'active'
                                    ? 'Confirm Verify'
                                    : 'Confirm Reject'}
                        </Button>
                    </DialogFooter>
                </DialogContent>
            </Dialog>
        </>
    );
}
