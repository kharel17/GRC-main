"use client";

import { useState } from 'react';
import {
  fetchCurrentUserProfile,
  updateCurrentUserProfile,
  fetchOrganization,
  updateOrganization,
  initializeControlApplicabilityFramework,
  fetchRisks,
  fetchEvidence,
  fetchAuditLogs,
  fetchControlApplicabilityComplianceScore,
} from '@/lib/data-service';
import { useAuth, useApiData } from '@/hooks';
import { Organization, UserProfile } from '@/types';
import {
  COMPLIANCE_FRAMEWORK_OPTIONS,
  normalizeComplianceFrameworkId,
} from '@/lib/constants';

import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Switch } from '@/components/ui/switch';
import { Badge } from '@/components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
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
  User as UserIcon,
  Shield,
  Bell,
  Settings,
  Lock,
  Mail,
  Globe,
  Palette,
  Loader2,
  Plus,
  CheckCircle2,
  Trash2,
  Laptop,
  Smartphone,
  Monitor,
  LogOut as RevokeIcon,
  Calendar,
  TrendingUp,
  TrendingDown,
  FileText,
  Activity,
  KeyRound,
} from 'lucide-react';
import { ThemeSelector } from '@/components/settings/ThemeSelector';
import { toast } from 'sonner';
import { useLanguage, Language } from '@/context/LanguageContext';
import { AccessManagementSection } from '@/components/settings/AccessManagementSection';

