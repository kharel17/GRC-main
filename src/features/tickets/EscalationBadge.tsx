'use client';

import { Badge } from '@/components/ui/badge';
import { EscalationLevel } from '@/types/ticket';

const ESCALATION_CONFIG: Record<EscalationLevel, { label: string; color: string; bgColor: string }> = {
  1: { label: 'Team', color: 'text-sky-700 dark:text-sky-300', bgColor: 'bg-sky-100 dark:bg-sky-900/30 border-sky-200 dark:border-sky-800' },
  2: { label: 'Department', color: 'text-amber-700 dark:text-amber-300', bgColor: 'bg-amber-100 dark:bg-amber-900/30 border-amber-200 dark:border-amber-800' },
  3: { label: 'Executive', color: 'text-orange-700 dark:text-orange-300', bgColor: 'bg-orange-100 dark:bg-orange-900/30 border-orange-200 dark:border-orange-800' },
  4: { label: 'Board', color: 'text-red-700 dark:text-red-300', bgColor: 'bg-red-100 dark:bg-red-900/30 border-red-200 dark:border-red-800' },
};

interface EscalationBadgeProps {
  level: EscalationLevel;
  showLevel?: boolean;
}

const DEFAULT_CONFIG = { label: 'Unknown', color: 'text-slate-700 dark:text-slate-300', bgColor: 'bg-slate-100 dark:bg-slate-900/30 border-slate-200 dark:border-slate-800' };

export function EscalationBadge({ level, showLevel = true }: EscalationBadgeProps) {
  const config = ESCALATION_CONFIG[level] || DEFAULT_CONFIG;
  return (
    <Badge variant="outline" className={`${config.bgColor} ${config.color} text-xs font-medium border`}>
      {showLevel && <span className="mr-1 opacity-60">L{level}</span>}
      {config.label}
    </Badge>
  );
}
