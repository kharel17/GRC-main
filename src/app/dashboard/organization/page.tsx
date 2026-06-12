"use client";

import { useState } from "react";
import { useApiData } from "@/hooks/use-api-data";
import { fetchOrganization, updateOrganization, createOrganization } from "@/lib/data-service";
import { Card, CardContent, CardDescription, CardHeader, CardTitle, CardFooter } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Building2, Globe, Users, FileCheck, Loader2, Edit2, Save, X, Calendar, CheckCircle2, Shield } from "lucide-react";
import { Separator } from "@/components/ui/separator";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Checkbox } from "@/components/ui/checkbox";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { toast } from "sonner";
import { format } from "date-fns";
import { Organization } from "@/types";

const INDUSTRIES = ["Technology", "Healthcare", "Finance", "Retail", "Manufacturing", "Education", "Government", "Other"];
const EMPLOYEE_RANGES = ["1-50", "51-200", "201-1000", "1000+"];
const INFRASTRUCTURE_OPTIONS = ["AWS", "Azure", "GCP", "On-premise", "Hybrid"];
const DATA_TYPES = ["PII", "PHI", "PCI", "Financial Data", "IP"];
const FRAMEWORKS = ["ISO 27001", "SOC2", "HIPAA", "GDPR", "NIST"];

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
      await updateOrganization(formData);
      toast.success("Organization updated successfully");
      setIsEditing(false);
      refetch();
    } catch (error) {
      toast.error("Failed to update organization");
    } finally {
      setSaving(false);
    }
  };

  const handleCreate = async () => {
    if (!formData.name) {
      toast.error("Company Name is required");
      return;
    }
    setSaving(true);
    try {
      // Prepare data (convert arrays to comma-separated strings if needed)
      const payload = {
        ...formData,
        infrastructure: formData.infrastructure.join(','),
        data_types: formData.data_types.join(','),
        complianceFrameworks: formData.complianceFrameworks, // This one is already string[] in types
        onboarding_completed: true,
      };
      await createOrganization(payload);
      toast.success("Organization profile created!");
      refetch();
    } catch (error) {
      toast.error("Failed to create organization");
    } finally {
      setSaving(false);
    }
  };

  const toggleMultiSelect = (field: string, value: string) => {
    setFormData((prev: any) => {
      const current = prev[field] || [];
      const updated = current.includes(value)
        ? current.filter((v: string) => v !== value)
        : [...current, value];
      return { ...prev, [field]: updated };
    });
  };

  if (loading && !org) {
    return (
      <div className="flex items-center justify-center py-24">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
        <span className="ml-3 text-muted-foreground">Loading organization data...</span>
      </div>
    );
  }

  // ONBOARDING FORM
  if (!org) {
    if (!formData) {
      setFormData({
        name: "",
        industry: "",
        employee_count: "",
        infrastructure: [],
        data_types: [],
        complianceFrameworks: [],
        description: "",
      });
      return null;
    }

    return (
      <div className="max-w-4xl mx-auto py-8 px-4">
        <div className="text-center mb-10">
          <div className="inline-flex items-center justify-center p-3 bg-primary/10 rounded-full mb-4">
            <Building2 className="h-8 w-8 text-primary" />
          </div>
          <h1 className="text-3xl font-bold tracking-tight">Organization Profile</h1>
          <p className="text-muted-foreground mt-2">Create your organization record to get started with GRC management.</p>
        </div>

        <Card className="border-2">
          <CardHeader className="bg-slate-50 dark:bg-slate-900 border-b">
            <CardTitle>Initial Setup</CardTitle>
            <CardDescription>Complete these details to calibrate the AI risk engine.</CardDescription>
          </CardHeader>
          <CardContent className="pt-8 space-y-8">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
              {/* Basic Info */}
              <div className="space-y-4">
                <div className="space-y-2">
                  <Label htmlFor="create-name">Company Name <span className="text-red-500">*</span></Label>
                  <Input 
                    id="create-name" 
                    placeholder="Acme Corp" 
                    value={formData.name}
                    onChange={(e) => setFormData({...formData, name: e.target.value})}
                  />
                </div>

                <div className="space-y-2">
                  <Label>Industry</Label>
                  <Select 
                    value={formData.industry} 
                    onValueChange={(val) => setFormData({...formData, industry: val})}
                  >
                    <SelectTrigger>
                      <SelectValue placeholder="Select industry..." />
                    </SelectTrigger>
                    <SelectContent>
                      {INDUSTRIES.map(i => (
                        <SelectItem key={i} value={i}>{i}</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>

                <div className="space-y-2">
                  <Label>Number of Employees</Label>
                  <Select 
                    value={formData.employee_count} 
                    onValueChange={(val) => setFormData({...formData, employee_count: val})}
                  >
                    <SelectTrigger>
                      <SelectValue placeholder="Select size..." />
                    </SelectTrigger>
                    <SelectContent>
                      {EMPLOYEE_RANGES.map(r => (
                        <SelectItem key={r} value={r}>{r}</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
              </div>

              {/* Infrastructure & Data */}
              <div className="space-y-6">
                <div className="space-y-3">
                  <Label className="text-sm font-bold uppercase text-slate-500 tracking-wider">Infrastructure</Label>
                  <div className="grid grid-cols-2 gap-3">
                    {INFRASTRUCTURE_OPTIONS.map(opt => (
                      <div key={opt} className="flex items-center space-x-2">
                        <Checkbox 
                          id={`infra-${opt}`} 
                          checked={formData.infrastructure.includes(opt)}
                          onCheckedChange={() => toggleMultiSelect('infrastructure', opt)}
                        />
                        <label htmlFor={`infra-${opt}`} className="text-sm cursor-pointer">{opt}</label>
                      </div>
                    ))}
                  </div>
                </div>

                <div className="space-y-3">
                  <Label className="text-sm font-bold uppercase text-slate-500 tracking-wider">Data Types Handled</Label>
                  <div className="grid grid-cols-2 gap-3">
                    {DATA_TYPES.map(dt => (
                      <div key={dt} className="flex items-center space-x-2">
                        <Checkbox 
                          id={`data-${dt}`} 
                          checked={formData.data_types.includes(dt)}
                          onCheckedChange={() => toggleMultiSelect('data_types', dt)}
                        />
                        <label htmlFor={`data-${dt}`} className="text-sm cursor-pointer">{dt}</label>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            </div>

            <Separator />

            {/* Frameworks */}
            <div className="space-y-4">
              <Label className="text-sm font-bold uppercase text-slate-500 tracking-wider flex items-center gap-2">
                <Shield className="h-4 w-4" />
                Security Frameworks
              </Label>
              <div className="flex flex-wrap gap-4">
                {FRAMEWORKS.map(f => (
                  <div key={f} className="flex items-center space-x-2 bg-slate-50 dark:bg-slate-900 px-3 py-2 rounded-lg border">
                    <Checkbox 
                      id={`fw-${f}`} 
                      checked={formData.complianceFrameworks.includes(f)}
                      onCheckedChange={() => toggleMultiSelect('complianceFrameworks', f)}
                    />
                    <label htmlFor={`fw-${f}`} className="text-sm font-medium cursor-pointer">{f}</label>
                  </div>
                ))}
              </div>
            </div>
            
            <div className="space-y-2">
              <Label htmlFor="create-desc">Brief Company Description</Label>
              <Textarea 
                id="create-desc" 
                placeholder="What does your company do?" 
                rows={3}
                value={formData.description}
                onChange={(e) => setFormData({...formData, description: e.target.value})}
              />
            </div>
          </CardContent>
          <CardFooter className="bg-slate-50 dark:bg-slate-900 border-t py-4 flex justify-between items-center">
            <p className="text-xs text-muted-foreground flex items-center gap-1.5">
              <CheckCircle2 className="h-4 w-4 text-green-500" />
              You can update these details anytime later
            </p>
            <Button onClick={handleCreate} disabled={saving} className="min-w-[150px]">
              {saving ? <Loader2 className="h-4 w-4 animate-spin mr-2" /> : <Save className="h-4 w-4 mr-2" />}
              Save and Continue
            </Button>
          </CardFooter>
        </Card>
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
