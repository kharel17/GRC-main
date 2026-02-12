
"use client";

import { useState, useEffect } from "react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Textarea } from "@/components/ui/textarea";
import { 
  Select, 
  SelectContent, 
  SelectItem, 
  SelectTrigger, 
  SelectValue 
} from "@/components/ui/select";
import { ChevronLeft, Save, Calendar, User, FileText, ShieldAlert } from "lucide-react";
import { isoService } from "@/lib/iso-service";
import { ISOControl, ISOControlStatus } from "@/types/iso27001";
import { useAuth } from "@/hooks/useAuth";
import { toast } from "sonner";
import Link from "next/link";
import { ISOEvidenceManager } from "./ISOEvidenceManager";
import { RiskMapping } from "./RiskMapping";
import { mockUsers } from "@/lib/mock-data"; 
import { Skeleton } from "@/components/ui/skeleton";

export function ISOControlDetail({ controlId }: { controlId: string }) {
  const { user } = useAuth();
  const [control, setControl] = useState<ISOControl | null>(null);
  const [loading, setLoading] = useState(true);
  const [status, setStatus] = useState<ISOControlStatus>("not_started");
  const [notes, setNotes] = useState("");
  const [ownerId, setOwnerId] = useState("");
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    loadControl();
  }, [controlId]);

  const loadControl = async () => {
    try {
      const data = await isoService.getControlById(controlId);
      if (data) {
        setControl(data);
        setStatus(data.status);
        setNotes(data.notes || "");
        setOwnerId(data.ownerId || "");
      }
    } catch (error) {
      console.error("Failed to load control", error);
      toast.error("Failed to load control details");
    } finally {
      setLoading(false);
    }
  };

  const handleSave = async () => {
    if (!control || !user) return;
    setSaving(true);
    try {
      // Update status & notes
      if (status !== control.status || notes !== (control.notes || "")) {
        await isoService.updateControlStatus(control.id, status, {
          id: user.id, name: user.email, role: user.role
        }, notes);
      }

      // Update owner if changed
      if (ownerId !== (control.ownerId || "")) {
         const owner = mockUsers.find(u => u.id === ownerId);
         if (owner) {
             await isoService.assignOwner(control.id, ownerId, owner.fullName, {
                 id: user.id, name: user.email, role: user.role
             });
         }
      }

      toast.success("Control updated successfully");
      loadControl(); // Reload to get updated timestamps etc.
    } catch (error: any) {
      toast.error(error.message || "Failed to update control");
    } finally {
      setSaving(false);
    }
  };

  if (loading) return <div className="space-y-6">
      <Skeleton className="h-8 w-1/3" />
      <Skeleton className="h-64 w-full" />
  </div>;

  if (!control) return <div>Control not found</div>;

  const canEdit = ["admin", "analyst"].includes(user?.role || "");

  // Review Workflow Logic (simple version)
  const nextReviewDate = control.nextReviewDate 
    ? new Date(control.nextReviewDate).toLocaleDateString() 
    : "Not scheduled";
  
  const isOverdue = control.nextReviewDate && new Date(control.nextReviewDate) < new Date();

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-2 text-sm text-muted-foreground mb-2">
        <Link href="/dashboard/iso27001/controls" className="hover:text-primary flex items-center gap-1">
          <ChevronLeft className="h-4 w-4" /> Back to Controls
        </Link>
        <span>/</span>
        <span>{control.id}</span>
      </div>

      <div className="flex flex-col md:flex-row justify-between gap-4 items-start">
        <div>
           <div className="flex items-center gap-3 mb-1">
             <h1 className="text-2xl font-bold text-foreground">{control.id} {control.title}</h1>
             <Badge variant="outline" className="text-sm">Annex {control.annex}</Badge>
           </div>
           <p className="text-muted-foreground max-w-3xl">{control.description}</p>
        </div>
        <div className="flex gap-2">
           {canEdit && (
             <Button onClick={handleSave} disabled={saving} className="min-w-[100px]">
               {saving ? "Saving..." : <><Save className="w-4 h-4 mr-2" /> Save Changes</>}
             </Button>
           )}
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2 space-y-6">
          <Tabs defaultValue="details" className="w-full">
            <TabsList className="w-full justify-start grid grid-cols-3 lg:w-auto">
              <TabsTrigger value="details">Details</TabsTrigger>
              <TabsTrigger value="evidence">Evidence ({control.evidenceIds?.length || 0})</TabsTrigger>
              <TabsTrigger value="risks">Risks ({control.riskIds?.length || 0})</TabsTrigger>
            </TabsList>
            
            <TabsContent value="details" className="mt-4 space-y-6">
              <Card>
                <CardHeader>
                  <CardTitle>Implementation Status</CardTitle>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                     <div className="space-y-2">
                       <label className="text-sm font-medium text-foreground">Current Status</label>
                       <Select 
                         value={status} 
                         onValueChange={(v) => setStatus(v as ISOControlStatus)}
                         disabled={!canEdit}
                       >
                         <SelectTrigger>
                           <SelectValue placeholder="Select status" />
                         </SelectTrigger>
                         <SelectContent>
                           <SelectItem value="not_started">Not Started</SelectItem>
                           <SelectItem value="in_progress">In Progress</SelectItem>
                           <SelectItem value="implemented">Implemented</SelectItem>
                           <SelectItem value="not_applicable">Not Applicable</SelectItem>
                         </SelectContent>
                       </Select>
                     </div>
                     <div className="space-y-2">
                       <label className="text-sm font-medium text-foreground">Owner</label>
                       <Select 
                         value={ownerId} 
                         onValueChange={setOwnerId}
                         disabled={!canEdit}
                       >
                         <SelectTrigger>
                           <SelectValue placeholder="Assign owner" />
                         </SelectTrigger>
                         <SelectContent>
                           <SelectItem value="unassigned">Unassigned</SelectItem>
                           {mockUsers.map(u => (
                             <SelectItem key={u.id} value={u.id}>{u.fullName}</SelectItem>
                           ))}
                         </SelectContent>
                       </Select>
                     </div>
                  </div>
                  
                  <div className="space-y-2">
                    <label className="text-sm font-medium text-foreground">Implementation Notes</label>
                    <Textarea 
                      value={notes} 
                      onChange={(e) => setNotes(e.target.value)}
                      placeholder="Describe how this control is implemented..."
                      className="min-h-[150px]"
                      disabled={!canEdit}
                    />
                  </div>
                </CardContent>
              </Card>

              {control.guidance && (
                <Card className="bg-muted/50 border-blue-200 dark:border-blue-900/50">
                  <CardHeader>
                     <CardTitle className="text-sm font-medium text-blue-700 dark:text-blue-400 flex items-center gap-2">
                        <FileText className="h-4 w-4" /> Implementation Guidance
                     </CardTitle>
                  </CardHeader>
                  <CardContent className="text-sm text-muted-foreground">
                    {control.guidance}
                  </CardContent>
                </Card>
              )}
            </TabsContent>

            <TabsContent value="evidence" className="mt-4">
               <ISOEvidenceManager controlId={control.id} />
            </TabsContent>

            <TabsContent value="risks" className="mt-4">
               <RiskMapping 
                 controlId={control.id} 
                 riskIds={control.riskIds} 
                 onUpdate={loadControl}
               />
            </TabsContent>
          </Tabs>
        </div>

        <div className="space-y-6">
           <Card>
             <CardHeader>
               <CardTitle className="text-sm font-medium uppercase tracking-wider text-muted-foreground">
                 Metadata
               </CardTitle>
             </CardHeader>
             <CardContent className="space-y-4">
                <div className="flex items-center justify-between">
                  <span className="text-sm text-muted-foreground">Clause</span>
                  <Badge variant="outline">{control.clauseId}</Badge>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-sm text-muted-foreground">Last Updated</span>
                  <span className="text-sm font-medium text-foreground">
                    {new Date(control.updatedAt).toLocaleDateString()}
                  </span>
                </div>
                 <div className="pt-4 border-t border-border">
                    <h4 className="text-sm font-medium mb-3 flex items-center gap-2 text-foreground">
                       <Calendar className="h-4 w-4 text-muted-foreground" /> Review Schedule
                    </h4>
                    <div className="space-y-2">
                       <div className="flex justify-between text-sm">
                          <span className="text-muted-foreground">Last Review</span>
                          <span className="text-foreground">{control.lastReviewDate ? new Date(control.lastReviewDate).toLocaleDateString() : 'Never'}</span>
                       </div>
                       <div className="flex justify-between text-sm">
                          <span className="text-muted-foreground">Next Due</span>
                          <span className={isOverdue ? "text-destructive font-medium" : "text-foreground"}>{nextReviewDate}</span>
                       </div>
                    </div>
                 </div>
                 {/* Audit Log / History Preview could go here */}
             </CardContent>
           </Card>
        </div>
      </div>
    </div>
  );
}
