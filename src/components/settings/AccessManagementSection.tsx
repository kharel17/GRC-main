'use client';

import { useState, useEffect } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Badge } from '@/components/ui/badge';
import { Checkbox } from '@/components/ui/checkbox';
import { Textarea } from '@/components/ui/textarea';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import {
  KeyRound,
  Plus,
  Edit2,
  Trash2,
  Users,
  ShieldCheck,
  CheckCircle2,
  Loader2,
  Layers,
  Sparkles,
} from 'lucide-react';
import { toast } from 'sonner';
import {
  PermissionProfile,
  fetchPermissionProfiles,
  createPermissionProfile,
  updatePermissionProfile,
  deletePermissionProfile,
  assignPermissionProfile,
  fetchUsers,
} from '@/lib/data-service';

const NAV_FEATURE_ITEMS = [
  { key: 'organization', label: 'Organization Settings', section: 'Manage' },
  { key: 'assets', label: 'Asset Inventory', section: 'Manage' },
  { key: 'risks', label: 'Risk Register', section: 'Manage' },
  { key: 'controls', label: 'Controls Catalog', section: 'Manage' },
  { key: 'tickets', label: 'Remediation Tickets', section: 'Manage' },
  { key: 'iso27001', label: 'ISO 27001 (SoA)', section: 'Comply' },
  { key: 'gap_analysis', label: 'Gap Analysis', section: 'Comply' },
  { key: 'evidence', label: 'Evidence Locker', section: 'Comply' },
  { key: 'audit_preparation', label: 'Audit Preparation', section: 'Audit' },
  { key: 'document_analysis', label: 'AI Document Analysis', section: 'Audit' },
  { key: 'audit_log', label: 'Audit Trail Logs', section: 'Audit' },
  { key: 'reports', label: 'Reports & Exports', section: 'Audit' },
  { key: 'users', label: 'Team User Directory', section: 'Admin' },
];

