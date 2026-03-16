"use client";

import { useState } from "react";
import { useApiData } from "@/hooks";
import { fetchDocumentAnalyses, submitDocumentForAnalysis } from "@/lib/data-service";
import { DocumentAnalysis } from "@/types";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { FileUp, Search, CheckCircle2, AlertCircle, FileText, Loader2, Microscope, Plus, FilePlus, ChevronRight, Eye } from "lucide-react";
import { Progress } from "@/components/ui/progress";
import { DocumentAnalysisDetailsDialog } from "@/components/document-analysis/DocumentAnalysisDetailsDialog";
import { format } from 'date-fns';

export default function DocumentAnalysisPage() {
  const { data: analyses, loading, refetch } = useApiData<DocumentAnalysis[]>(fetchDocumentAnalyses);
  const [isUploading, setIsUploading] = useState(false);
  const [selectedAnalysis, setSelectedAnalysis] = useState<DocumentAnalysis | null>(null);
  const [detailsOpen, setDetailsOpen] = useState(false);

  const handleFileChange = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;

    setIsUploading(true);
    try {
      await submitDocumentForAnalysis(file);
      await refetch();
    } catch (error) {
      console.error("Upload failed:", error);
    } finally {
      setIsUploading(false);
    }
  };

  const triggerUpload = () => {
    document.getElementById("doc-upload-input")?.click();
  };

  const handleViewDetails = (analysis: DocumentAnalysis) => {
    setSelectedAnalysis(analysis);
    setDetailsOpen(true);
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center py-24">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
        <span className="ml-3 text-muted-foreground">Loading analysis history...</span>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight text-foreground">Document Analysis</h1>
        <p className="text-muted-foreground text-sm">Upload security policies and documents for AI-powered compliance GAP analysis.</p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <input 
          type="file" 
          id="doc-upload-input" 
          className="hidden" 
          accept=".pdf,.docx"
          onChange={handleFileChange}
        />
        <Card className="md:col-span-1 border-dashed border-2 hover:border-primary transition-colors cursor-pointer group" onClick={triggerUpload}>
          <CardContent className="flex flex-col items-center justify-center py-12 text-center">
            {isUploading ? (
              <div className="space-y-4 w-full px-8">
                <Loader2 className="h-10 w-10 animate-spin text-primary mx-auto" />
                <p className="text-sm font-medium">Analyzing document...</p>
                <Progress value={65} className="h-1" />
              </div>
            ) : (
              <>
                <div className="p-4 bg-primary/10 rounded-full mb-4 group-hover:bg-primary/20 transition-colors">
                  <FileUp className="h-8 w-8 text-primary" />
                </div>
                <h3 className="font-semibold text-lg">Upload Document</h3>
                <p className="text-sm text-muted-foreground mt-1 px-4">Drag and drop your PDF or Word document here to start analysis</p>
                <Button variant="outline" className="mt-6" onClick={(e) => { e.stopPropagation(); triggerUpload(); }}>Select File</Button>
              </>
            )}
          </CardContent>
        </Card>

        <div className="md:col-span-2 space-y-4">
          <h2 className="text-lg font-semibold flex items-center gap-2">
            <Microscope className="h-5 w-5 text-primary" />
            Recent Analyses
          </h2>
          
          {analyses?.map((analysis) => (
            <Card key={analysis.id} className="overflow-hidden hover:shadow-md transition-all group border-slate-200 dark:border-slate-800">
              <div className="flex items-center gap-4 p-5">
                <div className="p-3 bg-blue-50 dark:bg-blue-900/20 rounded-xl group-hover:scale-110 transition-transform">
                  <FileText className="h-6 w-6 text-blue-600 dark:text-blue-400" />
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center justify-between gap-4 mb-1">
                    <h4 className="font-bold text-base truncate text-slate-900 dark:text-slate-100">{analysis.fileName}</h4>
                    <Badge 
                      variant={analysis.status === 'completed' ? 'secondary' : 'outline'} 
                      className={analysis.status === 'completed' ? "bg-emerald-50 text-emerald-700 dark:bg-emerald-950/30 dark:text-emerald-400 border-none uppercase text-[10px]" : "uppercase text-[10px]"}
                    >
                      {analysis.status}
                    </Badge>
                  </div>
                  <div className="flex items-center gap-3 text-xs text-muted-foreground font-medium">
                    <span className="bg-slate-100 dark:bg-slate-800 px-2 py-0.5 rounded uppercase tracking-wide text-[9px]">
                      {analysis.documentCategory || 'General'}
                    </span>
                    <span>•</span>
                    <span className="flex items-center gap-1">
                      {analysis.analyzedAt || analysis.createdAt ? format(new Date(analysis.analyzedAt || analysis.createdAt!), 'MMM d, yyyy') : '—'}
                    </span>
                  </div>
                </div>
              </div>
              
              <CardContent className="bg-slate-50/50 dark:bg-slate-900/30 px-5 py-4 border-t border-slate-100 dark:border-slate-800">
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-6 mb-4">
                  <div className="space-y-3">
                    <p className="text-[10px] font-bold text-emerald-600 dark:text-emerald-400 uppercase tracking-widest flex items-center gap-1.5">
                      <CheckCircle2 className="h-3 w-3" />
                      Compliant Logic
                    </p>
                    <div className="space-y-1.5">
                      {analysis.implemented_controls && analysis.implemented_controls.length > 0 ? (
                        <>
                          {analysis.implemented_controls.slice(0, 2).map((c: any, i: number) => (
                            <div key={i} className="flex items-center gap-2 group/item">
                              <div className="w-1 h-1 rounded-full bg-emerald-500" />
                              <p className="text-xs font-semibold truncate text-slate-700 dark:text-slate-300">
                                <span className="font-mono text-[10px] opacity-70 mr-1">{c.annex}</span>
                                {c.title}
                              </p>
                            </div>
                          ))}
                          {analysis.implemented_controls.length > 2 && (
                            <p className="text-[10px] text-emerald-600 font-bold ml-3">+{analysis.implemented_controls.length - 2} more findings</p>
                          )}
                        </>
                      ) : (
                        <p className="text-[10px] text-muted-foreground italic ml-3">No matches found</p>
                      )}
                    </div>
                  </div>
                  <div className="space-y-3">
                    <p className="text-[10px] font-bold text-amber-600 dark:text-amber-400 uppercase tracking-widest flex items-center gap-1.5">
                      <AlertCircle className="h-3 w-3" />
                      Identified Gaps
                    </p>
                    <div className="space-y-1.5">
                      {analysis.missing_controls && analysis.missing_controls.length > 0 ? (
                        <>
                          {analysis.missing_controls.slice(0, 2).map((c: any, i: number) => (
                            <div key={i} className="flex items-center gap-2">
                              <div className="w-1 h-1 rounded-full bg-amber-500" />
                              <p className="text-xs font-semibold truncate text-slate-700 dark:text-slate-300">
                                <span className="font-mono text-[10px] opacity-70 mr-1">{c.annex}</span>
                                {c.title}
                              </p>
                            </div>
                          ))}
                          {analysis.missing_controls.length > 2 && (
                            <p className="text-[10px] text-amber-600 font-bold ml-3">+{analysis.missing_controls.length - 2} potential gaps</p>
                          )}
                        </>
                      ) : (
                        <p className="text-[10px] text-muted-foreground italic ml-3">No gaps identified</p>
                      )}
                    </div>
                  </div>
                </div>

                <div className="flex justify-end pt-2 border-t border-slate-100 dark:border-slate-800 mt-2">
                  <Button 
                    variant="ghost" 
                    size="sm" 
                    className="text-primary hover:bg-primary/5 gap-2 font-bold uppercase tracking-wide text-[10px]"
                    onClick={() => handleViewDetails(analysis)}
                  >
                    <Eye className="h-3.5 w-3.5" />
                    View Full Analysis
                    <ChevronRight className="h-3 w-3" />
                  </Button>
                </div>
              </CardContent>
            </Card>
          ))}

          {(!analyses || analyses.length === 0) && !isUploading && (
            <div className="py-20 text-center border-2 border-dashed border-slate-200 dark:border-slate-800 rounded-xl bg-card">
              <FilePlus className="h-12 w-12 text-slate-300 dark:text-slate-600 mx-auto mb-4" />
              <h3 className="text-sm font-medium text-slate-900 dark:text-slate-100 mb-1">No documents analyzed yet</h3>
              <p className="text-sm text-slate-500 dark:text-slate-400 mb-6">
                Upload policies to see how they align with ISO 27001
              </p>
              <Button onClick={triggerUpload} className="gap-2">
                <Plus className="h-4 w-4" />
                Upload for Analysis
              </Button>
            </div>
          )}
        </div>
      </div>

      <DocumentAnalysisDetailsDialog
        analysis={selectedAnalysis}
        open={detailsOpen}
        onOpenChange={setDetailsOpen}
      />
    </div>
  );
}
