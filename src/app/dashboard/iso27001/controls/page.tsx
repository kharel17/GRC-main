
"use client";

import { useRouter } from "next/navigation";
import { ISOControlList } from "@/features/iso27001/ISOControlList";
import { Button } from "@/components/ui/button";
import { ArrowLeft } from "lucide-react";

export default function ISOControlsPage() {
  const router = useRouter();
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
      <div>
        <h1 className="text-2xl font-bold text-slate-900 mb-1">ISO 27001 Controls</h1>
        <p className="text-sm text-slate-600">
          Manage implementation status for Annex A controls.
        </p>
      </div>

      <ISOControlList />
    </div>
  );
}
