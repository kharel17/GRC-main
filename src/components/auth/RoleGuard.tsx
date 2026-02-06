'use client';

import { ReactNode } from 'react';
import { useAuth } from '@/hooks/useAuth';
import { UserRole } from '@/types/user';

// =============================================================================
// Types
// =============================================================================

interface RoleGuardProps {
  /** Roles that are allowed to see the content */
  allowedRoles: UserRole[];
  /** Content to render if user has permission */
  children: ReactNode;
  /** Optional fallback content if user doesn't have permission */
  fallback?: ReactNode;
}

// =============================================================================
// Component
// =============================================================================

/**
 * RoleGuard - Conditionally renders content based on user role.
 * 
 * Usage:
 * ```tsx
 * <RoleGuard allowedRoles={['admin', 'analyst']}>
 *   <Button>Edit</Button>
 * </RoleGuard>
 * 
 * // With fallback content
 * <RoleGuard 
 *   allowedRoles={['admin']} 
 *   fallback={<span>View Only</span>}
 * >
 *   <Button>Delete</Button>
 * </RoleGuard>
 * ```
 * 
 * NOTE: This is for UX only. All sensitive actions MUST be validated server-side.
 * Never rely solely on frontend role checks for security.
 */
export function RoleGuard({ allowedRoles, children, fallback = null }: RoleGuardProps) {
  const { user, isLoading } = useAuth();

  // Don't render anything while loading
  if (isLoading) {
    return null;
  }

  // Check if user has required role
  if (!user || !allowedRoles.includes(user.role)) {
    return <>{fallback}</>;
  }

  return <>{children}</>;
}

// =============================================================================
// Higher-Order Component (Alternative Pattern)
// =============================================================================

/**
 * withRoleGuard - HOC for wrapping components with role protection.
 * 
 * Usage:
 * ```tsx
 * const AdminButton = withRoleGuard(Button, ['admin']);
 * ```
 */
export function withRoleGuard<P extends object>(
  Component: React.ComponentType<P>,
  allowedRoles: UserRole[]
) {
  return function RoleGuardedComponent(props: P) {
    return (
      <RoleGuard allowedRoles={allowedRoles}>
        <Component {...props} />
      </RoleGuard>
    );
  };
}

export default RoleGuard;