export function AccessManagementSection() {
  const [profiles, setProfiles] = useState<PermissionProfile[]>([]);
  const [users, setUsers] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  // Dialog states
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editingProfile, setEditingProfile] = useState<PermissionProfile | null>(null);
  const [formData, setFormData] = useState<{
    name: string;
    description: string;
    nav_permissions: Record<string, boolean>;
  }>({
    name: '',
    description: '',
    nav_permissions: {},
  });
  const [saving, setSaving] = useState(false);
  const [deletingId, setDeletingId] = useState<string | null>(null);

  // User assignment state
  const [assigningUserId, setAssigningUserId] = useState<string | null>(null);

  const loadData = async () => {
    setLoading(true);
    try {
      const [profilesData, usersData] = await Promise.all([
        fetchPermissionProfiles(),
        fetchUsers(),
      ]);
      setProfiles(profilesData || []);
      setUsers(usersData || []);
    } catch (err: any) {
      toast.error('Failed to load permission management data');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const openCreateDialog = () => {
    setEditingProfile(null);
    setFormData({
      name: '',
      description: '',
      nav_permissions: {
        assets: true,
        risks: true,
        controls: true,
        iso27001: true,
        evidence: true,
      },
    });
    setDialogOpen(true);
  };

  const openEditDialog = (profile: PermissionProfile) => {
    setEditingProfile(profile);
    setFormData({
      name: profile.name,
      description: profile.description || '',
      nav_permissions: { ...(profile.nav_permissions || {}) },
    });
    setDialogOpen(true);
  };

  const togglePermission = (key: string) => {
    setFormData((prev) => ({
      ...prev,
      nav_permissions: {
        ...prev.nav_permissions,
        [key]: !prev.nav_permissions[key],
      },
    }));
  };

  const handleSelectAll = (checked: boolean) => {
    const next: Record<string, boolean> = {};
    NAV_FEATURE_ITEMS.forEach((item) => {
      next[item.key] = checked;
    });
    setFormData((prev) => ({ ...prev, nav_permissions: next }));
  };

  const handleSaveProfile = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!formData.name.trim()) {
      toast.error('Profile name is required');
      return;
    }

    setSaving(true);
    try {
      if (editingProfile) {
        await updatePermissionProfile(editingProfile.id, formData);
        toast.success(`Permission profile '${formData.name}' updated!`);
      } else {
        await createPermissionProfile(formData);
        toast.success(`Permission profile '${formData.name}' created!`);
      }
      setDialogOpen(false);
      await loadData();
    } catch (err: any) {
      toast.error(err.message || 'Failed to save profile');
    } finally {
      setSaving(false);
    }
  };

  const handleDeleteProfile = async (id: string, name: string) => {
    if (!confirm(`Are you sure you want to delete the '${name}' permission profile? Assigned users will revert to standard role permissions.`)) {
      return;
    }
    setDeletingId(id);
    try {
      await deletePermissionProfile(id);
      toast.success('Permission profile deleted');
      await loadData();
    } catch (err: any) {
      toast.error(err.message || 'Failed to delete profile');
    } finally {
      setDeletingId(null);
    }
  };

  const handleUserAssignProfile = async (userId: string, profileId: string | null) => {
    setAssigningUserId(userId);
    try {
      await assignPermissionProfile({
        user_id: userId,
        permission_profile_id: profileId === 'none' ? null : profileId,
      });
      toast.success('User permission profile updated!');
      await loadData();
    } catch (err: any) {
      toast.error(err.message || 'Failed to assign profile');
    } finally {
      setAssigningUserId(null);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center py-16">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
        <span className="ml-3 text-sm text-muted-foreground">Loading access controls...</span>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* ── 1. Header Card ── */}
      <Card className="border-indigo-100 bg-gradient-to-r from-indigo-50/50 via-slate-50/50 to-white dark:from-indigo-950/20 dark:via-slate-900/40 dark:to-slate-900">
        <CardHeader>
          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
            <div className="space-y-1">
              <CardTitle className="text-xl font-bold flex items-center gap-2">
                <KeyRound className="h-5 w-5 text-indigo-600" />
                Custom Permission Profiles & Access Management
              </CardTitle>
              <CardDescription>
                Create customized permission profiles with specific feature navigation access and assign them to your organization team members.
              </CardDescription>
            </div>
            <Button onClick={openCreateDialog} className="bg-indigo-600 hover:bg-indigo-700 text-white gap-2 shrink-0">
              <Plus className="h-4 w-4" />
              New Permission Profile
            </Button>
          </div>
        </CardHeader>
      </Card>

      {/* ── 2. Permission Profiles Grid ── */}
      <div className="space-y-3">
        <h3 className="text-sm font-semibold text-foreground flex items-center gap-2">
          <Layers className="h-4 w-4 text-indigo-600" />
          Active Permission Profiles ({profiles.length})
        </h3>

        {profiles.length === 0 ? (
          <Card className="border-dashed">
            <CardContent className="py-8 text-center text-muted-foreground space-y-3">
              <ShieldCheck className="h-10 w-10 text-muted-foreground/50 mx-auto" />
              <p className="text-sm">No custom permission profiles created yet.</p>
              <p className="text-xs text-muted-foreground max-w-sm mx-auto">
                Users currently operate on their standard default role permissions. Create a custom profile to grant enhanced feature navigation to specific analysts or managers.
              </p>
              <Button variant="outline" size="sm" onClick={openCreateDialog} className="mt-2">
                Create First Profile
              </Button>
            </CardContent>
          </Card>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {profiles.map((profile) => {
              const activePermissionsCount = Object.values(profile.nav_permissions || {}).filter(Boolean).length;
              const assignedCount = users.filter((u) => u.permission_profile_id === profile.id).length;

              return (
                <Card key={profile.id} className="relative hover:shadow-md transition-shadow">
                  <CardHeader className="pb-3">
                    <div className="flex items-start justify-between gap-2">
                      <CardTitle className="text-base font-semibold">{profile.name}</CardTitle>
                      <Badge variant="secondary" className="text-[11px] font-medium shrink-0">
                        {activePermissionsCount} of {NAV_FEATURE_ITEMS.length} Features
                      </Badge>
                    </div>
                    {profile.description && (
                      <CardDescription className="text-xs line-clamp-2">
                        {profile.description}
                      </CardDescription>
                    )}
                  </CardHeader>
                  <CardContent className="space-y-3 pb-3">
                    <div className="flex items-center gap-2 text-xs text-muted-foreground">
                      <Users className="h-3.5 w-3.5" />
                      <span><strong>{assignedCount}</strong> {assignedCount === 1 ? 'user' : 'users'} assigned</span>
                    </div>

                    <div className="flex flex-wrap gap-1 max-h-24 overflow-y-auto">
                      {NAV_FEATURE_ITEMS.filter((item) => profile.nav_permissions?.[item.key]).map((item) => (
                        <span key={item.key} className="inline-flex items-center px-2 py-0.5 rounded text-[10px] bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300 font-medium">
                          {item.label}
                        </span>
                      ))}
                    </div>
                  </CardContent>
                  <div className="border-t p-3 bg-muted/20 flex items-center justify-end gap-2 rounded-b-lg">
                    <Button variant="ghost" size="sm" onClick={() => openEditDialog(profile)} className="h-8 gap-1 text-xs">
                      <Edit2 className="h-3.5 w-3.5" />
                      Edit
                    </Button>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => handleDeleteProfile(profile.id, profile.name)}
                      disabled={deletingId === profile.id}
                      className="h-8 gap-1 text-xs text-red-600 hover:text-red-700 hover:bg-red-50"
                    >
                      {deletingId === profile.id ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Trash2 className="h-3.5 w-3.5" />}
                      Delete
                    </Button>
                  </div>
                </Card>
              );
            })}
          </div>
        )}
      </div>

      {/* ── 3. User Assignments Table ── */}
      <Card>
        <CardHeader>
          <CardTitle className="text-lg font-semibold flex items-center gap-2">
            <Users className="h-5 w-5 text-indigo-600" />
            Member Permission Assignments
          </CardTitle>
          <CardDescription>
            Assign customized permission profiles to organization members to expand their standard sidebar navigation and access privileges.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="border rounded-lg overflow-hidden">
            <table className="w-full text-sm">
              <thead className="bg-muted/50 border-b">
                <tr>
                  <th className="px-4 py-3 text-left font-semibold">User</th>
                  <th className="px-4 py-3 text-left font-semibold">Base Role</th>
                  <th className="px-4 py-3 text-left font-semibold">Assigned Profile</th>
                  <th className="px-4 py-3 text-right font-semibold">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y">
                {users.map((u: any) => (
                  <tr key={u.id} className="hover:bg-muted/30 transition-colors">
                    <td className="px-4 py-3">
                      <div className="font-medium text-foreground">{u.full_name || 'No Name'}</div>
                      <div className="text-xs text-muted-foreground">{u.email}</div>
                    </td>
                    <td className="px-4 py-3">
                      <span className={`inline-block text-[11px] px-2 py-0.5 rounded-full font-medium ${{
                        superadmin: 'bg-indigo-100 text-indigo-800',
                        admin: 'bg-purple-100 text-purple-700',
                        manager: 'bg-green-100 text-green-700',
                        analyst: 'bg-blue-100 text-blue-700',
                        compliance_officer: 'bg-amber-100 text-amber-700',
                        auditor: 'bg-slate-100 text-slate-700',
                      }[u.role as string] || 'bg-slate-100 text-slate-700'}`}>
                        {u.role}
                      </span>
                    </td>
                    <td className="px-4 py-3">
                      {u.permission_profile_id ? (
                        <Badge variant="outline" className="bg-indigo-50 text-indigo-700 border-indigo-200 gap-1 font-medium">
                          <Sparkles className="h-3 w-3" />
                          {profiles.find((p) => p.id === u.permission_profile_id)?.name || 'Custom Profile'}
                        </Badge>
                      ) : (
                        <span className="text-xs text-muted-foreground">Standard Role Defaults</span>
                      )}
                    </td>
                    <td className="px-4 py-3 text-right">
                      <Select
                        defaultValue={u.permission_profile_id || 'none'}
                        onValueChange={(val) => handleUserAssignProfile(u.id, val)}
                        disabled={assigningUserId === u.id || u.role === 'admin' || u.role === 'superadmin'}
                      >
                        <SelectTrigger className="w-48 h-8 text-xs ml-auto">
                          <SelectValue placeholder="Select profile..." />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="none">Standard Role Defaults</SelectItem>
                          {profiles.map((p) => (
                            <SelectItem key={p.id} value={p.id}>
                              {p.name}
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </CardContent>
      </Card>

      {/* ── 4. Create / Edit Profile Dialog ── */}
      <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
        <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
          <form onSubmit={handleSaveProfile}>
            <DialogHeader>
              <DialogTitle>
                {editingProfile ? 'Edit Permission Profile' : 'Create Custom Permission Profile'}
              </DialogTitle>
              <DialogDescription>
                Select which navigation modules and GRC features users with this profile can access.
              </DialogDescription>
            </DialogHeader>

            <div className="space-y-4 py-4">
              <div className="space-y-2">
                <Label htmlFor="profile-name">Profile Name</Label>
                <Input
                  id="profile-name"
                  placeholder="e.g. Lead Risk Analyst, External Auditor"
                  value={formData.name}
                  onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                  required
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="profile-desc">Description (Optional)</Label>
                <Textarea
                  id="profile-desc"
                  placeholder="Briefly describe what this permission profile is intended for..."
                  value={formData.description}
                  onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                  rows={2}
                />
              </div>

              {/* Navigation Permissions Checklist */}
              <div className="space-y-3 pt-2">
                <div className="flex items-center justify-between border-b pb-2">
                  <Label className="text-sm font-semibold">Navigation & Feature Permissions</Label>
                  <div className="flex items-center gap-2">
                    <Button type="button" variant="ghost" size="sm" onClick={() => handleSelectAll(true)} className="h-7 text-xs">
                      Select All
                    </Button>
                    <Button type="button" variant="ghost" size="sm" onClick={() => handleSelectAll(false)} className="h-7 text-xs text-muted-foreground">
                      Deselect All
                    </Button>
                  </div>
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 pt-1">
                  {NAV_FEATURE_ITEMS.map((item) => (
                    <div
                      key={item.key}
                      onClick={() => togglePermission(item.key)}
                      className={`flex items-start gap-3 p-3 rounded-lg border cursor-pointer transition-colors ${
                        formData.nav_permissions[item.key]
                          ? 'border-indigo-300 bg-indigo-50/40 dark:bg-indigo-950/20 dark:border-indigo-800'
                          : 'border-slate-200 hover:bg-slate-50 dark:hover:bg-slate-900'
                      }`}
                    >
                      <Checkbox
                        checked={Boolean(formData.nav_permissions[item.key])}
                        onCheckedChange={() => togglePermission(item.key)}
                        className="mt-0.5 data-[state=checked]:bg-indigo-600 data-[state=checked]:border-indigo-600"
                      />
                      <div className="space-y-0.5 leading-none">
                        <p className="text-sm font-medium text-foreground">{item.label}</p>
                        <p className="text-[11px] text-muted-foreground">Section: {item.section}</p>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>

            <DialogFooter>
              <Button type="button" variant="outline" onClick={() => setDialogOpen(false)} disabled={saving}>
                Cancel
              </Button>
              <Button type="submit" disabled={saving} className="bg-indigo-600 hover:bg-indigo-700 text-white">
                {saving ? (
                  <>
                    <Loader2 className="h-4 w-4 animate-spin mr-2" />
                    Saving...
                  </>
                ) : (
                  <>
                    <CheckCircle2 className="h-4 w-4 mr-2" />
                    {editingProfile ? 'Save Changes' : 'Create Profile'}
                  </>
                )}
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>
    </div>
  );
}
