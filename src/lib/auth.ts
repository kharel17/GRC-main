import { UserRole } from '@/types';
import { setTokens as storageSetTokens, getTokens as storageGetTokens, clearTokens as storageClearTokens } from './token-storage';
import { api } from './api-client';


// =============================================================================
// Types
// =============================================================================

export interface AuthUser {
  id: string;
  email: string;
  role: UserRole;
}

export interface JWTPayload {
  sub: string;
  email: string;
  role: UserRole;
  exp: number;
}

export interface AuthTokens {
  accessToken: string;
  refreshToken: string;
}


// =============================================================================
// Constants
// =============================================================================

const TOKEN_KEY = 'grc_tokens';
const USER_KEY = 'grc_user';

// Token expiry buffer (refresh 30 seconds before actual expiry)
const EXPIRY_BUFFER_MS = 30 * 1000;

// =============================================================================
// Token Storage
// =============================================================================

export function setTokens(tokens: any): void {
  storageSetTokens(tokens);
}

export function getTokens(): any | null {
  return storageGetTokens();
}

export function clearTokens(): void {
  storageClearTokens();
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
// Route Access Configuration
// =============================================================================

export const ROUTE_PERMISSIONS: Record<string, UserRole[]> = {
  '/dashboard': ['admin', 'analyst', 'control_owner', 'risk_owner', 'compliance_officer', 'department_manager', 'executive', 'auditor'],
  '/dashboard/risks': ['admin', 'analyst', 'risk_owner', 'compliance_officer', 'executive', 'auditor'],
  '/dashboard/controls': ['admin', 'analyst', 'control_owner', 'compliance_officer', 'auditor'],
  '/dashboard/evidence': ['admin', 'analyst', 'control_owner', 'risk_owner', 'compliance_officer', 'auditor'],
  '/dashboard/audits': ['admin', 'compliance_officer', 'department_manager', 'executive', 'auditor'],
  '/dashboard/reports': ['admin', 'analyst', 'compliance_officer', 'department_manager', 'executive', 'auditor'],
  '/dashboard/tickets': ['admin', 'analyst', 'control_owner', 'risk_owner', 'compliance_officer', 'department_manager', 'executive', 'auditor'],
  '/dashboard/iso27001': ['admin', 'analyst', 'compliance_officer', 'department_manager', 'executive', 'auditor'],
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
