'use client';

import React, { createContext, useContext, useState, useEffect, useCallback, ReactNode } from 'react';
import { UserRole } from '@/types';
import { AuthUser, canAccessRoute } from '@/lib/auth';
import { supabase } from '@/lib/supabase';
import { Session } from '@supabase/supabase-js';
import { fetchCurrentUserProfile } from '@/lib/data-service';

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
    // Default to 'admin' if no role is explicitly set in metadata
    const role = (supabaseUser.user_metadata?.role as UserRole) || 'admin';
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
          console.log('[Auth] Initial session found, fetching profile...');
          setSession(initialSession);
          
          // Fetch real profile from backend to get the correct role
          try {
            console.log('[Auth] Calling backend /auth/me...');
            const profile = await fetchCurrentUserProfile();
            console.log('[Auth] Backend profile received:', profile);
            setUser({
              id: profile.id,
              email: profile.email,
              role: profile.role,
            });
          } catch (profileErr: any) {
            // Check for invitation system errors
            if (profileErr?.response?.status === 403 || profileErr?.status === 403) {
              const detail = profileErr?.response?.data?.detail || profileErr?.data?.detail || profileErr?.detail;
              if (detail?.code === 'NOT_INVITED') {
                window.location.href = '/not-invited';
                return;
              }
              if (detail?.code === 'ACCOUNT_DEACTIVATED') {
                window.location.href = '/deactivated';
                return;
              }
            }
            console.warn('[Auth] Backend profile fetch failed:', profileErr);
            setUser(mapSupabaseUser(initialSession.user));
          }
        } else {
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
          
          // Prefer backend profile for correct roles
          try {
            const profile = await fetchCurrentUserProfile();
            setUser({
              id: profile.id,
              email: profile.email,
              role: profile.role,
            });
          } catch (profileErr: any) {
            // Check for invitation system errors
            if (profileErr?.response?.status === 403 || profileErr?.status === 403) {
              const detail = profileErr?.response?.data?.detail || profileErr?.data?.detail || profileErr?.detail;
              if (detail?.code === 'NOT_INVITED') {
                window.location.href = '/not-invited';
                return;
              }
              if (detail?.code === 'ACCOUNT_DEACTIVATED') {
                window.location.href = '/deactivated';
                return;
              }
            }
            console.warn('[Auth] Auth change profile fetch failed, using metadata', profileErr);
            setUser(mapSupabaseUser(currentSession.user));
          }
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
      const { data: _data, error: signInError } = await supabase.auth.signInWithPassword({ email, password });
      let error = signInError;

      // Auto-signup fallback for Dev Mode seed users if they don't exist yet in Supabase Auth
      if (
        error &&
        error.message.includes('Invalid login credentials') &&
        IS_DEV_MODE &&
        ['alice@company.com', 'bob@company.com', 'carol@company.com'].includes(email)
      ) {
        console.log(`[Auth] Seed user ${email} not found. Auto-creating...`);
        const signupRes = await supabase.auth.signUp({
          email,
          password,
          options: {
            data: {
              role: email === 'alice@company.com' ? 'admin' : (email === 'carol@company.com' ? 'department_manager' : 'analyst'),
              full_name: email.split('@')[0]
            }
          }
        });
        error = signupRes.error;
      }

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
