'use client';

import React, { createContext, useContext, useState, useEffect, useCallback, ReactNode } from 'react';
import { UserRole } from '@/types';
import { AuthUser, setTokens, clearTokens, getAccessToken, getUser, setUser as saveUser, getUserFromToken, refreshAccessToken } from '@/lib/auth';
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
  login: (email: string, password: string) => Promise<{ 
    success: boolean; 
    error?: string; 
    mfa_required?: boolean; 
    mfa_setup_required?: boolean; 
    two_fa_token?: string 
  }>;
  loginWithGoogle: (credential: string) => Promise<{ success: boolean; error?: string }>;
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
    const role = (supabaseUser.user_metadata?.role as UserRole) || 'admin';
    return {
      id: supabaseUser.id,
      email: supabaseUser.email || '',
      role: role,
      full_name: supabaseUser.user_metadata?.full_name,
    };
  };

  useEffect(() => {
    let mounted = true;

    async function initAuth() {
      try {
        // 1. Primary check: Local JWT token and cached user
        const localToken = getAccessToken();
        const cachedUser = getUser();

        if (localToken && cachedUser) {
          if (mounted) {
            setUser(cachedUser);
            setIsLoading(false);
          }

          // Enrich / verify profile with backend
          fetchCurrentUserProfile()
            .then((profile) => {
              if (!mounted) return;
              const enriched: AuthUser = {
                id: profile.id,
                email: profile.email,
                role: profile.role,
                full_name: profile.full_name,
                organization_id: profile.organization_id,
                organization_name: profile.organization_name,
              };
              setUser(enriched);
              saveUser(enriched);
            })
            .catch(async (profileErr: any) => {
              if (!mounted) return;
              if (profileErr?.status === 401 || profileErr?.response?.status === 401) {
                const refreshed = await refreshAccessToken();
                if (refreshed?.accessToken) {
                  try {
                    const refreshedProfile = await fetchCurrentUserProfile();
                    if (mounted) {
                      const enriched: AuthUser = {
                        id: refreshedProfile.id,
                        email: refreshedProfile.email,
                        role: refreshedProfile.role,
                        full_name: refreshedProfile.full_name,
                        organization_id: refreshedProfile.organization_id,
                        organization_name: refreshedProfile.organization_name,
                      };
                      setUser(enriched);
                      saveUser(enriched);
                    }
                    return;
                  } catch {
                    // ignore
                  }
                }
                clearTokens();
                if (mounted) setUser(null);
              } else if (profileErr?.response?.status === 403 || profileErr?.status === 403) {
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
            });
          return;
        }

        if (localToken && !cachedUser) {
          const tokenUser = getUserFromToken(localToken);
          if (tokenUser && mounted) {
            setUser(tokenUser);
            saveUser(tokenUser);
            setIsLoading(false);
          }

          fetchCurrentUserProfile()
            .then((profile) => {
              if (!mounted) return;
              const enriched: AuthUser = {
                id: profile.id,
                email: profile.email,
                role: profile.role,
                full_name: profile.full_name,
                organization_id: profile.organization_id,
                organization_name: profile.organization_name,
              };
              setUser(enriched);
              saveUser(enriched);
              setIsLoading(false);
            })
            .catch(() => {
              if (mounted) setIsLoading(false);
            });
          return;
        }

        // 2. Secondary fallback: Check legacy Supabase session
        try {
          const { data: { session: initialSession }, error } = await supabase.auth.getSession();
          if (!error && initialSession && mounted) {
            setSession(initialSession);
            const mapped = mapSupabaseUser(initialSession.user);
            setUser(mapped);
            setIsLoading(false);

            fetchCurrentUserProfile()
              .then((profile) => {
                if (!mounted) return;
                setUser({
                  id: profile.id,
                  email: profile.email,
                  role: profile.role,
                  full_name: profile.full_name,
                  organization_id: profile.organization_id,
                  organization_name: profile.organization_name,
                });
              })
              .catch(() => {});
            return;
          }
        } catch {
          // ignore Supabase error
        }

        if (mounted) {
          setUser(null);
          setIsLoading(false);
        }
      } catch (err) {
        console.error('[Auth] Init auth error:', err);
        if (mounted) {
          setUser(null);
          setIsLoading(false);
        }
      }
    }

    initAuth();

    // Listen for auth changes from Supabase (OAuth or legacy callbacks)
    try {
      const { data: { subscription } } = supabase.auth.onAuthStateChange(
        async (event, currentSession) => {
          if (!mounted) return;
          if (currentSession?.user) {
            setSession(currentSession);
            const mapped = mapSupabaseUser(currentSession.user);
            setUser(mapped);
            setIsLoading(false);

            fetchCurrentUserProfile()
              .then((profile) => {
                if (!mounted) return;
                setUser({
                  id: profile.id,
                  email: profile.email,
                  role: profile.role,
                  full_name: profile.full_name,
                  organization_id: profile.organization_id,
                  organization_name: profile.organization_name,
                });
              })
              .catch(() => {});
          }
        }
      );

      return () => {
        mounted = false;
        subscription.unsubscribe();
      };
    } catch {
      return () => {
        mounted = false;
      };
    }
  }, []);

  const login = useCallback(async (email: string, password: string) => {
    setIsLoading(true);
    try {
      const formData = new URLSearchParams();
      formData.append('username', email);
      formData.append('password', password);

      const res = await fetch('/api/v1/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
        credentials: 'include',
        body: formData,
      });

      const data = await res.json().catch(() => ({}));

      if (res.ok) {
        if (data.mfa_required) {
          return {
            success: true,
            mfa_required: true,
            mfa_setup_required: data.mfa_setup_required,
            two_fa_token: data.two_fa_token,
          };
        }

        if (data.access_token) {
          setTokens({ accessToken: data.access_token, refreshToken: data.access_token });
          const tokenUser = getUserFromToken(data.access_token);
          const authUser: AuthUser = {
            id: data.user?.id || tokenUser?.id || '',
            email: data.user?.email || tokenUser?.email || email,
            role: data.user?.role || tokenUser?.role || 'admin',
            full_name: data.user?.full_name || '',
            organization_id: data.user?.organization_id,
            organization_name: data.user?.organization_name,
          };
          setUser(authUser);
          saveUser(authUser);

          // Background sync
          fetchCurrentUserProfile().then((p) => {
            if (p) {
              const enriched: AuthUser = {
                id: p.id,
                email: p.email,
                role: p.role,
                full_name: p.full_name,
                organization_id: p.organization_id,
                organization_name: p.organization_name,
              };
              setUser(enriched);
              saveUser(enriched);
            }
          }).catch(() => {});

          return { success: true };
        }
      }

      // Fallback to Supabase auth if local login fails
      try {
        const { data: supaData, error: supaErr } = await supabase.auth.signInWithPassword({ email, password });
        if (supaErr) {
          return { success: false, error: data.detail || supaErr.message };
        }
        if (supaData?.session) {
          setSession(supaData.session);
          setUser(mapSupabaseUser(supaData.session.user));
          return { success: true };
        }
      } catch {
        return { success: false, error: data.detail || 'Incorrect email or password' };
      }

      return { success: false, error: data.detail || 'Incorrect email or password' };
    } catch (error: any) {
      console.error('[Auth] Login failed:', error);
      return { success: false, error: 'An unexpected error occurred.' };
    } finally {
      setIsLoading(false);
    }
  }, []);

  const loginWithGoogle = useCallback(async (credential: string) => {
    setIsLoading(true);
    try {
      const res = await fetch('/api/v1/auth/google', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({ credential }),
      });

      const data = await res.json().catch(() => ({}));

      if (res.ok && data.access_token) {
        setTokens({ accessToken: data.access_token, refreshToken: data.access_token });
        const tokenUser = getUserFromToken(data.access_token);
        const authUser: AuthUser = {
          id: data.user?.id || tokenUser?.id || '',
          email: data.user?.email || tokenUser?.email || '',
          role: data.user?.role || tokenUser?.role || 'analyst',
          full_name: data.user?.full_name || '',
          organization_id: data.user?.organization_id,
          organization_name: data.user?.organization_name,
        };
        setUser(authUser);
        saveUser(authUser);

        fetchCurrentUserProfile().then((p) => {
          if (p) {
            const enriched: AuthUser = {
              id: p.id,
              email: p.email,
              role: p.role,
              full_name: p.full_name,
              organization_id: p.organization_id,
              organization_name: p.organization_name,
            };
            setUser(enriched);
            saveUser(enriched);
          }
        }).catch(() => {});

        return { success: true };
      }

      return {
        success: false,
        error: data.detail || 'Google sign-in failed. Please try again.',
      };
    } catch (error: any) {
      console.error('[Auth] Google login failed:', error);
      return { success: false, error: 'Network error during Google sign-in.' };
    } finally {
      setIsLoading(false);
    }
  }, []);

  const logout = useCallback(async () => {
    setIsLoading(true);
    try {
      await fetch('/api/v1/auth/logout', {
        method: 'POST',
        credentials: 'include',
      }).catch(() => {});

      try {
        await supabase.auth.signOut();
      } catch {
        // ignore
      }

      clearTokens();
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
    isAuthenticated: !!user,
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
