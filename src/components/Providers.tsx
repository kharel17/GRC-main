'use client';

import { ReactNode } from 'react';
import { AuthProvider } from '@/context/AuthContext';
import { ThemeProvider } from '@/components/theme-provider';
import { LanguageProvider } from '@/context/LanguageContext';
import { SidebarCollapseProvider } from '@/context/SidebarContext';

interface ProvidersProps {
  children: ReactNode;
}

/**
 * Client-side providers wrapper.
 * This component wraps all client-side context providers.
 * Add additional providers here as needed (e.g., ThemeProvider, QueryClientProvider).
 */
export function Providers({ children }: ProvidersProps) {
  return (
    <ThemeProvider
      attribute="class"
      defaultTheme="system"
      enableSystem
      disableTransitionOnChange
    >
      <SidebarCollapseProvider>
        <LanguageProvider>
          <AuthProvider>{children}</AuthProvider>
        </LanguageProvider>
      </SidebarCollapseProvider>
    </ThemeProvider>
  );
}

