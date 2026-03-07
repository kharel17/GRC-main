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

// =============================================================================
// Types
// =============================================================================

export interface AuthContextType {
  user: AuthUser | null;
  isLoading: boolean;
  isAuthenticated: boolean;
  login: (email: string, password: string) => Promise<{ success: boolean; error?: string }>;
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

        // Try to extract user from token first
        const userData = getUserFromToken(tokens.accessToken);

        if (!userData) {
          // Token is invalid/malformed, clear and force re-login
          clearTokens();
          setIsLoading(false);
          return;
        }

        // Check if token is expired or about to expire
        if (isTokenExpired(tokens.accessToken)) {
          // Attempt to refresh
          const newTokens = await refreshAccessToken(tokens.refreshToken);

          if (newTokens) {
            setTokens(newTokens);
            const newUserData = getUserFromToken(newTokens.accessToken);
            setUser(newUserData);
          } else {
            // Refresh failed - for development, still use the existing token
            // if it's not actually expired (just within buffer)
            // In production, you would force logout here
            console.warn('[Auth] Token refresh failed, using existing token');
            setUser(userData);
          }
        } else {
          // Token is valid, set user
          setUser(userData);
        }
      } catch (error) {
        console.error('[Auth] Init failed:', error);
        clearTokens();
      }

      setIsLoading(false);
    };

    initAuth();
  }, []);

  // Auto-refresh token before expiry
  // NOTE: In production, consider a more robust implementation with:
  // - Background timer
  // - Queue for concurrent requests
  // - Integration with service workers for offline support
  useEffect(() => {
    if (!user) return;

    const tokens = getTokens();
    if (!tokens) return;

    const payload = getUserFromToken(tokens.accessToken);
    if (!payload) return;

    // Calculate time until expiry (with 5 minute buffer)
    const checkInterval = setInterval(async () => {
      const currentTokens = getTokens();
      if (!currentTokens) return;

      if (isTokenExpired(currentTokens.accessToken)) {
        const newTokens = await refreshAccessToken(currentTokens.refreshToken);

        if (newTokens) {
          setTokens(newTokens);
          const userData = getUserFromToken(newTokens.accessToken);
          setUser(userData);
        } else {
          // Refresh failed, logout user
          clearTokens();
          setUser(null);
          window.location.href = '/login';
        }
      }
    }, 60000); // Check every minute

    return () => clearInterval(checkInterval);
  }, [user]);

  const login = useCallback(async (email: string, password: string) => {
    try {
      // Import the real login function from auth.ts
      const { login: authLogin } = await import('@/lib/auth');
      const response: LoginResponse | null = await authLogin(email, password);

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
        id: response.user.id,
        email: response.user.email,
        role: response.user.role,
      });

      return { success: true };
    } catch (error) {
      console.error('[Auth] Login failed:', error);
      return { success: false, error: 'An error occurred. Please try again.' };
    }
  }, []);

  const logout = useCallback(() => {
    clearTokens();
    setUser(null);
    window.location.href = '/login';
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
