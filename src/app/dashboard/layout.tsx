"use client";

import { Sidebar } from "@/components/layout/Sidebar";
import { Header } from "@/components/layout/Header";
import { useEffect, useState } from "react";
import { UserProfile } from "@/types/user";
import { mockUsers } from "@/lib/mock-data";

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const [user, setUser] = useState<UserProfile | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const userStr = localStorage.getItem("grc_user");
    if (!userStr) {
      window.location.href = "/login";
      return;
    }

    const userEmail = JSON.parse(userStr).email;
    const foundUser = mockUsers.find((u) => u.email === userEmail);

    if (foundUser) {
      setUser(foundUser);
    } else {
      localStorage.removeItem("grc_user");
      window.location.href = "/login";
    }

    setIsLoading(false);
  }, []);

  if (isLoading || !user) {
    return <div className="h-screen bg-slate-50" />;
  }

  return (
    <div className="flex bg-slate-50">
      <Sidebar role={user.role} />
      <div className="flex-1 md:ml-64 flex flex-col min-h-screen">
        <Header user={user} />
        <main className="flex-1 overflow-auto">
          <div className="p-6 max-w-7xl mx-auto">{children}</div>
        </main>
      </div>
    </div>
  );
}
