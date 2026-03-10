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
<<<<<<< HEAD
// Constants
// =============================================================================

const TOKEN_KEY = 'grc_tokens';
const USER_KEY = 'grc_user';

// Token expiry buffer (refresh 30 seconds before actual expiry)
const EXPIRY_BUFFER_MS = 30 * 1000;

// =============================================================================
// Token Storage
// =============================================================================

export function setTokens(tokens: AuthTokens): void {
  if (typeof window === 'undefined') return;
  localStorage.setItem(TOKEN_KEY, JSON.stringify(tokens));
}

export function getTokens(): AuthTokens | null {
  if (typeof window === 'undefined') return null;
  const stored = localStorage.getItem(TOKEN_KEY);
  if (!stored) return null;

  try {
    return JSON.parse(stored) as AuthTokens;
  } catch {
    return null;
  }
}

export function clearTokens(): void {
  if (typeof window === 'undefined') return;
  localStorage.removeItem(TOKEN_KEY);
  localStorage.removeItem(USER_KEY);
}

// =============================================================================
// JWT Utilities
// =============================================================================

export function decodeToken(token: string): JWTPayload | null {
  try {
    const parts = token.split('.');
    if (parts.length !== 3) return null;

    const payload = parts[1];
    const decoded = atob(payload.replace(/-/g, '+').replace(/_/g, '/'));
    return JSON.parse(decoded) as JWTPayload;
  } catch {
    return null;
  }
}

export function isTokenExpired(token: string): boolean {
  const payload = decodeToken(token);
  if (!payload) return true;

  const expiryMs = payload.exp * 1000;
  const nowMs = Date.now();
  return nowMs >= expiryMs - EXPIRY_BUFFER_MS;
}

export function getUserFromToken(token: string): AuthUser | null {
  const payload = decodeToken(token);
  if (!payload) return null;

  return {
    id: payload.sub,
    email: payload.email,
    role: payload.role,
  };
}

// =============================================================================
// Token Refresh
// =============================================================================

export async function refreshAccessToken(): Promise<AuthTokens | null> {
  try {
    const response = await fetch(`${api.baseUrl}/auth/refresh`, {
      method: 'POST',
      credentials: 'include',
    });

    if (!response.ok) {
      return null;
    }

    const data = await response.json();
    const tokens: AuthTokens = {
      accessToken: data.access_token,
      refreshToken: data.access_token, // Simplified for now since cookies store the real refresh token
    };

    setTokens(tokens);
    return tokens;
  } catch (error) {
    console.error('[Auth] Token refresh failed:', error);
    return null;
  }
}

// =============================================================================
=======
>>>>>>> 42168cb2fdec1ec52ab0262d1f577c0211c45c5e
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
