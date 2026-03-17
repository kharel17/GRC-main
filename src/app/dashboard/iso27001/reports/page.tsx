
"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { ArrowLeft } from "lucide-react";
import { isoService } from "@/lib/iso-service";
import { ISOControl } from "@/types/iso27001";
import { Button } from "@/components/ui/button";
import { Download } from "lucide-react";
import { toast } from "sonner";
import { Skeleton } from "@/components/ui/skeleton";
import dynamic from "next/dynamic";

const ComplianceScoring = dynamic(
  () => import("@/features/iso27001/ComplianceScoring").then(mod => mod.ComplianceScoring),
  { ssr: false }
);

export default function ISOReportsPage() {
  const router = useRouter();
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
      <Button 
        variant="ghost" 
        size="sm" 
        onClick={() => router.push("/dashboard/iso27001")}
        className="gap-2 text-slate-600 -ml-2"
      >
        <ArrowLeft className="h-4 w-4" />
        Back to ISO 27001
      </Button>
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
