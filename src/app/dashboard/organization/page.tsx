"use client";

import { useState } from "react";
import { useApiData } from "@/hooks/use-api-data";
import { fetchOrganization, updateOrganization } from "@/lib/data-service";
import { Card, CardContent, CardDescription, CardHeader, CardTitle, CardFooter } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Building2, Globe, Users, FileCheck, Loader2, Edit2, Save, X, Calendar } from "lucide-react";
import { Separator } from "@/components/ui/separator";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { toast } from "sonner";
import { format } from "date-fns";
import { Organization } from "@/types";

export default function OrganizationPage() {
  const { data: org, loading, refetch } = useApiData(fetchOrganization);
  const [isEditing, setIsEditing] = useState(false);
  const [saving, setSaving] = useState(false);
  const [formData, setFormData] = useState<any>(null);

  const startEditing = () => {
    setFormData({
      name: org?.name || "",
      description: org?.description || "",
      industry: org?.industry || "",
      size: org?.size || "",
      website: org?.website || "",
      country: org?.country || "",
      employee_count: org?.employee_count || 0,
      compliance_target_date: org?.compliance_target_date || "",
    });
    setIsEditing(true);
  };

  const handleSave = async () => {
    if (!org?.id) return;
    setSaving(true);
    try {
      await updateOrganization(org.id, formData);
      toast.success("Organization updated successfully");
      setIsEditing(false);
      refetch();
    } catch (error) {
      toast.error("Failed to update organization");
    } finally {
      setSaving(false);
    }
  };

  if (loading && !org) {
    return (
      <div className="flex items-center justify-center py-24">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
        <span className="ml-3 text-muted-foreground">Loading organization data...</span>
      </div>
    );
  }

  if (!org) {
    return (
      <div className="p-8 text-center border-2 border-dashed rounded-lg">
        <h2 className="text-xl font-semibold mb-2">No Organization Found</h2>
        <p className="text-muted-foreground">Please set up your organization profile.</p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Organization Setup</h1>
          <p className="text-muted-foreground text-sm">Manage your organization profile and compliance frameworks.</p>
        </div>
        {!isEditing ? (
          <Button onClick={startEditing} variant="outline" className="gap-2">
            <Edit2 className="h-4 w-4" />
            Edit Profile
          </Button>
        ) : (
          <div className="flex items-center gap-2">
            <Button onClick={() => setIsEditing(false)} variant="ghost" disabled={saving}>
              <X className="h-4 w-4 mr-2" />
              Cancel
            </Button>
            <Button onClick={handleSave} className="gap-2" disabled={saving}>
              {saving ? <Loader2 className="h-4 w-4 animate-spin" /> : <Save className="h-4 w-4" />}
              Save Changes
            </Button>
          </div>
        )}
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <Card className="md:col-span-2">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Building2 className="h-5 w-5 text-primary" />
              Company Details
            </CardTitle>
            <CardDescription>Basic information about your organization</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            {isEditing ? (
              <div className="grid grid-cols-2 gap-6">
                <div className="space-y-2">
                  <Label htmlFor="org-name">Company Name</Label>
                  <Input 
                    id="org-name" 
                    value={formData.name} 
                    onChange={(e) => setFormData({...formData, name: e.target.value})}
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="org-industry">Industry</Label>
                  <Input 
                    id="org-industry" 
                    value={formData.industry} 
                    onChange={(e) => setFormData({...formData, industry: e.target.value})}
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="org-size">Size</Label>
                  <Input 
                    id="org-size" 
                    value={formData.size} 
                    onChange={(e) => setFormData({...formData, size: e.target.value})}
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="org-country">Country</Label>
                  <Input 
                    id="org-country" 
                    value={formData.country} 
                    onChange={(e) => setFormData({...formData, country: e.target.value})}
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="org-employees">Employee Count</Label>
                  <Input 
                    id="org-employees" 
                    type="number"
                    value={formData.employee_count} 
                    onChange={(e) => setFormData({...formData, employee_count: parseInt(e.target.value) || 0})}
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="org-target-date">Compliance Target Date</Label>
                  <Input 
                    id="org-target-date" 
                    type="date"
                    value={formData.compliance_target_date ? formData.compliance_target_date.split('T')[0] : ""} 
                    onChange={(e) => setFormData({...formData, compliance_target_date: e.target.value})}
                  />
                </div>
                <div className="col-span-2 space-y-2">
                  <Label htmlFor="org-website">Website URL</Label>
                  <Input 
                    id="org-website" 
                    value={formData.website} 
                    onChange={(e) => setFormData({...formData, website: e.target.value})}
                  />
                </div>
                <div className="col-span-2 space-y-2">
                  <Label htmlFor="org-desc">Description</Label>
                  <Textarea 
                    id="org-desc" 
                    rows={3}
                    value={formData.description} 
                    onChange={(e) => setFormData({...formData, description: e.target.value})}
                  />
                </div>
              </div>
            ) : (
              <>
                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-1">
                    <span className="text-xs font-semibold text-muted-foreground uppercase">Name</span>
                    <p className="font-medium">{org.name}</p>
                  </div>
                  <div className="space-y-1">
                    <span className="text-xs font-semibold text-muted-foreground uppercase">Industry</span>
                    <p className="font-medium">{org.industry || 'Not specified'}</p>
                  </div>
                  <div className="space-y-1">
                    <span className="text-xs font-semibold text-muted-foreground uppercase">Size</span>
                    <p className="font-medium capitalize">{org.size || 'Not specified'}</p>
                  </div>
                  <div className="space-y-1">
                    <span className="text-xs font-semibold text-muted-foreground uppercase">Country</span>
                    <p className="font-medium">{org.country || 'Not specified'}</p>
                  </div>
                  <div className="space-y-1">
                    <span className="text-xs font-semibold text-muted-foreground uppercase">Employee Count</span>
                    <p className="font-medium">{org.employee_count || 'Not specified'}</p>
                  </div>
                  <div className="space-y-1">
                    <span className="text-xs font-semibold text-muted-foreground uppercase">Target Date</span>
                    <p className="font-medium flex items-center gap-2 text-primary">
                      <Calendar className="h-4 w-4" />
                      {org.compliance_target_date ? format(new Date(org.compliance_target_date), 'PPP') : 'Not set'}
                    </p>
                  </div>
                </div>
                
                <Separator />
                
                <div className="space-y-1">
                  <span className="text-xs font-semibold text-muted-foreground uppercase">Description</span>
                  <p className="text-sm text-muted-foreground">{org.description || 'No description provided.'}</p>
                </div>

                <div className="flex items-center gap-4 pt-2">
                  <div className="flex items-center gap-1.5 text-sm">
                    <Globe className="h-4 w-4 text-muted-foreground" />
                    <a href={org.website} target="_blank" rel="noopener noreferrer" className="text-primary hover:underline">
                      {org.website?.replace('https://', '') || 'No website'}
                    </a>
                  </div>
                  <div className="flex items-center gap-1.5 text-sm">
                    <Users className="h-4 w-4 text-muted-foreground" />
                    <span>Primary Contact: {org.primaryContactId ? 'Alice Johnson' : 'Not assigned'}</span>
                  </div>
                </div>
              </>
            )}
          </CardContent>
        </Card>

        <div className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <FileCheck className="h-5 w-5 text-primary" />
                Active Frameworks
              </CardTitle>
              <CardDescription>GRC standards currently being tracked</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="flex flex-wrap gap-2">
                {org.complianceFrameworks?.map((framework: string) => (
                  <Badge key={framework} variant="secondary" className="px-3 py-1 text-sm font-medium">
                    {framework}
                  </Badge>
                ))}
                {(!org.complianceFrameworks || org.complianceFrameworks.length === 0) && (
                  <p className="text-sm text-muted-foreground italic">No frameworks selected.</p>
                )}
              </div>
              <p className="mt-4 text-xs text-muted-foreground">
                These frameworks define the controls and compliance requirements for your organization.
              </p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <div className="flex items-center justify-between">
                <CardTitle className="text-sm">ISO 27001 Context</CardTitle>
                <Badge variant="outline" className="text-[10px] uppercase">Beta</Badge>
              </div>
            </CardHeader>
            <CardContent className="space-y-3">
              <div className="flex items-center justify-between text-sm">
                <span className="text-muted-foreground">Assets Linked</span>
                <span className="font-bold">12</span>
              </div>
              <div className="flex items-center justify-between text-sm">
                <span className="text-muted-foreground">Risk Appetite</span>
                <span className="font-bold text-orange-500">Moderate</span>
              </div>
              <div className="pt-2">
                <div className="w-full bg-secondary h-2 rounded-full overflow-hidden">
                  <div className="bg-primary h-full w-[17%]" />
                </div>
                <p className="text-[10px] text-muted-foreground mt-1 text-center">
                  17% of controls implemented
                </p>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
