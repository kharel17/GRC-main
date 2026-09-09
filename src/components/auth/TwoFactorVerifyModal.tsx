"use client";

import React, { useState, useEffect } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Label } from "@/components/ui/label";
import { AlertCircle, CheckCircle2, Copy, KeyRound, ShieldAlert, Loader2 } from "lucide-react";

interface TwoFactorVerifyModalProps {
  twoFaToken: string;
  mfaSetupRequired?: boolean;
  onSuccess: (tokens?: any) => void;
  onCancel: () => void;
}

export function TwoFactorVerifyModal({
  twoFaToken,
  mfaSetupRequired = false,
  onSuccess,
  onCancel,
}: TwoFactorVerifyModalProps) {
  const [code, setCode] = useState("");
  const [isBackup, setIsBackup] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState("");

  // Setup state
  const [setupData, setSetupData] = useState<{ secret: string; qr_code: string; provisioning_uri: string } | null>(null);
  const [copied, setCopied] = useState(false);
  const [backupCodes, setBackupCodes] = useState<string[] | null>(null);

  useEffect(() => {
    if (mfaSetupRequired) {
      // Fetch QR code & secret for mandatory setup
      setIsLoading(true);
      fetch("/api/v1/auth/2fa/setup-login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ two_fa_token: twoFaToken, code: "" }),
      })
        .then(async (res) => {
          if (!res.ok) {
            const data = await res.json().catch(() => ({}));
            throw new Error(data.detail || "Failed to initialize 2FA setup");
          }
          return res.json();
        })
        .then((data) => setSetupData(data))
        .catch((err) => setError(err.message))
        .finally(() => setIsLoading(false));
    }
  }, [mfaSetupRequired, twoFaToken]);

  const handleVerify = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!code.trim()) {
      setError("Please enter your verification code");
      return;
    }

    setIsLoading(true);
    setError("");

    try {
      if (mfaSetupRequired) {
        // Confirm setup & enable 2FA
        const res = await fetch("/api/v1/auth/2fa/enable", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ two_fa_token: twoFaToken, code: code.trim() }),
        });

        const data = await res.json();
        if (!res.ok) {
          throw new Error(data.detail || "Invalid verification code");
        }

        if (data.backup_codes) {
          setBackupCodes(data.backup_codes);
        } else {
          onSuccess(data);
        }
      } else {
        // Standard 2FA verification during login
        const res = await fetch("/api/v1/auth/2fa/verify-login", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ two_fa_token: twoFaToken, code: code.trim() }),
        });

        const data = await res.json();
        if (!res.ok) {
          throw new Error(data.detail || "Invalid verification code");
        }

        onSuccess(data);
      }
    } catch (err: any) {
      setError(err.message || "Verification failed");
    } finally {
      setIsLoading(false);
    }
  };

  const copySecret = () => {
    if (setupData?.secret) {
      navigator.clipboard.writeText(setupData.secret);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  if (backupCodes) {
    return (
      <Card className="w-full max-w-md mx-auto border-0 shadow-lg bg-white dark:bg-slate-900">
        <CardHeader className="text-center">
          <div className="mx-auto w-12 h-12 bg-green-100 dark:bg-green-950 rounded-full flex items-center justify-center mb-2">
            <CheckCircle2 className="h-6 w-6 text-green-600 dark:text-green-400" />
          </div>
          <CardTitle className="text-xl">Two-Factor Authentication Enabled!</CardTitle>
          <CardDescription>
            Save these emergency backup codes in a safe place. You can use them to sign in if you lose access to your authenticator app.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid grid-cols-2 gap-2 p-3 bg-slate-50 dark:bg-slate-800 rounded-lg font-mono text-sm border text-center">
            {backupCodes.map((bCode, idx) => (
              <div key={idx} className="py-1 px-2 text-slate-800 dark:text-slate-200">
                {bCode}
              </div>
            ))}
          </div>
          <Button
            type="button"
            className="w-full bg-blue-600 hover:bg-blue-700 text-white"
            onClick={() => onSuccess()}
          >
            Done & Continue
          </Button>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className="w-full max-w-md mx-auto border-0 shadow-lg bg-white dark:bg-slate-900">
      <CardHeader className="text-center pb-4">
        <div className="mx-auto w-12 h-12 bg-blue-100 dark:bg-blue-950 rounded-full flex items-center justify-center mb-2">
          <KeyRound className="h-6 w-6 text-blue-600 dark:text-blue-400" />
        </div>
        <CardTitle className="text-2xl font-semibold">
          {mfaSetupRequired ? "Set up 2FA Required" : "Two-Factor Authentication"}
        </CardTitle>
        <CardDescription>
          {mfaSetupRequired
            ? "Your account role requires Two-Factor Authentication. Scan the QR code below using Google Authenticator or Authy."
            : isBackup
            ? "Enter one of your emergency backup codes"
            : "Enter the 6-digit code from your authenticator app"}
        </CardDescription>
      </CardHeader>

      <CardContent className="space-y-4">
        {error && (
          <div className="flex gap-3 p-3 bg-red-50 dark:bg-red-950/40 border border-red-200 dark:border-red-900 rounded-lg text-sm text-red-700 dark:text-red-300">
            <AlertCircle className="h-5 w-5 flex-shrink-0 mt-0.5" />
            <p>{error}</p>
          </div>
        )}

        {mfaSetupRequired && setupData && (
          <div className="space-y-4 text-center">
            <div className="flex justify-center p-2 bg-white rounded-lg border inline-block mx-auto">
              <img src={setupData.qr_code} alt="2FA QR Code" className="w-44 h-44 mx-auto" />
            </div>
            <div className="text-xs text-slate-500">
              Can't scan? Use manual setup key:
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
        )}

        <form onSubmit={handleVerify} className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="totp-code" className="text-sm font-medium">
              {isBackup ? "Backup Code" : "Verification Code"}
            </Label>
            <Input
              id="totp-code"
              type="text"
              placeholder={isBackup ? "e.g. a1b2-c3d4" : "123456"}
              value={code}
              onChange={(e) => setCode(e.target.value)}
              maxLength={isBackup ? 16 : 7}
              autoFocus
              className="text-center font-mono text-lg tracking-widest bg-slate-50 dark:bg-slate-900"
            />
          </div>

          <Button
            type="submit"
            disabled={isLoading}
            className="w-full bg-slate-900 hover:bg-slate-800 text-white dark:bg-blue-600 dark:hover:bg-blue-700"
          >
            {isLoading ? (
              <>
                <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                Verifying...
              </>
            ) : mfaSetupRequired ? (
              "Enable & Continue"
            ) : (
              "Verify Code"
            )}
          </Button>

          {!mfaSetupRequired && (
            <div className="flex justify-between items-center text-xs pt-2">
              <button
                type="button"
                onClick={() => setIsBackup(!isBackup)}
                className="text-blue-600 hover:underline"
              >
                {isBackup ? "Use 6-digit authenticator code" : "Use a backup code"}
              </button>
              <button
                type="button"
                onClick={onCancel}
                className="text-slate-500 hover:underline"
              >
                Back to login
              </button>
            </div>
          )}
        </form>
      </CardContent>
    </Card>
  );
}
