'use client';

import React, { createContext, useContext, useState, useEffect, useCallback, ReactNode } from 'react';
import { UserRole } from '@/types/user';
import { AuthUser, canAccessRoute } from '@/lib/auth';
import { supabase } from '@/lib/supabase';
import { Session } from '@supabase/supabase-js';

const IS_DEV_MODE = process.env.NEXT_PUBLIC_DEV_MODE === 'true';

// =============================================================================
// Types
// =============================================================================

export interface AuthContextType {
  user: AuthUser | null;
  isLoading: boolean;
  isAuthenticated: boolean;
  isDevMode: boolean;
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
        console.log('[Auth] Fetching initial session...');
        const { data: { session: initialSession }, error } = await supabase.auth.getSession();
        
        if (error) {
          console.error('[Auth] Error getting session:', error.message);
        } else if (initialSession && mounted) {
          console.log('[Auth] Initial session found:', {
            user_id: initialSession.user.id,
            email: initialSession.user.email,
          });
          setSession(initialSession);
          setUser(mapSupabaseUser(initialSession.user));
        } else if (!initialSession) {
          console.log('[Auth] No initial session found');
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
        
        console.log(`[Auth] State changed: ${event}`, {
          has_session: !!currentSession,
          user_id: currentSession?.user.id,
          event_details: event,
        });
        
        if (event === 'SIGNED_IN' || event === 'TOKEN_REFRESHED') {
          console.log('[Auth] User authenticated, setting session');
        }
        
        setSession(currentSession);
        if (currentSession?.user) {
          console.log('[Auth] Setting user:', {
            id: currentSession.user.id,
            email: currentSession.user.email,
          });
          setUser(mapSupabaseUser(currentSession.user));
        } else {
          console.log('[Auth] Clearing user');
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
      const { data, error } = await supabase.auth.signInWithPassword({ email, password });

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
      console.log('[Auth] Starting Google OAuth flow...');
      // Supabase will redirect to /login after OAuth with Google
      // The onAuthStateChange listener will pick up the authenticated session
      // Login page will then redirect to /dashboard
      const { error } = await supabase.auth.signInWithOAuth({
        provider: 'google',
        options: {
          redirectTo: `${window.location.origin}/login`,
        }
      });

      if (error) {
        console.error('[Auth] OAuth initialization error:', error);
        throw error;
      }
      
      console.log('[Auth] OAuth flow initiated, user redirected to Google');
      return { success: true };
    } catch (error: any) {
      console.error('[Auth] Google login failed:', {
        message: error.message,
        error: error,
      });
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
    isDevMode: IS_DEV_MODE,
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
