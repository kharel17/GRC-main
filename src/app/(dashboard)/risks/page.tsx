'use client';

import { mockRisks } from '@/lib/mock-data';
import { RiskList } from '@/features/risk/RiskList';
import { Button } from '@/components/ui/button';
import { Plus } from 'lucide-react';

export default function RisksPage() {
  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 mb-1">Risks</h1>
          <p className="text-sm text-slate-600">Manage and assess organizational risks</p>
        </div>
        <Button className="gap-2">
          <Plus className="h-4 w-4" />
          New Risk
        </Button>
      </div>

      <RiskList risks={mockRisks} />
    </div>
  );
}
