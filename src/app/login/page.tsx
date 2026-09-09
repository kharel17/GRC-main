"use client";

import { Suspense, useState, useEffect } from "react";
import { useRouter, useSearchParams } from "next/navigation";

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
import { setTokens } from "@/lib/token-storage";

import { TwoFactorVerifyModal } from "@/components/auth/TwoFactorVerifyModal";
import { GoogleLogin } from "@react-oauth/google";

function LoginContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { login, loginWithGoogle, isDevMode, isAuthenticated, isLoading: authLoading } = useAuth();

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState("");
  const [mfaData, setMfaData] = useState<{ twoFaToken: string; mfaSetupRequired?: boolean } | null>(null);

  // Redirect if already authenticated
  useEffect(() => {
    if (isAuthenticated && !authLoading) {
      const isSuper = (window as any)?.__USER_ROLE__ === 'superadmin';
      const redirect = searchParams.get("redirect") || (isSuper ? "/superadmin" : "/dashboard");
      router.push(redirect);
    }
  }, [isAuthenticated, authLoading, router, searchParams]);

  // Email validation
  const validateEmail = (email: string): boolean => {
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    return emailRegex.test(email);
  };

  const handleGoogleSuccess = async (credential?: string) => {
    if (!credential) return;
    setIsLoading(true);
    setError("");
    try {
      const result = await loginWithGoogle(credential);
      if (result.success) {
        const isSuper = (window as any)?.__USER_ROLE__ === 'superadmin';
        const redirect = searchParams.get("redirect") || (isSuper ? "/superadmin" : "/dashboard");
        window.location.href = redirect;
      } else {
        setError(result.error || "Google sign-in failed. Please try again.");
        setIsLoading(false);
      }
    } catch {
      setError("An unexpected error occurred during Google sign-in.");
      setIsLoading(false);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);
    setError("");

    if (!email.trim()) {
      setError("Email is required");
      setIsLoading(false);
      return;
    }

    if (!validateEmail(email)) {
      setError("Please enter a valid email address");
      setIsLoading(false);
      return;
    }

    if (!password) {
      setError("Password is required");
      setIsLoading(false);
      return;
    }

    try {
      const result = await login(email, password);

      if (result.success) {
        if (result.mfa_required && result.two_fa_token) {
          setMfaData({
            twoFaToken: result.two_fa_token,
            mfaSetupRequired: result.mfa_setup_required,
          });
        } else {
          const redirect = searchParams.get("redirect") || "/dashboard";
          window.location.href = redirect;
        }
      } else {
        setError(result.error || "Invalid email or password");
      }
    } catch {
      setError("An error occurred. Please try again.");
    } finally {
      setIsLoading(false);
    }
  };

  if (authLoading) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-slate-50 to-slate-100 flex items-center justify-center p-4">
        <Loader2 className="h-8 w-8 animate-spin text-blue-600" />
      </div>
    );
  }

  if (mfaData) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-slate-50 to-slate-100 flex items-center justify-center p-4">
        <TwoFactorVerifyModal
          twoFaToken={mfaData.twoFaToken}
          mfaSetupRequired={mfaData.mfaSetupRequired}
          onSuccess={(tokens?: any) => {
            if (tokens?.access_token) {
              setTokens({ accessToken: tokens.access_token, refreshToken: tokens.access_token });
            }
            const redirect = searchParams.get("redirect") || "/dashboard";
            window.location.href = redirect;
          }}
          onCancel={() => setMfaData(null)}
        />
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
                GRC Platform
              </span>
            </div>

            <CardTitle className="text-2xl">Sign in</CardTitle>
            <CardDescription>
              Risk-aware compliance management platform
            </CardDescription>
          </CardHeader>

          <CardContent>
            {error && (
              <div className="flex gap-3 p-3 mb-6 bg-red-50 border border-red-200 rounded-lg">
                <AlertCircle className="h-5 w-5 text-red-600 flex-shrink-0 mt-0.5" />
                <p className="text-sm text-red-700">{error}</p>
              </div>
            )}

            <div className="flex justify-center mb-6">
              <GoogleLogin
                onSuccess={(credentialResponse) => {
                  if (credentialResponse.credential) {
                    handleGoogleSuccess(credentialResponse.credential);
                  }
                }}
                onError={() => {
                  setError("Google sign-in failed. Please try again.");
                }}
                useOneTap
                theme="outline"
                shape="rectangular"
                width="100%"
              />
            </div>

            <div className="relative mb-6">
              <div className="absolute inset-0 flex items-center">
                <span className="w-full border-t border-slate-200" />
              </div>
              <div className="relative flex justify-center text-xs uppercase">
                <span className="bg-white px-2 text-slate-500">Or continue with email</span>
              </div>
            </div>

            <form onSubmit={handleSubmit} className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="email" className="text-sm font-medium">
                  Email
                </Label>
                <Input
                  id="email"
                  type="email"
                  placeholder="user@example.com"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  disabled={isLoading}
                  className="bg-slate-50 dark:bg-slate-900"
                  autoComplete="email"
                />
              </div>

              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <Label htmlFor="password" className="text-sm font-medium">
                    Password
                  </Label>
                  <button
                    type="button"
                    onClick={() => router.push("/forgot-password")}
                    className="text-xs text-blue-600 hover:text-blue-800 transition-colors"
                  >
                    Forgot password?
                  </button>
                </div>
                <Input
                  id="password"
                  type="password"
                  placeholder="••••••••"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  disabled={isLoading}
                  className="bg-slate-50 dark:bg-slate-900"
                  autoComplete="current-password"
                />
              </div>

              <Button
                type="submit"
                className="w-full mt-6 bg-slate-900 hover:bg-slate-800 text-white"
                disabled={isLoading}
              >
                {isLoading ? (
                  <>
                    <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                    Signing in...
                  </>
                ) : (
                  "Sign in manually"
                )}
              </Button>
            </form>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

export default function LoginPage() {
  return (
    <Suspense fallback={
      <div className="min-h-screen bg-gradient-to-br from-slate-50 to-slate-100 flex items-center justify-center p-4">
        <Loader2 className="h-8 w-8 animate-spin text-blue-600" />
      </div>
    }>
      <LoginContent />
    </Suspense>
  );
}