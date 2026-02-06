import { UserRole } from '@/types/user';

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

const TOKEN_KEY = 'grc_tokens';
const USER_KEY = 'grc_user';

// Token expiry buffer (refresh 30 seconds before actual expiry)
// NOTE: In production with proper refresh implementation, increase to 5 minutes
const EXPIRY_BUFFER_MS = 30 * 1000;

// =============================================================================
// Token Storage
// NOTE: Using localStorage for development. In production, consider:
// - HTTP-only cookies for refresh tokens (prevents XSS)
// - In-memory storage for access tokens
// - Secure cookie flags (Secure, SameSite=Strict)
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

/**
 * Decode a JWT token without verification.
 * NOTE: In production, verification should happen server-side.
 * Frontend decoding is only for extracting claims.
 */
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

/**
 * Check if a token is expired or about to expire.
 */
export function isTokenExpired(token: string): boolean {
  const payload = decodeToken(token);
  if (!payload) return true;
  
  const expiryMs = payload.exp * 1000;
  const nowMs = Date.now();
  
  // Consider expired if within buffer period
  return nowMs >= expiryMs - EXPIRY_BUFFER_MS;
}

/**
 * Extract user data from an access token.
 */
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
// NOTE: Placeholder for production implementation.
// In production, this should:
// - Call the refresh endpoint with the refresh token
// - Handle 401 errors by forcing logout
// - Queue multiple refresh calls to prevent race conditions
// - Integrate with AWS Cognito or your auth provider
// =============================================================================

export async function refreshAccessToken(refreshToken: string): Promise<AuthTokens | null> {
  try {
    // TODO: Replace with actual API call in production
    // const response = await fetch('/api/auth/refresh', {
    //   method: 'POST',
    //   headers: { 'Content-Type': 'application/json' },
    //   body: JSON.stringify({ refreshToken }),
    // });
    // 
    // if (!response.ok) {
    //   return null;
    // }
    // 
    // const data = await response.json();
    // return { accessToken: data.access_token, refreshToken: data.refresh_token };
    
    console.warn('[Auth] Token refresh not implemented - using mock');
    return null;
  } catch (error) {
    console.error('[Auth] Token refresh failed:', error);
    return null;
  }
}

// =============================================================================
// Route Access Configuration
// Centralized role-to-route mapping for easy scalability.
// Adding new roles or routes only requires updating this config.
// =============================================================================

export const ROUTE_PERMISSIONS: Record<string, UserRole[]> = {
  // Dashboard - accessible to all authenticated users
  '/dashboard': ['admin', 'analyst', 'manager'],
  
  // Risk Management
  '/dashboard/risks': ['admin', 'analyst'],
  
  // Control Management
  '/dashboard/controls': ['admin', 'analyst'],
  
  // Evidence Management
  '/dashboard/evidence': ['admin', 'analyst'],
  
  // Audit Logs
  '/dashboard/audits': ['admin', 'manager'],
  
  // Reports
  '/dashboard/reports': ['admin', 'analyst', 'manager'],
  
  // Settings - Admin only
  '/dashboard/settings': ['admin'],
  
  // User Management (future)
  '/dashboard/users': ['admin'],
};

/**
 * Check if a role has access to a specific route.
 */
export function canAccessRoute(route: string, role: UserRole): boolean {
  // Check exact match first
  if (ROUTE_PERMISSIONS[route]) {
    return ROUTE_PERMISSIONS[route].includes(role);
  }
  
  // Check parent routes for nested paths
  const segments = route.split('/').filter(Boolean);
  while (segments.length > 0) {
    const parentRoute = '/' + segments.join('/');
    if (ROUTE_PERMISSIONS[parentRoute]) {
      return ROUTE_PERMISSIONS[parentRoute].includes(role);
    }
    segments.pop();
  }
  
  // Default: deny access to unknown routes
  return false;
}

// =============================================================================
// Mock API Helpers (for development)
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

/**
 * Generate a mock JWT token for development.
 * In production, tokens are generated server-side with proper signing.
 */
function generateMockToken(user: MockUser): string {
  const now = Math.floor(Date.now() / 1000);
  const payload: JWTPayload = {
    sub: user.id,
    email: user.email,
    role: user.role,
    iat: now,
    exp: now + 3600, // 1 hour expiry
  };
  
  // Create a mock JWT (header.payload.signature)
  const header = btoa(JSON.stringify({ alg: 'HS256', typ: 'JWT' }));
  const payloadB64 = btoa(JSON.stringify(payload));
  const signature = btoa('mock-signature');
  
  return `${header}.${payloadB64}.${signature}`;
}

export interface LoginResponse {
  access_token: string;
  refresh_token: string;
  user: {
    id: string;
    email: string;
    role: UserRole;
  };
}

/**
 * Mock login function for development.
 * Replace with actual API call in production.
 */
export async function mockLogin(email: string, password: string): Promise<LoginResponse | null> {
  // Simulate network delay
  await new Promise(resolve => setTimeout(resolve, 800));
  
  const user = MOCK_USERS.find(u => u.email === email && u.password === password);
  
  if (!user) {
    return null;
  }
  
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
