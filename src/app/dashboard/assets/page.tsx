"use client";

import { useState } from "react";
import { useApiData } from "@/hooks/use-api-data";
import { fetchAssets, fetchRisks, linkRiskToAsset, unlinkRiskFromAsset } from "@/lib/data-service";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Boxes, ShieldAlert, Database, Laptop, Server, HardDrive, Loader2, Link, Plus, X, Globe, AlertTriangle } from "lucide-react";
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle, DialogTrigger, DialogFooter } from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { toast } from "sonner";
import { RoleGuard } from "@/components/auth/RoleGuard";
import { NewAssetDialog } from "@/features/asset/NewAssetDialog";
import type { Asset, AssetType, AssetCriticality, AssetClassification, TicketActivity } from "@/types";
import { Ticket } from "@/types"; // Just in case, ensuring they are exported from index.ts

const AssetTypeIcon = ({ type }: { type: AssetType }) => {
  switch (type) {
    case 'data': return <Database className="h-4 w-4" />;
    case 'software': return <Server className="h-4 w-4" />;
    case 'hardware': return <Laptop className="h-4 w-4" />;
    case 'service': return <Globe className="h-4 w-4" />;
    default: return <HardDrive className="h-4 w-4" />;
  }
};

const getCriticalityColor = (crit: AssetCriticality) => {
  switch (crit) {
    case 'critical': return 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-300';
    case 'high': return 'bg-orange-100 text-orange-700 dark:bg-orange-900/30 dark:text-orange-300';
    case 'medium': return 'bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-300';
    case 'low': return 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300';
    default: return 'bg-slate-100 text-slate-700 dark:bg-slate-900/30 dark:text-slate-300';
  }
};

