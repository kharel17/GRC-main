"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/hooks/useAuth";
import { api } from "@/lib/api-client";
import {
  Building2,
  Users,
  Server,
  Database,
  ChevronRight,
  CheckCircle2,
  Loader2,
} from "lucide-react";

const STEPS = [
  { id: 1, title: "Organization", icon: Building2 },
  { id: 2, title: "Industry & Size", icon: Users },
  { id: 3, title: "Infrastructure", icon: Server },
  { id: 4, title: "Data Types", icon: Database },
];

const INDUSTRIES = [
  "Technology",
  "Healthcare",
  "Finance",
  "Retail",
  "Manufacturing",
  "Other",
];

const EMPLOYEE_COUNTS = [
  "1-50",
  "51-200",
  "201-1000",
  "1000+",
];

export default function OnboardingPage() {
  const router = useRouter();
  const { isLoading: authLoading, isAuthenticated } = useAuth();

  const [step, setStep] = useState(1);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState("");

  // Form data
  const [organizationName, setOrganizationName] = useState("");
  const [industry, setIndustry] = useState("");
  const [employeeCount, setEmployeeCount] = useState("");
  const [infrastructure, setInfrastructure] = useState("");
  const [dataTypes, setDataTypes] = useState("");

  // Redirect if not authenticated
  useEffect(() => {
    if (!authLoading && !isAuthenticated) {
      router.push("/login");
    }
  }, [authLoading, isAuthenticated, router]);

  // Check if onboarding already completed
  useEffect(() => {
    async function checkOnboarding() {
      try {
        const status = await api.get<{ completed: boolean }>("/onboarding/status");
        if (status.completed) {
          router.push("/dashboard");
        }
      } catch {
        // Ignore — if the endpoint fails, show onboarding anyway
      }
    }
    if (isAuthenticated) {
      checkOnboarding();
    }
  }, [isAuthenticated, router]);

  const canAdvance = () => {
    switch (step) {
      case 1:
        return organizationName.trim().length > 0;
      case 2:
        return industry && employeeCount;
      case 3:
        return infrastructure.trim().length > 0;
      case 4:
        return dataTypes.trim().length > 0;
      default:
        return false;
    }
  };

  const handleSubmit = async () => {
    setIsSubmitting(true);
    setError("");

    try {
      await api.post("/onboarding/complete", {
        organization_name: organizationName,
        industry,
        employee_count: employeeCount,
        infrastructure,
        data_types: dataTypes,
      });
      router.push("/dashboard");
    } catch (err: any) {
      setError(err?.message || "Failed to complete onboarding. Please try again.");
      setIsSubmitting(false);
    }
  };

  if (authLoading) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-slate-50 to-slate-100 flex items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-blue-600" />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 to-slate-100 flex items-center justify-center p-4">
      <div className="w-full max-w-2xl">
        {/* Header */}
        <div className="text-center mb-8">
          <div className="inline-flex items-center gap-2 mb-4">
            <div className="w-8 h-8 bg-blue-600 rounded-lg flex items-center justify-center">
              <span className="text-white font-bold text-sm">GRC</span>
            </div>
            <span className="font-semibold text-lg text-slate-900">
              GRC Platform
            </span>
          </div>
          <h1 className="text-2xl font-bold text-slate-900">
            Welcome! Let&apos;s set up your organization
          </h1>
          <p className="text-slate-600 mt-2">
            Complete these steps to configure your GRC environment
          </p>
        </div>

        {/* Step indicator */}
        <div className="flex items-center justify-center gap-2 mb-8">
          {STEPS.map((s, i) => (
            <div key={s.id} className="flex items-center">
              <div
                className={`w-10 h-10 rounded-full flex items-center justify-center text-sm font-medium transition-colors ${
                  step > s.id
                    ? "bg-green-100 text-green-700"
                    : step === s.id
                    ? "bg-blue-600 text-white"
                    : "bg-slate-100 text-slate-400"
                }`}
              >
                {step > s.id ? (
                  <CheckCircle2 className="h-5 w-5" />
                ) : (
                  s.id
                )}
              </div>
              {i < STEPS.length - 1 && (
                <div
                  className={`w-12 h-0.5 mx-1 ${
                    step > s.id ? "bg-green-300" : "bg-slate-200"
                  }`}
                />
              )}
            </div>
          ))}
        </div>

        {/* Form card */}
        <div className="bg-white rounded-2xl shadow-lg border border-slate-200 p-8">
          {error && (
            <div className="mb-6 p-3 bg-red-50 border border-red-200 rounded-lg text-sm text-red-700">
              {error}
            </div>
          )}

          {/* Step 1: Organization Name */}
          {step === 1 && (
            <div className="space-y-4">
              <h2 className="text-lg font-semibold text-slate-900 flex items-center gap-2">
                <Building2 className="h-5 w-5 text-blue-600" />
                Organization Name
              </h2>
              <p className="text-sm text-slate-600">
                Enter your company or organization name as it should appear in the platform.
              </p>
              <input
                type="text"
                value={organizationName}
                onChange={(e) => setOrganizationName(e.target.value)}
                placeholder="e.g., Acme Corporation"
                className="w-full px-4 py-3 border border-slate-200 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none text-slate-900"
              />
            </div>
          )}

          {/* Step 2: Industry & Employee Count */}
          {step === 2 && (
            <div className="space-y-6">
              <div>
                <h2 className="text-lg font-semibold text-slate-900 flex items-center gap-2 mb-4">
                  <Users className="h-5 w-5 text-blue-600" />
                  Industry & Company Size
                </h2>

                <label className="block text-sm font-medium text-slate-700 mb-2">
                  Industry
                </label>
                <div className="grid grid-cols-2 gap-2">
                  {INDUSTRIES.map((ind) => (
                    <button
                      key={ind}
                      onClick={() => setIndustry(ind)}
                      className={`px-4 py-3 rounded-lg border text-sm font-medium transition-colors ${
                        industry === ind
                          ? "border-blue-600 bg-blue-50 text-blue-700"
                          : "border-slate-200 text-slate-700 hover:bg-slate-50"
                      }`}
                    >
                      {ind}
                    </button>
                  ))}
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium text-slate-700 mb-2">
                  Number of Employees
                </label>
                <div className="grid grid-cols-4 gap-2">
                  {EMPLOYEE_COUNTS.map((count) => (
                    <button
                      key={count}
                      onClick={() => setEmployeeCount(count)}
                      className={`px-4 py-3 rounded-lg border text-sm font-medium transition-colors ${
                        employeeCount === count
                          ? "border-blue-600 bg-blue-50 text-blue-700"
                          : "border-slate-200 text-slate-700 hover:bg-slate-50"
                      }`}
                    >
                      {count}
                    </button>
                  ))}
                </div>
              </div>
            </div>
          )}

          {/* Step 3: Infrastructure */}
          {step === 3 && (
            <div className="space-y-4">
              <h2 className="text-lg font-semibold text-slate-900 flex items-center gap-2">
                <Server className="h-5 w-5 text-blue-600" />
                Infrastructure Overview
              </h2>
              <p className="text-sm text-slate-600">
                Briefly describe your IT infrastructure (cloud providers, on-premises, hybrid, etc.)
              </p>
              <textarea
                value={infrastructure}
                onChange={(e) => setInfrastructure(e.target.value)}
                placeholder="e.g., AWS cloud infrastructure with some on-premises legacy systems..."
                rows={4}
                className="w-full px-4 py-3 border border-slate-200 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none text-slate-900 resize-none"
              />
            </div>
          )}

          {/* Step 4: Data Types */}
          {step === 4 && (
            <div className="space-y-4">
              <h2 className="text-lg font-semibold text-slate-900 flex items-center gap-2">
                <Database className="h-5 w-5 text-blue-600" />
                Data Types Handled
              </h2>
              <p className="text-sm text-slate-600">
                Describe the types of data your organization processes (PII, financial, healthcare, etc.)
              </p>
              <textarea
                value={dataTypes}
                onChange={(e) => setDataTypes(e.target.value)}
                placeholder="e.g., Customer PII, financial transaction data, employee records..."
                rows={4}
                className="w-full px-4 py-3 border border-slate-200 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none text-slate-900 resize-none"
              />
            </div>
          )}

          {/* Navigation buttons */}
          <div className="flex justify-between mt-8 pt-6 border-t border-slate-100">
            {step > 1 ? (
              <button
                onClick={() => setStep(step - 1)}
                className="px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-100 rounded-lg transition-colors"
              >
                Back
              </button>
            ) : (
              <div />
            )}

            {step < 4 ? (
              <button
                onClick={() => setStep(step + 1)}
                disabled={!canAdvance()}
                className="inline-flex items-center gap-1 px-6 py-2 text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              >
                Next
                <ChevronRight className="h-4 w-4" />
              </button>
            ) : (
              <button
                onClick={handleSubmit}
                disabled={!canAdvance() || isSubmitting}
                className="inline-flex items-center gap-2 px-6 py-2 text-sm font-medium text-white bg-green-600 hover:bg-green-700 rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {isSubmitting ? (
                  <>
                    <Loader2 className="h-4 w-4 animate-spin" />
                    Completing...
                  </>
                ) : (
                  <>
                    <CheckCircle2 className="h-4 w-4" />
                    Complete Setup
                  </>
                )}
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
