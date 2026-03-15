"use client";

import { useState, useCallback } from "react";
import { useApiData, useAuth } from "@/hooks";
import { fetchUsers, inviteUser } from "@/lib";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
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
import { Loader2, AlertTriangle, Send, Trash2 } from "lucide-react";
import { RoleGuard } from "@/components/auth";
import { api } from "@/lib/api-client";

export default function UsersPage() {
    const { data: users, loading, error, refetch } = useApiData(fetchUsers);
    const { user: currentUser } = useAuth();

    // Invite dialog state
    const [inviteDialogOpen, setInviteDialogOpen] = useState(false);
    const [inviteSubmitting, setInviteSubmitting] = useState(false);
    const [inviteError, setInviteError] = useState<string | null>(null);
    const [inviteEmail, setInviteEmail] = useState("");
    const [inviteFullName, setInviteFullName] = useState("");
    const [inviteRole, setInviteRole] = useState("analyst");
    const [inviteManagerId, setInviteManagerId] = useState("");
    const [inviteSuccess, setInviteSuccess] = useState<string | null>(null);

    // Remove user state
    const [removingUserId, setRemovingUserId] = useState<string | null>(null);
    const [confirmRemoveId, setConfirmRemoveId] = useState<string | null>(null);

    const resetInviteForm = () => {
        setInviteEmail("");
        setInviteFullName("");
        setInviteRole("analyst");
        setInviteManagerId("");
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
            await inviteUser({
                email: inviteEmail,
                full_name: inviteFullName,
                role: inviteRole,
                manager_id: inviteManagerId || undefined,
            });
            setInviteSuccess(`Invitation sent to ${inviteEmail}`);
            setInviteEmail("");
            setInviteFullName("");
            refetch();
        } catch (err: any) {
            setInviteError(err?.message || "Failed to send invitation.");
        } finally {
            setInviteSubmitting(false);
        }
    }, [inviteEmail, inviteFullName, inviteRole, inviteManagerId, refetch]);

    const handleRemoveUser = useCallback(async (userId: string) => {
        setRemovingUserId(userId);
        try {
            await api.delete(`/users/${userId}/`);
            refetch();
        } catch (err: any) {
            alert(err?.message || "Failed to remove user.");
        } finally {
            setRemovingUserId(null);
            setConfirmRemoveId(null);
        }
    }, [refetch]);

    if (loading) {
        return (
            <div className="flex items-center justify-center py-24">
                <Loader2 className="h-8 w-8 animate-spin text-blue-600" />
                <span className="ml-3 text-slate-600">Loading users…</span>
            </div>
        );
    }

    if (error) {
        return (
            <div className="flex flex-col items-center justify-center py-24 text-center">
                <AlertTriangle className="h-12 w-12 text-red-400 mb-4" />
                <h3 className="text-sm font-medium text-slate-900 mb-1">Failed to load users</h3>
                <p className="text-sm text-slate-500">{error.message}</p>
            </div>
        );
    }

    return (
        <div className="space-y-6">
            {/* Header */}
            <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
                <div>
                    <h1 className="text-2xl font-bold text-slate-900 mb-1">User Management</h1>
                    <p className="text-sm text-slate-600">Manage system users and their roles</p>
                </div>
                <RoleGuard allowedRoles={['admin']}>
                    {/* Invite User Dialog */}
                    <Dialog open={inviteDialogOpen} onOpenChange={(open) => { setInviteDialogOpen(open); if (!open) resetInviteForm(); }}>
                        <DialogTrigger asChild>
                            <Button variant="outline" className="gap-2 w-full sm:w-auto">
                                <Send className="h-4 w-4" />
                                Invite User
                            </Button>
                        </DialogTrigger>
                        <DialogContent className="sm:max-w-[425px]">
                            <DialogHeader>
                                <DialogTitle>Invite User</DialogTitle>
                                <DialogDescription>
                                    Send an email invitation. The user will receive a link to join the platform.
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
                                            <SelectItem value="manager">Manager</SelectItem>
                                            <SelectItem value="analyst">Analyst</SelectItem>
                                        </SelectContent>
                                    </Select>
                                </div>
                                {inviteRole === 'analyst' && (
                                    <div className="space-y-2">
                                        <label className="text-sm font-medium text-slate-700">Assign Manager *</label>
                                        <Select value={inviteManagerId} onValueChange={setInviteManagerId}>
                                            <SelectTrigger>
                                                <SelectValue placeholder="Select a manager" />
                                            </SelectTrigger>
                                            <SelectContent>
                                                {users?.filter((u: any) => u.role === 'admin' || u.role === 'manager').map((m: any) => (
                                                    <SelectItem key={m.id} value={m.id}>{m.full_name} ({m.role})</SelectItem>
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
                                <Button onClick={handleInviteSubmit} disabled={inviteSubmitting}>
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
                </RoleGuard>
            </div>

            {/* Users Table */}
            <div className="bg-white border rounded-xl overflow-hidden shadow-sm">
                <div className="overflow-x-auto">
                    <table className="w-full text-sm text-left">
                        <thead className="bg-slate-50 text-slate-500 font-medium border-b hidden sm:table-header-group">
                            <tr>
                                <th className="px-6 py-4">User</th>
                                <th className="px-6 py-4">Role</th>
                                <th className="px-6 py-4">Department</th>
                                <th className="px-6 py-4 text-right">Status</th>
                                <th className="px-6 py-4 text-right">Actions</th>
                            </tr>
                        </thead>
                        <tbody className="divide-y">
                            {users?.length === 0 ? (
                                <tr>
                                    <td colSpan={5} className="px-6 py-12 text-center text-slate-500">
                                        No users found. Use &quot;Invite User&quot; to add someone.
                                    </td>
                                </tr>
                            ) : (
                                users?.map((user: any) => (
                                    <tr key={user.id} className="hover:bg-slate-50/50 transition-colors flex flex-col sm:table-row">
                                        <td className="px-6 py-4 flex gap-3 items-center">
                                            <div className="h-10 w-10 rounded-full bg-blue-100 flex items-center justify-center text-blue-700 font-semibold shrink-0">
                                                {user.full_name ? user.full_name.charAt(0).toUpperCase() : user.email.charAt(0).toUpperCase()}
                                            </div>
                                            <div>
                                                <div className="font-medium text-slate-900">{user.full_name || 'No Name'}</div>
                                                <div className="text-slate-500 text-xs">{user.email}</div>
                                            </div>
                                        </td>
                                        <td className="px-6 py-2 sm:py-4">
                                            <span className={`inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full font-medium text-xs ${{
                                                admin: 'bg-purple-100 text-purple-700',
                                                manager: 'bg-green-100 text-green-700',
                                                analyst: 'bg-blue-100 text-blue-700',
                                            }[user.role as string] || 'bg-slate-100 text-slate-700'}`}>
                                                {{
                                                    admin: 'Administrator',
                                                    manager: 'Manager',
                                                    analyst: 'Risk Analyst',
                                                }[user.role as string] || user.role}
                                            </span>
                                        </td>
                                        <td className="px-6 py-2 sm:py-4 text-slate-600">
                                            {user.department || '—'}
                                        </td>
                                        <td className="px-6 py-2 sm:py-4 sm:text-right">
                                            <span className={`inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full font-medium text-xs ${
                                                user.is_active ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'
                                            }`}>
                                                {user.is_active ? 'Active' : 'Inactive'}
                                            </span>
                                        </td>
                                        <td className="px-6 py-2 sm:py-4 sm:text-right">
                                            {user.id !== currentUser?.id && (
                                                confirmRemoveId === user.id ? (
                                                    <div className="flex items-center justify-end gap-2">
                                                        <span className="text-xs text-slate-500">Are you sure?</span>
                                                        <Button
                                                            variant="destructive"
                                                            size="sm"
                                                            disabled={removingUserId === user.id}
                                                            onClick={() => handleRemoveUser(user.id)}
                                                        >
                                                            {removingUserId === user.id ? (
                                                                <Loader2 className="h-3 w-3 animate-spin" />
                                                            ) : (
                                                                "Yes, Remove"
                                                            )}
                                                        </Button>
                                                        <Button
                                                            variant="outline"
                                                            size="sm"
                                                            onClick={() => setConfirmRemoveId(null)}
                                                        >
                                                            Cancel
                                                        </Button>
                                                    </div>
                                                ) : (
                                                    <Button
                                                        variant="ghost"
                                                        size="sm"
                                                        className="text-red-500 hover:text-red-700 hover:bg-red-50"
                                                        onClick={() => setConfirmRemoveId(user.id)}
                                                    >
                                                        <Trash2 className="h-4 w-4" />
                                                    </Button>
                                                )
                                            )}
                                        </td>
                                    </tr>
                                ))
                            )}
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
    );
}
