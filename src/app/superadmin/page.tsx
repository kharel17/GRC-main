"use client";

import { useState, useEffect } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Building2, Shield, Users, Loader2, Plus, UserCheck, Search, KeyRound, ArrowUpCircle, ShieldAlert, ArrowLeft } from "lucide-react";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { toast } from "sonner";
import { format } from "date-fns";
import { api } from "@/lib/api-client";
import { useAuth } from "@/hooks/useAuth";
import Link from "next/link";

interface TenantSummary {
  id: string;
  name: string;
  industry?: string;
  size?: string;
  onboarding_completed: boolean;
  user_count: number;
  compliance_frameworks: string[];
  created_at: string;
}

export default function SuperAdminPage() {
  const { user: currentUser, isLoading: authLoading } = useAuth();
  const [tenants, setTenants] = useState<TenantSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState("");
  
  // Provisioning dialog state
  const [isInviteOpen, setIsInviteOpen] = useState(false);
  const [isSuperAdminInviteOpen, setIsSuperAdminInviteOpen] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  
  const [inviteForm, setInviteForm] = useState({
    email: "",
    full_name: "",
    organization_name: "",
    organization_id: "",
  });

  const [superAdminForm, setSuperAdminForm] = useState({
    email: "",
    full_name: "",
  });

  // Promote dialog state
  const [isPromoteOpen, setIsPromoteOpen] = useState(false);
  const [promoteEmail, setPromoteEmail] = useState("");
  const [promoteResult, setPromoteResult] = useState<{ id: string; email: string; full_name: string; role: string } | null>(null);
  const [promoteSearching, setPromoteSearching] = useState(false);

  const isSuperAdmin = currentUser?.role === "superadmin";

  const fetchTenants = async () => {
    if (!isSuperAdmin) return;
    setLoading(true);
    try {
      const data = await api.get<TenantSummary[]>("/superadmin/organizations");
      setTenants(data || []);
    } catch (err: any) {
      toast.error(err.message || "Could not load superadmin data");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (isSuperAdmin) {
      fetchTenants();
    }
  }, [isSuperAdmin]);

  // ── 1. Auth Loading State ──
  if (authLoading) {
    return (
      <div className="flex h-[80vh] items-center justify-center">
        <div className="flex flex-col items-center gap-3">
          <Loader2 className="h-8 w-8 animate-spin text-indigo-600" />
          <p className="text-sm text-muted-foreground">Verifying platform administrative credentials...</p>
        </div>
      </div>
    );
  }

  // ── 2. Strict 403 Forbidden Access Guard (Zero data leak) ──
  if (!currentUser || !isSuperAdmin) {
    return (
      <div className="flex min-h-[75vh] items-center justify-center p-4">
        <Card className="max-w-md w-full border-red-200 bg-red-50/40 text-center shadow-lg">
          <CardHeader className="pb-4">
            <div className="mx-auto mb-3 flex h-16 w-16 items-center justify-center rounded-full bg-red-100 text-red-600">
              <ShieldAlert className="h-8 w-8" />
            </div>
            <CardTitle className="text-2xl font-bold text-red-950">403 — Access Denied</CardTitle>
            <CardDescription className="text-red-700 text-sm mt-1">
              You do not have permission to view or manage the Super Admin Control Plane.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <p className="text-xs text-muted-foreground bg-white/70 p-3 rounded border border-red-100">
              Your active account role is <strong className="capitalize text-foreground">{currentUser?.role || "guest"}</strong>. This zone is exclusively restricted to verified Platform Operations Personnel.
            </p>
            <Link href="/dashboard">
              <Button className="w-full bg-slate-900 hover:bg-slate-800 text-white gap-2">
                <ArrowLeft className="h-4 w-4" />
                Return to Dashboard
              </Button>
            </Link>
          </CardContent>
        </Card>
      </div>
    );
  }

  const handleInviteAdmin = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitting(true);
    try {
      const payload: any = {
        email: inviteForm.email,
        full_name: inviteForm.full_name,
      };

      if (inviteForm.organization_id && inviteForm.organization_id !== "new") {
        payload.organization_id = inviteForm.organization_id;
      } else {
        payload.organization_name = inviteForm.organization_name;
      }

      await api.post("/invitations/invite-admin", payload);

      toast.success(`Invitation sent to ${inviteForm.email}`);
      setIsInviteOpen(false);
      setInviteForm({ email: "", full_name: "", organization_name: "", organization_id: "" });
      fetchTenants();
    } catch (err: any) {
      toast.error(err.message || "Failed to send invitation");
    } finally {
      setSubmitting(false);
    }
  };

  const handleInviteSuperAdmin = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitting(true);
    try {
      await api.post("/invitations/invite-superadmin", superAdminForm);

      toast.success(`Super Admin invitation sent to ${superAdminForm.email}`);
      setIsSuperAdminInviteOpen(false);
      setSuperAdminForm({ email: "", full_name: "" });
    } catch (err: any) {
      toast.error(err.message || "Failed to send Super Admin invitation");
    } finally {
      setSubmitting(false);
    }
  };

  const handlePromoteSearch = async () => {
    if (!promoteEmail.trim()) return;
    setPromoteSearching(true);
    setPromoteResult(null);
    try {
      const users = await api.get<any[]>(`/superadmin/users/search?email=${encodeURIComponent(promoteEmail.trim())}`);
      const found = Array.isArray(users) && users.length > 0 ? users.find((u: any) => u.email === promoteEmail.trim()) || users[0] : null;
      if (!found) throw new Error("No user found with that email");
      setPromoteResult({ id: found.id, email: found.email, full_name: found.full_name || found.email, role: found.role });
    } catch (err: any) {
      toast.error(err.message || "Could not find user");
    } finally {
      setPromoteSearching(false);
    }
  };

  const handlePromoteConfirm = async () => {
    if (!promoteResult) return;
    setSubmitting(true);
    try {
      const data: any = await api.post(`/superadmin/promote/${promoteResult.id}`);
      toast.success(data?.message || `${promoteResult.email} promoted to Super Admin`);
      setIsPromoteOpen(false);
      setPromoteEmail("");
      setPromoteResult(null);
      fetchTenants();
    } catch (err: any) {
      toast.error(err.message || "Failed to promote user");
    } finally {
      setSubmitting(false);
    }
  };

  const handleImpersonate = async (orgId: string, orgName: string) => {
    try {
      const data: any = await api.post(`/superadmin/impersonate/${orgId}`);

      toast.success(`Support session initiated for ${orgName}`);
      sessionStorage.setItem("support_access_token", data.access_token);
      window.location.href = "/dashboard";
    } catch (err: any) {
      toast.error(err.message || "Failed to start support session");
    }
  };

  const filteredTenants = tenants.filter((t) =>
    t.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
    (t.industry && t.industry.toLowerCase().includes(searchQuery.toLowerCase()))
  );

  return (
    <div className="max-w-7xl mx-auto py-8 px-4 space-y-8">
      {/* Top back navigation bar */}
      <div className="flex items-center justify-between border-b pb-4">
        <Link href="/dashboard/users" className="inline-flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground transition-colors">
          <ArrowLeft className="h-4 w-4" />
          Back to User Management
        </Link>
        <div className="flex items-center gap-2">
          <Badge variant="outline" className="bg-indigo-50 text-indigo-700 border-indigo-200 text-xs">
            Super Admin Plane
          </Badge>
        </div>
      </div>

      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <Shield className="h-7 w-7 text-indigo-600" />
            <h1 className="text-3xl font-bold tracking-tight">Super Admin Control Plane</h1>
          </div>
          <p className="text-muted-foreground mt-1">
            Global tenant oversight, bank onboarding, and support session management.
          </p>
        </div>

        <div className="flex items-center gap-3">
          {/* Promote Existing User */}
          <Dialog open={isPromoteOpen} onOpenChange={(open) => { setIsPromoteOpen(open); if (!open) { setPromoteEmail(""); setPromoteResult(null); } }}>
            <DialogTrigger asChild>
              <Button variant="outline" className="gap-2 border-amber-200 text-amber-700 hover:bg-amber-50">
                <ArrowUpCircle className="h-4 w-4" />
                Promote User
              </Button>
            </DialogTrigger>
            <DialogContent>
              <DialogHeader>
                <DialogTitle>Promote Existing User to Super Admin</DialogTitle>
                <DialogDescription>
                  Search for an existing platform user by email and promote them to Super Admin. This will move them to the Platform Team and revoke their current sessions.
                </DialogDescription>
              </DialogHeader>

              <div className="space-y-4 py-4">
                <div className="flex gap-2">
                  <Input
                    placeholder="Enter user email..."
                    value={promoteEmail}
                    onChange={(e) => setPromoteEmail(e.target.value)}
                    onKeyDown={(e) => e.key === "Enter" && handlePromoteSearch()}
                  />
                  <Button type="button" variant="outline" onClick={handlePromoteSearch} disabled={promoteSearching}>
                    {promoteSearching ? <Loader2 className="h-4 w-4 animate-spin" /> : <Search className="h-4 w-4" />}
                  </Button>
                </div>

                {promoteResult && (
                  <div className="border rounded-lg p-4 space-y-2 bg-muted/30">
                    <div className="flex items-center justify-between">
                      <div>
                        <p className="font-semibold">{promoteResult.full_name}</p>
                        <p className="text-sm text-muted-foreground">{promoteResult.email}</p>
                      </div>
                      <Badge variant="outline" className="capitalize">{promoteResult.role}</Badge>
                    </div>
                    {promoteResult.role === "superadmin" ? (
                      <p className="text-sm text-amber-600 font-medium">This user is already a Super Admin.</p>
                    ) : (
                      <p className="text-sm text-muted-foreground">
                        Will be promoted from <strong className="capitalize">{promoteResult.role}</strong> → <strong>Super Admin</strong> and moved to Platform Team.
                      </p>
                    )}
                  </div>
                )}
              </div>

              <DialogFooter>
                <Button type="button" variant="ghost" onClick={() => setIsPromoteOpen(false)}>
                  Cancel
                </Button>
                <Button
                  onClick={handlePromoteConfirm}
                  disabled={submitting || !promoteResult || promoteResult.role === "superadmin"}
                  className="bg-amber-600 hover:bg-amber-700 text-white"
                >
                  {submitting ? <Loader2 className="h-4 w-4 animate-spin mr-2" /> : <ArrowUpCircle className="h-4 w-4 mr-2" />}
                  Confirm Promotion
                </Button>
              </DialogFooter>
            </DialogContent>
          </Dialog>

          {/* Invite Co-SuperAdmin */}
          <Dialog open={isSuperAdminInviteOpen} onOpenChange={setIsSuperAdminInviteOpen}>
            <DialogTrigger asChild>
              <Button variant="outline" className="gap-2 border-indigo-200 text-indigo-700 hover:bg-indigo-50">
                <Shield className="h-4 w-4" />
                Add Super Admin
              </Button>
            </DialogTrigger>
            <DialogContent>
              <form onSubmit={handleInviteSuperAdmin}>
                <DialogHeader>
                  <DialogTitle>Invite Co-Super Admin Operator</DialogTitle>
                  <DialogDescription>
                    Grant full platform administrative privileges to a co-operator.
                  </DialogDescription>
                </DialogHeader>

                <div className="space-y-4 py-4">
                  <div className="space-y-2">
                    <Label htmlFor="sa-name">Full Name</Label>
                    <Input
                      id="sa-name"
                      placeholder="e.g. Alex Rivera"
                      value={superAdminForm.full_name}
                      onChange={(e) => setSuperAdminForm({ ...superAdminForm, full_name: e.target.value })}
                      required
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="sa-email">Email Address</Label>
                    <Input
                      id="sa-email"
                      type="email"
                      placeholder="alex.rivera@platform.com"
                      value={superAdminForm.email}
                      onChange={(e) => setSuperAdminForm({ ...superAdminForm, email: e.target.value })}
                      required
                    />
                  </div>
                </div>

                <DialogFooter>
                  <Button type="button" variant="ghost" onClick={() => setIsSuperAdminInviteOpen(false)}>
                    Cancel
                  </Button>
                  <Button type="submit" disabled={submitting} className="bg-indigo-600 hover:bg-indigo-700 text-white">
                    {submitting ? <Loader2 className="h-4 w-4 animate-spin mr-2" /> : <UserCheck className="h-4 w-4 mr-2" />}
                    Send Super Admin Invite
                  </Button>
                </DialogFooter>
              </form>
            </DialogContent>
          </Dialog>

          {/* Provision Tenant Admin */}
          <Dialog open={isInviteOpen} onOpenChange={setIsInviteOpen}>
            <DialogTrigger asChild>
              <Button className="bg-indigo-600 hover:bg-indigo-700 text-white gap-2">
                <Plus className="h-4 w-4" />
                Invite Tenant Admin
              </Button>
            </DialogTrigger>
            <DialogContent>
              <form onSubmit={handleInviteAdmin}>
                <DialogHeader>
                  <DialogTitle>Invite Tenant Administrator</DialogTitle>
                  <DialogDescription>
                    Create a new organization or add an additional admin to an existing bank tenant.
                  </DialogDescription>
                </DialogHeader>

                <div className="space-y-4 py-4">
                  <div className="space-y-2">
                    <Label htmlFor="target-org">Target Organization</Label>
                    <select
                      id="target-org"
                      className="w-full px-3 py-2 border rounded-md bg-background text-sm"
                      value={inviteForm.organization_id}
                      onChange={(e) => setInviteForm({ ...inviteForm, organization_id: e.target.value })}
                    >
                      <option value="">-- Create New Organization --</option>
                      {tenants.map((t) => (
                        <option key={t.id} value={t.id}>
                          Existing: {t.name}
                        </option>
                      ))}
                    </select>
                  </div>

                  {(!inviteForm.organization_id || inviteForm.organization_id === "") && (
                    <div className="space-y-2">
                      <Label htmlFor="org-name">New Organization Name</Label>
                      <Input
                        id="org-name"
                        placeholder="e.g. Acme Commercial Bank"
                        value={inviteForm.organization_name}
                        onChange={(e) => setInviteForm({ ...inviteForm, organization_name: e.target.value })}
                        required={!inviteForm.organization_id}
                      />
                    </div>
                  )}

                  <div className="space-y-2">
                    <Label htmlFor="admin-name">Admin Full Name</Label>
                    <Input
                      id="admin-name"
                      placeholder="e.g. Jane Doe"
                      value={inviteForm.full_name}
                      onChange={(e) => setInviteForm({ ...inviteForm, full_name: e.target.value })}
                      required
                    />
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="admin-email">Admin Email Address</Label>
                    <Input
                      id="admin-email"
                      type="email"
                      placeholder="jane.doe@acmebank.com"
                      value={inviteForm.email}
                      onChange={(e) => setInviteForm({ ...inviteForm, email: e.target.value })}
                      required
                    />
                  </div>
                </div>

                <DialogFooter>
                  <Button type="button" variant="ghost" onClick={() => setIsInviteOpen(false)}>
                    Cancel
                  </Button>
                  <Button type="submit" disabled={submitting} className="bg-indigo-600 hover:bg-indigo-700 text-white">
                    {submitting ? <Loader2 className="h-4 w-4 animate-spin mr-2" /> : <UserCheck className="h-4 w-4 mr-2" />}
                    Send Invitation
                  </Button>
                </DialogFooter>
              </form>
            </DialogContent>
          </Dialog>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <Card className="border-l-4 border-l-indigo-600">
          <CardHeader className="pb-2">
            <CardDescription className="text-xs uppercase font-semibold">Total Onboarded Tenants</CardDescription>
            <CardTitle className="text-3xl font-bold">{tenants.length}</CardTitle>
          </CardHeader>
        </Card>
        <Card className="border-l-4 border-l-green-500">
          <CardHeader className="pb-2">
            <CardDescription className="text-xs uppercase font-semibold">Completed ISO Onboarding</CardDescription>
            <CardTitle className="text-3xl font-bold">
              {tenants.filter((t) => t.onboarding_completed).length}
            </CardTitle>
          </CardHeader>
        </Card>
        <Card className="border-l-4 border-l-amber-500">
          <CardHeader className="pb-2">
            <CardDescription className="text-xs uppercase font-semibold">Active User Provisioning</CardDescription>
            <CardTitle className="text-3xl font-bold">
              {tenants.reduce((acc, t) => acc + t.user_count, 0)}
            </CardTitle>
          </CardHeader>
        </Card>
      </div>

      <Card>
        <CardHeader className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
          <div>
            <CardTitle>Customer Tenants</CardTitle>
            <CardDescription>Active organizations and platform instances.</CardDescription>
          </div>
          <div className="relative w-full md:w-72">
            <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" />
            <Input
              placeholder="Search tenant or industry..."
              className="pl-9"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
            />
          </div>
        </CardHeader>

        <CardContent>
          {loading ? (
            <div className="flex justify-center py-12">
              <Loader2 className="h-8 w-8 animate-spin text-indigo-600" />
            </div>
          ) : filteredTenants.length === 0 ? (
            <div className="text-center py-12 text-muted-foreground">No tenants found matching search criteria.</div>
          ) : (
            <div className="divide-y border rounded-lg overflow-hidden">
              {filteredTenants.map((tenant) => (
                <div key={tenant.id} className="p-4 flex flex-col md:flex-row md:items-center md:justify-between gap-4 hover:bg-slate-50 dark:hover:bg-slate-900 transition-colors">
                  <div className="space-y-1">
                    <div className="flex items-center gap-2">
                      <Building2 className="h-5 w-5 text-indigo-600" />
                      <span className="font-semibold text-lg">{tenant.name}</span>
                      {tenant.onboarding_completed ? (
                        <Badge className="bg-green-100 text-green-800 hover:bg-green-100">Ready</Badge>
                      ) : (
                        <Badge variant="outline" className="text-amber-600 border-amber-300">Onboarding Pending</Badge>
                      )}
                    </div>
                    <div className="flex flex-wrap gap-4 text-xs text-muted-foreground">
                      <span>Org ID: <code className="bg-muted px-1.5 py-0.5 rounded font-mono text-[11px] text-foreground">{tenant.id}</code></span>
                      <span>Industry: <strong className="text-foreground">{tenant.industry || "Not specified"}</strong></span>
                      <span>Users: <strong className="text-foreground">{tenant.user_count}</strong></span>
                      <span>Created: <strong className="text-foreground">{format(new Date(tenant.created_at), "MMM d, yyyy")}</strong></span>
                    </div>
                  </div>

                  <div className="flex items-center gap-3">
                    <div className="flex flex-wrap gap-1">
                      {tenant.compliance_frameworks?.map((fw) => (
                        <Badge key={fw} variant="secondary" className="text-[10px]">
                          {fw}
                        </Badge>
                      ))}
                    </div>

                    <Button
                      variant="outline"
                      size="sm"
                      className="gap-1.5 text-xs text-slate-700 hover:text-slate-900 border-slate-300"
                      onClick={() => handleImpersonate(tenant.id, tenant.name)}
                    >
                      <KeyRound className="h-3.5 w-3.5 text-indigo-600" />
                      Support Access
                    </Button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
