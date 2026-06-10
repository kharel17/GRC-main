"use client";

import { useState } from 'react';
import {
  fetchCurrentUserProfile,
  fetchOrganization,
  initializeControlApplicabilityFramework,
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
} from 'lucide-react';
import { ThemeSelector } from '@/components/settings/ThemeSelector';
import { toast } from 'sonner';

export default function SettingsPage() {
  const [activeTab, setActiveTab] = useState('profile');
  const [frameworkDialogOpen, setFrameworkDialogOpen] = useState(false);
  const [selectedFrameworkId, setSelectedFrameworkId] = useState('iso27001');
  const [addingFramework, setAddingFramework] = useState(false);
  const { user: authUser, isLoading: authLoading } = useAuth();
  const { data: profile, loading: profileLoading } = useApiData<UserProfile>(fetchCurrentUserProfile);
  const {
    data: organization,
    loading: organizationLoading,
    refetch: refetchOrganization,
  } = useApiData<Organization | undefined>(fetchOrganization);

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

  const openFrameworkDialog = () => {
    setSelectedFrameworkId(availableFrameworks[0]?.id ?? 'iso27001');
    setFrameworkDialogOpen(true);
  };

  const handleAddFramework = async () => {
    if (!selectedFrameworkId) return;

    setAddingFramework(true);
    try {
      const result = await initializeControlApplicabilityFramework(selectedFrameworkId);
      toast.success(
        `${result.framework_name || selectedFrameworkId} added. ${result.initialized_count} controls initialized.`
      );
      refetchOrganization();
      setFrameworkDialogOpen(false);
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Failed to add framework');
    } finally {
      setAddingFramework(false);
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

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-foreground mb-1">Settings</h1>
        <p className="text-sm text-muted-foreground">
          Manage your account settings and preferences
        </p>
      </div>

      <Tabs value={activeTab} onValueChange={setActiveTab} className="space-y-6">
        <TabsList className="grid w-full grid-cols-2 sm:grid-cols-5 h-auto p-1 gap-1">
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
          <TabsTrigger value="frameworks" className="gap-2 py-2">
            <Globe className="h-4 w-4" />
            <span className="hidden sm:inline">Frameworks</span>
          </TabsTrigger>
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
                  <Input id="fullName" defaultValue={profile.full_name || profile.fullName || profile.email.split('@')[0]} />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="email">Email</Label>
                  <Input id="email" type="email" defaultValue={profile.email} disabled />
                </div>
              </div>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="department">Department</Label>
                  <Input id="department" defaultValue={profile.department || "General"} />
                </div>
                <div className="space-y-2">
                  <Label>Role</Label>
                  <div className="h-10 flex items-center">
                    <Badge className="capitalize">{profile.role}</Badge>
                  </div>
                </div>
              </div>
              <div className="pt-4 flex justify-end">
                <Button>Save Changes</Button>
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
                  <p className="text-xs text-muted-foreground">Currently set to English (US)</p>
                </div>
                <Button variant="outline" size="sm">Change</Button>
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
                disabled={availableFrameworks.length === 0}
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
                    <div key={framework.id} className="rounded-lg border p-4 bg-muted/30">
                      <div className="flex items-start justify-between gap-3">
                        <div>
                          <p className="font-semibold text-sm">{framework.name}</p>
                          <p className="text-xs text-muted-foreground mt-1">{framework.description}</p>
                        </div>
                        <Badge variant="outline" className="gap-1 shrink-0">
                          <CheckCircle2 className="h-3 w-3" />
                          Active
                        </Badge>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>

          <Dialog open={frameworkDialogOpen} onOpenChange={setFrameworkDialogOpen}>
            <DialogContent>
              <DialogHeader>
                <DialogTitle>Add Compliance Framework</DialogTitle>
                <DialogDescription>
                  Select a framework to enable for this organization.
                </DialogDescription>
              </DialogHeader>
              <div className="grid gap-3 py-2">
                {availableFrameworks.map((framework) => {
                  const selected = selectedFrameworkId === framework.id;
                  return (
                    <button
                      key={framework.id}
                      type="button"
                      onClick={() => setSelectedFrameworkId(framework.id)}
                      className={`text-left rounded-lg border p-4 transition-colors ${
                        selected
                          ? 'border-primary bg-primary/5'
                          : 'border-border hover:bg-muted/50'
                      }`}
                    >
                      <div className="flex items-start justify-between gap-3">
                        <div>
                          <p className="font-semibold text-sm">{framework.name}</p>
                          <p className="text-xs text-muted-foreground mt-1">{framework.description}</p>
                        </div>
                        {selected && <CheckCircle2 className="h-5 w-5 text-primary shrink-0" />}
                      </div>
                    </button>
                  );
                })}
              </div>
              <DialogFooter>
                <Button variant="outline" onClick={() => setFrameworkDialogOpen(false)} disabled={addingFramework}>
                  Cancel
                </Button>
                <Button onClick={handleAddFramework} disabled={!selectedFrameworkId || addingFramework}>
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
                  <p className="text-xs text-muted-foreground">You are logged in on 2 devices</p>
                </div>
                <Button variant="outline" size="sm">View All</Button>
              </div>
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
                <Switch />
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}
