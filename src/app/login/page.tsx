"use client";

import { useState, useEffect } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import Link from "next/link";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Label } from "@/components/ui/label";
import { AlertCircle, Loader2 } from "lucide-react";
import { useAuth } from "@/hooks/useAuth";

export default function LoginPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { login, verifyMfa, isAuthenticated, isLoading: authLoading } = useAuth();

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState("");

  // MFA State
  const [showMfa, setShowMfa] = useState(false);
  const [mfaToken, setMfaToken] = useState("");
  const [mfaCode, setMfaCode] = useState("");

  // Redirect if already authenticated
  useEffect(() => {
    if (isAuthenticated && !authLoading) {
      const redirect = searchParams.get("redirect") || "/dashboard";
      router.push(redirect);
    }
  }, [isAuthenticated, authLoading, router, searchParams]);

  // Email validation
  const validateEmail = (email: string): boolean => {
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    return emailRegex.test(email);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);
    setError("");

    // Client-side validation
    if (!email.trim() || !password) {
      setError("Email and password are required");
      setIsLoading(false);
      return;
    }

    try {
      const result = await login(email, password);

      if (result.mfaRequired && result.mfaToken) {
        setShowMfa(true);
        setMfaToken(result.mfaToken);
        return;
      }

      if (result.success) {
        window.location.href = searchParams.get("redirect") || "/dashboard";
      } else {
        setError(result.error || "Invalid email or password");
      }
    } catch {
      setError("An error occurred. Please try again.");
    } finally {
      setIsLoading(false);
    }
  };

  const handleMfaSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (mfaCode.length !== 6) {
      setError("MFA code must be 6 digits");
      return;
    }

    setIsLoading(true);
    setError("");

    try {
      const result = await verifyMfa(mfaToken, mfaCode);
      if (result.success) {
        window.location.href = searchParams.get("redirect") || "/dashboard";
      } else {
        setError(result.error || "Invalid MFA code");
      }
    } catch {
      setError("MFA verification failed. Please try again.");
    } finally {
      setIsLoading(false);
    }
  };

  // Show loading if checking auth state
  if (authLoading) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-slate-50 to-slate-100 flex items-center justify-center p-4">
        <Loader2 className="h-8 w-8 animate-spin text-blue-600" />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 to-slate-100 flex items-center justify-center p-4">
      <div className="w-full max-w-md">
        <Card className="border-0 shadow-lg">
          <CardHeader className="space-y-2 pb-6">
            <div className="flex items-center gap-2 mb-2">
              <div className="w-8 h-8 bg-blue-600 rounded-lg flex items-center justify-center">
                <span className="text-white font-bold text-sm">GRC</span>
              </div>
              <span className="font-semibold text-lg text-slate-900">
                Governance Platform
              </span>
            </div>

            <CardTitle className="text-2xl">Sign in</CardTitle>
            <CardDescription>
              Risk-aware compliance management platform
            </CardDescription>
          </CardHeader>

          <CardContent>
            {showMfa ? (
              <form onSubmit={handleMfaSubmit} className="space-y-4">
                {error && (
                  <div className="flex gap-3 p-3 bg-red-50 border border-red-200 rounded-lg">
                    <AlertCircle className="h-5 w-5 text-red-600 flex-shrink-0 mt-0.5" />
                    <p className="text-sm text-red-700">{error}</p>
                  </div>
                )}

                <div className="space-y-2">
                  <Label htmlFor="mfaCode" className="text-sm font-medium">
                    Six-digit code
                  </Label>
                  <Input
                    id="mfaCode"
                    type="text"
                    placeholder="000 000"
                    value={mfaCode}
                    onChange={(e) => setMfaCode(e.target.value.replace(/\D/g, '').slice(0, 6))}
                    disabled={isLoading}
                    className="bg-slate-50 text-center tracking-widest text-lg"
                    autoFocus
                  />
                  <p className="text-xs text-slate-500 mt-1">
                    Enter the code from your authenticator app
                  </p>
                </div>

                <Button
                  type="submit"
                  className="w-full mt-6"
                  disabled={isLoading}
                >
                  {isLoading ? (
                    <>
                      <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                      Verifying...
                    </>
                  ) : (
                    "Verify & Sign In"
                  )}
                </Button>

                <Button
                  variant="ghost"
                  type="button"
                  className="w-full text-slate-500"
                  onClick={() => setShowMfa(false)}
                  disabled={isLoading}
                >
                  Back to login
                </Button>
              </form>
            ) : (
              <form onSubmit={handleSubmit} className="space-y-4">
                {error && (
                  <div className="flex gap-3 p-3 bg-red-50 border border-red-200 rounded-lg">
                    <AlertCircle className="h-5 w-5 text-red-600 flex-shrink-0 mt-0.5" />
                    <p className="text-sm text-red-700">{error}</p>
                  </div>
                )}

                <div className="space-y-2">
                  <Label htmlFor="email" className="text-sm font-medium">
                    Email
                  </Label>
                  <Input
                    id="email"
                    type="email"
                    placeholder="alice@company.com"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    disabled={isLoading}
                    className="bg-slate-50"
                    autoComplete="email"
                    aria-describedby="email-hint"
                  />
                  <p id="email-hint" className="text-xs text-slate-500 mt-1">
                    Demo: alice@company.com
                  </p>
                </div>

                <div className="space-y-2">
                  <div className="flex items-center justify-between">
                    <Label htmlFor="password text-sm font-medium">
                      Password
                    </Label>
                    <Link
                      href="/forgot-password"
                      className="text-xs text-blue-600 hover:underline font-medium"
                    >
                      Forgot password?
                    </Link>
                  </div>
                  <Input
                    id="password"
                    type="password"
                    placeholder="••••••••"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    disabled={isLoading}
                    className="bg-slate-50"
                    autoComplete="current-password"
                    aria-describedby="password-hint"
                  />
                  <p id="password-hint" className="text-xs text-slate-500 mt-1">
                    Demo: demo
                  </p>
                </div>

                <Button
                  type="submit"
                  className="w-full mt-6"
                  disabled={isLoading}
                >
                  {isLoading ? (
                    <>
                      <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                      Signing in...
                    </>
                  ) : (
                    "Sign in"
                  )}
                </Button>
              </form>
            )}

            <div className="mt-6 pt-6 border-t border-slate-200">
              <p className="text-xs text-slate-600 mb-3 font-semibold">
                Test Accounts:
              </p>

              <div className="space-y-2 text-xs text-slate-600">
                <p>
                  <strong className="text-blue-600">Admin:</strong> alice@company.com / demo
                </p>
                <p>
                  <strong className="text-green-600">Analyst:</strong> bob@company.com / demo
                </p>
                <p>
                  <strong className="text-purple-600">Manager:</strong> carol@company.com / demo
                </p>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
