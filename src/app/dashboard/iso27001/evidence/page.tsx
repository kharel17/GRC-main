
"use client";

import { useState, useEffect } from "react";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow
} from "@/components/ui/table";
import { Button } from "@/components/ui/button";
import { Download, FileText, Search, ExternalLink } from "lucide-react";
import { Input } from "@/components/ui/input";
import { isoService } from "@/lib/iso-service";
import { ISOEvidence } from "@/types/iso27001";
import { Skeleton } from "@/components/ui/skeleton";
import Link from "next/link";

export default function ISOEvidencePage() {
  const [evidence, setEvidence] = useState<ISOEvidence[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState("");

  useEffect(() => {
    loadEvidence();
  }, []);

  const loadEvidence = async () => {
    try {
      const data = await isoService.getAllEvidence();
      setEvidence(data);
    } catch (error) {
      console.error("Failed to load evidence", error);
    } finally {
      setLoading(false);
    }
  };

  const filteredEvidence = evidence.filter(item =>
    item.fileName?.toLowerCase().includes(searchTerm.toLowerCase()) ||
    item.description?.toLowerCase().includes(searchTerm.toLowerCase()) ||
    item.controlId?.includes(searchTerm)
  );

  if (loading) {
    return <div className="space-y-4">
      <Skeleton className="h-10 w-full" />
      <Skeleton className="h-20 w-full" />
    </div>;
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-slate-900 mb-1">Evidence Repository</h1>
        <p className="text-sm text-slate-600">
          Centralized view of all evidence uploaded for ISO 27001 controls.
        </p>
      </div>

      <div className="flex items-center gap-4">
        <div className="relative w-full sm:w-96">
          <Search className="absolute left-2 top-2.5 h-4 w-4 text-slate-500" />
          <Input
            placeholder="Search evidence..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="pl-8"
          />
        </div>
      </div>

      <div className="rounded-md border bg-white">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>File Name</TableHead>
              <TableHead>Related Control</TableHead>
              <TableHead>Uploaded By</TableHead>
              <TableHead>Date</TableHead>
              <TableHead className="w-[100px]"></TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {filteredEvidence.length === 0 ? (
              <TableRow>
                <TableCell colSpan={5} className="text-center h-24 text-slate-500">
                  No evidence found.
                </TableCell>
              </TableRow>
            ) : (
              filteredEvidence.map((item) => (
                <TableRow key={item.id}>
                  <TableCell>
                    <div className="flex items-center gap-2">
                      <FileText className="h-4 w-4 text-blue-500" />
                      <div className="flex flex-col">
                        <span className="font-medium text-sm">{item.fileName}</span>
                        {item.description && <span className="text-xs text-slate-500">{item.description}</span>}
                      </div>
                    </div>
                  </TableCell>
                  <TableCell>
                    <Link href={`/dashboard/iso27001/controls/${item.controlId}`} className="flex items-center gap-1 text-blue-600 hover:underline">
                      {item.controlId} <ExternalLink className="h-3 w-3" />
                    </Link>
                  </TableCell>
                  <TableCell className="text-sm">{item.uploadedByName || item.uploadedBy}</TableCell>
                  <TableCell className="text-sm text-slate-500">
                    {new Date(item.uploadedAt).toLocaleDateString()}
                  </TableCell>
                  <TableCell>
                    <div className="flex justify-end">
                      <Button variant="ghost" size="icon" asChild>
                        <a href={item.fileUrl} target="_blank" rel="noopener noreferrer" download>
                          <Download className="h-4 w-4" />
                        </a>
                      </Button>
                    </div>
                  </TableCell>
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
      </div>
      <div className="text-sm text-slate-500">
        Showing {filteredEvidence.length} of {evidence.length} files
      </div>
    </div>
  );
}
