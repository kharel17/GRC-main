const TOKEN_KEY = 'grc_tokens';
const USER_KEY = 'grc_user';

export function clearTokens(): void {
  if (typeof window === 'undefined') return;
  localStorage.removeItem(TOKEN_KEY);
  localStorage.removeItem(USER_KEY);
  localStorage.removeItem('access_token');
}

export function setTokens(tokens: any): void {
  if (typeof window === 'undefined') return;
  localStorage.setItem(TOKEN_KEY, JSON.stringify(tokens));
  if (tokens?.accessToken || tokens?.access_token) {
    localStorage.setItem('access_token', tokens.accessToken || tokens.access_token);
  }
}

export function getTokens(): any | null {
  if (typeof window === 'undefined') return null;
  const stored = localStorage.getItem(TOKEN_KEY);
  if (!stored) {
    const rawAccessToken = localStorage.getItem('access_token');
    if (rawAccessToken) {
      return { accessToken: rawAccessToken, access_token: rawAccessToken };
    }
    return null;
  }
  try {
    return JSON.parse(stored);
  } catch {
    return null;
  }
}

export function getAccessToken(): string | null {
  if (typeof window === 'undefined') return null;
  const tokens = getTokens();
  if (tokens?.accessToken) return tokens.accessToken;
  if (tokens?.access_token) return tokens.access_token;
  return localStorage.getItem('access_token') || null;
}

export function setAccessToken(token: string): void {
  if (typeof window === 'undefined') return;
  const tokens = getTokens() || {};
  tokens.accessToken = token;
  tokens.access_token = token;
  setTokens(tokens);
}

export function setUser(user: any): void {
  if (typeof window === 'undefined') return;
  localStorage.setItem(USER_KEY, JSON.stringify(user));
}

export function getUser(): any | null {
  if (typeof window === 'undefined') return null;
  const stored = localStorage.getItem(USER_KEY);
  if (!stored) return null;
  try {
    return JSON.parse(stored);
  } catch {
    return null;
  }
}
