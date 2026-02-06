"use client";

import { useState, useEffect } from "react";
import { mockEvidence } from "@/lib/mock-data";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Plus, FileText, CheckCircle2, Clock, Filter, LayoutGrid, List } from "lucide-react";
import { RoleGuard } from "@/components/auth/RoleGuard";

type ViewMode = 'table' | 'cards';
type VerificationFilter = 'all' | 'verified' | 'pending';

function formatFileSize(bytes: number): string {
  if (bytes < 1024) return bytes + ' B';
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
  return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
}

export default function EvidencePage() {
  const [verificationFilter, setVerificationFilter] = useState<VerificationFilter>('all');
  const [viewMode, setViewMode] = useState<ViewMode>('table');
  const [isMobile, setIsMobile] = useState(false);

  useEffect(() => {
    const checkMobile = () => setIsMobile(window.innerWidth < 768);
    checkMobile();
    window.addEventListener('resize', checkMobile);
    return () => window.removeEventListener('resize', checkMobile);
  }, []);

  const filteredEvidence = mockEvidence.filter((item) => {
    if (verificationFilter === 'verified') return item.verified;
    if (verificationFilter === 'pending') return !item.verified;
    return true;
  });

  const filterButtons: { label: string; value: VerificationFilter; count: number }[] = [
    { label: 'All', value: 'all', count: mockEvidence.length },
    { label: 'Verified', value: 'verified', count: mockEvidence.filter(e => e.verified).length },
    { label: 'Pending', value: 'pending', count: mockEvidence.filter(e => !e.verified).length },
  ];

  // Auto-switch to cards on mobile
  const effectiveViewMode = isMobile ? 'cards' : viewMode;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 mb-1">Evidence</h1>
          <p className="text-sm text-slate-600">
            Supporting documentation for risks and controls
          </p>
        </div>
        <RoleGuard allowedRoles={['admin', 'analyst']}>
          <Button className="gap-2 w-full sm:w-auto">
            <Plus className="h-4 w-4" />
            Upload Evidence
          </Button>
        </RoleGuard>
      </div>

      {/* Filter Bar */}
      <div className="flex flex-col sm:flex-row gap-4 items-start sm:items-center justify-between">
        <div className="flex flex-wrap gap-2">
          {filterButtons.map((btn) => (
            <button
              key={btn.value}
              onClick={() => setVerificationFilter(btn.value)}
              className={`px-3 py-1.5 text-xs font-medium rounded-full transition-colors ${
                verificationFilter === btn.value
                  ? 'bg-blue-600 text-white'
                  : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
              }`}
            >
              {btn.label} ({btn.count})
            </button>
          ))}
        </div>

        {/* View Toggle (hidden on mobile) */}
        <div className="hidden md:flex items-center gap-1 bg-slate-100 rounded-lg p-1">
          <Button
            variant={viewMode === 'table' ? 'secondary' : 'ghost'}
            size="sm"
            className="h-8 px-3"
            onClick={() => setViewMode('table')}
          >
            <List className="h-4 w-4" />
          </Button>
          <Button
            variant={viewMode === 'cards' ? 'secondary' : 'ghost'}
            size="sm"
            className="h-8 px-3"
            onClick={() => setViewMode('cards')}
          >
            <LayoutGrid className="h-4 w-4" />
          </Button>
        </div>
      </div>

      {/* Results Count */}
      <div className="text-sm text-slate-500">
        Showing {filteredEvidence.length} of {mockEvidence.length} items
      </div>

      {/* Empty State */}
      {filteredEvidence.length === 0 ? (
        <Card className="border-dashed">
          <CardContent className="py-12 text-center">
            <FileText className="h-12 w-12 text-slate-300 mx-auto mb-4" />
            <h3 className="text-sm font-medium text-slate-900 mb-1">No evidence found</h3>
            <p className="text-sm text-slate-500">
              Upload documentation to support your risks and controls.
            </p>
          </CardContent>
        </Card>
      ) : effectiveViewMode === 'table' ? (
        <div className="rounded-lg border border-slate-200 overflow-hidden">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Title</TableHead>
                <TableHead>Related To</TableHead>
                <TableHead className="hidden sm:table-cell">Size</TableHead>
                <TableHead className="hidden md:table-cell">Uploaded By</TableHead>
                <TableHead>Status</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {filteredEvidence.map((item) => (
                <TableRow key={item.id} className="hover:bg-slate-50">
                  <TableCell>
                    <div className="flex items-center gap-2">
                      <FileText className="h-4 w-4 text-slate-400 flex-shrink-0" />
                      <div className="min-w-0">
                        <p className="font-medium text-sm truncate">{item.title}</p>
                        <p className="text-xs text-slate-500 truncate">{item.fileName}</p>
                      </div>
                    </div>
                  </TableCell>
                  <TableCell className="text-sm">{item.relatedName}</TableCell>
                  <TableCell className="text-sm text-slate-500 hidden sm:table-cell">
                    {formatFileSize(item.fileSize ?? 0)}
                  </TableCell>
                  <TableCell className="text-sm text-slate-600 hidden md:table-cell">
                    {item.uploadedByName}
                  </TableCell>
                  <TableCell>
                    {item.verified ? (
                      <Badge className="gap-1 bg-green-100 text-green-700">
                        <CheckCircle2 className="h-3 w-3" />
                        Verified
                      </Badge>
                    ) : (
                      <Badge variant="outline" className="gap-1">
                        <Clock className="h-3 w-3" />
                        Pending
                      </Badge>
                    )}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      ) : (
        /* Card View */
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {filteredEvidence.map((item) => (
            <Card key={item.id} className="hover:shadow-md transition-shadow">
              <CardContent className="pt-6 space-y-3">
                <div className="flex items-start gap-3">
                  <div className="p-2 bg-slate-100 rounded-lg">
                    <FileText className="h-5 w-5 text-slate-500" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="font-medium text-sm truncate">{item.title}</p>
                    <p className="text-xs text-slate-500 truncate">{item.fileName}</p>
                  </div>
                </div>
                
                <div className="text-xs text-slate-500 space-y-1">
                  <p>Related: {item.relatedName}</p>
                  <p>Size: {formatFileSize(item.fileSize ?? 0)}</p>
                  <p>By: {item.uploadedByName}</p>
                </div>

                <div className="pt-2 border-t">
                  {item.verified ? (
                    <Badge className="gap-1 bg-green-100 text-green-700">
                      <CheckCircle2 className="h-3 w-3" />
                      Verified by {item.verifiedByName}
                    </Badge>
                  ) : (
                    <Badge variant="outline" className="gap-1">
                      <Clock className="h-3 w-3" />
                      Pending verification
                    </Badge>
                  )}
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
