'use client';

import { useAuthContext, AuthContextType } from '@/context/AuthContext';

/**
 * Custom hook for accessing authentication state and methods.
 * 
 * Usage:
 * ```tsx
 * const { user, isAuthenticated, login, logout, hasRole } = useAuth();
 * 
 * // Check if user has a specific role
 * if (hasRole('admin')) {
 *   // Show admin content
 * }
 * 
 * // Check if user has any of the specified roles
 * if (hasRole(['admin', 'analyst'])) {
 *   // Show content for admin or analyst
 * }
 * ```
 */
export function useAuth(): AuthContextType {
  return useAuthContext();
}

export default useAuth;
