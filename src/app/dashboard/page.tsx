"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";

import { mockRisks, mockControls, mockComplianceItems } from "@/lib/mock-data";
import { DashboardSummary } from "@/features/dashboard/DashboardSummary";
import { RiskHighlights } from "@/features/dashboard/RiskHighlights";
import { OverdueItems } from "@/features/dashboard/OverdueItems";

export default function DashboardPage() {
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const router = useRouter();

  useEffect(() => {
    const user = localStorage.getItem("grc_user");

    if (!user) {
      router.push("/login");
    } else {
      setIsAuthenticated(true);
    }
  }, [router]);

  if (!isAuthenticated) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <p className="text-slate-600">Loading...</p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-slate-900 mb-1">Dashboard</h1>
        <p className="text-sm text-slate-600">Risk and compliance overview</p>
      </div>

      <DashboardSummary
        risks={mockRisks}
        controls={mockControls}
        complianceItems={mockComplianceItems}
      />

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2">
          <RiskHighlights risks={mockRisks} />
        </div>
        <div>
          <OverdueItems complianceItems={mockComplianceItems} />
        </div>
      </div>
    </div>
  );
}
