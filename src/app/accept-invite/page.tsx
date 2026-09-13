"use client";

import { Suspense, useState, useEffect, useCallback } from "react";
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
import { AlertCircle, Loader2, CheckCircle2 } from "lucide-react";
import { acceptInvite } from "@/lib/data-service";
import { GoogleLogin } from "@react-oauth/google";
import { useAuth } from "@/hooks/useAuth";

interface InviteVerification {
  valid: boolean;
  email: string;
  full_name: string;
  organization_name: string;
  role: string;
  auth_provider: string;
}

function AcceptInviteContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const token = searchParams.get("token");
  const { loginWithGoogle } = useAuth();

  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [isVerifying, setIsVerifying] = useState(true);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState(false);
  const [inviteData, setInviteData] = useState<InviteVerification | null>(null);

  // Verify the invite token on mount to determine auth_provider
  useEffect(() => {
    if (!token) {
      setError("Invitation token is missing. Please check your email link.");
      setIsVerifying(false);
      return;
    }

    const verifyToken = async () => {
      try {
        const res = await fetch(`/api/v1/auth/verify-invite?token=${encodeURIComponent(token)}`);
        const data = await res.json();
        if (res.ok && data.valid) {
          setInviteData(data);
        } else {
          setError(data.detail || "Invalid or expired invitation link.");
        }
      } catch {
        setError("Failed to verify invitation. Please try again.");
      } finally {
        setIsVerifying(false);
      }
    };

    verifyToken();
  }, [token]);

  const authProvider = inviteData?.auth_provider || "any";

  // Handle password-based form submission
  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!token) return;

    setIsLoading(true);
    setError("");

    if (password.length < 8) {
      setError("Password must be at least 8 characters long.");
      setIsLoading(false);
      return;
    }

    if (password !== confirmPassword) {
      setError("Passwords do not match.");
      setIsLoading(false);
      return;
    }

    try {
      await acceptInvite({ token, password });
      setSuccess(true);
      setTimeout(() => {
        window.location.href = "/login";
      }, 2000);
    } catch (err: any) {
      setError(err.message || "Failed to accept invitation. The link may be expired or invalid.");
    } finally {
      setIsLoading(false);
    }
  };

  // Handle SSO-only accept (no password)
  const handleSsoAccept = useCallback(async (provider: "microsoft" | "google") => {
    if (!token) return;
    setIsLoading(true);
    setError("");

    try {
      // Accept the invite without a password (backend auto-generates one)
      await acceptInvite({ token, password: "" });
      setSuccess(true);
      setTimeout(() => {
        window.location.href = "/login";
      }, 2000);
    } catch (err: any) {
      setError(err.message || "Failed to accept invitation.");
    } finally {
      setIsLoading(false);
    }
  }, [token]);

  const handleGoogleSsoAccept = useCallback(async (credential?: string) => {
    if (!token) return;
    setIsLoading(true);
    setError("");

    try {
      // 1. Accept the invite (auto-generate password)
      await acceptInvite({ token, password: "" });

      // 2. Immediately log in via Google SSO
      if (credential) {
        const result = await loginWithGoogle(credential);
        if (result.success) {
          setSuccess(true);
          setTimeout(() => {
            window.location.href = "/dashboard";
          }, 1500);
          return;
        }
      }

      setSuccess(true);
      setTimeout(() => {
        window.location.href = "/login";
      }, 2000);
    } catch (err: any) {
      setError(err.message || "Failed to accept invitation.");
    } finally {
      setIsLoading(false);
    }
  }, [token, loginWithGoogle]);

  if (isVerifying) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-slate-50 to-slate-100 flex items-center justify-center p-4">
        <div className="flex flex-col items-center gap-3">
          <Loader2 className="h-8 w-8 animate-spin text-blue-600" />
          <p className="text-sm text-muted-foreground">Verifying invitation...</p>
        </div>
      </div>
    );
  }

  if (success) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-slate-50 to-slate-100 flex items-center justify-center p-4">
        <Card className="w-full max-w-md border-0 shadow-lg text-center p-8">
          <div className="flex justify-center mb-6">
            <div className="w-16 h-16 bg-green-100 rounded-full flex items-center justify-center">
              <CheckCircle2 className="h-10 w-10 text-green-600" />
            </div>
          </div>
          <CardTitle className="text-2xl mb-2">Welcome Aboard!</CardTitle>
          <CardDescription className="text-lg">
            Your account has been activated. Redirecting you to login...
          </CardDescription>
        </Card>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 to-slate-100 flex items-center justify-center p-4">
      <div className="w-full max-w-md">
        <Card className="border-0 shadow-lg">
          <CardHeader className="space-y-1 pb-6">
            <div className="flex items-center gap-2 mb-4">
              <div className="w-8 h-8 bg-blue-600 rounded-lg flex items-center justify-center">
                <span className="text-white font-bold text-sm">GRC</span>
              </div>
              <span className="font-semibold text-lg text-slate-900">
                GRC Platform
              </span>
            </div>
            <CardTitle className="text-2xl">Accept Invitation</CardTitle>
            <CardDescription>
              {inviteData ? (
                <>
                  Join <strong>{inviteData.organization_name}</strong> as <strong className="capitalize">{inviteData.role}</strong>
                </>
              ) : (
                "Set your password to join your organization"
              )}
            </CardDescription>
          </CardHeader>

          <CardContent>
            {error && (
              <div className="flex gap-3 p-3 mb-6 bg-red-50 border border-red-200 rounded-lg">
                <AlertCircle className="h-5 w-5 text-red-600 flex-shrink-0 mt-0.5" />
                <p className="text-sm text-red-700">{error}</p>
              </div>
            )}

            {/* ── Microsoft-only org ── */}
            {authProvider === "microsoft" && (
              <div className="space-y-4">
                <div className="text-center p-4 bg-blue-50 border border-blue-200 rounded-lg">
                  <p className="text-sm text-blue-800 font-medium mb-1">
                    💼 Microsoft 365 / Entra ID
                  </p>
                  <p className="text-xs text-blue-600">
                    Your organization uses Microsoft for authentication.
                  </p>
                </div>
                <Button
                  onClick={() => handleSsoAccept("microsoft")}
                  className="w-full bg-[#0078d4] hover:bg-[#106ebe] text-white gap-2"
                  disabled={isLoading || !token}
                >
                  {isLoading ? (
                    <>
                      <Loader2 className="h-4 w-4 animate-spin" />
                      Activating Account...
                    </>
                  ) : (
                    <>
                      <svg className="h-4 w-4" viewBox="0 0 21 21" fill="none">
                        <rect x="1" y="1" width="9" height="9" fill="#f25022" />
                        <rect x="11" y="1" width="9" height="9" fill="#7fba00" />
                        <rect x="1" y="11" width="9" height="9" fill="#00a4ef" />
                        <rect x="11" y="11" width="9" height="9" fill="#ffb900" />
                      </svg>
                      Join with Microsoft
                    </>
                  )}
                </Button>
              </div>
            )}

            {/* ── Google-only org ── */}
            {authProvider === "google" && (
              <div className="space-y-4">
                <div className="text-center p-4 bg-amber-50 border border-amber-200 rounded-lg">
                  <p className="text-sm text-amber-800 font-medium mb-1">
                    🔑 Google Workspace
                  </p>
                  <p className="text-xs text-amber-600">
                    Your organization uses Google for authentication.
                  </p>
                </div>
                <div className="flex justify-center">
                  <GoogleLogin
                    onSuccess={(credentialResponse) => {
                      if (credentialResponse.credential) {
                        handleGoogleSsoAccept(credentialResponse.credential);
                      }
                    }}
                    onError={() => {
                      setError("Google sign-in failed. Please try again.");
                    }}
                    theme="outline"
                    shape="rectangular"
                    text="continue_with"
                    width="100%"
                  />
                </div>
              </div>
            )}

            {/* ── Standard (any) org: show all options ── */}
            {authProvider === "any" && (
              <>
                {/* Google SSO button */}
                <div className="flex justify-center mb-4">
                  <GoogleLogin
                    onSuccess={(credentialResponse) => {
                      if (credentialResponse.credential) {
                        handleGoogleSsoAccept(credentialResponse.credential);
                      }
                    }}
                    onError={() => {
                      setError("Google sign-in failed. Please try again.");
                    }}
                    theme="outline"
                    shape="rectangular"
                    text="continue_with"
                    width="100%"
                  />
                </div>

                {/* Microsoft SSO button */}
                <Button
                  type="button"
                  variant="outline"
                  className="w-full mb-4 gap-2"
                  onClick={() => handleSsoAccept("microsoft")}
                  disabled={isLoading}
                >
                  <svg className="h-4 w-4" viewBox="0 0 21 21" fill="none">
                    <rect x="1" y="1" width="9" height="9" fill="#f25022" />
                    <rect x="11" y="1" width="9" height="9" fill="#7fba00" />
                    <rect x="1" y="11" width="9" height="9" fill="#00a4ef" />
                    <rect x="11" y="11" width="9" height="9" fill="#ffb900" />
                  </svg>
                  Continue with Microsoft
                </Button>

                <div className="relative mb-4">
                  <div className="absolute inset-0 flex items-center">
                    <span className="w-full border-t border-slate-200" />
                  </div>
                  <div className="relative flex justify-center text-xs uppercase">
                    <span className="bg-white px-2 text-slate-500">Or set a password</span>
                  </div>
                </div>

                <form onSubmit={handleSubmit} className="space-y-4">
                  <div className="space-y-2">
                    <Label htmlFor="password">New Password</Label>
                    <Input
                      id="password"
                      type="password"
                      placeholder="Minimum 8 characters"
                      value={password}
                      onChange={(e) => setPassword(e.target.value)}
                      disabled={isLoading || !token}
                      required
                    />
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="confirm-password">Confirm Password</Label>
                    <Input
                      id="confirm-password"
                      type="password"
                      placeholder="Re-enter password"
                      value={confirmPassword}
                      onChange={(e) => setConfirmPassword(e.target.value)}
                      disabled={isLoading || !token}
                      required
                    />
                  </div>

                  <Button
                    type="submit"
                    className="w-full mt-6 bg-slate-900 hover:bg-slate-800 text-white"
                    disabled={isLoading || !token}
                  >
                    {isLoading ? (
                      <>
                        <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                        Activating Account...
                      </>
                    ) : (
                      "Join Platform"
                    )}
                  </Button>
                </form>
              </>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

export default function AcceptInvitePage() {
  return (
    <Suspense fallback={
      <div className="min-h-screen bg-gradient-to-br from-slate-50 to-slate-100 flex items-center justify-center p-4">
        <Loader2 className="h-8 w-8 animate-spin text-blue-600" />
      </div>
    }>
      <AcceptInviteContent />
    </Suspense>
  );
}
