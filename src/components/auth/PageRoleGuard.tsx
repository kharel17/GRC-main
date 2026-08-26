'use client';

import { ReactNode } from 'react';
import { useAuth } from '@/hooks/useAuth';
import { UserRole } from '@/types';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { ShieldAlert, ArrowLeft, Loader2 } from 'lucide-react';
import Link from 'next/link';

interface PageRoleGuardProps {
  /** Base roles that are allowed to see the page */
  allowedRoles: UserRole[];
  /** Optional specific permission profile key (e.g. 'gap_analysis', 'reports') */
  permissionKey?: string;
  /** Content to render if user has permission */
  children: ReactNode;
}

/**
 * PageRoleGuard - Full page auth guard.
 * If user does not have permission via base role or custom permission profile,
 * renders a crisp 403 Forbidden screen.
 */
export function PageRoleGuard({ allowedRoles, permissionKey, children }: PageRoleGuardProps) {
  const { user, isLoading } = useAuth();

  if (isLoading) {
    return (
      <div className="flex h-[70vh] items-center justify-center">
        <div className="flex flex-col items-center gap-3">
          <Loader2 className="h-8 w-8 animate-spin text-primary" />
          <p className="text-sm text-muted-foreground">Checking authorization...</p>
        </div>
      </div>
    );
  }

  if (!user) {
    return null;
  }

  // Check base role
  const hasBaseRole = allowedRoles.includes(user.role);

  // Check custom permission profile overrides
  const userProfilePermissions = (user as any)?.permission_profile?.nav_permissions || {};
  const hasProfileOverride = Boolean(permissionKey && userProfilePermissions[permissionKey] === true);

  if (!hasBaseRole && !hasProfileOverride) {
    return (
      <div className="flex min-h-[70vh] items-center justify-center p-4">
        <Card className="max-w-md w-full border-red-200 bg-red-50/40 text-center shadow-lg dark:bg-red-950/20 dark:border-red-900">
          <CardHeader className="pb-4">
            <div className="mx-auto mb-3 flex h-16 w-16 items-center justify-center rounded-full bg-red-100 text-red-600 dark:bg-red-900/50 dark:text-red-400">
              <ShieldAlert className="h-8 w-8" />
            </div>
            <CardTitle className="text-2xl font-bold text-red-950 dark:text-red-200">403 — Access Denied</CardTitle>
            <CardDescription className="text-red-700 dark:text-red-300 text-sm mt-1">
              Your role (<strong>{user.role}</strong>) does not have permission to access this feature.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <p className="text-xs text-muted-foreground">
              If you require access to this section, please contact your organization administrator to assign a custom permission profile to your account.
            </p>
            <Button asChild className="w-full bg-slate-900 hover:bg-slate-800 text-white dark:bg-slate-100 dark:text-slate-900">
              <Link href="/dashboard" className="flex items-center justify-center gap-2">
                <ArrowLeft className="h-4 w-4" />
                Return to Dashboard
              </Link>
            </Button>
          </CardContent>
        </Card>
      </div>
    );
  }

  return <>{children}</>;
}
