"use client";

import { useState, useEffect } from "react";
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

export default function LoginPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { login, loginWithGoogle, isDevMode, isAuthenticated, isLoading: authLoading } = useAuth();

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState("");

  // Redirect if already authenticated
  useEffect(() => {
    // Redirect if already authenticated
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

  const handleGoogleLogin = async () => {
    setIsLoading(true);
    setError("");
    try {
      const result = await loginWithGoogle();
      if (!result.success) {
        setError(result.error || "Google login failed");
        setIsLoading(false);
      }
      // On success, Supabase will redirect the browser to Google
    } catch (e) {
      setError("An unexpected error occurred");
      setIsLoading(false);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);
    setError("");

    // Client-side validation
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
        // Redirect based on role or to specified redirect path
        const redirect = searchParams.get("redirect") || "/dashboard";
        window.location.href = redirect;
      } else {
        setError(result.error || "Invalid email or password");
      }
    } catch {
      setError("An error occurred. Please try again.");
    } finally {
      setIsLoading(false);
    }
  };

  const handleQuickLogin = async (roleEmail: string) => {
    setIsLoading(true);
    setError("");
    try {
      const result = await login(roleEmail, 'demo');
      if (result.success) {
        const redirect = searchParams.get("redirect") || "/dashboard";
        window.location.href = redirect;
      } else {
        setError(`Failed to login as ${roleEmail}. Did you create this user in Supabase Auth yet?`);
      }
    } catch {
      setError("An error occurred during quick login.");
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

            <Button
              type="button"
              variant="outline"
              className="w-full mb-6 relative hover:bg-slate-50"
              onClick={handleGoogleLogin}
              disabled={isLoading}
            >
              <svg className="h-5 w-5 mr-2" viewBox="0 0 24 24">
                <path
                  d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"
                  fill="#4285F4"
                />
                <path
                  d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"
                  fill="#34A853"
                />
                <path
                  d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"
                  fill="#FBBC05"
                />
                <path
                  d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"
                  fill="#EA4335"
                />
              </svg>
              Sign in with Google
            </Button>

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
                  placeholder="alice@company.com"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  disabled={isLoading}
                  className="bg-slate-50 dark:bg-slate-900"
                  autoComplete="email"
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="password" className="text-sm font-medium">
                  Password
                </Label>
                <div className="flex justify-between items-center mt-1">
                  <p id="password-hint" className="text-xs text-slate-500">
                    Demo: demo
                  </p>
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

            {/* Dev quick-login - only visible in local development */}
            {isDevMode && (
              <div className="mt-6 pt-5 border-t border-dashed border-slate-200">
                <p className="text-xs text-slate-400 text-center mb-3 font-mono">&#x26a1; DEV QUICK LOGIN — one click, no password</p>
                <div className="grid grid-cols-3 gap-2">
                  <button
                    type="button"
                    onClick={() => handleQuickLogin('alice@company.com')}
                    disabled={isLoading}
                    className="text-xs py-2 px-2 rounded border border-blue-200 bg-blue-50 text-blue-700 hover:bg-blue-100 transition-colors font-semibold disabled:opacity-50"
                  >
                    &#x1f451; Admin
                  </button>
                  <button
                    type="button"
                    onClick={() => handleQuickLogin('carol@company.com')}
                    disabled={isLoading}
                    className="text-xs py-2 px-2 rounded border border-purple-200 bg-purple-50 text-purple-700 hover:bg-purple-100 transition-colors font-semibold disabled:opacity-50"
                  >
                    &#x1f9ed; Manager
                  </button>
                  <button
                    type="button"
                    onClick={() => handleQuickLogin('bob@company.com')}
                    disabled={isLoading}
                    className="text-xs py-2 px-2 rounded border border-green-200 bg-green-50 text-green-700 hover:bg-green-100 transition-colors font-semibold disabled:opacity-50"
                  >
                    &#x1f50d; Analyst
                  </button>
                </div>
              </div>

            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}