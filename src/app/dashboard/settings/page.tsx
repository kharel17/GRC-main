"use client";

import { useState } from 'react';
import {
  fetchCurrentUserProfile,
  updateCurrentUserProfile,
  fetchOrganization,
} from '@/lib/data-service';
import { useAuth, useApiData } from '@/hooks';
import { Organization, UserProfile } from '@/types';

import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Switch } from '@/components/ui/switch';
import { Badge } from '@/components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
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
  CheckCircle2,
  KeyRound,
} from 'lucide-react';
import { ThemeSelector } from '@/components/settings/ThemeSelector';
import { toast } from 'sonner';
import { useLanguage, Language } from '@/context/LanguageContext';
import { AccessManagementSection } from '@/components/settings/AccessManagementSection';
import { SecuritySettings } from '@/components/settings/SecuritySettings';
import { SessionsDialog } from '@/components/settings/SessionsDialog';
import { WeeklyDigestToggle } from '@/components/settings/WeeklyDigestDialog';
import { FrameworksTab } from '@/components/settings/FrameworksTab';

export default function SettingsPage() {
  const [activeTab, setActiveTab] = useState('profile');
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
  const [sessionsDialogOpen, setSessionsDialogOpen] = useState(false);

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
          <FrameworksTab organization={organization} refetchOrganization={refetchOrganization} />
        </TabsContent>

        {/* Security Tab */}
        <TabsContent value="security" className="space-y-4">
          <SecuritySettings />
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
                  <p className="text-xs text-muted-foreground">Manage your active device sessions</p>
                </div>
                <Button variant="outline" size="sm" onClick={() => setSessionsDialogOpen(true)}>
                  View All
                </Button>
              </div>

              <SessionsDialog open={sessionsDialogOpen} onOpenChange={setSessionsDialogOpen} />
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
              <WeeklyDigestToggle />
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
