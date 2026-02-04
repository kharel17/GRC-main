'use client';

import { Risk } from '@/types/risk';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { Badge } from '@/components/ui/badge';
import Link from 'next/link';
import { sortRisksByPriority, getStatusColor, getScoreBadgeColor } from './risk.logic';
import { AlertTriangle } from 'lucide-react';

interface RiskListProps {
  risks: Risk[];
  showCategory?: boolean;
}

export function RiskList({ risks, showCategory = true }: RiskListProps) {
  const sorted = sortRisksByPriority(risks);

  if (sorted.length === 0) {
    return (
      <div className="text-center py-12">
        <p className="text-slate-500">No risks found</p>
      </div>
    );
  }

  return (
    <div className="rounded-lg border border-slate-200 overflow-hidden">
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead className="w-1/3">Title</TableHead>
            {showCategory && <TableHead className="w-1/6">Category</TableHead>}
            <TableHead className="text-center">Score</TableHead>
            <TableHead className="text-center">L/I</TableHead>
            <TableHead>Status</TableHead>
            <TableHead>Owner</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {sorted.map((risk) => (
            <TableRow key={risk.id} className="hover:bg-slate-50">
              <TableCell>
                <Link
                  href={`/risks/${risk.id}`}
                  className="font-medium text-blue-600 hover:underline"
                >
                  {risk.title}
                </Link>
              </TableCell>
              {showCategory && (
                <TableCell>
                  <span
                    className="inline-block px-2 py-1 rounded text-xs font-medium"
                    style={{ backgroundColor: risk.category?.color + '20', color: risk.category?.color }}
                  >
                    {risk.category?.name}
                  </span>
                </TableCell>
              )}
              <TableCell>
                <div className="flex justify-center">
                  <Badge className={getScoreBadgeColor(risk.riskScore)}>
                    {risk.riskScore}
                  </Badge>
                </div>
              </TableCell>
              <TableCell className="text-center text-sm text-slate-600">
                {risk.likelihood}/{risk.impact}
              </TableCell>
              <TableCell>
                <Badge className={getStatusColor(risk.status)} variant="secondary">
                  {risk.status}
                </Badge>
              </TableCell>
              <TableCell className="text-sm text-slate-600">{risk.ownerName || '-'}</TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  );
}
