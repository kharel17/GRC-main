import { NextResponse } from 'next/server';
import type { NextRequest } from 'next/server';
import { UserRole } from '@/types/user';



const ROUTE_PERMISSIONS: Record<string, UserRole[]> = {
  '/dashboard': ['admin', 'analyst', 'manager'],
  '/dashboard/risks': ['admin', 'analyst'],
  '/dashboard/controls': ['admin', 'analyst'],
  '/dashboard/evidence': ['admin', 'analyst'],
  '/dashboard/audits': ['admin', 'manager'],
  '/dashboard/reports': ['admin', 'analyst', 'manager'],
  '/dashboard/iso27001': ['admin', 'analyst', 'manager'],
  '/dashboard/settings': ['admin'],
  '/dashboard/users': ['admin'],
};

// =============================================================================
// Helper Functions
// =============================================================================

function getRoutePermissions(pathname: string): UserRole[] | null {
  // Check exact match first
  if (ROUTE_PERMISSIONS[pathname]) {
    return ROUTE_PERMISSIONS[pathname];
  }

  // Check parent routes for nested paths (e.g., /dashboard/risks/123)
  const segments = pathname.split('/').filter(Boolean);
  while (segments.length > 0) {
    const parentRoute = '/' + segments.join('/');
    if (ROUTE_PERMISSIONS[parentRoute]) {
      return ROUTE_PERMISSIONS[parentRoute];
    }
    segments.pop();
  }

  return null;
}

function decodeTokenPayload(token: string): { role: UserRole; exp: number } | null {
  try {
    const parts = token.split('.');
    if (parts.length !== 3) return null;

    const payload = parts[1];
    const decoded = atob(payload.replace(/-/g, '+').replace(/_/g, '/'));
    return JSON.parse(decoded);
  } catch {
    return null;
  }
}

// =============================================================================
// Middleware
// NOTE: For development, we're using a permissive approach that allows
// client-side auth to handle authentication. In production with proper
// HTTP-only cookies, this middleware would be more strict.
// =============================================================================

export function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;

  // Only protect /dashboard routes
  if (!pathname.startsWith('/dashboard')) {
    return NextResponse.next();
  }

  // Check for auth token cookie
  const tokenCookie = request.cookies.get('access_token');

  // If no cookie, let client-side auth handle it
  // The dashboard layout will redirect to login if not authenticated
  if (!tokenCookie?.value) {
    // For development: allow through, let client handle auth
    // For production: uncomment the redirect below
    // const loginUrl = new URL('/login', request.url);
    // loginUrl.searchParams.set('redirect', pathname);
    // return NextResponse.redirect(loginUrl);
    return NextResponse.next();
  }

  // Decode token to get role
  const payload = decodeTokenPayload(tokenCookie.value);

  if (!payload?.role) {
    // Invalid token - clear the cookie and let client handle
    const response = NextResponse.next();
    response.cookies.delete('access_token');
    return response;
  }

  // Check if token is expired
  const nowSeconds = Math.floor(Date.now() / 1000);
  if (payload.exp && payload.exp < nowSeconds) {
    // Token expired - clear cookie and let client handle refresh
    const response = NextResponse.next();
    response.cookies.delete('access_token');
    return response;
  }

  // Check route permissions
  const allowedRoles = getRoutePermissions(pathname);

  if (allowedRoles && !allowedRoles.includes(payload.role)) {
    // User doesn't have permission, redirect to dashboard with error
    const dashboardUrl = new URL('/dashboard', request.url);
    dashboardUrl.searchParams.set('error', 'unauthorized');
    return NextResponse.redirect(dashboardUrl);
  }

  return NextResponse.next();
}

// =============================================================================
// Matcher Configuration
// =============================================================================

export const config = {
  matcher: [
    /*
     * Match all dashboard routes
     * Excludes:
     * - api routes
     * - static files
     * - public assets
     */
    '/dashboard/:path*',
  ],
};
