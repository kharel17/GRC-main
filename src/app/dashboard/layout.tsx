"use client";

import { Sidebar } from "@/components/layout/Sidebar";
import { Header } from "@/components/layout/Header";
import { useAuth } from "@/hooks/useAuth";
import { Loader2 } from "lucide-react";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api-client";

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const { user, isLoading, isAuthenticated } = useAuth();
  const router = useRouter();
  const [onboardingChecked, setOnboardingChecked] = useState(false);

  // Redirect to login if not authenticated
  useEffect(() => {
    if (!isLoading && !isAuthenticated) {
      router.push("/login");
    }
  }, [isLoading, isAuthenticated, router]);

  // Check onboarding status for admin users
  useEffect(() => {
    async function checkOnboarding() {
      if (!user || user.role !== "admin") {
        setOnboardingChecked(true);
        return;
      }
      try {
        const status = await api.get<{ completed: boolean }>("/onboarding/status");
        if (!status.completed) {
          router.push("/onboarding");
          return;
        }
      } catch {
        // If the check fails, allow access
      }
      setOnboardingChecked(true);
    }

    if (isAuthenticated && user) {
      checkOnboarding();
    }
  }, [isAuthenticated, user, router]);

  // Show loading state ONLY while waiting for base authentication to initialize
  if (isLoading) {
    return (
      <div className="h-screen bg-background flex items-center justify-center">
        <div className="flex flex-col items-center gap-3">
          <Loader2 className="h-8 w-8 animate-spin text-primary" />
          <p className="text-sm text-muted-foreground">Loading...</p>
        </div>
      </div>
    );
  }

  // Don't render layout if not authenticated
  if (!isAuthenticated || !user) {
    return <div className="h-screen bg-background" />;
  }

  return (
    <div className="flex min-h-screen bg-muted/40">
      <Sidebar />
      <div className="flex-1 md:ml-64 flex flex-col min-h-screen">
        <Header user={user} title="Dashboard" />
        <main className="flex-1 overflow-auto">
          <div className="p-6 max-w-7xl mx-auto">{children}</div>
        </main>
      </div>
    </div>
  );
}
