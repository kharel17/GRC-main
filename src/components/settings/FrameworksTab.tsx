'use client';

import { useState } from 'react';
import {
  initializeControlApplicabilityFramework,
  updateOrganization,
} from '@/lib/data-service';
import { Organization } from '@/types';
import {
  COMPLIANCE_FRAMEWORK_OPTIONS,
  normalizeComplianceFrameworkId,
} from '@/lib/constants';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import {
  Globe,
  Loader2,
  Plus,
  CheckCircle2,
  Trash2,
} from 'lucide-react';
import { toast } from 'sonner';

interface FrameworksTabProps {
  organization: Organization | null | undefined;
  refetchOrganization: () => void | Promise<any>;
}

export function FrameworksTab({ organization, refetchOrganization }: FrameworksTabProps) {
  const [frameworkDialogOpen, setFrameworkDialogOpen] = useState(false);
  const [selectedFrameworkId, setSelectedFrameworkId] = useState('iso27001');
  const [addingFramework, setAddingFramework] = useState(false);
  const [deletingFrameworkId, setDeletingFrameworkId] = useState<string | null>(null);

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

  return (
    <>
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
    </>
  );
}
