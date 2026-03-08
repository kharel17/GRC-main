import { UserRole } from '@/types/user';

// =============================================================================
// Types
// =============================================================================

export interface AuthUser {
  id: string;
  email: string;
  role: UserRole;
}

// =============================================================================
// Route Access Configuration
// =============================================================================

export const ROUTE_PERMISSIONS: Record<string, UserRole[]> = {
  '/dashboard': ['admin', 'analyst', 'manager'],
  '/dashboard/risks': ['admin', 'analyst'],
  '/dashboard/controls': ['admin', 'analyst'],
  '/dashboard/evidence': ['admin', 'analyst'],
  '/dashboard/audits': ['admin', 'manager'],
  '/dashboard/reports': ['admin', 'analyst', 'manager'],
  '/dashboard/settings': ['admin'],
  '/dashboard/users': ['admin'],
};

export function canAccessRoute(route: string, role: UserRole): boolean {
  if (ROUTE_PERMISSIONS[route]) {
    return ROUTE_PERMISSIONS[route].includes(role);
  }

  const segments = route.split('/').filter(Boolean);
  while (segments.length > 0) {
    const parentRoute = '/' + segments.join('/');
    if (ROUTE_PERMISSIONS[parentRoute]) {
      return ROUTE_PERMISSIONS[parentRoute].includes(role);
    }
    segments.pop();
  }
  return false;
}
