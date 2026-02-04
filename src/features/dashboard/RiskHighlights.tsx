import { Risk } from '@/types/risk';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { AlertTriangle } from 'lucide-react';

interface RiskHighlightsProps {
  risks: Risk[];
}

export function RiskHighlights({ risks }: RiskHighlightsProps) {
  const criticalRisks = risks.filter((r) => r.riskScore >= 17);
  const highRisks = risks.filter((r) => r.riskScore >= 10 && r.riskScore < 17);
  const mediumRisks = risks.filter((r) => r.riskScore >= 5 && r.riskScore < 10);
  const lowRisks = risks.filter((r) => r.riskScore < 5);

  const riskSummary = [
    { label: 'Critical', count: criticalRisks.length, color: 'bg-red-100 text-red-700' },
    { label: 'High', count: highRisks.length, color: 'bg-orange-100 text-orange-700' },
    { label: 'Medium', count: mediumRisks.length, color: 'bg-amber-100 text-amber-700' },
    { label: 'Low', count: lowRisks.length, color: 'bg-green-100 text-green-700' },
  ];

  return (
    <Card>
      <CardHeader className="pb-3">
        <CardTitle className="text-base font-semibold flex items-center gap-2">
          <AlertTriangle className="h-5 w-5 text-orange-600" />
          Risk Summary
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
          {riskSummary.map((item) => (
            <div
              key={item.label}
              className={`p-3 rounded-lg text-center ${item.color}`}
            >
              <div className="text-2xl font-bold">{item.count}</div>
              <div className="text-xs font-medium">{item.label}</div>
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}
