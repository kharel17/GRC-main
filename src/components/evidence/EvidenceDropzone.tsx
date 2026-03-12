'use client';

import { useCallback, useState } from 'react';
import { useDropzone } from 'react-dropzone';
import { api } from '@/lib/api-client';
import { Upload, CheckCircle2, AlertCircle, FileText, X } from 'lucide-react';
import { toast } from 'sonner';
import { handleApiError } from '@/lib/handle-api-error';

// ── Types ───────────────────────────────────────────────────

interface EvidenceDropzoneProps {
    relatedTo: 'control' | 'risk';
    relatedId: string;
    onUploadSuccess: () => void;
}

interface UploadState {
    status: 'idle' | 'selected' | 'uploading' | 'success' | 'error';
    progress: number;
    errorMessage?: string;
}

// ── Constants ───────────────────────────────────────────────

const ACCEPTED_TYPES: Record<string, string[]> = {
    'application/pdf': ['.pdf'],
    'image/png': ['.png'],
    'image/jpeg': ['.jpg', '.jpeg'],
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document': ['.docx'],
    'text/csv': ['.csv'],
    'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': ['.xlsx'],
};

const MAX_SIZE = 10 * 1024 * 1024; // 10 MB

function formatBytes(bytes: number): string {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

// ── Component ───────────────────────────────────────────────

export function EvidenceDropzone({ relatedTo, relatedId, onUploadSuccess }: EvidenceDropzoneProps) {
    const [selectedFile, setSelectedFile] = useState<File | null>(null);
    const [uploadState, setUploadState] = useState<UploadState>({ status: 'idle', progress: 0 });

    const onDrop = useCallback((acceptedFiles: File[]) => {
        if (acceptedFiles.length > 0) {
            setSelectedFile(acceptedFiles[0]);
            setUploadState({ status: 'selected', progress: 0 });
        }
    }, []);

    const { getRootProps, getInputProps, isDragActive, fileRejections } = useDropzone({
        onDrop,
        accept: ACCEPTED_TYPES,
        maxSize: MAX_SIZE,
        maxFiles: 1,
        multiple: false,
    });

    const handleUpload = async () => {
        if (!selectedFile) return;

        setUploadState({ status: 'uploading', progress: 20 });

        try {
            // Simulate progress steps
            setUploadState({ status: 'uploading', progress: 40 });

            await api.upload('/evidence/', selectedFile, {
                title: selectedFile.name,
                related_to: relatedTo,
                related_id: relatedId,
            });

            setUploadState({ status: 'success', progress: 100 });
            toast.success('Evidence uploaded successfully');
            onUploadSuccess();

            // Reset after 2 seconds
            setTimeout(() => {
                setSelectedFile(null);
                setUploadState({ status: 'idle', progress: 0 });
            }, 2000);
        } catch (error: unknown) {
            const errorMessage = handleApiError(error);
            setUploadState({ status: 'error', progress: 0, errorMessage: errorMessage });
            toast.error(errorMessage);
        }
    };

    const handleClear = () => {
        setSelectedFile(null);
        setUploadState({ status: 'idle', progress: 0 });
    };

    // ── Render ──────────────────────────────────────────────

    return (
        <div className="space-y-3">
            {/* Dropzone area */}
            <div
                {...getRootProps()}
                className={`
          relative border-2 border-dashed rounded-xl p-8 text-center cursor-pointer
          transition-all duration-200 ease-out
          ${isDragActive
                        ? 'border-blue-500 bg-blue-50/60 dark:bg-blue-950/20 scale-[1.01]'
                        : uploadState.status === 'success'
                            ? 'border-emerald-400 bg-emerald-50/60 dark:bg-emerald-950/20'
                            : uploadState.status === 'error'
                                ? 'border-red-400 bg-red-50/40 dark:bg-red-950/20'
                                : 'border-border hover:border-blue-400 hover:bg-muted/40'
                    }
        `}
            >
                <input {...getInputProps()} />

                {uploadState.status === 'success' ? (
                    <div className="flex flex-col items-center gap-2 text-emerald-600 dark:text-emerald-400">
                        <CheckCircle2 className="h-10 w-10" />
                        <p className="font-semibold">Upload Complete</p>
                    </div>
                ) : uploadState.status === 'error' ? (
                    <div className="flex flex-col items-center gap-2 text-red-600 dark:text-red-400">
                        <AlertCircle className="h-10 w-10" />
                        <p className="font-semibold">Upload Failed</p>
                        <p className="text-sm opacity-80">{uploadState.errorMessage}</p>
                    </div>
                ) : (
                    <div className="flex flex-col items-center gap-2">
                        <Upload className={`h-10 w-10 ${isDragActive ? 'text-blue-500' : 'text-muted-foreground'}`} />
                        <div>
                            <p className="font-medium text-foreground">
                                {isDragActive ? 'Drop your file here' : 'Drag & drop a file, or click to browse'}
                            </p>
                            <p className="text-xs text-muted-foreground mt-1">
                                PDF, PNG, JPG, DOCX, CSV, XLSX — Max 10 MB
                            </p>
                        </div>
                    </div>
                )}
            </div>

            {/* File rejection errors */}
            {fileRejections.length > 0 && (
                <p className="text-sm text-red-500">
                    {fileRejections[0].errors.map(e => e.message).join('. ')}
                </p>
            )}

            {/* Selected file preview & upload button */}
            {selectedFile && uploadState.status !== 'success' && (
                <div className="flex items-center justify-between gap-3 bg-muted/50 rounded-lg px-4 py-3 border border-border">
                    <div className="flex items-center gap-3 min-w-0">
                        <FileText className="h-5 w-5 text-blue-500 shrink-0" />
                        <div className="min-w-0">
                            <p className="text-sm font-medium text-foreground truncate">{selectedFile.name}</p>
                            <p className="text-xs text-muted-foreground">{formatBytes(selectedFile.size)}</p>
                        </div>
                    </div>

                    <div className="flex items-center gap-2 shrink-0">
                        {uploadState.status === 'uploading' ? (
                            <div className="flex items-center gap-3">
                                {/* Progress bar */}
                                <div className="w-24 h-2 bg-muted rounded-full overflow-hidden">
                                    <div
                                        className="h-full bg-blue-500 rounded-full transition-all duration-500"
                                        style={{ width: `${uploadState.progress}%` }}
                                    />
                                </div>
                                <span className="text-xs text-muted-foreground">{uploadState.progress}%</span>
                            </div>
                        ) : (
                            <>
                                <button
                                    onClick={(e) => { e.stopPropagation(); handleClear(); }}
                                    className="p-1.5 rounded-md hover:bg-muted transition-colors text-muted-foreground"
                                    title="Remove file"
                                >
                                    <X className="h-4 w-4" />
                                </button>
                                <button
                                    onClick={(e) => { e.stopPropagation(); handleUpload(); }}
                                    className="px-4 py-1.5 rounded-md bg-blue-600 text-white text-sm font-medium hover:bg-blue-700 transition-colors"
                                >
                                    Upload
                                </button>
                            </>
                        )}
                    </div>
                </div>
            )}
        </div>
    );
}
