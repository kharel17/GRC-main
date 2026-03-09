"use client";

import { useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { Loader2, AlertCircle } from "lucide-react";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";

/**
 * OAuth Callback Processing Page
 * 
 * This page is shown while the OAuth callback is being processed.
 * The actual callback handling is done by /auth/callback/route.ts
 * This page just provides user feedback during the process.
 */

export default function AuthCallbackPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [error, setError] = useState<string | null>(null);
  const [isProcessing, setIsProcessing] = useState(true);

  useEffect(() => {
    // Check for OAuth errors from the callback handler
    const errorParam = searchParams.get("error");
    const errorDescription = searchParams.get("error_description");

    if (errorParam) {
      console.error("[Callback Page] OAuth Error:", {
        error: errorParam,
        description: errorDescription,
      });
      setError(errorDescription || "Authentication failed");
      setIsProcessing(false);
      return;
    }

    // If we're on this page without error, the callback route should have already redirected
    // If we reach here, wait a moment then check auth state
    const timeout = setTimeout(() => {
      console.log("[Callback Page] Checking authentication state...");
      // The route handler should have already redirected to /dashboard
      // If we're still here, force a navigation
      router.push("/dashboard");
    }, 2000);

    return () => clearTimeout(timeout);
  }, [searchParams, router]);

  if (error) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center p-4">
        <Card className="w-full max-w-md">
          <CardHeader>
            <CardTitle>Authentication Failed</CardTitle>
            <CardDescription>
              There was a problem signing you in with Google
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <Alert variant="destructive">
              <AlertCircle className="h-4 w-4" />
              <AlertDescription>{error}</AlertDescription>
            </Alert>
            <div className="flex gap-2">
              <Button
                variant="outline"
                className="flex-1"
                onClick={() => router.push("/login")}
              >
                Back to Login
              </Button>
              <Button
                className="flex-1"
                onClick={() => {
                  setError(null);
                  setIsProcessing(true);
                  router.push("/login");
                }}
              >
                Try Again
              </Button>
            </div>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-background flex items-center justify-center">
      <Card className="w-full max-w-md">
        <CardHeader>
          <CardTitle>Signing You In</CardTitle>
          <CardDescription>
            Please wait while we complete your authentication with Google
          </CardDescription>
        </CardHeader>
        <CardContent className="flex flex-col items-center gap-4">
          <Loader2 className="h-8 w-8 animate-spin text-primary" />
          {isProcessing && (
            <p className="text-sm text-muted-foreground">
              Verifying your credentials...
            </p>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
