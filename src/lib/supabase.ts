import { createClient } from '@supabase/supabase-js';

const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL;
const supabaseKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY;


if (!supabaseUrl || !supabaseKey) {
  console.error('Missing Supabase environment variables:', {
    url: !!supabaseUrl,
    key: !!supabaseKey,
  });
  throw new Error(
    'Supabase URL and Anon Key are required. Please check your .env file and ensure NEXT_PUBLIC_SUPABASE_URL and NEXT_PUBLIC_SUPABASE_ANON_KEY are set.'
  );
}

export const supabase = createClient(supabaseUrl, supabaseKey, {
  auth: {
    // Store the session in localStorage so it survives page refreshes
    // and local dev-server restarts (lives in browser, not the server).
    persistSession: true,
    // Automatically refresh the access token before it expires.
    // Supabase access tokens expire in 1h; refresh tokens last 7 days.
    // This means you only need to log in once per week during development.
    autoRefreshToken: true,
    // Detect and handle OAuth callback tokens from the URL hash.
    detectSessionInUrl: true,
    // Use a consistent storage key so all tabs share the same session.
    storageKey: 'grc-platform-session',
  },
});
