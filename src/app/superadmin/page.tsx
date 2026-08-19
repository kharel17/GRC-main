"use client";

import { useState, useEffect } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Building2, Shield, Users, Loader2, Plus, UserCheck, Search, KeyRound } from "lucide-react";
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
  const [tenants, setTenants] = useState<TenantSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState("");
  const [isInviteOpen, setIsInviteOpen] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [inviteForm, setInviteForm] = useState({
    email: "",
    full_name: "",
    organization_name: "",
  });

  const fetchTenants = async () => {
    setLoading(true);
    try {
      const res = await fetch("/api/v1/superadmin/organizations", {
        headers: {
          Authorization: `Bearer ${localStorage.getItem("access_token")}`,
        },
      });
      if (!res.ok) throw new Error("Failed to load tenant overview");
      const data = await res.json();
      setTenants(data);
    } catch (err: any) {
      toast.error(err.message || "Could not load superadmin data");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchTenants();
  }, []);

  const handleInviteAdmin = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitting(true);
    try {
      const res = await fetch("/api/v1/invitations/invite-admin", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${localStorage.getItem("access_token")}`,
        },
        body: JSON.stringify(inviteForm),
      });

      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "Failed to invite tenant admin");

      toast.success(`Invitation sent to ${inviteForm.email}`);
      setIsInviteOpen(false);
      setInviteForm({ email: "", full_name: "", organization_name: "" });
      fetchTenants();
    } catch (err: any) {
      toast.error(err.message || "Failed to send invitation");
    } finally {
      setSubmitting(false);
    }
  };

  const handleImpersonate = async (orgId: string, orgName: string) => {
    try {
      const res = await fetch(`/api/v1/superadmin/impersonate/${orgId}`, {
        method: "POST",
        headers: {
          Authorization: `Bearer ${localStorage.getItem("access_token")}`,
        },
      });

      if (!res.ok) throw new Error("Impersonation request denied");
      const data = await res.json();

      toast.success(`Support session initiated for ${orgName}`);
      // Store temporary support session token
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

        <Dialog open={isInviteOpen} onOpenChange={setIsInviteOpen}>
          <DialogTrigger asChild>
            <Button className="bg-indigo-600 hover:bg-indigo-700 text-white gap-2">
              <Plus className="h-4 w-4" />
              Onboard New Tenant
            </Button>
          </DialogTrigger>
          <DialogContent>
            <form onSubmit={handleInviteAdmin}>
              <DialogHeader>
                <DialogTitle>Provision Customer Tenant</DialogTitle>
                <DialogDescription>
                  Invite a Primary Tenant Administrator to onboard a new organization.
                </DialogDescription>
              </DialogHeader>

              <div className="space-y-4 py-4">
                <div className="space-y-2">
                  <Label htmlFor="org-name">Organization Name</Label>
                  <Input
                    id="org-name"
                    placeholder="e.g. Acme Commercial Bank"
                    value={inviteForm.organization_name}
                    onChange={(e) => setInviteForm({ ...inviteForm, organization_name: e.target.value })}
                    required
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="admin-name">Primary Admin Name</Label>
                  <Input
                    id="admin-name"
                    placeholder="e.g. Jane Doe"
                    value={inviteForm.full_name}
                    onChange={(e) => setInviteForm({ ...inviteForm, full_name: e.target.value })}
                    required
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="admin-email">Primary Admin Email</Label>
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
