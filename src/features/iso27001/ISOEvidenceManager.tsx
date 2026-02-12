
"use client";

import { useState, useEffect } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { 
  Table, 
  TableBody, 
  TableCell, 
  TableHead, 
  TableHeader, 
  TableRow 
} from "@/components/ui/table";
import { 
  Dialog, 
  DialogContent, 
  DialogHeader, 
  DialogTitle, 
  DialogTrigger,
  DialogFooter,
} from "@/components/ui/dialog";
import { FileText, Upload, Trash2, Download, Eye } from "lucide-react";
import { isoService } from "@/lib/iso-service";
import { ISOEvidence } from "@/types/iso27001";
import { useAuth } from "@/hooks/useAuth";
import { toast } from "sonner"; // Assuming sonner is used based on list_dir
import { format } from "date-fns"; // Standard date formatting if available, or native

export function ISOEvidenceManager({ controlId }: { controlId: string }) {
  const { user } = useAuth();
  const [evidence, setEvidence] = useState<ISOEvidence[]>([]);
  const [loading, setLoading] = useState(true);
  const [uploadOpen, setUploadOpen] = useState(false);
  const [file, setFile] = useState<File | null>(null);
  const [description, setDescription] = useState("");
  const [uploading, setUploading] = useState(false);

  // RBAC
  const canUpload = user?.role === 'admin' || user?.role === 'analyst';
  const canDelete = user?.role === 'admin' || user?.role === 'analyst';

  useEffect(() => {
    loadEvidence();
  }, [controlId]);

  const loadEvidence = async () => {
    try {
      const data = await isoService.getEvidenceForControl(controlId);
      setEvidence(data);
    } catch (error) {
      console.error("Failed to load evidence", error);
    } finally {
      setLoading(false);
    }
  };

  const handleUpload = async () => {
    if (!file || !user) return;
    
    setUploading(true);
    try {
      await isoService.uploadEvidence(controlId, file, { 
        id: user.id, 
        name: user.email, // AuthUser only has email 
        role: user.role 
      }, description);
      
      toast.success("Evidence uploaded successfully");
      setUploadOpen(false);
      setFile(null);
      setDescription("");
      loadEvidence();
    } catch (error: any) {
      toast.error(error.message || "Failed to upload evidence");
    } finally {
      setUploading(false);
    }
  };

  const handleDelete = async (id: string) => {
    if (!user || !confirm("Are you sure you want to delete this evidence?")) return;

    try {
      await isoService.deleteEvidence(id, controlId, {
        id: user.id,
        name: user.email,
        role: user.role
      });
      toast.success("Evidence deleted");
      loadEvidence();
    } catch (error: any) {
      toast.error(error.message || "Failed to delete evidence");
    }
  };

  return (
    <div className="space-y-4">
      <div className="flex justify-between items-center">
        <h3 className="text-lg font-medium">Evidence ({evidence.length})</h3>
        {canUpload && (
          <Dialog open={uploadOpen} onOpenChange={setUploadOpen}>
            <DialogTrigger asChild>
              <Button size="sm">
                <Upload className="w-4 h-4 mr-2" />
                Upload Evidence
              </Button>
            </DialogTrigger>
            <DialogContent>
              <DialogHeader>
                <DialogTitle>Upload Evidence</DialogTitle>
              </DialogHeader>
              <div className="space-y-4 py-4">
                <div className="space-y-2">
                  <Label htmlFor="file">File</Label>
                  <Input 
                    id="file" 
                    type="file" 
                    onChange={(e) => setFile(e.target.files?.[0] || null)} 
                  />
                  <p className="text-xs text-slate-500">Max 10MB. PDF, DOCX, PNG, JPG supported.</p>
                </div>
                <div className="space-y-2">
                  <Label htmlFor="desc">Description</Label>
                  <Input 
                    id="desc" 
                    value={description} 
                    onChange={(e) => setDescription(e.target.value)}
                    placeholder="Brief description of this evidence"
                  />
                </div>
              </div>
              <DialogFooter>
                <Button variant="outline" onClick={() => setUploadOpen(false)}>Cancel</Button>
                <Button onClick={handleUpload} disabled={!file || uploading}>
                  {uploading ? "Uploading..." : "Upload"}
                </Button>
              </DialogFooter>
            </DialogContent>
          </Dialog>
        )}
      </div>

      <div className="rounded-md border border-border bg-card">
        <Table>
          <TableHeader>
            <TableRow className="hover:bg-muted/50 border-border">
              <TableHead className="text-muted-foreground">File Name</TableHead>
              <TableHead className="text-muted-foreground">Uploaded By</TableHead>
              <TableHead className="text-muted-foreground">Date</TableHead>
              <TableHead className="w-[100px]"></TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {evidence.length === 0 ? (
              <TableRow>
                <TableCell colSpan={4} className="text-center h-24 text-muted-foreground">
                  No evidence uploaded yet.
                </TableCell>
              </TableRow>
            ) : (
              evidence.map((item) => (
                <TableRow key={item.id} className="hover:bg-muted/50 border-border">
                  <TableCell>
                    <div className="flex items-center gap-2">
                      <FileText className="h-4 w-4 text-blue-500" />
                      <div className="flex flex-col">
                        <span className="font-medium text-sm text-foreground">{item.fileName}</span>
                        {item.description && <span className="text-xs text-muted-foreground">{item.description}</span>}
                      </div>
                    </div>
                  </TableCell>
                  <TableCell className="text-sm text-foreground">
                    {item.uploadedByName || item.uploadedBy}
                  </TableCell>
                  <TableCell className="text-sm text-muted-foreground">
                    {new Date(item.uploadedAt).toLocaleDateString()}
                  </TableCell>
                  <TableCell>
                    <div className="flex gap-1 justify-end">
                      <Button variant="ghost" size="icon" asChild className="hover:bg-muted">
                        <a href={item.fileUrl} target="_blank" rel="noopener noreferrer" download>
                          <Download className="h-4 w-4" />
                        </a>
                      </Button>
                      {canDelete && (
                        <Button 
                          variant="ghost" 
                          size="icon" 
                          className="text-destructive hover:text-destructive hover:bg-destructive/10"
                          onClick={() => handleDelete(item.id)}
                        >
                          <Trash2 className="h-4 w-4" />
                        </Button>
                      )}
                    </div>
                  </TableCell>
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
      </div>
    </div>
  );
}
