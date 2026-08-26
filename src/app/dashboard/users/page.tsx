"use client";

import { useState, useCallback, useEffect } from "react";
import { useAuth } from "@/hooks";
import { inviteUser, deleteUser } from "@/lib";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import {
    Select,
    SelectContent,
    SelectItem,
    SelectTrigger,
    SelectValue,
} from "@/components/ui/select";
import {
    Dialog,
    DialogContent,
    DialogDescription,
    DialogFooter,
    DialogHeader,
    DialogTitle,
    DialogTrigger,
} from "@/components/ui/dialog";
import { Loader2, AlertTriangle, Send, Trash2, Building2, Shield, Users } from "lucide-react";
import { api } from "@/lib/api-client";

import { PageRoleGuard } from "@/components/auth/PageRoleGuard";

interface TenantOption {
    id: string;
    name: string;
}

export default function UsersPage() {
    return (
        <PageRoleGuard allowedRoles={['superadmin', 'admin', 'manager', 'department_manager']} permissionKey="users">
            <UsersContent />
        </PageRoleGuard>
    );
}

function UsersContent() {
    const { user: currentUser } = useAuth();
    const [users, setUsers] = useState<any[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    // Super Admin Org Filter state
    const [tenants, setTenants] = useState<TenantOption[]>([]);
    const [selectedOrgId, setSelectedOrgId] = useState<string>("all");

    // Invite dialog state
    const [inviteDialogOpen, setInviteDialogOpen] = useState(false);
    const [inviteSubmitting, setInviteSubmitting] = useState(false);
    const [inviteError, setInviteError] = useState<string | null>(null);
    const [inviteEmail, setInviteEmail] = useState("");
    const [inviteFullName, setInviteFullName] = useState("");
    const [inviteRole, setInviteRole] = useState("analyst");
    const [inviteManagerId, setInviteManagerId] = useState("");
    const [inviteAuditDuration, setInviteAuditDuration] = useState("30_days");
    const [inviteSuccess, setInviteSuccess] = useState<string | null>(null);

    // Remove user state
    const [removingUserId, setRemovingUserId] = useState<string | null>(null);
    const [confirmRemoveId, setConfirmRemoveId] = useState<string | null>(null);
    const [confirmRemoveName, setConfirmRemoveName] = useState<string | null>(null);

    const isSuperAdmin = currentUser?.role === "superadmin";
    const isAdmin = currentUser?.role === "admin";
    const isManager = currentUser?.role === "manager" || currentUser?.role === "department_manager";

    const loadUsers = useCallback(async () => {
        setLoading(true);
        setError(null);
        try {
            let url = "/users/";
            if (isSuperAdmin && selectedOrgId && selectedOrgId !== "all") {
                url += `?organization_id=${selectedOrgId}`;
            }
            const data = await api.get<any[]>(url);
            setUsers(data || []);
        } catch (err: any) {
            setError(err?.message || "Failed to load users");
        } finally {
            setLoading(false);
        }
    }, [isSuperAdmin, selectedOrgId]);

    const loadTenants = useCallback(async () => {
        if (!isSuperAdmin) return;
        try {
            const data = await api.get<TenantOption[]>("/superadmin/organizations");
            setTenants(data || []);
        } catch (err) {
            console.error("Failed to load organizations for superadmin filter", err);
        }
    }, [isSuperAdmin]);

    useEffect(() => {
        loadUsers();
    }, [loadUsers]);

    useEffect(() => {
        loadTenants();
    }, [loadTenants]);

    const resetInviteForm = () => {
        setInviteEmail("");
        setInviteFullName("");
        setInviteRole(isManager ? "analyst" : "analyst");
        setInviteManagerId(isManager ? (currentUser?.id || "") : "");
        setInviteError(null);
        setInviteSuccess(null);
    };

    const handleInviteSubmit = useCallback(async () => {
        setInviteError(null);
        setInviteSuccess(null);

        if (!inviteEmail || !inviteFullName) {
            setInviteError("Email and full name are required.");
            return;
        }

        setInviteSubmitting(true);
        try {
            let expiresAt: string | undefined = undefined;
            if (inviteRole === "auditor") {
                const now = new Date();
                if (inviteAuditDuration === "7_days") now.setDate(now.getDate() + 7);
                else if (inviteAuditDuration === "14_days") now.setDate(now.getDate() + 14);
                else if (inviteAuditDuration === "30_days") now.setDate(now.getDate() + 30);
                else if (inviteAuditDuration === "90_days") now.setDate(now.getDate() + 90);
                expiresAt = now.toISOString();
            }

            await inviteUser({
                email: inviteEmail,
                full_name: inviteFullName,
                role: inviteRole,
                manager_id: isManager ? currentUser?.id : (inviteManagerId || undefined),
                access_expires_at: expiresAt,
            });
            setInviteSuccess(`Invitation sent to ${inviteEmail}`);
            setInviteEmail("");
            setInviteFullName("");
            loadUsers();
        } catch (err: any) {
            setInviteError(err?.message || "Failed to send invitation.");
        } finally {
            setInviteSubmitting(false);
        }
    }, [inviteEmail, inviteFullName, inviteRole, inviteManagerId, inviteAuditDuration, isManager, currentUser?.id, loadUsers]);

    const handleRemoveUser = useCallback(async (userId: string) => {
        if (userId === currentUser?.id) {
            toast.error("You cannot delete your own account");
            return;
        }

        setRemovingUserId(userId);
        try {
            await deleteUser(userId);
            toast.success("User deactivated");
            loadUsers();
        } catch (err: any) {
            toast.error(err?.message || "Failed to remove user.");
        } finally {
            setRemovingUserId(null);
            setConfirmRemoveId(null);
            setConfirmRemoveName(null);
        }
    }, [loadUsers, currentUser?.id]);

    return (
        <div className="space-y-6">
            {/* Header */}
            <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
                <div>
                    <div className="flex items-center gap-2">
                        <Users className="h-6 w-6 text-indigo-600" />
                        <h1 className="text-2xl font-bold text-slate-900">
                            {isManager ? "Team & Direct Reports Directory" : "User Management"}
                        </h1>
                    </div>
                    <p className="text-sm text-slate-600 mt-1">
                        {isSuperAdmin && "Platform-wide user directory with cross-organization filtering."}
                        {isAdmin && "Manage user accounts, roles, and supervisor assignments for your bank."}
                        {isManager && "View direct reporting analysts, control owners, and peer department managers."}
                        {!isSuperAdmin && !isAdmin && !isManager && "Your assigned supervisor and team contact info."}
                    </p>
                </div>

                {(isAdmin || isSuperAdmin || isManager) && (
                    <Dialog open={inviteDialogOpen} onOpenChange={(open) => { setInviteDialogOpen(open); if (!open) resetInviteForm(); }}>
                        <DialogTrigger asChild>
                            <Button className="bg-indigo-600 hover:bg-indigo-700 text-white gap-2 w-full sm:w-auto">
                                <Send className="h-4 w-4" />
                                {isManager ? "Add Team Analyst" : "Invite User"}
                            </Button>
                        </DialogTrigger>
                        <DialogContent className="sm:max-w-[425px]">
                            <DialogHeader>
                                <DialogTitle>{isManager ? "Invite Team Member" : "Invite User"}</DialogTitle>
                                <DialogDescription>
                                    Send an email invitation. The user will receive a link to set up their account.
                                </DialogDescription>
                            </DialogHeader>

                            <div className="grid gap-4 py-4">
                                <div className="space-y-2">
                                    <label className="text-sm font-medium text-slate-700">Full Name *</label>
                                    <Input
                                        placeholder="e.g. Jane Doe"
                                        value={inviteFullName}
                                        onChange={(e) => setInviteFullName(e.target.value)}
                                    />
                                </div>
                                <div className="space-y-2">
                                    <label className="text-sm font-medium text-slate-700">Email *</label>
                                    <Input
                                        type="email"
                                        placeholder="e.g. jane@company.com"
                                        value={inviteEmail}
                                        onChange={(e) => setInviteEmail(e.target.value)}
                                    />
                                </div>
                                <div className="space-y-2">
                                    <label className="text-sm font-medium text-slate-700">Role</label>
                                    <Select value={inviteRole} onValueChange={setInviteRole}>
                                        <SelectTrigger>
                                            <SelectValue />
                                        </SelectTrigger>
                                        <SelectContent>
                                            {isManager ? (
                                                <>
                                                    <SelectItem value="analyst">Risk Analyst</SelectItem>
                                                    <SelectItem value="control_owner">Control Owner</SelectItem>
                                                    <SelectItem value="risk_owner">Risk Owner</SelectItem>
                                                </>
                                            ) : (
                                                <>
                                                    <SelectItem value="admin">Tenant Admin</SelectItem>
                                                    <SelectItem value="manager">Manager</SelectItem>
                                                    <SelectItem value="analyst">Risk Analyst</SelectItem>
                                                    <SelectItem value="compliance_officer">Compliance Officer</SelectItem>
                                                    <SelectItem value="control_owner">Control Owner</SelectItem>
                                                    <SelectItem value="risk_owner">Risk Owner</SelectItem>
                                                    <SelectItem value="auditor">External Auditor</SelectItem>
                                                </>
                                            )}
                                        </SelectContent>
                                    </Select>
                                </div>

                                {inviteRole === 'auditor' && (
                                    <div className="space-y-2 bg-slate-50 p-3 rounded-lg border">
                                        <div className="flex items-center justify-between">
                                            <label className="text-sm font-medium text-slate-700">Audit Access Window *</label>
                                            <span className="text-[11px] text-muted-foreground">Auto-revokes upon expiration</span>
                                        </div>
                                        <Select value={inviteAuditDuration} onValueChange={setInviteAuditDuration}>
                                            <SelectTrigger>
                                                <SelectValue />
                                            </SelectTrigger>
                                            <SelectContent>
                                                <SelectItem value="7_days">7 Days (Short Audit)</SelectItem>
                                                <SelectItem value="14_days">14 Days (Standard Review)</SelectItem>
                                                <SelectItem value="30_days">30 Days (Full Audit Window)</SelectItem>
                                                <SelectItem value="90_days">90 Days (Quarterly Engagement)</SelectItem>
                                            </SelectContent>
                                        </Select>
                                    </div>
                                )}

                                {!isManager && inviteRole === 'analyst' && (
                                    <div className="space-y-2">
                                        <label className="text-sm font-medium text-slate-700">Assign Manager *</label>
                                        <Select value={inviteManagerId} onValueChange={setInviteManagerId}>
                                            <SelectTrigger>
                                                <SelectValue placeholder="Select a manager" />
                                            </SelectTrigger>
                                            <SelectContent>
                                                {users?.filter((u: any) => u.role === 'admin' || u.role === 'manager' || u.role === 'department_manager').map((m: any) => (
                                                    <SelectItem key={m.id} value={m.id}>{m.full_name || m.email} ({m.role})</SelectItem>
                                                ))}
                                            </SelectContent>
                                        </Select>
                                    </div>
                                )}

                                {inviteError && (
                                    <div className="rounded-md bg-red-50 border border-red-200 p-3">
                                        <p className="text-sm text-red-700">{inviteError}</p>
                                    </div>
                                )}
                                {inviteSuccess && (
                                    <div className="rounded-md bg-green-50 border border-green-200 p-3">
                                        <p className="text-sm text-green-700">{inviteSuccess}</p>
                                    </div>
                                )}
                            </div>

                            <DialogFooter>
                                <Button variant="outline" onClick={() => setInviteDialogOpen(false)} disabled={inviteSubmitting}>
                                    Cancel
                                </Button>
                                <Button onClick={handleInviteSubmit} disabled={inviteSubmitting} className="bg-indigo-600 hover:bg-indigo-700 text-white">
                                    {inviteSubmitting ? (
                                        <>
                                            <Loader2 className="h-4 w-4 animate-spin mr-2" />
                                            Sending…
                                        </>
                                    ) : (
                                        <>
                                            <Send className="h-4 w-4 mr-2" />
                                            Send Invitation
                                        </>
                                    )}
                                </Button>
                            </DialogFooter>
                        </DialogContent>
                    </Dialog>
                )}
            </div>

            {/* Super Admin Org Filter */}
            {isSuperAdmin && (
                <div className="bg-slate-50 border rounded-lg p-4 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                    <div className="flex items-center gap-2">
                        <Building2 className="h-5 w-5 text-indigo-600" />
                        <span className="text-sm font-semibold text-slate-800">Filter by Customer Tenant:</span>
                    </div>
                    <div className="w-full sm:w-72">
                        <Select value={selectedOrgId} onValueChange={setSelectedOrgId}>
                            <SelectTrigger className="bg-white">
                                <SelectValue placeholder="All Organizations" />
                            </SelectTrigger>
                            <SelectContent>
                                <SelectItem value="all">All Organizations (Global)</SelectItem>
                                {tenants.map((t) => (
                                    <SelectItem key={t.id} value={t.id}>
                                        {t.name}
                                    </SelectItem>
                                ))}
                            </SelectContent>
                        </Select>
                    </div>
                </div>
            )}

            {/* Users Table */}
            <div className="bg-white border rounded-xl overflow-hidden shadow-sm">
                {loading ? (
                    <div className="flex items-center justify-center py-24">
                        <Loader2 className="h-8 w-8 animate-spin text-indigo-600" />
                        <span className="ml-3 text-slate-600">Loading directory…</span>
                    </div>
                ) : error ? (
                    <div className="flex flex-col items-center justify-center py-24 text-center">
                        <AlertTriangle className="h-12 w-12 text-red-400 mb-4" />
                        <h3 className="text-sm font-medium text-slate-900 mb-1">Failed to load users</h3>
                        <p className="text-sm text-slate-500">{error}</p>
                    </div>
                ) : (
                    <div className="overflow-x-auto">
                        <table className="w-full text-sm text-left">
                            <thead className="bg-slate-50 text-slate-500 font-medium border-b hidden sm:table-header-group">
                                <tr>
                                    <th className="px-6 py-4">User</th>
                                    <th className="px-6 py-4">Role</th>
                                    {isSuperAdmin && <th className="px-6 py-4">Organization</th>}
                                    <th className="px-6 py-4">Department</th>
                                    <th className="px-6 py-4 text-right">Status</th>
                                    {(isAdmin || isSuperAdmin || isManager) && (
                                        <th className="px-6 py-4 text-right">Actions</th>
                                    )}
                                </tr>
                            </thead>
                            <tbody className="divide-y">
                                {users?.length === 0 ? (
                                    <tr>
                                        <td colSpan={6} className="px-6 py-12 text-center text-slate-500">
                                            No users found for the current view.
                                        </td>
                                    </tr>
                                ) : (
                                    users?.map((u: any) => (
                                        <tr key={u.id} className="hover:bg-slate-50/50 transition-colors flex flex-col sm:table-row">
                                            <td className="px-6 py-4 flex gap-3 items-center">
                                                <div className="h-10 w-10 rounded-full bg-indigo-100 flex items-center justify-center text-indigo-700 font-semibold shrink-0">
                                                    {u.full_name ? u.full_name.charAt(0).toUpperCase() : u.email.charAt(0).toUpperCase()}
                                                </div>
                                                <div>
                                                    <div className="font-medium text-slate-900 flex items-center gap-2">
                                                        {u.full_name || 'No Name'}
                                                        {u.id === currentUser?.id && (
                                                            <Badge variant="outline" className="text-[10px]">You</Badge>
                                                        )}
                                                    </div>
                                                    <div className="text-slate-500 text-xs">{u.email}</div>
                                                </div>
                                            </td>
                                            <td className="px-6 py-2 sm:py-4">
                                                <span className={`inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full font-medium text-xs ${{
                                                    superadmin: 'bg-indigo-100 text-indigo-800',
                                                    admin: 'bg-purple-100 text-purple-700',
                                                    manager: 'bg-green-100 text-green-700',
                                                    analyst: 'bg-blue-100 text-blue-700',
                                                    compliance_officer: 'bg-amber-100 text-amber-700',
                                                    control_owner: 'bg-teal-100 text-teal-700',
                                                    risk_owner: 'bg-rose-100 text-rose-700',
                                                    auditor: 'bg-slate-100 text-slate-700',
                                                }[u.role as string] || 'bg-slate-100 text-slate-700'}`}>
                                                    {u.role}
                                                </span>
                                            </td>
                                            {isSuperAdmin && (
                                                <td className="px-6 py-2 sm:py-4 text-slate-600 font-medium">
                                                    <div>{u.organization_name || 'Platform Team'}</div>
                                                    {u.organization_id && (
                                                        <div className="font-mono text-[10px] text-slate-400 select-all">ID: {u.organization_id}</div>
                                                    )}
                                                </td>
                                            )}
                                            <td className="px-6 py-2 sm:py-4 text-slate-600">
                                                {u.department || '—'}
                                            </td>
                                            <td className="px-6 py-2 sm:py-4 sm:text-right">
                                                <div className="flex flex-col sm:items-end gap-1">
                                                    <span className={`inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full font-medium text-xs ${
                                                        u.is_active ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'
                                                    }`}>
                                                        {u.is_active ? 'Active' : 'Inactive'}
                                                    </span>
                                                    {u.access_expires_at && (
                                                        <span className="text-[10px] text-amber-700 bg-amber-50 px-2 py-0.5 rounded border border-amber-200">
                                                            Expires: {new Date(u.access_expires_at).toLocaleDateString()}
                                                        </span>
                                                    )}
                                                </div>
                                            </td>
                                            {(isAdmin || isSuperAdmin || isManager) && (
                                                <td className="px-6 py-2 sm:py-4 sm:text-right">
                                                    {confirmRemoveId === u.id ? (
                                                        <div className="flex flex-col items-end gap-2">
                                                            <span className="text-xs font-medium text-red-600">
                                                                Deactivate {u.full_name || u.email}?
                                                            </span>
                                                            <div className="flex items-center justify-end gap-2">
                                                                <Button
                                                                    variant="destructive"
                                                                    size="sm"
                                                                    disabled={removingUserId === u.id}
                                                                    onClick={() => handleRemoveUser(u.id)}
                                                                >
                                                                    {removingUserId === u.id ? (
                                                                        <Loader2 className="h-3 w-3 animate-spin" />
                                                                    ) : (
                                                                        "Deactivate"
                                                                    )}
                                                                </Button>
                                                                <Button
                                                                    variant="outline"
                                                                    size="sm"
                                                                    onClick={() => {
                                                                        setConfirmRemoveId(null);
                                                                        setConfirmRemoveName(null);
                                                                    }}
                                                                >
                                                                    Cancel
                                                                </Button>
                                                            </div>
                                                        </div>
                                                    ) : (
                                                        <Button
                                                            variant="ghost"
                                                            size="sm"
                                                            disabled={u.id === currentUser?.id || (isManager && u.manager_id !== currentUser?.id)}
                                                            className="text-red-500 hover:text-red-700 hover:bg-red-50 disabled:opacity-30"
                                                            onClick={() => {
                                                                setConfirmRemoveId(u.id);
                                                                setConfirmRemoveName(u.full_name || u.email);
                                                            }}
                                                        >
                                                            <Trash2 className="h-4 w-4" />
                                                        </Button>
                                                    )}
                                                </td>
                                            )}
                                        </tr>
                                    ))
                                )}
                            </tbody>
                        </table>
                    </div>
                )}
            </div>
        </div>
    );
}
