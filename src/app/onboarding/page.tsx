"use client";

import { useState, useEffect, useRef } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/hooks/useAuth";
import { api } from "@/lib/api-client";
import { COMPLIANCE_FRAMEWORK_OPTIONS } from "@/lib/constants";
import {
  Building2,
  Users,
  Server,
  Database,
  FileText,
  ShieldCheck,
  ChevronRight,
  CheckCircle2,
  Loader2,
  Sparkles,
  UploadCloud,
  Trash2,
  Lock,
  ShieldAlert,
  FileCheck,
} from "lucide-react";

const STEPS = [
  { id: 1, title: "Organization", icon: Building2 },
  { id: 2, title: "Industry & Size", icon: Users },
  { id: 3, title: "Infrastructure", icon: Server },
  { id: 4, title: "Data Types", icon: Database },
  { id: 5, title: "Internal Policies", icon: FileText },
  { id: 6, title: "Frameworks", icon: ShieldCheck },
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

const STARTER_POLICIES = [
  {
    id: "access_control",
    title: "Access Control & Identity Policy",
    code: "POL-SEC-001",
    controls: "ISO 27001:2022 A.9.1, A.9.2, A.9.4",
    icon: Lock,
    description:
      "Enforces role-based access control (RBAC), password complexity standards, mandatory multi-factor authentication (MFA), and quarterly access privilege reviews.",
  },
  {
    id: "incident_response",
    title: "Information Security Incident Response",
    code: "POL-SEC-002",
    controls: "ISO 27001:2022 A.16.1, A.16.2",
    icon: ShieldAlert,
    description:
      "Defines severe incident triage protocols, reporting SLAs (<1 hour for critical breaches), escalation matrix, evidence preservation, and post-mortem procedures.",
  },
  {
    id: "data_protection",
    title: "Data Classification & Encryption Policy",
    code: "POL-SEC-003",
    controls: "ISO 27001:2022 A.8.2, A.10.1",
    icon: FileCheck,
    description:
      "Mandates three-tier data classification (Public, Confidential, Restricted), AES-256 encryption at rest, TLS 1.3 in transit, and secure data sanitization.",
  },
];

export default function OnboardingPage() {
  const router = useRouter();
  const { isLoading: authLoading, isAuthenticated } = useAuth();
  const fileInputRef = useRef<HTMLInputElement>(null);

  const [step, setStep] = useState(1);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [submitStatus, setSubmitStatus] = useState("");
  const [error, setError] = useState("");

  // Form data
  const [organizationName, setOrganizationName] = useState("");
  const [industry, setIndustry] = useState("");
  const [employeeCount, setEmployeeCount] = useState("");
  const [infrastructure, setInfrastructure] = useState("");
  const [dataTypes, setDataTypes] = useState("");
  
  // Step 5: Internal Policies
  const [policyOption, setPolicyOption] = useState<"generate" | "upload" | "skip">("generate");
  const [uploadedFiles, setUploadedFiles] = useState<File[]>([]);
  const [isDragging, setIsDragging] = useState(false);

  // Step 6: Frameworks
  const [selectedFrameworks, setSelectedFrameworks] = useState<string[]>(["iso27001"]);

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
        return !!industry && !!employeeCount;
      case 3:
        return infrastructure.trim().length > 0;
      case 4:
        return dataTypes.trim().length > 0;
      case 5:
        if (policyOption === "upload") {
          return uploadedFiles.length > 0;
        }
        return true; // generate or skip can proceed
      case 6:
        return selectedFrameworks.length > 0;
      default:
        return false;
    }
  };

  const toggleFramework = (frameworkId: string) => {
    setSelectedFrameworks((current) =>
      current.includes(frameworkId)
        ? current.filter((id) => id !== frameworkId)
        : [...current, frameworkId]
    );
  };

  const handleFileDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      const newFiles = Array.from(e.dataTransfer.files).filter((file) =>
        file.name.match(/\.(pdf|docx|txt)$/i)
      );
      setUploadedFiles((prev) => [...prev, ...newFiles]);
    }
  };

  const handleFileInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      const newFiles = Array.from(e.target.files).filter((file) =>
        file.name.match(/\.(pdf|docx|txt)$/i)
      );
      setUploadedFiles((prev) => [...prev, ...newFiles]);
    }
  };

  const removeFile = (index: number) => {
    setUploadedFiles((prev) => prev.filter((_, i) => i !== index));
  };

  const handleSubmit = async () => {
    setIsSubmitting(true);
    setError("");
    setSubmitStatus("Configuring organization profile...");

    try {
      // 1. Complete base onboarding
      await api.post("/onboarding/complete", {
        organization_name: organizationName,
        industry,
        employee_count: employeeCount,
        infrastructure,
        data_types: dataTypes,
        compliance_frameworks: selectedFrameworks,
      });

      // 2. Provision or index policies based on policyOption
      if (policyOption === "generate") {
        setSubmitStatus("Generating and indexing 3 AI starter security policies...");
        try {
          await api.post("/policies/generate-starter", {
            industry,
            company_size: employeeCount,
            infrastructure,
            data_types: dataTypes,
          });
        } catch (genErr) {
          console.warn("Non-fatal starter policy generation error:", genErr);
        }
      } else if (policyOption === "upload" && uploadedFiles.length > 0) {
        setSubmitStatus(`Ingesting and indexing ${uploadedFiles.length} uploaded policies...`);
        for (const file of uploadedFiles) {
          try {
            await api.upload("/document-analysis/upload", file, {
              link_as_evidence: "true",
            });
          } catch (uploadErr) {
            console.warn(`Failed to upload ${file.name}:`, uploadErr);
          }
        }
      }

      setSubmitStatus("Setup complete! Redirecting...");
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
      <div className="w-full max-w-3xl">
        {/* Header */}
        <div className="text-center mb-8">
          <div className="inline-flex items-center gap-2 mb-4">
            <div className="w-8 h-8 bg-blue-600 rounded-lg flex items-center justify-center shadow-md">
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
            Complete these 6 steps to establish your policy-first compliance environment
          </p>
        </div>

        {/* Step indicator */}
        <div className="flex items-center justify-center gap-2 mb-8 overflow-x-auto py-2">
          {STEPS.map((s, i) => (
            <div key={s.id} className="flex items-center">
              <div
                className={`w-10 h-10 rounded-full flex items-center justify-center text-sm font-medium transition-all ${
                  step > s.id
                    ? "bg-green-100 text-green-700 shadow-sm"
                    : step === s.id
                    ? "bg-blue-600 text-white shadow-md ring-4 ring-blue-100"
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
                  className={`w-8 sm:w-10 h-0.5 mx-1 transition-colors ${
                    step > s.id ? "bg-green-300" : "bg-slate-200"
                  }`}
                />
              )}
            </div>
          ))}
        </div>

        {/* Form card */}
        <div className="bg-white rounded-2xl shadow-xl border border-slate-200 p-8">
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
                <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
                  {INDUSTRIES.map((ind) => (
                    <button
                      key={ind}
                      onClick={() => setIndustry(ind)}
                      className={`px-4 py-3 rounded-lg border text-sm font-medium transition-colors ${
                        industry === ind
                          ? "border-blue-600 bg-blue-50 text-blue-700 shadow-sm"
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
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
                  {EMPLOYEE_COUNTS.map((count) => (
                    <button
                      key={count}
                      onClick={() => setEmployeeCount(count)}
                      className={`px-4 py-3 rounded-lg border text-sm font-medium transition-colors ${
                        employeeCount === count
                          ? "border-blue-600 bg-blue-50 text-blue-700 shadow-sm"
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
                placeholder="e.g., AWS cloud infrastructure with containerized microservices and RDS PostgreSQL..."
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
                placeholder="e.g., Customer PII, billing credentials, proprietary source code, and employee records..."
                rows={4}
                className="w-full px-4 py-3 border border-slate-200 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none text-slate-900 resize-none"
              />
            </div>
          )}

          {/* Step 5: Internal Security Policies (Policy-First Architecture) */}
          {step === 5 && (
            <div className="space-y-6">
              <div>
                <div className="flex items-center justify-between">
                  <h2 className="text-lg font-semibold text-slate-900 flex items-center gap-2">
                    <FileText className="h-5 w-5 text-blue-600" />
                    Internal Security Policies
                  </h2>
                  <span className="text-xs font-semibold px-2.5 py-1 bg-blue-50 text-blue-700 rounded-full border border-blue-200">
                    Policy-First Architecture
                  </span>
                </div>
                <p className="text-sm text-slate-600 mt-1">
                  AI verification maps uploaded evidence against your internal policies first, then evaluates alignment with ISO 27001. Choose how to set up your baseline policies.
                </p>
              </div>

              {/* Toggle Mode Cards */}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <button
                  type="button"
                  onClick={() => setPolicyOption("generate")}
                  className={`p-4 rounded-xl border text-left transition-all ${
                    policyOption === "generate"
                      ? "border-blue-600 bg-blue-50/70 ring-2 ring-blue-500/20 shadow-sm"
                      : "border-slate-200 hover:border-slate-300 hover:bg-slate-50"
                  }`}
                >
                  <div className="flex items-center justify-between mb-2">
                    <div className="flex items-center gap-2">
                      <div className="w-8 h-8 rounded-lg bg-blue-100 flex items-center justify-center text-blue-600">
                        <Sparkles className="h-4 w-4" />
                      </div>
                      <span className="font-semibold text-sm text-slate-900">
                        Generate Starter Policies
                      </span>
                    </div>
                    {policyOption === "generate" && (
                      <CheckCircle2 className="h-5 w-5 text-blue-600" />
                    )}
                  </div>
                  <p className="text-xs text-slate-600">
                    Auto-synthesizes 3 baseline policies tailored to your organization and indexes them into your private vector store.
                  </p>
                </button>

                <button
                  type="button"
                  onClick={() => setPolicyOption("upload")}
                  className={`p-4 rounded-xl border text-left transition-all ${
                    policyOption === "upload"
                      ? "border-blue-600 bg-blue-50/70 ring-2 ring-blue-500/20 shadow-sm"
                      : "border-slate-200 hover:border-slate-300 hover:bg-slate-50"
                  }`}
                >
                  <div className="flex items-center justify-between mb-2">
                    <div className="flex items-center gap-2">
                      <div className="w-8 h-8 rounded-lg bg-emerald-100 flex items-center justify-center text-emerald-600">
                        <UploadCloud className="h-4 w-4" />
                      </div>
                      <span className="font-semibold text-sm text-slate-900">
                        Upload Existing Policies
                      </span>
                    </div>
                    {policyOption === "upload" && (
                      <CheckCircle2 className="h-5 w-5 text-blue-600" />
                    )}
                  </div>
                  <p className="text-xs text-slate-600">
                    Upload your existing documents (PDF, DOCX) to extract, chunk, and index your company standards.
                  </p>
                </button>
              </div>

              {/* Mode A: AI Starter Policies Preview */}
              {policyOption === "generate" && (
                <div className="space-y-3 pt-2">
                  <div className="flex items-center justify-between text-xs text-slate-500 px-1">
                    <span className="font-medium text-slate-700">
                      3 Baseline Policies Included
                    </span>
                    <span>Ready to synthesize & index</span>
                  </div>

                  <div className="space-y-2.5">
                    {STARTER_POLICIES.map((policy) => {
                      const Icon = policy.icon;
                      return (
                        <div
                          key={policy.id}
                          className="p-3.5 rounded-lg border border-slate-200 bg-slate-50/50 flex items-start gap-3"
                        >
                          <div className="w-7 h-7 rounded bg-blue-100 text-blue-700 flex items-center justify-center shrink-0 mt-0.5">
                            <Icon className="h-4 w-4" />
                          </div>
                          <div className="flex-1 min-w-0">
                            <div className="flex items-center justify-between">
                              <h4 className="text-sm font-semibold text-slate-900">
                                {policy.title}
                              </h4>
                              <span className="text-[11px] font-mono font-medium px-2 py-0.5 bg-slate-100 text-slate-600 rounded">
                                {policy.code}
                              </span>
                            </div>
                            <p className="text-xs text-slate-600 mt-1 leading-relaxed">
                              {policy.description}
                            </p>
                            <span className="inline-block text-[10px] text-blue-700 font-medium mt-1">
                              Mapped: {policy.controls}
                            </span>
                          </div>
                        </div>
                      );
                    })}
                  </div>

                  <div className="p-3 bg-blue-50/50 border border-blue-100 rounded-lg text-xs text-blue-800 flex items-start gap-2">
                    <Sparkles className="h-4 w-4 text-blue-600 shrink-0 mt-0.5" />
                    <span>
                      Starter policies will be customized with your organization name (<strong>{organizationName || "Your Company"}</strong>), industry (<strong>{industry || "Technology"}</strong>), and infrastructure details upon setup.
                    </span>
                  </div>
                </div>
              )}

              {/* Mode B: Upload Existing Dropzone */}
              {policyOption === "upload" && (
                <div className="space-y-4 pt-2">
                  <div
                    onDragOver={(e) => {
                      e.preventDefault();
                      setIsDragging(true);
                    }}
                    onDragLeave={() => setIsDragging(false)}
                    onDrop={handleFileDrop}
                    onClick={() => fileInputRef.current?.click()}
                    className={`border-2 border-dashed rounded-xl p-6 text-center cursor-pointer transition-colors ${
                      isDragging
                        ? "border-blue-500 bg-blue-50/50"
                        : "border-slate-300 hover:border-slate-400 bg-slate-50/50"
                    }`}
                  >
                    <input
                      ref={fileInputRef}
                      type="file"
                      multiple
                      accept=".pdf,.docx,.txt"
                      className="hidden"
                      onChange={handleFileInputChange}
                    />
                    <div className="w-10 h-10 rounded-full bg-blue-50 text-blue-600 flex items-center justify-center mx-auto mb-2">
                      <UploadCloud className="h-5 w-5" />
                    </div>
                    <p className="text-sm font-medium text-slate-800">
                      Click to browse or drag and drop files here
                    </p>
                    <p className="text-xs text-slate-500 mt-1">
                      Supports PDF, DOCX, or TXT documents
                    </p>
                  </div>

                  {uploadedFiles.length > 0 && (
                    <div className="space-y-2">
                      <p className="text-xs font-medium text-slate-700">
                        Selected Files ({uploadedFiles.length})
                      </p>
                      <div className="max-h-48 overflow-y-auto space-y-1.5 pr-1">
                        {uploadedFiles.map((file, idx) => (
                          <div
                            key={idx}
                            className="flex items-center justify-between p-2.5 rounded-lg border border-slate-200 bg-white text-xs"
                          >
                            <div className="flex items-center gap-2 truncate">
                              <FileText className="h-4 w-4 text-slate-500 shrink-0" />
                              <span className="font-medium text-slate-800 truncate">
                                {file.name}
                              </span>
                              <span className="text-slate-400 text-[11px] shrink-0">
                                ({(file.size / 1024).toFixed(1)} KB)
                              </span>
                            </div>
                            <button
                              type="button"
                              onClick={(e) => {
                                e.stopPropagation();
                                removeFile(idx);
                              }}
                              className="text-slate-400 hover:text-red-600 transition-colors p-1"
                            >
                              <Trash2 className="h-3.5 w-3.5" />
                            </button>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  <div className="flex justify-end">
                    <button
                      type="button"
                      onClick={() => setPolicyOption("skip")}
                      className="text-xs text-slate-500 hover:text-slate-700 underline"
                    >
                      Skip for now (I will upload policies later)
                    </button>
                  </div>
                </div>
              )}

              {/* Mode C: Skip notice */}
              {policyOption === "skip" && (
                <div className="p-4 bg-amber-50 border border-amber-200 rounded-lg text-xs text-amber-800 flex items-start justify-between">
                  <div>
                    <p className="font-medium">Policy setup skipped</p>
                    <p className="mt-0.5 text-amber-700">
                      You can add policies later from the Documents section. Two-tier evidence verification will default to direct standard mapping until policies are indexed.
                    </p>
                  </div>
                  <button
                    type="button"
                    onClick={() => setPolicyOption("generate")}
                    className="text-xs font-semibold text-blue-700 hover:underline shrink-0 ml-3"
                  >
                    Restore Starter Policies
                  </button>
                </div>
              )}
            </div>
          )}

          {/* Step 6: Compliance Frameworks */}
          {step === 6 && (
            <div className="space-y-4">
              <h2 className="text-lg font-semibold text-slate-900 flex items-center gap-2">
                <ShieldCheck className="h-5 w-5 text-blue-600" />
                Compliance Frameworks
              </h2>
              <p className="text-sm text-slate-600">
                Select the compliance frameworks your organization wants to track.
              </p>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                {COMPLIANCE_FRAMEWORK_OPTIONS.map((framework) => {
                  const selected = selectedFrameworks.includes(framework.id);
                  return (
                    <button
                      key={framework.id}
                      type="button"
                      onClick={() => toggleFramework(framework.id)}
                      className={`text-left rounded-lg border p-4 transition-colors ${
                        selected
                          ? "border-blue-600 bg-blue-50 text-blue-900 shadow-sm"
                          : "border-slate-200 text-slate-700 hover:bg-slate-50"
                      }`}
                    >
                      <div className="flex items-start justify-between gap-3">
                        <div>
                          <p className="font-semibold text-sm">{framework.name}</p>
                          <p className="text-xs text-slate-600 mt-1">{framework.description}</p>
                        </div>
                        {selected && <CheckCircle2 className="h-5 w-5 text-blue-600 shrink-0" />}
                      </div>
                    </button>
                  );
                })}
              </div>
            </div>
          )}

          {/* Navigation buttons */}
          <div className="flex justify-between mt-8 pt-6 border-t border-slate-100">
            {step > 1 ? (
              <button
                onClick={() => setStep(step - 1)}
                disabled={isSubmitting}
                className="px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-100 rounded-lg transition-colors disabled:opacity-50"
              >
                Back
              </button>
            ) : (
              <div />
            )}

            {step < STEPS.length ? (
              <button
                onClick={() => setStep(step + 1)}
                disabled={!canAdvance() || isSubmitting}
                className="inline-flex items-center gap-1 px-6 py-2 text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed shadow-sm"
              >
                Next
                <ChevronRight className="h-4 w-4" />
              </button>
            ) : (
              <button
                onClick={handleSubmit}
                disabled={!canAdvance() || isSubmitting}
                className="inline-flex items-center gap-2 px-6 py-2 text-sm font-medium text-white bg-green-600 hover:bg-green-700 rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed shadow-sm"
              >
                {isSubmitting ? (
                  <>
                    <Loader2 className="h-4 w-4 animate-spin" />
                    <span>{submitStatus || "Completing..."}</span>
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
