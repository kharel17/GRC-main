"use client";

import { mockEvidence } from "@/lib/mock-data";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Plus, FileText, CheckCircle2 } from "lucide-react";

export default function EvidencePage() {
  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 mb-1">Evidence</h1>
          <p className="text-sm text-slate-600">
            Supporting documentation for risks and controls
          </p>
        </div>
        <Button className="gap-2">
          <Plus className="h-4 w-4" />
          Upload Evidence
        </Button>
      </div>

      <div className="rounded-lg border border-slate-200 overflow-hidden">
        <Table>
          <TableHead>
            <TableRow>
              <TableHead>Title</TableHead>
              <TableHead>Related To</TableHead>
              <TableHead>Uploaded By</TableHead>
              <TableHead>Status</TableHead>
            </TableRow>
          </TableHead>
          <TableBody>
            {mockEvidence.map((item) => (
              <TableRow key={item.id}>
                <TableCell>
                  <div className="flex items-center gap-2">
                    <FileText className="h-4 w-4 text-slate-400" />
                    <div>
                      <p className="font-medium text-sm">{item.title}</p>
                      <p className="text-xs text-slate-500">{item.fileName}</p>
                    </div>
                  </div>
                </TableCell>
                <TableCell className="text-sm">{item.relatedName}</TableCell>
                <TableCell className="text-sm text-slate-600">
                  {item.uploadedByName}
                </TableCell>
                <TableCell>
                  {item.verified ? (
                    <Badge className="gap-1 bg-green-100 text-green-700">
                      <CheckCircle2 className="h-3 w-3" />
                      Verified
                    </Badge>
                  ) : (
                    <Badge variant="outline">Pending</Badge>
                  )}
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>
    </div>
  );
}
