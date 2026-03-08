'use client';

import React, { createContext, useContext, useState, useEffect, useCallback, ReactNode } from 'react';
import { UserRole } from '@/types/user';
import { AuthUser, canAccessRoute } from '@/lib/auth';
import { supabase } from '@/lib/supabase';
import { Session } from '@supabase/supabase-js';

// =============================================================================
// Types
// =============================================================================

export interface AuthContextType {
  user: AuthUser | null;
  isLoading: boolean;
  isAuthenticated: boolean;
  login: (email: string, password: string) => Promise<{ success: boolean; error?: string }>;
  loginWithGoogle: () => Promise<{ success: boolean; error?: string }>;
  logout: () => Promise<void>;
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
  const [session, setSession] = useState<Session | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  // Helper to map Supabase user to our AuthUser type
  const mapSupabaseUser = (supabaseUser: any): AuthUser => {
    // Default to 'analyst' if no role is explicitly set in metadata
    const role = (supabaseUser.user_metadata?.role as UserRole) || 'analyst';
    return {
      id: supabaseUser.id,
      email: supabaseUser.email || '',
      role: role,
    };
  };

  useEffect(() => {
    let mounted = true;

    async function getInitialSession() {
      try {
        const { data: { session: initialSession }, error } = await supabase.auth.getSession();
        
        if (error) {
          console.error('[Auth] Error getting session:', error.message);
        } else if (initialSession && mounted) {
          setSession(initialSession);
          setUser(mapSupabaseUser(initialSession.user));
        }
      } catch (e) {
        console.error('[Auth] Failed to initialize session', e);
      } finally {
        if (mounted) setIsLoading(false);
      }
    }

    getInitialSession();

    // Listen for auth changes (login, logout, token refresh)
    const { data: { subscription } } = supabase.auth.onAuthStateChange(
      async (event, currentSession) => {
        if (!mounted) return;
        
        console.log(`[Auth] State changed: ${event}`);
        
        setSession(currentSession);
        if (currentSession?.user) {
          setUser(mapSupabaseUser(currentSession.user));
        } else {
          setUser(null);
        }
        setIsLoading(false);
      }
    );

    return () => {
      mounted = false;
      subscription.unsubscribe();
    };
  }, []);

  const login = useCallback(async (email: string, password: string) => {
    setIsLoading(true);
    try {
      const { data, error } = await supabase.auth.signInWithPassword({
        email,
        password,
      });

      if (error) {
        return { success: false, error: error.message };
      }

      return { success: true };
    } catch (error: any) {
      console.error('[Auth] Login failed:', error);
      return { success: false, error: 'An unexpected error occurred.' };
    } finally {
      setIsLoading(false);
    }
  }, []);

  const loginWithGoogle = useCallback(async () => {
    try {
      const { error } = await supabase.auth.signInWithOAuth({
        provider: 'google',
        options: {
          redirectTo: `${window.location.origin}/dashboard`,
        }
      });

      if (error) throw error;
      return { success: true };
    } catch (error: any) {
      console.error('[Auth] Google login failed:', error);
      return { success: false, error: error.message || 'Google login failed' };
    }
  }, []);

  const logout = useCallback(async () => {
    setIsLoading(true);
    try {
      const { error } = await supabase.auth.signOut();
      if (error) throw error;
      
      setUser(null);
      setSession(null);
      window.location.href = '/login';
    } catch (error) {
      console.error('[Auth] Logout failed:', error);
    } finally {
      setIsLoading(false);
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
    isAuthenticated: !!user && !!session,
    login,
    loginWithGoogle,
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
