
"use client";

import { useEffect, useState } from "react";
import { ComplianceScoring } from "@/features/iso27001/ComplianceScoring";
import { isoService } from "@/lib/iso-service";
import { ISOControl } from "@/types/iso27001";
import { Button } from "@/components/ui/button";
import { Download } from "lucide-react";
import { toast } from "sonner";
import { Skeleton } from "@/components/ui/skeleton";

export default function ISOReportsPage() {
  const [controls, setControls] = useState<ISOControl[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    isoService.getControls().then(data => {
      setControls(data);
      setLoading(false);
    });
  }, []);

  const handleDownloadReport = () => {
    // Mock report generation
    const reportData = {
      generatedAt: new Date().toISOString(),
      totalControls: controls.length,
      implemented: controls.filter(c => c.status === 'implemented').length,
      details: controls.map(c => ({ id: c.id, title: c.title, status: c.status }))
    };
    
    // Create a Blob and download it
    const blob = new Blob([JSON.stringify(reportData, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `iso27001-report-${new Date().toISOString().split('T')[0]}.json`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
    
    toast.success("Report downloaded successfully");
  };

  if (loading) {
    return <div className="space-y-6">
       <Skeleton className="h-10 w-1/3" />
       <Skeleton className="h-[200px] w-full" />
       <Skeleton className="h-[300px] w-full" />
    </div>;
  }

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 mb-1">Compliance Reports</h1>
          <p className="text-sm text-slate-600">
            Detailed breakdown of ISO 27001 implementation status.
          </p>
        </div>
        <Button onClick={handleDownloadReport}>
          <Download className="w-4 h-4 mr-2" />
          Export Report
        </Button>
      </div>

      <ComplianceScoring controls={controls} />
      
      {/* Future: Add more report types here, like Audit Logs, Risk Coverage, etc. */}
    </div>
  );
}
