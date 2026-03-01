"use client";

import { useState } from "react";
import { fetchRisks, getRiskCategories } from "@/lib/data-service";
import { useApiData } from "@/hooks/use-api-data";
import { RiskList } from "@/features/risk/RiskList";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Plus, LayoutGrid, List, AlertTriangle, Filter, Loader2 } from "lucide-react";
import Link from "next/link";
import { RoleGuard } from "@/components/auth/RoleGuard";

type ViewMode = 'table' | 'cards';

function getRiskLevel(score: number): 'high' | 'medium' | 'low' {
  if (score >= 12) return 'high';
  if (score >= 6) return 'medium';
  return 'low';
}

function getScoreStyles(score: number) {
  const level = getRiskLevel(score);
  switch (level) {
    case 'high':
      return 'bg-red-100 text-red-700 border-red-200';
    case 'medium':
      return 'bg-amber-100 text-amber-700 border-amber-200';
    case 'low':
      return 'bg-green-100 text-green-700 border-green-200';
  }
}

function getStatusStyles(status: string) {
  switch (status) {
    case 'identified':
      return 'bg-blue-100 text-blue-700';
    case 'assessed':
      return 'bg-purple-100 text-purple-700';
    case 'mitigated':
      return 'bg-green-100 text-green-700';
    case 'accepted':
      return 'bg-slate-100 text-slate-700';
    default:
      return 'bg-slate-100 text-slate-700';
  }
}

export default function RisksPage() {
  const { data: risks, loading, error } = useApiData(fetchRisks);
  const riskCategories = getRiskCategories();
  const [statusFilter, setStatusFilter] = useState<string>('all');
  const [categoryFilter, setCategoryFilter] = useState<string>('all');
  const [viewMode, setViewMode] = useState<ViewMode>('table');

  const allRisks = risks ?? [];

  const filteredRisks = allRisks.filter((risk) => {
    if (statusFilter !== 'all' && risk.status !== statusFilter) return false;
    if (categoryFilter !== 'all' && risk.categoryId !== categoryFilter) return false;
    return true;
  });

  const clearFilters = () => {
    setStatusFilter('all');
    setCategoryFilter('all');
  };

  const hasActiveFilters = statusFilter !== 'all' || categoryFilter !== 'all';

  if (loading) {
    return (
      <div className="flex items-center justify-center py-24">
        <Loader2 className="h-8 w-8 animate-spin text-blue-600" />
        <span className="ml-3 text-slate-600">Loading risks…</span>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex flex-col items-center justify-center py-24 text-center">
        <AlertTriangle className="h-12 w-12 text-red-400 mb-4" />
        <h3 className="text-sm font-medium text-slate-900 mb-1">Failed to load risks</h3>
        <p className="text-sm text-slate-500">{error.message}</p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 mb-1">Risks</h1>
          <p className="text-sm text-slate-600">
            Manage and assess organizational risks
          </p>
        </div>
        <RoleGuard allowedRoles={['admin', 'analyst']}>
          <Button className="gap-2 w-full sm:w-auto">
            <Plus className="h-4 w-4" />
            New Risk
          </Button>
        </RoleGuard>
      </div>

      {/* Filter Bar */}
      <div className="flex flex-col sm:flex-row gap-3 items-start sm:items-center justify-between">
        <div className="flex flex-wrap gap-2 items-center w-full sm:w-auto">
          <div className="flex items-center gap-2">
            <Filter className="h-4 w-4 text-slate-500" />
            <span className="text-sm text-slate-500 hidden sm:inline">Filters:</span>
          </div>
          
          <Select value={statusFilter} onValueChange={setStatusFilter}>
            <SelectTrigger className="w-[130px] h-9">
              <SelectValue placeholder="Status" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All Status</SelectItem>
              <SelectItem value="identified">Identified</SelectItem>
              <SelectItem value="assessed">Assessed</SelectItem>
              <SelectItem value="mitigated">Mitigated</SelectItem>
              <SelectItem value="accepted">Accepted</SelectItem>
            </SelectContent>
          </Select>

          <Select value={categoryFilter} onValueChange={setCategoryFilter}>
            <SelectTrigger className="w-[140px] h-9">
              <SelectValue placeholder="Category" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All Categories</SelectItem>
              {riskCategories.map((cat) => (
                <SelectItem key={cat.id} value={cat.id}>
                  {cat.name}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>

          {hasActiveFilters && (
            <Button variant="ghost" size="sm" onClick={clearFilters} className="text-slate-500">
              Clear
            </Button>
          )}
        </div>

        {/* View Toggle */}
        <div className="flex items-center gap-1 bg-slate-100 rounded-lg p-1">
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

      {/* Results Info */}
      <div className="text-sm text-slate-500">
        Showing {filteredRisks.length} of {allRisks.length} risks
      </div>

      {/* Empty State */}
      {filteredRisks.length === 0 ? (
        <Card className="border-dashed">
          <CardContent className="py-12 text-center">
            <AlertTriangle className="h-12 w-12 text-slate-300 mx-auto mb-4" />
            <h3 className="text-sm font-medium text-slate-900 mb-1">No risks found</h3>
            <p className="text-sm text-slate-500 mb-4">
              {hasActiveFilters
                ? 'Try adjusting your filters to see more results.'
                : 'Get started by creating your first risk assessment.'}
            </p>
            {hasActiveFilters && (
              <Button variant="outline" size="sm" onClick={clearFilters}>
                Clear Filters
              </Button>
            )}
          </CardContent>
        </Card>
      ) : viewMode === 'table' ? (
        <RiskList risks={filteredRisks} />
      ) : (
        /* Card View */
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {filteredRisks.map((risk) => (
            <Link key={risk.id} href={`/dashboard/risks/${risk.id}`}>
              <Card className="h-full hover:shadow-md transition-shadow cursor-pointer group">
                <CardContent className="pt-6 space-y-3">
                  <div className="flex items-start justify-between gap-2">
                    <h3 className="font-medium text-sm text-slate-900 group-hover:text-blue-600 transition-colors line-clamp-2">
                      {risk.title}
                    </h3>
                    <Badge className={`${getScoreStyles(risk.riskScore)} font-semibold shrink-0`}>
                      {risk.riskScore}
                    </Badge>
                  </div>
                  
                  <p className="text-xs text-slate-500 line-clamp-2">
                    {risk.description}
                  </p>
                  
                  <div className="flex flex-wrap gap-2">
                    {risk.category && (
                      <span
                        className="text-xs px-2 py-0.5 rounded-full font-medium"
                        style={{
                          backgroundColor: risk.category.color + '15',
                          color: risk.category.color,
                        }}
                      >
                        {risk.category.name}
                      </span>
                    )}
                    <Badge variant="outline" className={`text-xs ${getStatusStyles(risk.status)}`}>
                      {risk.status}
                    </Badge>
                  </div>
                  
                  <div className="flex items-center justify-between text-xs text-slate-500 pt-2 border-t">
                    <span>L:{risk.likelihood} × I:{risk.impact}</span>
                    <span>{risk.ownerName || 'Unassigned'}</span>
                  </div>
                </CardContent>
              </Card>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
