import { Risk } from '@/types';

export function sortRisksByPriority(risks: Risk[]): Risk[] {
  return [...risks].sort((a, b) => {
    if (a.score !== b.score) {
      return (b.score || 0) - (a.score || 0);
    }
    return new Date(b.updated_at || b.created_at || '').getTime() - new Date(a.updated_at || a.created_at || '').getTime();
  });
}

export function filterRisksByStatus(risks: Risk[], status: string): Risk[] {
  if (status === 'all') return risks;
  return risks.filter((r) => r.status === status);
}

export function filterRisksByCategory(risks: Risk[], categoryId: string): Risk[] {
  if (categoryId === 'all') return risks;
  return risks.filter((r) => r.categoryId === categoryId);
}

export function getStatusColor(status: string): string {
  const colors: Record<string, string> = {
    identified: 'bg-blue-100 text-blue-700',
    assessed: 'bg-purple-100 text-purple-700',
    mitigated: 'bg-green-100 text-green-700',
    accepted: 'bg-slate-100 text-slate-700',
  };
  return colors[status] || 'bg-slate-100 text-slate-700';
}

export function getScoreBadgeColor(score: number): string {
  if (score >= 17) return 'bg-red-100 text-red-700';
  if (score >= 10) return 'bg-orange-100 text-orange-700';
  if (score >= 5) return 'bg-amber-100 text-amber-700';
  return 'bg-green-100 text-green-700';
}
