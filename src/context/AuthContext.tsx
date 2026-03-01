'use client';

import React, { createContext, useContext, useState, useEffect, useCallback, ReactNode } from 'react';
import { UserRole } from '@/types/user';
import {
  AuthTokens,
  AuthUser,
  setTokens,
  getTokens,
  clearTokens,
  getUserFromToken,
  isTokenExpired,
  refreshAccessToken,
  mockLogin,
  LoginResponse,
} from '@/lib/auth';
import { api } from '@/lib/api-client';

// =============================================================================
// Types
// =============================================================================

export interface AuthContextType {
  user: AuthUser | null;
  isLoading: boolean;
  isAuthenticated: boolean;
  login: (email: string, password: string) => Promise<{ success: boolean; error?: string; mfaRequired?: boolean; mfaToken?: string }>;
  verifyMfa: (mfaToken: string, code: string) => Promise<{ success: boolean; error?: string }>;
  logout: () => void;
  hasRole: (roles: UserRole | UserRole[]) => boolean;
}

// =============================================================================
// Context
// =============================================================================

const AuthContext = createContext<AuthContextType | undefined>(undefined);

// =============================================================================
// Provider
// =============================================================================

interface AuthProviderProps {
  children: ReactNode;
}

export function AuthProvider({ children }: AuthProviderProps) {
  const [user, setUser] = useState<AuthUser | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  // Initialize auth state from stored tokens
  useEffect(() => {
    const initAuth = async () => {
      try {
        const tokens = getTokens();

        if (!tokens) {
          setIsLoading(false);
          return;
        }

        // Try to verify session with real API if possible
        if (!api.isMock) {
          try {
            const userData = await api.get<AuthUser>('/auth/me');
            if (userData) {
              setUser(userData);
              setIsLoading(false);
              return;
            }
          } catch (apiError) {
            console.log('[Auth] API session init failed, falling back to local tokens');
          }
        }

        // Fallback to local token handling (Manual/Mock)
        // Note: For cookie-based auth, tokens.accessToken might be empty string
        if (tokens.accessToken) {
          const userData = getUserFromToken(tokens.accessToken);
          if (userData && !isTokenExpired(tokens.accessToken)) {
            setUser(userData);
          }
        }
      } catch (error) {
        console.error('[Auth] Init failed:', error);
        clearTokens();
      } finally {
        setIsLoading(false);
      }
    };

    initAuth();
  }, []);

  // Auto-refresh token before expiry
  // NOTE: In production, consider a more robust implementation with:
  // - Background timer
  // - Queue for concurrent requests
  // - Integration with service workers for offline support
  // Passive refresh loop removed:
  // We now rely on api-client's 401 interceptor for JIT refresh.
  // This is more efficient and works better with httpOnly cookies.

  const login = useCallback(async (email: string, password: string) => {
    try {
      let response: LoginResponse | null = null;

      if (!api.isMock) {
        try {
          const formData = new URLSearchParams();
          formData.append('username', email);
          formData.append('password', password);

          const rawResponse = await fetch(`${api.baseUrl}/auth/login`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
            body: formData.toString(),
          });

          if (!rawResponse.ok) {
            return { success: false, error: 'Invalid email or password' };
          }

          response = await rawResponse.json();

          if (response?.mfa_required) {
            return {
              success: false,
              mfaRequired: true,
              mfaToken: response.mfa_token
            };
          }

          // Signal login (cookies carry the tokens)
          setTokens({ accessToken: '', refreshToken: '' });

          // Fetch user profile
          const userData = await api.get<AuthUser>('/auth/me');
          setUser(userData);
          return { success: true };
        } catch (apiError) {
          console.warn('[Auth] API login failed, checking fallback');
        }
      }

      // Fallback to manual/mock login as requested
      response = await mockLogin(email, password);

      if (!response) {
        return { success: false, error: 'Invalid email or password' };
      }

      // Store tokens
      setTokens({
        accessToken: response.access_token,
        refreshToken: response.refresh_token,
      });

      // Set user state
      setUser({
        id: response.user?.id || '',
        email: response.user?.email || email,
        role: response.user?.role || 'analyst',
      });

      return { success: true };
    } catch (error) {
      console.error('[Auth] Login failed:', error);
      return { success: false, error: 'An error occurred. Please try again.' };
    }
  }, []);

  const verifyMfa = useCallback(async (mfaToken: string, code: string) => {
    try {
      const response = await api.post<LoginResponse>('/auth/mfa/verify', {
        mfa_token: mfaToken,
        code
      });

      if (!response) {
        return { success: false, error: 'Invalid MFA code' };
      }

      // Signal login
      setTokens({ accessToken: '', refreshToken: '' });

      // Fetch user profile
      const userData = await api.get<AuthUser>('/auth/me');
      setUser(userData);
      return { success: true };
    } catch (error) {
      console.error('[Auth] MFA verification failed:', error);
      return { success: false, error: 'Invalid code or expired session.' };
    }
  }, []);

  const logout = useCallback(async () => {
    try {
      await api.post('/auth/logout');
    } catch (error) {
      console.error('[Auth] Logout failed:', error);
    } finally {
      clearTokens();
      setUser(null);
      window.location.href = '/login';
    }
  }, []);

  const hasRole = useCallback((roles: UserRole | UserRole[]) => {
    if (!user) return false;
    const roleArray = Array.isArray(roles) ? roles : [roles];
    return roleArray.includes(user.role);
  }, [user]);

  const value: AuthContextType = {
    user,
    isLoading,
    isAuthenticated: !!user,
    login,
    verifyMfa,
    logout,
    hasRole,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

// =============================================================================
// Hook
// =============================================================================

export function useAuthContext(): AuthContextType {
  const context = useContext(AuthContext);

  if (context === undefined) {
    throw new Error('useAuthContext must be used within an AuthProvider');
  }

  return context;
}
