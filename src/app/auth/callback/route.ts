import { createClient } from '@supabase/supabase-js';
import { NextRequest, NextResponse } from 'next/server';

/**
 * OAuth Callback Handler
 * 
 * This route handles the Supabase OAuth callback after the user authenticates with Google.
 * It processes the OAuth code and state, establishes the session, and redirects to the dashboard.
 */

export async function GET(request: NextRequest) {
  const { searchParams } = new URL(request.url);
  const code = searchParams.get('code');
  const state = searchParams.get('state');
  const error = searchParams.get('error');
  const errorDescription = searchParams.get('error_description');

  // Log the callback parameters for debugging
  console.log('[OAuth Callback] Received:', {
    code: code ? 'present' : 'missing',
    state: state ? 'present' : 'missing',
    error: error || 'none',
    url: request.url,
  });

  // Handle OAuth errors
  if (error) {
    console.error('[OAuth Callback] OAuth Error:', {
      error,
      error_description: errorDescription,
    });

    const redirectUrl = new URL('/login', request.url);
    redirectUrl.searchParams.set('error', error);
    redirectUrl.searchParams.set('error_description', errorDescription || 'OAuth authentication failed');
    return NextResponse.redirect(redirectUrl);
  }

  // Missing authorization code
  if (!code) {
    console.error('[OAuth Callback] Missing authorization code');
    const redirectUrl = new URL('/login', request.url);
    redirectUrl.searchParams.set('error', 'missing_code');
    redirectUrl.searchParams.set('error_description', 'Authorization code not received from OAuth provider');
    return NextResponse.redirect(redirectUrl);
  }

  try {
    // Initialize Supabase client with service role for token exchange
    const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL;
    const supabaseAnonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY;

    if (!supabaseUrl || !supabaseAnonKey) {
      throw new Error('Supabase configuration missing');
    }

    const supabase = createClient(supabaseUrl, supabaseAnonKey);

    // Exchange the code for a session using Supabase Auth
    // Supabase SDK handles state validation automatically
    const { data, error: sessionError } = await supabase.auth.exchangeCodeForSession(code);

    if (sessionError || !data.session) {
      console.error('[OAuth Callback] Session exchange failed:', sessionError?.message);
      const redirectUrl = new URL('/login', request.url);
      redirectUrl.searchParams.set('error', 'session_error');
      redirectUrl.searchParams.set('error_description', sessionError?.message || 'Failed to establish session');
      return NextResponse.redirect(redirectUrl);
    }

    // Session established successfully
    console.log('[OAuth Callback] Session established:', {
      user_id: data.session.user.id,
      email: data.session.user.email,
    });

    // Create response that redirects to dashboard
    const redirectUrl = new URL('/dashboard', request.url);
    const response = NextResponse.redirect(redirectUrl);

    // Note: The Supabase SDK handles setting auth cookies automatically
    // when using exchangeCodeForSession. However, we'll explicitly set them
    // to ensure they're captured in the response.
    if (data.session) {
      // Store session info in sessionStorage for the client
      // This will be picked up by the AuthContext when the page loads
      response.headers.set(
        'Set-Cookie',
        `supabase-auth-token=${data.session.access_token}; Path=/; HttpOnly; SameSite=Lax; ${process.env.NODE_ENV === 'production' ? 'Secure;' : ''}`
      );
    }

    return response;
  } catch (err) {
    console.error('[OAuth Callback] Unexpected error:', err instanceof Error ? err.message : String(err));
    const redirectUrl = new URL('/login', request.url);
    redirectUrl.searchParams.set('error', 'unknown_error');
    redirectUrl.searchParams.set('error_description', 'An unexpected error occurred during authentication');
    return NextResponse.redirect(redirectUrl);
  }
}
