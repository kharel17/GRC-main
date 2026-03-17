
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
import { Input } from "@/components/ui/input";
import { 
  Select, 
  SelectContent, 
  SelectItem, 
  SelectTrigger, 
  SelectValue 
} from "@/components/ui/select";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Search, Filter, ArrowUpDown, ChevronRight } from "lucide-react";
import { isoService } from "@/lib/iso-service";
import { ISOControl, ISOControlStatus } from "@/types/iso27001";
import { useAuth } from "@/hooks/useAuth";
import Link from "next/link";
import { Skeleton } from "@/components/ui/skeleton";

export function ISOControlList() {
  const { user } = useAuth();
  const [controls, setControls] = useState<ISOControl[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState("");
  const [statusFilter, setStatusFilter] = useState<string>("all");
  const [clauseFilter, setClauseFilter] = useState<string>("all");

  useEffect(() => {
    loadControls();
  }, []);

  const loadControls = async () => {
    try {
      const data = await isoService.getControls();
      setControls(data);
    } catch (error) {
      console.error("Failed to load controls", error);
    } finally {
      setLoading(false);
    }
  };

  const filteredControls = controls.filter(control => {
    const matchesSearch = control.title.toLowerCase().includes(searchTerm.toLowerCase()) || 
                          control.id.includes(searchTerm) ||
                          control.description.toLowerCase().includes(searchTerm.toLowerCase());
    const matchesStatus = statusFilter === "all" || control.status === statusFilter;
    const matchesClause = clauseFilter === "all" || control.clauseId === clauseFilter;
    
    return matchesSearch && matchesStatus && matchesClause;
  });

  const getStatusBadge = (status: ISOControlStatus) => {
    switch (status) {
      case 'implemented':
        return <Badge className="bg-green-100 text-green-700 hover:bg-green-200 border-none">Implemented</Badge>;
      case 'in_progress':
        return <Badge className="bg-amber-100 text-amber-700 hover:bg-amber-200 border-none">In Progress</Badge>;
      case 'not_started':
        return <Badge className="bg-slate-100 text-slate-700 hover:bg-slate-200 border-none">Not Started</Badge>;
       case 'not_applicable':
        return <Badge className="bg-slate-100 text-slate-400 hover:bg-slate-200 border-none">N/A</Badge>;
      default:
        return <Badge variant="outline">{status}</Badge>;
    }
  };

  if (loading) {
    return <div className="space-y-4">
      <Skeleton className="h-10 w-full" />
      <Skeleton className="h-20 w-full" />
      <Skeleton className="h-20 w-full" />
    </div>;
  }

  // Group clauses for filter
  const clauses = Array.from(new Set(controls.map(c => c.clauseId))).sort();

  return (
    <div className="space-y-4">
      <div className="flex flex-col sm:flex-row gap-4 justify-between items-center">
        <div className="relative w-full sm:w-96">
          <Search className="absolute left-2 top-2.5 h-4 w-4 text-slate-500" />
          <Input 
            placeholder="Search controls..." 
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="pl-8"
          />
        </div>
        <div className="flex gap-2 w-full sm:w-auto">
          <Select value={statusFilter} onValueChange={setStatusFilter}>
            <SelectTrigger className="w-[150px]">
              <Filter className="w-4 h-4 mr-2" />
              <SelectValue placeholder="Status" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All Statuses</SelectItem>
              <SelectItem value="not_started">Not Started</SelectItem>
              <SelectItem value="in_progress">In Progress</SelectItem>
              <SelectItem value="implemented">Implemented</SelectItem>
            </SelectContent>
          </Select>

           <Select value={clauseFilter} onValueChange={setClauseFilter}>
            <SelectTrigger className="w-[150px]">
              <SelectValue placeholder="Clause" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All Clauses</SelectItem>
              {clauses.map(id => (
                <SelectItem key={id} value={id}>Clause {id}</SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
      </div>

      <div className="rounded-md border border-border bg-card">
        <Table>
          <TableHeader>
            <TableRow className="hover:bg-muted/50 border-border">
              <TableHead className="w-[80px] text-muted-foreground">ID</TableHead>
              <TableHead className="text-muted-foreground">Control Title</TableHead>
              <TableHead className="w-[120px] text-muted-foreground">Status</TableHead>
              <TableHead className="w-[100px] text-muted-foreground text-center">Evidence</TableHead>
              <TableHead className="w-[150px] text-muted-foreground">Owner</TableHead>
              <TableHead className="w-[50px]"></TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {filteredControls.length === 0 ? (
              <TableRow>
                <TableCell colSpan={6} className="text-center h-24 text-muted-foreground">
                  No controls found.
                </TableCell>
              </TableRow>
            ) : (
              filteredControls.map((control) => (
                <TableRow key={control.id} className="hover:bg-muted/50 border-border">
                  <TableCell className="font-medium text-muted-foreground">{control.id}</TableCell>
                  <TableCell>
                    <div className="font-medium text-foreground">{control.title}</div>
                    <div className="text-xs text-muted-foreground truncate max-w-[400px]">
                      {control.description}
                    </div>
                  </TableCell>
                  <TableCell>{getStatusBadge(control.status)}</TableCell>
                  <TableCell className="text-center">
                    <Badge variant="outline" className="font-mono bg-slate-50/50">
                      {control.evidenceCount || 0}
                    </Badge>
                  </TableCell>
                  <TableCell className="text-sm max-w-[150px] truncate">
                    {control.ownerName ? (
                       <span className="text-foreground">{control.ownerName}</span>
                    ) : (
                      <span className="text-muted-foreground italic text-xs">Unassigned</span>
                    )}
                  </TableCell>
                  <TableCell>
                    <Link href={`/dashboard/iso27001/controls/${control.id}`}>
                      <Button variant="ghost" size="sm" className="hover:bg-muted">
                        <ChevronRight className="h-4 w-4" />
                      </Button>
                    </Link>
                  </TableCell>
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
      </div>
      <div className="text-sm text-muted-foreground">
        Showing {filteredControls.length} of {controls.length} controls
      </div>
    </div>
  );
}
