"use client";

import { useState } from "react";
import { useApiData } from "@/hooks";
import { fetchDocumentAnalyses, submitDocumentForAnalysis } from "@/lib/data-service";
import { DocumentAnalysis } from "@/types";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { FileUp, Search, CheckCircle2, AlertCircle, FileText, Loader2, Microscope } from "lucide-react";
import { Progress } from "@/components/ui/progress";

export default function DocumentAnalysisPage() {
  const { data: analyses, loading, refetch } = useApiData<DocumentAnalysis[]>(fetchDocumentAnalyses);
  const [isUploading, setIsUploading] = useState(false);

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
            <Card key={analysis.id} className="overflow-hidden">
              <div className="flex items-center gap-4 p-4">
                <div className="p-2 bg-muted rounded-lg">
                  <FileText className="h-6 w-6 text-muted-foreground" />
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center justify-between">
                    <h4 className="font-bold text-sm truncate">{analysis.fileName}</h4>
                    <Badge variant={analysis.status === 'completed' ? 'outline' : 'secondary'} className="text-[10px]">
                      {analysis.status}
                    </Badge>
                  </div>
                  <div className="flex items-center gap-4 mt-1 text-xs text-muted-foreground">
                    <span>{analysis.documentCategory || 'General'}</span>
                    <span>•</span>
                    <span>Analyzed on {analysis.analyzedAt || analysis.createdAt}</span>
                  </div>
                </div>
              </div>
              
              <CardContent className="bg-muted/30 p-4 border-t border-border grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <p className="text-[10px] font-bold text-muted-foreground uppercase flex items-center gap-1">
                    <CheckCircle2 className="h-3 w-3 text-green-500" />
                    Implemented Controls
                  </p>
                  <div className="space-y-1">
                    {analysis.implementedControls?.slice(0, 2).map((c: any, i: number) => (
                      <p key={i} className="text-xs font-medium truncate">{c.annex}: {c.title}</p>
                    ))}
                    {analysis.implementedControls && analysis.implementedControls.length > 2 && (
                      <p className="text-[10px] text-primary italic">+{analysis.implementedControls.length - 2} more controls</p>
                    )}
                  </div>
                </div>
                <div className="space-y-2">
                  <p className="text-[10px] font-bold text-muted-foreground uppercase flex items-center gap-1">
                    <AlertCircle className="h-3 w-3 text-amber-500" />
                    Identified Gaps
                  </p>
                  <div className="space-y-1">
                    {analysis.missingControls?.slice(0, 2).map((c: any, i: number) => (
                      <p key={i} className="text-xs font-medium truncate">{c.annex}: {c.title}</p>
                    ))}
                    {analysis.missingControls && analysis.missingControls.length > 2 && (
                      <p className="text-[10px] text-amber-600 italic">+{analysis.missingControls.length - 2} more potential gaps</p>
                    )}
                  </div>
                </div>
              </CardContent>
            </Card>
          ))}

          {(!analyses || analyses.length === 0) && !isUploading && (
            <div className="p-8 text-center border rounded-lg bg-muted/20">
              <p className="text-sm text-muted-foreground italic">No analysis history available.</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
