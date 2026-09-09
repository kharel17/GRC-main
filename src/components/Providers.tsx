'use client';

import { ReactNode } from 'react';
import { GoogleOAuthProvider } from '@react-oauth/google';
import { AuthProvider } from '@/context/AuthContext';
import { ThemeProvider } from '@/components/theme-provider';
import { LanguageProvider } from '@/context/LanguageContext';
import { SidebarCollapseProvider } from '@/context/SidebarContext';

interface ProvidersProps {
  children: ReactNode;
}

/**
 * Client-side providers wrapper.
 * This component wraps all client-side context providers including GoogleOAuthProvider.
 */
export function Providers({ children }: ProvidersProps) {
  const googleClientId = process.env.NEXT_PUBLIC_GOOGLE_CLIENT_ID || '';

  return (
    <GoogleOAuthProvider clientId={googleClientId}>
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
    </GoogleOAuthProvider>
  );
}

