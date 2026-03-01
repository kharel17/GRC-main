import { UserRole } from '@/types/user';
import { api } from './api-client';

// =============================================================================
// Types
// =============================================================================

export interface AuthTokens {
  accessToken: string;
  refreshToken: string;
}

export interface JWTPayload {
  sub: string; // user id
  email: string;
  role: UserRole;
  exp: number; // expiration timestamp
  iat: number; // issued at timestamp
}

export interface AuthUser {
  id: string;
  email: string;
  role: UserRole;
}

// =============================================================================
// Constants
// =============================================================================

const TOKEN_KEY = 'tokens';
const USER_KEY = 'user';

// Token expiry buffer (refresh 30 seconds before actual expiry)
const EXPIRY_BUFFER_MS = 30 * 1000;

// =============================================================================
// Token Storage
// =============================================================================

export function setTokens(tokens: AuthTokens): void {
  if (typeof window === 'undefined') return;
  // Signal login (for cookie detection fallback)
  localStorage.setItem('is_logged_in', 'true');
  // Store actual tokens if not empty (Mock/Manual support)
  if (tokens.accessToken !== '') {
    localStorage.setItem(TOKEN_KEY, JSON.stringify(tokens));
  }
}

export function getTokens(): AuthTokens | null {
  if (typeof window === 'undefined') return null;

  // Try to get actual stored tokens first
  const stored = localStorage.getItem(TOKEN_KEY);
  if (stored) {
    try {
      return JSON.parse(stored) as AuthTokens;
    } catch {
      // ignore
    }
  }

  // Fallback to checking the login flag (for cookie-only auth)
  const isLoggedIn = localStorage.getItem('is_logged_in');
  if (isLoggedIn) {
    return {
      accessToken: '',
      refreshToken: '',
    };
  }

  return null;
}

export function clearTokens(): void {
  if (typeof window === 'undefined') return;
  localStorage.removeItem('is_logged_in');
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

export async function refreshAccessToken(refreshToken: string): Promise<AuthTokens | null> {
  try {
    console.warn('[Auth] Token refresh not implemented - using mock');
    return null;
  } catch (error) {
    console.error('[Auth] Token refresh failed:', error);
    return null;
  }
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

// =============================================================================
// Login — Real API + Mock Fallback
// =============================================================================

interface MockUser {
  id: string;
  email: string;
  password: string;
  role: UserRole;
}

const MOCK_USERS: MockUser[] = [
  { id: '1', email: 'alice@company.com', password: 'demo', role: 'admin' },
  { id: '2', email: 'bob@company.com', password: 'demo', role: 'analyst' },
  { id: '3', email: 'carol@company.com', password: 'demo', role: 'manager' },
];

function generateMockToken(user: MockUser): string {
  const now = Math.floor(Date.now() / 1000);
  const payload: JWTPayload = {
    sub: user.id,
    email: user.email,
    role: user.role,
    iat: now,
    exp: now + 3600,
  };

  const header = btoa(JSON.stringify({ alg: 'HS256', typ: 'JWT' }));
  const payloadB64 = btoa(JSON.stringify(payload));
  const signature = btoa('mock-signature');
  return `${header}.${payloadB64}.${signature}`;
}

export interface LoginResponse {
  access_token: string;
  refresh_token: string;
  mfa_required?: boolean;
  mfa_token?: string;
  user?: {
    id: string;
    email: string;
    role: UserRole;
  };
}

/**
 * Login: calls real API when available, falls back to mock.
 */
export async function login(email: string, password: string): Promise<LoginResponse | null> {
  // If mock mode, use local mock
  if (api.isMock) {
    return mockLogin(email, password);
  }

  // Real API login using OAuth2 form data
  try {
    const formData = new URLSearchParams();
    formData.append('username', email);
    formData.append('password', password);

    const response = await fetch(`${api.baseUrl}/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      body: formData.toString(),
    });

    if (!response.ok) {
      return null;
    }

    const data = await response.json();

    if (data.mfa_required) {
      return {
        access_token: '',
        refresh_token: '',
        mfa_required: true,
        mfa_token: data.mfa_token,
        user: { id: '', email, role: 'analyst' as UserRole }
      };
    }

    // Store state flag
    setTokens({ accessToken: '', refreshToken: '' });

    // Fetch user profile after login since token is in cookie
    const userResponse = await fetch(`${api.baseUrl}/auth/me`, {
      headers: { 'Content-Type': 'application/json' },
      credentials: 'include'
    });

    let userFromToken = null;
    if (userResponse.ok) {
      userFromToken = await userResponse.json();
    }

    return {
      access_token: '',
      refresh_token: '',
      user: userFromToken || { id: '', email, role: 'analyst' as UserRole },
    };
  } catch (error) {
    console.error('[Auth] API login failed, falling back to mock:', error);
    return mockLogin(email, password);
  }
}

/**
 * Mock login for development/demo.
 */
export async function mockLogin(email: string, password: string): Promise<LoginResponse | null> {
  await new Promise(resolve => setTimeout(resolve, 800));

  const user = MOCK_USERS.find(u => u.email === email && u.password === password);
  if (!user) return null;

  const accessToken = generateMockToken(user);
  const refreshToken = generateMockToken({ ...user, id: `refresh-${user.id}` });

  return {
    access_token: accessToken,
    refresh_token: refreshToken,
    user: {
      id: user.id,
      email: user.email,
      role: user.role,
    },
  };
}
/**
 * Verify MFA code for login.
 */
export async function verifyMfa(mfaToken: string, code: string): Promise<LoginResponse | null> {
  try {
    const response = await fetch(`${api.baseUrl}/auth/mfa/verify`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ mfa_token: mfaToken, code }),
      credentials: 'include'
    });

    if (!response.ok) return null;

    // Flag login
    setTokens({ accessToken: '', refreshToken: '' });

    return await response.json();
  } catch (error) {
    console.error('[Auth] MFA verification failed:', error);
    return null;
  }
}