export default function AssetsPage() {
  const { data: assets, loading, refetch: refetchAssets } = useApiData(fetchAssets);
  const { data: risks } = useApiData(fetchRisks);
  
  const [isLinking, setIsLinking] = useState(false);
  const [selectedAssetId, setSelectedAssetId] = useState<string | null>(null);
  const [selectedRiskId, setSelectedRiskId] = useState<string>("");
  const [linking, setLinking] = useState(false);
  const [isRegistering, setIsRegistering] = useState(false);

  const handleLinkRisk = async () => {
    if (!selectedAssetId || !selectedRiskId) return;
    setLinking(true);
    try {
      await linkRiskToAsset(selectedAssetId, selectedRiskId);
      toast.success("Risk linked to asset successfully");
      setIsLinking(false);
      refetchAssets();
    } catch (error) {
      toast.error("Failed to link risk");
    } finally {
      setLinking(false);
    }
  };

  const handleUnlinkRisk = async (assetId: string, riskId: string) => {
    try {
      await unlinkRiskFromAsset(assetId, riskId);
      toast.success("Risk unlinked");
      refetchAssets();
    } catch (error) {
      toast.error("Failed to unlink risk");
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center py-24">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
        <span className="ml-3 text-muted-foreground">Loading assets...</span>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Asset Identification</h1>
          <p className="text-muted-foreground text-sm">Inventory of all critical organizational assets and their classifications.</p>
        </div>
        <RoleGuard allowedRoles={['admin', 'analyst']}>
          <Button onClick={() => setIsRegistering(true)} className="gap-2">
            <Plus className="h-4 w-4" />
            Register Asset
          </Button>
        </RoleGuard>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <Card>
          <CardContent className="pt-6">
            <div className="text-2xl font-bold">{assets?.length || 0}</div>
            <p className="text-xs text-muted-foreground">Total Assets</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6">
            <div className="text-2xl font-bold text-red-600">
              {assets?.filter(a => a.criticality === 'critical').length || 0}
            </div>
            <p className="text-xs text-muted-foreground">Critical Assets</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6">
            <div className="text-2xl font-bold text-orange-600">
              {assets?.filter(a => a.classification === 'restricted').length || 0}
            </div>
            <p className="text-xs text-muted-foreground">Restricted Data Items</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6">
            <div className="text-2xl font-bold text-green-600">
              {assets?.filter(a => a.status === 'active').length || 0}
            </div>
            <p className="text-xs text-muted-foreground">Active Assets</p>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-lg flex items-center gap-2">
            <Boxes className="h-5 w-5 text-primary" />
            Asset Register
          </CardTitle>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Asset Name</TableHead>
                <TableHead>Type</TableHead>
                <TableHead>Classification</TableHead>
                <TableHead>Criticality</TableHead>
                <TableHead>Location</TableHead>
                <TableHead>Status</TableHead>
                <TableHead>Linked Risks</TableHead>
                <TableHead className="text-right">Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {assets?.map((asset) => (
                <TableRow key={asset.id}>
                  <TableCell className="font-medium">
                    <div>
                      {asset.name}
                      <p className="text-xs text-muted-foreground font-normal line-clamp-1">{asset.description}</p>
                    </div>
                  </TableCell>
                  <TableCell>
                    <div className="flex items-center gap-1.5 capitalize text-sm">
                      <AssetTypeIcon type={asset.type || 'data'} />
                      {asset.type || 'N/A'}
                    </div>
                  </TableCell>
                  <TableCell>
                    <Badge variant="outline" className="capitalize text-[10px] px-2 py-0">
                      {asset.classification || 'internal'}
                    </Badge>
                  </TableCell>
                  <TableCell>
                    <span className={`px-2 py-0.5 rounded-full text-[10px] font-bold uppercase ${getCriticalityColor(asset.criticality || 'medium' as any)}`}>
                      {asset.criticality || 'medium'}
                    </span>
                  </TableCell>
                  <TableCell className="text-xs text-muted-foreground">{asset.location || 'N/A'}</TableCell>
                  <TableCell>
                    <Badge variant={asset.status === 'active' ? 'secondary' : 'outline'} className="text-[10px]">
                      {asset.status}
                    </Badge>
                  </TableCell>
                  <TableCell>
                    <div className="flex flex-wrap gap-1">
                      {asset.related_risks && asset.related_risks.length > 0 ? (
                        asset.related_risks.map((riskId: string) => {
                          const risk = risks?.find(r => r.id === riskId);
                          return (
                            <Badge key={riskId} variant="outline" className="text-[9px] gap-1 bg-amber-50 text-amber-700 border-amber-200 pr-1">
                              {risk?.title || 'Unknown Risk'}
                              <button onClick={() => handleUnlinkRisk(asset.id, riskId)} className="hover:text-red-600">
                                <X className="h-2 w-2" />
                              </button>
                            </Badge>
                          );
                        })
                      ) : (
                        <span className="text-[10px] text-muted-foreground italic">None</span>
                      )}
                    </div>
                  </TableCell>
                  <TableCell className="text-right">
                    <Button 
                      variant="ghost" 
                      size="sm" 
                      className="h-8 w-8 p-0"
                      onClick={() => {
                        setSelectedAssetId(asset.id);
                        setIsLinking(true);
                      }}
                    >
                      <Link className="h-4 w-4" />
                    </Button>
                  </TableCell>
                </TableRow>
              ))}
              {(!assets || assets.length === 0) && (
                <TableRow>
                  <TableCell colSpan={8} className="text-center py-20">
                    <Boxes className="h-12 w-12 text-slate-300 dark:text-slate-600 mx-auto mb-4" />
                    <h3 className="text-sm font-medium text-slate-900 dark:text-slate-100 mb-1">No assets registered</h3>
                    <p className="text-sm text-slate-500 dark:text-slate-400 mb-6">
                      Register hardware, software, and data assets to assess their risk
                    </p>
                    <RoleGuard allowedRoles={['admin', 'analyst']}>
                      <Button onClick={() => setIsRegistering(true)} className="gap-2">
                        <Plus className="h-4 w-4" />
                        Register First Asset
                      </Button>
                    </RoleGuard>
                  </TableCell>
                </TableRow>
              )}
            </TableBody>
          </Table>
        </CardContent>
      </Card>

      <Dialog open={isLinking} onOpenChange={setIsLinking}>
        <DialogContent className="sm:max-width-[425px]">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <AlertTriangle className="h-5 w-5 text-amber-500" />
              Link Risk to Asset
            </DialogTitle>
            <DialogDescription>
              Associate a known risk with this asset to inform compliance scoring.
            </DialogDescription>
          </DialogHeader>
          <div className="py-4 space-y-4">
            <div className="space-y-2">
              <label className="text-sm font-medium">Select Risk</label>
              <Select value={selectedRiskId} onValueChange={setSelectedRiskId}>
                <SelectTrigger>
                  <SelectValue placeholder="Choose a risk from the register..." />
                </SelectTrigger>
                <SelectContent>
                  {risks?.map((risk) => (
                    <SelectItem key={risk.id} value={risk.id}>
                      <span className="flex items-center gap-2 text-xs">
                        <Badge variant="outline" className="text-[8px] uppercase">Score: {risk.score}</Badge>
                        {risk.title}
                      </span>
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setIsLinking(false)}>Cancel</Button>
            <Button onClick={handleLinkRisk} disabled={!selectedRiskId || linking}>
              {linking && <Loader2 className="h-4 w-4 mr-2 animate-spin" />}
              Link Risk
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <NewAssetDialog 
        open={isRegistering} 
        onOpenChange={setIsRegistering} 
        onSuccess={refetchAssets} 
      />
    </div>
  );
}

