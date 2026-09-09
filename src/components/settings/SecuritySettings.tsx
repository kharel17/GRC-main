"use client";

import React, { useState, useEffect } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Label } from "@/components/ui/label";
import { ShieldCheck, ShieldAlert, KeyRound, Copy, CheckCircle2, AlertCircle, Loader2 } from "lucide-react";

export function SecuritySettings() {
  const [status, setStatus] = useState<{
    totp_enabled: boolean;
    is_mandatory: boolean;
    has_backup_codes: boolean;
  } | null>(null);

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [step, setStep] = useState<"idle" | "setup" | "backup">("idle");

  // Setup state
  const [setupData, setSetupData] = useState<{ secret: string; qr_code: string; provisioning_uri: string } | null>(null);
  const [verificationCode, setVerificationCode] = useState("");
  const [copied, setCopied] = useState(false);
  const [backupCodes, setBackupCodes] = useState<string[]>([]);
  const [isSubmitting, setIsSubmitting] = useState(false);

  // Disable state
  const [disableCode, setDisableCode] = useState("");
  const [showDisableConfirm, setShowDisableConfirm] = useState(false);

  const fetchStatus = async () => {
    setLoading(true);
    setError("");
    try {
      const res = await fetch("/api/v1/auth/2fa/status");
      if (res.ok) {
        const data = await res.json();
        setStatus(data);
      } else {
        throw new Error("Failed to fetch 2FA status");
      }
    } catch (err: any) {
      setError(err.message || "Failed to load security settings");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchStatus();
  }, []);

  const handleStartSetup = async () => {
    setIsSubmitting(true);
    setError("");
    try {
      const res = await fetch("/api/v1/auth/2fa/setup", { method: "POST" });
      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        throw new Error(data.detail || "Failed to initiate 2FA setup");
      }
      const data = await res.json();
      setSetupData(data);
      setStep("setup");
    } catch (err: any) {
      setError(err.message);
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleConfirmEnable = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!verificationCode.trim()) {
      setError("Please enter the verification code");
      return;
    }

    setIsSubmitting(true);
    setError("");
    try {
      const res = await fetch("/api/v1/auth/2fa/enable-auth", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ code: verificationCode.trim() }),
      });

      const data = await res.json();
      if (!res.ok) {
        throw new Error(data.detail || "Invalid verification code");
      }

      setBackupCodes(data.backup_codes || []);
      setStep("backup");
      fetchStatus();
    } catch (err: any) {
      setError(err.message);
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleDisable2FA = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSubmitting(true);
    setError("");
    try {
      const res = await fetch("/api/v1/auth/2fa/disable", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ code: disableCode.trim() }),
      });

      const data = await res.json();
      if (!res.ok) {
        throw new Error(data.detail || "Failed to disable 2FA");
      }

      setShowDisableConfirm(false);
      setDisableCode("");
      fetchStatus();
    } catch (err: any) {
      setError(err.message);
    } finally {
      setIsSubmitting(false);
    }
  };

  const copySecret = () => {
    if (setupData?.secret) {
      navigator.clipboard.writeText(setupData.secret);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center p-8">
        <Loader2 className="h-6 w-6 animate-spin text-blue-600" />
      </div>
    );
  }

  return (
    <Card className="w-full">
      <CardHeader>
        <div className="flex items-center justify-between">
          <div>
            <CardTitle className="text-xl font-semibold flex items-center gap-2">
              <ShieldCheck className="h-5 w-5 text-blue-600" />
              Two-Factor Authentication (2FA)
            </CardTitle>
            <CardDescription className="mt-1">
              Protect your account by requiring an authenticator code (Google Authenticator, Authy, etc.) during sign in.
            </CardDescription>
          </div>
          {status?.totp_enabled ? (
            <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-800 dark:bg-green-950 dark:text-green-300">
              Enabled
            </span>
          ) : (
            <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-amber-100 text-amber-800 dark:bg-amber-950 dark:text-amber-300">
              {status?.is_mandatory ? "Setup Required" : "Disabled"}
            </span>
          )}
        </div>
      </CardHeader>

      <CardContent className="space-y-6">
        {error && (
          <div className="flex gap-3 p-3 bg-red-50 dark:bg-red-950/40 border border-red-200 dark:border-red-900 rounded-lg text-sm text-red-700 dark:text-red-300">
            <AlertCircle className="h-5 w-5 flex-shrink-0" />
            <p>{error}</p>
          </div>
        )}

        {status?.is_mandatory && !status?.totp_enabled && (
          <div className="flex gap-3 p-4 bg-amber-50 dark:bg-amber-950/40 border border-amber-200 dark:border-amber-900 rounded-lg text-sm text-amber-800 dark:text-amber-300">
            <ShieldAlert className="h-5 w-5 flex-shrink-0 mt-0.5" />
            <div>
              <p className="font-semibold">Mandatory 2FA Policy</p>
              <p className="mt-1">
                Your role requires two-factor authentication to access platform features. Please complete enrollment below.
              </p>
            </div>
          </div>
        )}

        {step === "idle" && (
          <div>
            {!status?.totp_enabled ? (
              <div className="space-y-4">
                <p className="text-sm text-slate-600 dark:text-slate-400">
                  When enabled, signing in will require both your password and a 6-digit code generated by your mobile authenticator app.
                </p>
                <Button
                  onClick={handleStartSetup}
                  disabled={isSubmitting}
                  className="bg-blue-600 hover:bg-blue-700 text-white"
                >
                  {isSubmitting ? <Loader2 className="h-4 w-4 mr-2 animate-spin" /> : <KeyRound className="h-4 w-4 mr-2" />}
                  Set up Two-Factor Authentication
                </Button>
              </div>
            ) : (
              <div className="space-y-4">
                <div className="p-4 bg-slate-50 dark:bg-slate-800/50 rounded-lg space-y-2 text-sm border">
                  <div className="flex items-center text-slate-700 dark:text-slate-300">
                    <CheckCircle2 className="h-4 w-4 text-green-600 mr-2" />
                    <span>Authenticator app is active</span>
                  </div>
                  {status.has_backup_codes && (
                    <div className="flex items-center text-slate-700 dark:text-slate-300">
                      <CheckCircle2 className="h-4 w-4 text-green-600 mr-2" />
                      <span>Backup codes are generated</span>
                    </div>
                  )}
                </div>

                {!status.is_mandatory && (
                  <div>
                    {!showDisableConfirm ? (
                      <Button
                        variant="outline"
                        className="text-red-600 border-red-200 hover:bg-red-50"
                        onClick={() => setShowDisableConfirm(true)}
                      >
                        Disable Two-Factor Authentication
                      </Button>
                    ) : (
                      <form onSubmit={handleDisable2FA} className="p-4 border border-red-200 rounded-lg bg-red-50/50 space-y-3">
                        <Label className="text-xs font-semibold text-red-900">
                          Enter your current 6-digit code or password to confirm disabling 2FA:
                        </Label>
                        <Input
                          type="password"
                          placeholder="Code or Password"
                          value={disableCode}
                          onChange={(e) => setDisableCode(e.target.value)}
                          className="bg-white dark:bg-slate-900 max-w-xs"
                        />
                        <div className="flex gap-2 pt-1">
                          <Button type="submit" size="sm" variant="destructive" disabled={isSubmitting}>
                            Confirm Disable
                          </Button>
                          <Button type="button" size="sm" variant="ghost" onClick={() => setShowDisableConfirm(false)}>
                            Cancel
                          </Button>
                        </div>
                      </form>
                    )}
                  </div>
                )}
              </div>
            )}
          </div>
        )}

        {step === "setup" && setupData && (
          <div className="space-y-6 pt-2">
            <div className="space-y-4 text-center">
              <p className="text-sm text-slate-600 dark:text-slate-400">
                1. Scan this QR code with Google Authenticator, Microsoft Authenticator, or Authy:
              </p>
              <div className="flex justify-center p-3 bg-white rounded-lg border inline-block mx-auto">
                <img src={setupData.qr_code} alt="2FA QR Code" className="w-48 h-48 mx-auto" />
              </div>
              <div className="text-xs text-slate-500">
                Secret key for manual entry:
                <div className="flex items-center justify-center gap-2 mt-1">
                  <code className="bg-slate-100 dark:bg-slate-800 px-2 py-1 rounded text-slate-800 dark:text-slate-200 font-mono text-sm">
                    {setupData.secret}
                  </code>
                  <Button variant="ghost" size="icon" onClick={copySecret} className="h-7 w-7">
                    {copied ? <CheckCircle2 className="h-4 w-4 text-green-600" /> : <Copy className="h-4 w-4" />}
                  </Button>
                </div>
              </div>
            </div>

            <form onSubmit={handleConfirmEnable} className="space-y-4 max-w-xs mx-auto text-center">
              <div className="space-y-2">
                <Label htmlFor="setup-code" className="text-sm font-medium">
                  2. Enter the 6-digit code from your app:
                </Label>
                <Input
                  id="setup-code"
                  type="text"
                  placeholder="123456"
                  maxLength={6}
                  value={verificationCode}
                  onChange={(e) => setVerificationCode(e.target.value)}
                  className="text-center font-mono text-lg tracking-widest bg-slate-50 dark:bg-slate-900"
                />
              </div>

              <div className="flex gap-2">
                <Button type="submit" disabled={isSubmitting} className="flex-1 bg-blue-600 hover:bg-blue-700 text-white">
                  {isSubmitting ? <Loader2 className="h-4 w-4 mr-2 animate-spin" /> : "Verify & Enable"}
                </Button>
                <Button type="button" variant="outline" onClick={() => setStep("idle")}>
                  Cancel
                </Button>
              </div>
            </form>
          </div>
        )}

        {step === "backup" && (
          <div className="space-y-4 text-center">
            <div className="mx-auto w-12 h-12 bg-green-100 dark:bg-green-950 rounded-full flex items-center justify-center">
              <CheckCircle2 className="h-6 w-6 text-green-600 dark:text-green-400" />
            </div>
            <h3 className="text-lg font-semibold">2FA Successfully Enabled</h3>
            <p className="text-sm text-slate-600 dark:text-slate-400">
              Save these emergency backup codes in a secure password manager.
            </p>
            <div className="grid grid-cols-2 gap-2 p-4 bg-slate-50 dark:bg-slate-800 rounded-lg font-mono text-sm border">
              {backupCodes.map((bCode, idx) => (
                <div key={idx} className="py-1 px-2 text-slate-800 dark:text-slate-200">
                  {bCode}
                </div>
              ))}
            </div>
            <Button className="w-full bg-slate-900 hover:bg-slate-800 text-white" onClick={() => setStep("idle")}>
              Done
            </Button>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
