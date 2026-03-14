'use client';

import { fetchControl } from '@/lib/data-service';
import { useApiData } from '@/hooks';
import { EditControlDialog } from '@/features/control/EditControlDialog';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { ArrowLeft, Edit, Loader2, Shield } from 'lucide-react';
import Link from 'next/link';
import { useCallback, useState } from 'react';
import { EvidenceDropzone } from '@/components/evidence/EvidenceDropzone';
import { EvidenceList } from '@/components/evidence/EvidenceList';

function getEffectivenessStyles(effectiveness: string) {
    switch (effectiveness) {
        case 'high': return 'bg-green-100 text-green-700';
        case 'medium': return 'bg-amber-100 text-amber-700';
        case 'low': return 'bg-red-100 text-red-700';
        default: return 'bg-slate-100 text-slate-700';
    }
}

function getStatusStyles(status: string) {
    switch (status) {
        case 'implemented': return 'bg-green-100 text-green-700';
        case 'under_review': return 'bg-blue-100 text-blue-700';
        case 'planned': return 'bg-amber-100 text-amber-700';
        default: return 'bg-slate-100 text-slate-700';
    }
}

function getTypeLabel(type: string) {
    switch (type) {
        case 'preventive': return { label: 'Preventive', color: 'bg-blue-100 text-blue-700' };
        case 'detective': return { label: 'Detective', color: 'bg-purple-100 text-purple-700' };
        case 'corrective': return { label: 'Corrective', color: 'bg-orange-100 text-orange-700' };
        default: return { label: type, color: 'bg-slate-100 text-slate-700' };
    }
}

export default function ControlDetailPage({ params }: { params: { id: string } }) {
    const fetcher = useCallback(() => fetchControl(params.id), [params.id]);
    const { data: control, loading, error, refetch } = useApiData(fetcher, [params.id]);
    const [editOpen, setEditOpen] = useState(false);
    const [evidenceRefresh, setEvidenceRefresh] = useState(0);

    if (loading) {
        return (
            <div className="flex items-center justify-center py-24">
                <Loader2 className="h-8 w-8 animate-spin text-blue-600" />
                <span className="ml-3 text-slate-600">Loading control…</span>
            </div>
        );
    }

    if (error || !control) {
        return (
            <div className="space-y-4">
                <Link href="/dashboard/controls" className="inline-flex items-center gap-2 text-blue-600 hover:underline">
                    <ArrowLeft className="h-4 w-4" />
                    Back to controls
                </Link>
                <p className="text-slate-600">Control not found</p>
            </div>
        );
    }

    const typeInfo = getTypeLabel(control.type || (control as any).controlType);

    return (
        <div className="space-y-6">
            <div className="flex items-center justify-between">
                <Link href="/dashboard/controls" className="inline-flex items-center gap-2 text-slate-600 hover:text-slate-900">
                    <ArrowLeft className="h-4 w-4" />
                    <span className="text-sm">Back to controls</span>
                </Link>
                <Button variant="outline" className="gap-2" onClick={() => setEditOpen(true)}>
                    <Edit className="h-4 w-4" />
                    Edit
                </Button>
            </div>

            <Card>
                <CardHeader className="pb-4">
                    <div className="space-y-4">
                        <div className="flex items-start gap-3">
                            <Shield className="h-6 w-6 text-blue-600 shrink-0 mt-1" />
                            <div>
                                <h1 className="text-2xl font-bold text-slate-900">{control.title}</h1>
                                <p className="text-slate-600 mt-2">{control.description}</p>
                            </div>
                        </div>

                        <div className="flex flex-wrap items-center gap-3">
                            <Badge className={typeInfo.color}>{typeInfo.label}</Badge>
                            <Badge className={getEffectivenessStyles(String(control.effectiveness || 'medium'))}>
                                Effectiveness: {String(control.effectiveness || 'N/A')}
                            </Badge>
                            <Badge className={getStatusStyles(control.status || 'planned')}>
                                {(control.status || 'planned').replace('_', ' ')}
                            </Badge>
                        </div>
                    </div>
                </CardHeader>

                <CardContent className="space-y-6 border-t border-slate-200 pt-6">
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                        <div className="bg-slate-50 p-4 rounded-lg">
                            <p className="text-xs text-slate-600 font-medium mb-2">Type</p>
                            <p className="font-medium text-slate-900 capitalize">{control.type || (control as any).controlType}</p>
                        </div>
                        <div className="bg-slate-50 p-4 rounded-lg">
                            <p className="text-xs text-slate-600 font-medium mb-2">Effectiveness</p>
                            <p className="font-medium text-slate-900 capitalize">{control.effectiveness}</p>
                        </div>
                        <div className="bg-slate-50 p-4 rounded-lg">
                            <p className="text-xs text-slate-600 font-medium mb-2">Owner</p>
                            <p className="font-medium text-slate-900">{control.ownerName || 'Unassigned'}</p>
                        </div>
                        <div className="bg-slate-50 p-4 rounded-lg">
                            <p className="text-xs text-slate-600 font-medium mb-2">Created</p>
                             <p className="font-medium text-slate-900">{new Date(control.created_at || '').toLocaleDateString()}</p>
                        </div>
                    </div>
                </CardContent>
            </Card>

            {/* ── Evidence ─────────────────────────── */}
            <Card>
                <CardHeader>
                    <CardTitle className="text-base">Supporting Evidence</CardTitle>
                </CardHeader>
                <CardContent className="space-y-4">
                    <EvidenceDropzone
                        relatedTo="control"
                        relatedId={params.id}
                        onUploadSuccess={() => setEvidenceRefresh((k) => k + 1)}
                    />
                    <EvidenceList
                        relatedTo="control"
                        relatedId={params.id}
                        refreshKey={evidenceRefresh}
                    />
                </CardContent>
            </Card>

            {/* ── Dialogs ─────────────────────────── */}
            <EditControlDialog
                open={editOpen}
                onOpenChange={setEditOpen}
                control={control}
                onSuccess={() => refetch()}
            />
        </div>
    );
}