export default function SettingsPage() {
  const [activeTab, setActiveTab] = useState('profile');
  const [frameworkDialogOpen, setFrameworkDialogOpen] = useState(false);
  const [selectedFrameworkId, setSelectedFrameworkId] = useState('iso27001');
  const [addingFramework, setAddingFramework] = useState(false);
  const { user: authUser, isLoading: authLoading } = useAuth();
  const { language, setLanguage, t } = useLanguage();
  const { data: profile, loading: profileLoading, refetch: refetchProfile } = useApiData<UserProfile>(fetchCurrentUserProfile);
  const {
    data: organization,
    loading: organizationLoading,
    refetch: refetchOrganization,
  } = useApiData<Organization | undefined>(fetchOrganization);

  const [profileSaving, setProfileSaving] = useState(false);
  const [profileFullName, setProfileFullName] = useState<string | null>(null);
  const [profileDepartment, setProfileDepartment] = useState<string | null>(null);

  const handleSaveProfile = async () => {
    setProfileSaving(true);
    try {
      const finalName = profileFullName !== null ? profileFullName : (profile?.full_name || profile?.fullName || '');
      const finalDept = profileDepartment !== null ? profileDepartment : (profile?.department || 'General');

      await updateCurrentUserProfile({
        full_name: finalName,
        department: finalDept,
      });
      toast.success('Profile details updated successfully!');
      if (refetchProfile) {
        await refetchProfile();
      }
    } catch (err: any) {
      toast.error(err.message || 'Failed to update profile');
    } finally {
      setProfileSaving(false);
    }
  };

  const [sessionsDialogOpen, setSessionsDialogOpen] = useState(false);
  const [sessions, setSessions] = useState([
    {
      id: 'session-1',
      device: 'Chrome on Windows 11',
      ip: '182.93.84.12',
      location: 'Kathmandu, Nepal',
      lastActive: 'Active now',
      isCurrent: true,
      icon: Laptop,
    },
    {
      id: 'session-2',
      device: 'Safari on iPhone 15 Pro',
      ip: '110.44.115.90',
      location: 'Lalitpur, Nepal',
      lastActive: '2 hours ago',
      isCurrent: false,
      icon: Smartphone,
    },
    {
      id: 'session-3',
      device: 'Firefox on macOS Sonoma',
      ip: '202.70.76.5',
      location: 'Pokhara, Nepal',
      lastActive: '3 days ago',
      isCurrent: false,
      icon: Monitor,
    },
  ]);

  const handleRevokeSession = (sessionId: string) => {
    setSessions((prev) => prev.filter((s) => s.id !== sessionId));
    toast.success('Session revoked successfully.');
  };

  // ── Weekly Digest ─────────────────────────────────────────────────────
  const [weeklyDigestEnabled, setWeeklyDigestEnabled] = useState<boolean>(() => {
    if (typeof window !== 'undefined') {
      return localStorage.getItem('weekly_digest') === 'true';
    }
    return false;
  });
  const [digestPreviewOpen, setDigestPreviewOpen] = useState(false);
  const [digestStats, setDigestStats] = useState<{
    totalRisks: number;
    highRisks: number;
    complianceScore: number;
    totalEvidence: number;
    verifiedEvidence: number;
    recentActivity: number;
  } | null>(null);
  const [loadingDigest, setLoadingDigest] = useState(false);

  const handleWeeklyDigestToggle = async (checked: boolean) => {
    setWeeklyDigestEnabled(checked);
    if (typeof window !== 'undefined') {
      localStorage.setItem('weekly_digest', String(checked));
    }
    if (checked) {
      setLoadingDigest(true);
      try {
        const [risks, evidence, auditLogs, compliance] = await Promise.all([
          fetchRisks(),
          fetchEvidence(),
          fetchAuditLogs(),
          fetchControlApplicabilityComplianceScore(),
        ]);
        const highRisks = risks.filter((r: any) => (r.risk_score || 0) >= 15).length;
        const verified = evidence.filter((e: any) => e.status === 'verified').length;
        const weekAgo = new Date();
        weekAgo.setDate(weekAgo.getDate() - 7);
        const recentActivity = auditLogs.filter((l: any) => {
          const ts = l.timestamp ? new Date(l.timestamp) : null;
          return ts && ts >= weekAgo;
        }).length;
        setDigestStats({
          totalRisks: risks.length,
          highRisks,
          complianceScore: compliance.compliance_percentage,
          totalEvidence: evidence.length,
          verifiedEvidence: verified,
          recentActivity,
        });
        setDigestPreviewOpen(true);
        toast.success('Weekly Digest enabled. Preview your first report below.');
      } catch {
        toast.error('Failed to load digest preview. Digest is still enabled.');
      } finally {
        setLoadingDigest(false);
      }
    } else {
      toast.info('Weekly Digest disabled.');
    }
  };

  const handleLanguageChange = (newLang: string) => {
    setLanguage(newLang as Language);
    const langNames: Record<string, string> = {
      'en-US': 'English (US)',
      'en-GB': 'English (UK)',
      'es-ES': 'Spanish (Español)',
      'fr-FR': 'French (Français)',
      'de-DE': 'German (Deutsch)',
      'ja-JP': 'Japanese (日本語)',
      'zh-CN': 'Chinese (Simplified)',
    };
    toast.success(`Language set to ${langNames[newLang] || newLang}`);
  };

  const loading = authLoading || profileLoading || organizationLoading;
  const activeFrameworkIds = Array.from(
    new Set(
      (organization?.compliance_frameworks ?? organization?.complianceFrameworks ?? [])
        .map((id) => normalizeComplianceFrameworkId(id))
    )
  );
  const activeFrameworks = activeFrameworkIds.map((id) => {
    const option = COMPLIANCE_FRAMEWORK_OPTIONS.find((framework) => framework.id === id);
    return option ?? { id, name: id, description: 'Custom framework' };
  });
  const availableFrameworks = COMPLIANCE_FRAMEWORK_OPTIONS.filter(
    (framework) => !activeFrameworkIds.includes(framework.id)
  );

  const [deletingFrameworkId, setDeletingFrameworkId] = useState<string | null>(null);

  const openFrameworkDialog = () => {
    const firstAvailable = availableFrameworks[0]?.id;
    if (firstAvailable) {
      setSelectedFrameworkId(firstAvailable);
    } else {
      setSelectedFrameworkId('');
    }
    setFrameworkDialogOpen(true);
  };

  const handleAddFramework = async () => {
    if (!selectedFrameworkId) return;

    if (activeFrameworkIds.includes(selectedFrameworkId)) {
      toast.info('This framework is already added to your organization.');
      return;
    }

    setAddingFramework(true);
    try {
      const result = await initializeControlApplicabilityFramework(selectedFrameworkId);
      toast.success(
        `${result.framework_name || selectedFrameworkId} added. ${result.initialized_count || 0} controls initialized.`
      );
      await refetchOrganization();
      setFrameworkDialogOpen(false);
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Failed to add framework');
    } finally {
      setAddingFramework(false);
    }
  };

  const handleDeleteFramework = async (frameworkId: string) => {
    if (!organization) return;
    const targetNorm = normalizeComplianceFrameworkId(frameworkId);

    const option = COMPLIANCE_FRAMEWORK_OPTIONS.find((f) => f.id === targetNorm);
    const frameworkName = option?.name || frameworkId.toUpperCase();

    const confirmDelete = window.confirm(`Are you sure you want to remove ${frameworkName} from your compliance frameworks?`);
    if (!confirmDelete) return;

    setDeletingFrameworkId(frameworkId);
    try {
      const currentFrameworks = organization.compliance_frameworks ?? organization.complianceFrameworks ?? [];
      const updatedFrameworks = currentFrameworks.filter(
        (id) => normalizeComplianceFrameworkId(id) !== targetNorm
      );

      await updateOrganization({ compliance_frameworks: updatedFrameworks });
      toast.success(`${frameworkName} removed from organization frameworks.`);
      await refetchOrganization();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Failed to remove framework');
    } finally {
      setDeletingFrameworkId(null);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <Loader2 className="h-8 w-8 animate-spin text-blue-600" />
      </div>
    );
  }

  if (!authUser || !profile) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[400px]">
        <p className="text-muted-foreground">Please log in to view settings.</p>
      </div>
    );
  }

  const isOrgAdmin = authUser?.role === 'admin' || authUser?.role === 'superadmin';

  return (
    <div className="space-y-6 max-w-5xl">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-foreground mb-1">Settings</h1>
        <p className="text-sm text-muted-foreground">
          Manage your account settings, security preferences, and organization controls
        </p>
      </div>

      <Tabs value={activeTab} onValueChange={setActiveTab} className="space-y-6">
        <TabsList className={`grid w-full ${isOrgAdmin ? 'grid-cols-2 sm:grid-cols-6' : 'grid-cols-2 sm:grid-cols-4'} h-auto p-1 gap-1`}>
          <TabsTrigger value="profile" className="gap-2 py-2">
            <UserIcon className="h-4 w-4" />
            <span className="hidden sm:inline">Profile</span>
          </TabsTrigger>
          <TabsTrigger value="preferences" className="gap-2 py-2">
            <Palette className="h-4 w-4" />
            <span className="hidden sm:inline">Preferences</span>
          </TabsTrigger>
          <TabsTrigger value="security" className="gap-2 py-2">
            <Shield className="h-4 w-4" />
            <span className="hidden sm:inline">Security</span>
          </TabsTrigger>
          {isOrgAdmin && (
            <>
              <TabsTrigger value="frameworks" className="gap-2 py-2">
                <Globe className="h-4 w-4" />
                <span className="hidden sm:inline">Frameworks</span>
              </TabsTrigger>
              <TabsTrigger value="access" className="gap-2 py-2">
                <KeyRound className="h-4 w-4 text-indigo-600" />
                <span className="hidden sm:inline font-medium">Access Control</span>
              </TabsTrigger>
            </>
          )}
          <TabsTrigger value="notifications" className="gap-2 py-2">
            <Bell className="h-4 w-4" />
            <span className="hidden sm:inline">Notifications</span>
          </TabsTrigger>
        </TabsList>

        {/* Profile Tab */}
        <TabsContent value="profile" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle className="text-lg flex items-center gap-2">
                <UserIcon className="h-5 w-5" />
                Profile Information
              </CardTitle>
              <CardDescription>
                Update your personal information and profile settings
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="fullName">Full Name</Label>
                  <Input
                    id="fullName"
                    value={profileFullName !== null ? profileFullName : (profile.full_name || profile.fullName || '')}
                    onChange={(e) => setProfileFullName(e.target.value)}
                    placeholder="Your Full Name"
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="email">Email</Label>
                  <Input id="email" type="email" defaultValue={profile.email} disabled className="bg-muted cursor-not-allowed opacity-80" />
                </div>
              </div>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="department">Department</Label>
                  <Input
                    id="department"
                    value={profileDepartment !== null ? profileDepartment : (profile.department || 'General')}
                    onChange={(e) => setProfileDepartment(e.target.value)}
                    placeholder="e.g. Compliance, Security, IT"
                  />
                </div>
                <div className="space-y-2">
                  <Label>Role</Label>
                  <div className="h-10 flex items-center">
                    <Badge className="capitalize">{profile.role}</Badge>
                  </div>
                </div>
              </div>
              <div className="pt-4 flex justify-end">
                <Button onClick={handleSaveProfile} disabled={profileSaving} className="gap-2">
                  {profileSaving ? (
                    <>
                      <Loader2 className="h-4 w-4 animate-spin" />
                      Saving...
                    </>
                  ) : (
                    <>
                      <CheckCircle2 className="h-4 w-4" />
                      Save Changes
                    </>
                  )}
                </Button>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Preferences Tab */}
        <TabsContent value="preferences" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle className="text-lg flex items-center gap-2">
                <Palette className="h-5 w-5" />
                Display Preferences
              </CardTitle>
              <CardDescription>
                Customize how the application looks and behaves
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
              <div className="flex flex-col gap-4">
                <div className="space-y-0.5">
                  <Label className="flex items-center gap-2">
                    Theme Preferences
                  </Label>
                  <p className="text-xs text-muted-foreground">Choose your preferred appearance</p>
                </div>
                <div className="w-full">
                  <ThemeSelector />
                </div>
              </div>
              <div className="flex items-center justify-between">
                <div className="space-y-0.5">
                  <Label className="flex items-center gap-2">
                    <Settings className="h-4 w-4" />
                    Compact View
                  </Label>
                  <p className="text-xs text-muted-foreground">Reduce spacing between elements</p>
                </div>
                <Switch />
              </div>
              <div className="flex items-center justify-between">
                <div className="space-y-0.5">
                  <Label className="flex items-center gap-2">
                    <Globe className="h-4 w-4" />
                    Language
                  </Label>
                  <p className="text-xs text-muted-foreground">Select your preferred system language</p>
                </div>
                <Select value={language} onValueChange={handleLanguageChange}>
                  <SelectTrigger className="w-[180px]">
                    <SelectValue placeholder="Select Language" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="en-US">English (US)</SelectItem>
                    <SelectItem value="en-GB">English (UK)</SelectItem>
                    <SelectItem value="es-ES">Spanish (Español)</SelectItem>
                    <SelectItem value="fr-FR">French (Français)</SelectItem>
                    <SelectItem value="de-DE">German (Deutsch)</SelectItem>
                    <SelectItem value="ja-JP">Japanese (日本語)</SelectItem>
                    <SelectItem value="zh-CN">Chinese (Simplified)</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Frameworks Tab */}
        <TabsContent value="frameworks" className="space-y-4">
          <Card>
            <CardHeader className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
              <div>
                <CardTitle className="text-lg flex items-center gap-2">
                  <Globe className="h-5 w-5" />
                  Compliance Frameworks
                </CardTitle>
                <CardDescription>
                  Manage the compliance frameworks active for your organization
                </CardDescription>
              </div>
              <Button
                className="gap-2"
                onClick={openFrameworkDialog}
              >
                <Plus className="h-4 w-4" />
                Add Framework
              </Button>
            </CardHeader>
            <CardContent>
              {activeFrameworks.length === 0 ? (
                <div className="rounded-lg border border-dashed p-6 text-center">
                  <p className="text-sm font-medium">No frameworks active yet</p>
                  <p className="text-xs text-muted-foreground mt-1">
                    Add ISO 27001 or another framework to initialize compliance tracking.
                  </p>
                </div>
              ) : (
                <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                  {activeFrameworks.map((framework) => (
                    <div key={framework.id} className="rounded-lg border p-4 bg-muted/30 hover:border-slate-300 transition-colors">
                      <div className="flex items-start justify-between gap-3">
                        <div>
                          <p className="font-semibold text-sm">{framework.name}</p>
                          <p className="text-xs text-muted-foreground mt-1">{framework.description}</p>
                        </div>
                        <div className="flex items-center gap-2 shrink-0">
                          <Badge variant="outline" className="gap-1 bg-emerald-50 text-emerald-700 border-emerald-300">
                            <CheckCircle2 className="h-3 w-3 text-emerald-600" />
                            Active
                          </Badge>
                          <Button
                            variant="ghost"
                            size="icon"
                            className="h-8 w-8 text-muted-foreground hover:text-destructive hover:bg-destructive/10"
                            title={`Delete ${framework.name}`}
                            onClick={() => handleDeleteFramework(framework.id)}
                            disabled={deletingFrameworkId === framework.id}
                          >
                            {deletingFrameworkId === framework.id ? (
                              <Loader2 className="h-4 w-4 animate-spin text-destructive" />
                            ) : (
                              <Trash2 className="h-4 w-4" />
                            )}
                          </Button>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>

          <Dialog open={frameworkDialogOpen} onOpenChange={setFrameworkDialogOpen}>
            <DialogContent className="sm:max-w-[500px]">
              <DialogHeader>
                <DialogTitle>Add Compliance Framework</DialogTitle>
                <DialogDescription>
                  Select a framework to enable for your organization. Frameworks already active are marked with a check.
                </DialogDescription>
              </DialogHeader>
              <div className="grid gap-3 py-2 max-h-[60vh] overflow-y-auto pr-1">
                {COMPLIANCE_FRAMEWORK_OPTIONS.map((framework) => {
                  const isAlreadyAdded = activeFrameworkIds.includes(framework.id);
                  const isSelected = selectedFrameworkId === framework.id;

                  if (isAlreadyAdded) {
                    return (
                      <div
                        key={framework.id}
                        onClick={() => toast.info(`${framework.name} is already active for your organization.`)}
                        className="text-left rounded-lg border p-4 bg-muted/40 opacity-80 border-emerald-200 cursor-not-allowed transition-colors"
                      >
                        <div className="flex items-start justify-between gap-3">
                          <div>
                            <p className="font-semibold text-sm text-foreground/80">{framework.name}</p>
                            <p className="text-xs text-muted-foreground mt-1">{framework.description}</p>
                          </div>
                          <Badge variant="outline" className="gap-1 bg-emerald-50 text-emerald-700 border-emerald-300 font-medium shrink-0">
                            <CheckCircle2 className="h-3.5 w-3.5 text-emerald-600" />
                            Added
                          </Badge>
                        </div>
                      </div>
                    );
                  }

                  return (
                    <button
                      key={framework.id}
                      type="button"
                      onClick={() => setSelectedFrameworkId(framework.id)}
                      className={`text-left rounded-lg border p-4 transition-all ${
                        isSelected
                          ? 'border-primary bg-primary/5 ring-1 ring-primary/20 shadow-sm'
                          : 'border-border hover:bg-muted/50'
                      }`}
                    >
                      <div className="flex items-start justify-between gap-3">
                        <div>
                          <p className="font-semibold text-sm">{framework.name}</p>
                          <p className="text-xs text-muted-foreground mt-1">{framework.description}</p>
                        </div>
                        {isSelected ? (
                          <CheckCircle2 className="h-5 w-5 text-primary shrink-0" />
                        ) : (
                          <Badge variant="outline" className="text-muted-foreground">Select</Badge>
                        )}
                      </div>
                    </button>
                  );
                })}
              </div>
              <DialogFooter>
                <Button variant="outline" onClick={() => setFrameworkDialogOpen(false)} disabled={addingFramework}>
                  Cancel
                </Button>
                <Button
                  onClick={handleAddFramework}
                  disabled={!selectedFrameworkId || activeFrameworkIds.includes(selectedFrameworkId) || addingFramework}
                >
                  {addingFramework ? (
                    <>
                      <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                      Adding...
                    </>
                  ) : (
                    'Add Framework'
                  )}
                </Button>
              </DialogFooter>
            </DialogContent>
          </Dialog>
        </TabsContent>

        {/* Security Tab */}
        <TabsContent value="security" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle className="text-lg flex items-center gap-2">
                <Lock className="h-5 w-5" />
                Password & Authentication
              </CardTitle>
              <CardDescription>
                Manage your password and security settings
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
              <div className="flex items-center justify-between p-4 bg-muted/50 rounded-lg">
                <div>
                  <p className="font-medium text-sm">Password</p>
                  <p className="text-xs text-muted-foreground">Last changed 30 days ago</p>
                </div>
                <Button variant="outline">Change Password</Button>
              </div>
              <div className="flex items-center justify-between p-4 bg-muted/50 rounded-lg">
                <div>
                  <p className="font-medium text-sm">Active Sessions</p>
                  <p className="text-xs text-muted-foreground">You are logged in on {sessions.length} devices</p>
                </div>
                <Button variant="outline" size="sm" onClick={() => setSessionsDialogOpen(true)}>
                  View All
                </Button>
              </div>

              {/* Active Sessions Dialog */}
              <Dialog open={sessionsDialogOpen} onOpenChange={setSessionsDialogOpen}>
                <DialogContent className="sm:max-w-[550px]">
                  <DialogHeader>
                    <DialogTitle className="flex items-center gap-2">
                      <Lock className="h-5 w-5 text-primary" />
                      Active Sessions
                    </DialogTitle>
                    <DialogDescription>
                      These devices are currently signed into your account. Revoke any session you do not recognize.
                    </DialogDescription>
                  </DialogHeader>

                  <div className="space-y-3 py-3 max-h-[60vh] overflow-y-auto">
                    {sessions.map((sess) => {
                      const DeviceIcon = sess.icon;
                      return (
                        <div key={sess.id} className="flex items-center justify-between p-3.5 border rounded-lg bg-card hover:bg-muted/40 transition-colors">
                          <div className="flex items-center gap-3.5">
                            <div className="p-2.5 rounded-full bg-primary/10 text-primary shrink-0">
                              <DeviceIcon className="h-5 w-5" />
                            </div>
                            <div className="space-y-0.5">
                              <div className="flex items-center gap-2">
                                <p className="font-semibold text-sm">{sess.device}</p>
                                {sess.isCurrent && (
                                  <Badge variant="outline" className="bg-emerald-50 text-emerald-700 border-emerald-300 text-[10px] py-0 px-1.5 font-medium">
                                    Current Device
                                  </Badge>
                                )}
                              </div>
                              <p className="text-xs text-muted-foreground">
                                {sess.ip} • {sess.location}
                              </p>
                              <p className="text-[11px] text-slate-500">
                                Last active: <span className="font-medium">{sess.lastActive}</span>
                              </p>
                            </div>
                          </div>

                          {!sess.isCurrent && (
                            <Button
                              variant="ghost"
                              size="sm"
                              className="text-destructive hover:bg-destructive/10 hover:text-destructive gap-1 text-xs"
                              onClick={() => handleRevokeSession(sess.id)}
                            >
                              <RevokeIcon className="h-3.5 w-3.5" />
                              Revoke
                            </Button>
                          )}
                        </div>
                      );
                    })}
                  </div>

                  <DialogFooter>
                    <Button variant="outline" onClick={() => setSessionsDialogOpen(false)}>
                      Close
                    </Button>
                  </DialogFooter>
                </DialogContent>
              </Dialog>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Notifications Tab */}
        <TabsContent value="notifications" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle className="text-lg flex items-center gap-2">
                <Bell className="h-5 w-5" />
                Notification Preferences
              </CardTitle>
              <CardDescription>
                Choose how and when you want to be notified
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
              <div className="flex items-center justify-between">
                <div className="space-y-0.5">
                  <Label className="flex items-center gap-2">
                    <Mail className="h-4 w-4" />
                    Email Notifications
                  </Label>
                  <p className="text-xs text-muted-foreground">Receive notifications via email</p>
                </div>
                <Switch defaultChecked />
              </div>
              <div className="flex items-center justify-between">
                <div className="space-y-0.5">
                  <Label>Risk Alerts</Label>
                  <p className="text-xs text-muted-foreground">Get alerted when high-risk items are identified</p>
                </div>
                <Switch defaultChecked />
              </div>
              <div className="flex items-center justify-between">
                <div className="space-y-0.5">
                  <Label>Compliance Deadlines</Label>
                  <p className="text-xs text-muted-foreground">Reminders for upcoming compliance deadlines</p>
                </div>
                <Switch defaultChecked />
              </div>
              <div className="flex items-center justify-between">
                <div className="space-y-0.5">
                  <Label>Weekly Digest</Label>
                  <p className="text-xs text-muted-foreground">Summary of all activities sent weekly</p>
                </div>
                <Switch
                  checked={weeklyDigestEnabled}
                  onCheckedChange={handleWeeklyDigestToggle}
                  disabled={loadingDigest}
                />
              </div>

              {/* Weekly Digest Preview Dialog */}
              <Dialog open={digestPreviewOpen} onOpenChange={setDigestPreviewOpen}>
                <DialogContent className="sm:max-w-[560px]">
                  <DialogHeader>
                    <DialogTitle className="flex items-center gap-2">
                      <Calendar className="h-5 w-5 text-primary" />
                      Weekly Activity Digest
                    </DialogTitle>
                    <DialogDescription>
                      Here's a preview of what your weekly digest email will look like.
                    </DialogDescription>
                  </DialogHeader>

                  {digestStats && (
                    <div className="space-y-4 py-2">
                      {/* Header banner */}
                      <div className="rounded-lg bg-gradient-to-r from-primary/10 to-blue-50 border border-primary/20 p-4">
                        <p className="text-xs font-semibold text-primary uppercase tracking-wider">GRC Platform</p>
                        <p className="text-base font-bold text-foreground mt-0.5">Weekly Security & Compliance Report</p>
                        <p className="text-xs text-muted-foreground mt-1">
                          Week of {new Date(Date.now() - 7 * 24 * 60 * 60 * 1000).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })} – {new Date().toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })}
                        </p>
                      </div>

                      {/* KPI blocks */}
                      <div className="grid grid-cols-2 gap-3">
                        <div className="rounded-lg border p-3.5 bg-card space-y-1">
                          <div className="flex items-center justify-between">
                            <p className="text-xs text-muted-foreground">Total Risks</p>
                            <TrendingUp className="h-3.5 w-3.5 text-amber-500" />
                          </div>
                          <p className="text-2xl font-bold text-foreground">{digestStats.totalRisks}</p>
                          <p className="text-[11px] text-red-500 font-medium">{digestStats.highRisks} high-severity</p>
                        </div>

                        <div className="rounded-lg border p-3.5 bg-card space-y-1">
                          <div className="flex items-center justify-between">
                            <p className="text-xs text-muted-foreground">Compliance Score</p>
                            <TrendingUp className="h-3.5 w-3.5 text-emerald-500" />
                          </div>
                          <p className="text-2xl font-bold text-foreground">{digestStats.complianceScore}%</p>
                          <div className="w-full bg-muted rounded-full h-1.5 mt-1">
                            <div
                              className="bg-emerald-500 h-1.5 rounded-full transition-all"
                              style={{ width: `${digestStats.complianceScore}%` }}
                            />
                          </div>
                        </div>

                        <div className="rounded-lg border p-3.5 bg-card space-y-1">
                          <div className="flex items-center justify-between">
                            <p className="text-xs text-muted-foreground">Evidence</p>
                            <FileText className="h-3.5 w-3.5 text-blue-500" />
                          </div>
                          <p className="text-2xl font-bold text-foreground">{digestStats.totalEvidence}</p>
                          <p className="text-[11px] text-emerald-600 font-medium">{digestStats.verifiedEvidence} verified</p>
                        </div>

                        <div className="rounded-lg border p-3.5 bg-card space-y-1">
                          <div className="flex items-center justify-between">
                            <p className="text-xs text-muted-foreground">Activity This Week</p>
                            <Activity className="h-3.5 w-3.5 text-purple-500" />
                          </div>
                          <p className="text-2xl font-bold text-foreground">{digestStats.recentActivity}</p>
                          <p className="text-[11px] text-muted-foreground">audit log entries</p>
                        </div>
                      </div>

                      <p className="text-xs text-center text-muted-foreground border-t pt-3">
                        📧 This summary will be emailed every Monday at 9:00 AM to your registered email.
                      </p>
                    </div>
                  )}

                  <DialogFooter>
                    <Button variant="outline" onClick={() => setDigestPreviewOpen(false)}>Close</Button>
                    <Button onClick={() => { setDigestPreviewOpen(false); toast.success('Weekly digest scheduled!'); }}>
                      <Calendar className="h-4 w-4 mr-1.5" />
                      Confirm Schedule
                    </Button>
                  </DialogFooter>
                </DialogContent>
              </Dialog>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Access Control & Permission Profiles Tab (Admin only) */}
        {isOrgAdmin && (
          <TabsContent value="access" className="space-y-4">
            <AccessManagementSection />
          </TabsContent>
        )}
      </Tabs>
    </div>
  );
}
