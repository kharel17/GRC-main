"use client";

import { useApiData } from "@/hooks/use-api-data";
import { fetchAssets } from "@/lib/data-service";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Boxes, ShieldAlert, Database, Laptop, Server, HardDrive, Loader2 } from "lucide-react";
import type { Asset, AssetType, AssetCriticality, AssetClassification } from "@/types";

const AssetTypeIcon = ({ type }: { type: AssetType }) => {
  switch (type) {
    case 'data': return <Database className="h-4 w-4" />;
    case 'software': return <Server className="h-4 w-4" />;
    case 'hardware': return <Laptop className="h-4 w-4" />;
    case 'service': return <Globe className="h-4 w-4" />; // re-importing globe if needed or using fallback
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
  const { data: assets, loading } = useApiData(fetchAssets);

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
                      <AssetTypeIcon type={asset.assetType} />
                      {asset.assetType}
                    </div>
                  </TableCell>
                  <TableCell>
                    <Badge variant="outline" className="capitalize text-[10px] px-2 py-0">
                      {asset.classification}
                    </Badge>
                  </TableCell>
                  <TableCell>
                    <span className={`px-2 py-0.5 rounded-full text-[10px] font-bold uppercase ${getCriticalityColor(asset.criticality)}`}>
                      {asset.criticality}
                    </span>
                  </TableCell>
                  <TableCell className="text-xs text-muted-foreground">{asset.location || 'N/A'}</TableCell>
                  <TableCell>
                    <Badge variant={asset.status === 'active' ? 'secondary' : 'outline'} className="text-[10px]">
                      {asset.status}
                    </Badge>
                  </TableCell>
                </TableRow>
              ))}
              {(!assets || assets.length === 0) && (
                <TableRow>
                  <TableCell colSpan={6} className="text-center py-6 text-muted-foreground">
                    No assets found in the register.
                  </TableCell>
                </TableRow>
              )}
            </TableBody>
          </Table>
        </CardContent>
      </Card>
    </div>
  );
}

// Simple Globe mock if not imported from lucide-react above
const Globe = ({ className }: { className?: string }) => <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className={className}><circle cx="12" cy="12" r="10"/><line x1="2" y1="12" x2="22" y2="12"/><path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z"/></svg>;
