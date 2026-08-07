
"use client";

import { useState, useEffect } from "react";
import { Button } from "@/components/ui/button";
import { 
  Select, 
  SelectContent, 
  SelectItem, 
  SelectTrigger, 
  SelectValue 
} from "@/components/ui/select";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { X, ShieldAlert, Link as LinkIcon, Plus, Loader2 } from "lucide-react";
import { isoService } from "@/lib/iso-service";
import { useAuth } from "@/hooks/useAuth";
import { toast } from "sonner"; 
import { fetchRisks } from "@/lib/data-service";
import { useApiData } from "@/hooks/use-api-data";
import { Risk } from "@/types";

export function RiskMapping({ 
  controlId, 
  riskIds = [], 
  onUpdate 
}: { 
  controlId: string, 
  riskIds?: string[], 
  onUpdate: () => void 
}) {
  const { user } = useAuth();
  const { data: allRisks, loading: risksLoading } = useApiData(fetchRisks);
  const [isLinking, setIsLinking] = useState(false);
  const [selectedRiskId, setSelectedRiskId] = useState("");
  const [loading, setLoading] = useState(false);

  const risks = allRisks ?? [];

  // Filter linked risks
  const linkedRisks = risks.filter(r => riskIds.includes(r.id));
  
  // Available risks (not yet linked)
  const availableRisks = risks.filter(r => !riskIds.includes(r.id));

  const canEdit = user?.role === 'admin' || user?.role === 'analyst';

  if (risksLoading) {
    return (
      <div className="flex items-center justify-center py-8">
        <Loader2 className="h-5 w-5 animate-spin text-blue-600" />
        <span className="ml-2 text-sm text-slate-600">Loading risks…</span>
      </div>
    );
  }

  const handleLink = async () => {
    if (!selectedRiskId || !user) return;

    setLoading(true);
    try {
      // 1. Persist to local storage (ISO service layer)
      await isoService.linkRiskToControl(controlId, selectedRiskId, {
        id: user.id,
        name: user.email,
        role: user.role
      });

      // 2. Bug 9: Also persist to the backend database so it survives page reload
      //    Backend: POST /risks/{riskId}/controls/  with { control_id: controlDbId }
      //    The controlId prop here is the annex string (e.g. "5.1") — we look up
      //    the control applicability record from the backend to get its DB UUID.
      try {
        const { api } = await import('@/lib/api-client');
        // Fetch control applicability records to find the DB UUID for this annex
        const caRecords = await api.get<any[]>('/control-applicability/');
        const caMatch = Array.isArray(caRecords)
          ? caRecords.find((ca: any) => ca.annex_id === controlId || ca.control_annex === controlId)
          : null;

        if (caMatch?.id) {
          // Create the risk → control mapping in the backend
          await api.post(`/risks/${selectedRiskId}/controls/`, {
            control_id: caMatch.id,
          });
        }
      } catch (backendErr) {
        // Non-fatal: local storage succeeded, backend sync failed
        console.warn('[RiskMapping] Backend sync failed (non-fatal):', backendErr);
      }

      toast.success("Risk linked successfully");
      setIsLinking(false);
      setSelectedRiskId("");
      onUpdate(); // triggers loadControl() in parent → refreshes riskIds prop
    } catch (error: any) {
      toast.error(error.message || "Failed to link risk");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-4">
      <div className="flex justify-between items-center">
        <h3 className="text-lg font-medium">Linked Risks ({linkedRisks.length})</h3>
        {canEdit && !isLinking && (
          <Button size="sm" variant="outline" onClick={() => setIsLinking(true)}>
            <LinkIcon className="w-4 h-4 mr-2" />
            Link Risk
          </Button>
        )}
      </div>

      {isLinking && (
        <Card className="bg-slate-50 border-dashed">
          <CardContent className="p-4 flex gap-4 items-end">
            <div className="flex-1 space-y-2">
              <label className="text-sm font-medium">Select Risk</label>
              <Select value={selectedRiskId} onValueChange={setSelectedRiskId}>
                <SelectTrigger>
                  <SelectValue placeholder="Choose a risk..." />
                </SelectTrigger>
                <SelectContent>
                  {availableRisks.length === 0 ? (
                    <SelectItem value="none" disabled>No available risks</SelectItem>
                  ) : (
                    availableRisks.map(r => (
                      <SelectItem key={r.id} value={r.id}>
                        {r.title} ({r.score})
                      </SelectItem>
                    ))
                  )}
                </SelectContent>
              </Select>
            </div>
            <Button onClick={handleLink} disabled={!selectedRiskId || loading}>
              Link
            </Button>
            <Button variant="ghost" onClick={() => setIsLinking(false)}>
              Cancel
            </Button>
          </CardContent>
        </Card>
      )}

      <div className="space-y-2">
        {linkedRisks.length === 0 ? (
           <div className="text-sm text-muted-foreground italic">No risks linked to this control.</div>
        ) : (
          linkedRisks.map(risk => (
            <div key={risk.id} className="flex items-center justify-between p-3 border border-border rounded-lg bg-card">
              <div className="flex items-center gap-3">
                 <ShieldAlert className={`h-5 w-5 ${
                   (risk.score || 0) >= 15 ? "text-red-500" : 
                   (risk.score || 0) >= 8 ? "text-amber-500" : "text-blue-500"
                 }`} />
                 <div>
                   <div className="font-medium text-sm text-foreground">{risk.title}</div>
                   <div className="text-xs text-muted-foreground">Score: {risk.score} | Impact: {risk.impact}</div>
                 </div>
              </div>
              <Badge variant="outline">{risk.status}</Badge>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
