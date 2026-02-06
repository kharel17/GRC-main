'use client';

import { ReactNode } from 'react';
import { AuthProvider } from '@/context/AuthContext';

interface ProvidersProps {
  children: ReactNode;
}

/**
 * Client-side providers wrapper.
 * This component wraps all client-side context providers.
 * Add additional providers here as needed (e.g., ThemeProvider, QueryClientProvider).
 */
export function Providers({ children }: ProvidersProps) {
  return <AuthProvider>{children}</AuthProvider>;
}
