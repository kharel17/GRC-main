"use client";

import { useApiData } from "@/hooks/use-api-data";
import { fetchOrganization } from "@/lib/data-service";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Building2, Globe, Users, FileCheck, Loader2 } from "lucide-react";
import { Separator } from "@/components/ui/separator";

export default function OrganizationPage() {
  const { data: org, loading } = useApiData(fetchOrganization);

  if (loading) {
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
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Organization Setup</h1>
        <p className="text-muted-foreground text-sm">Manage your organization profile and compliance frameworks.</p>
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
          </CardContent>
        </Card>

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
              {org.complianceFrameworks.map((framework) => (
                <Badge key={framework} variant="secondary" className="px-3 py-1 text-sm font-medium">
                  {framework}
                </Badge>
              ))}
              {org.complianceFrameworks.length === 0 && (
                <p className="text-sm text-muted-foreground italic">No frameworks selected.</p>
              )}
            </div>
            <p className="mt-4 text-xs text-muted-foreground">
              These frameworks define the controls and compliance requirements for your organization.
            </p>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
