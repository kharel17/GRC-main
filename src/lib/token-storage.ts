
const TOKEN_KEY = 'grc_tokens';
const USER_KEY = 'grc_user';

export function clearTokens(): void {
    if (typeof window === 'undefined') return;
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(USER_KEY);
}

export function setTokens(tokens: any): void {
    if (typeof window === 'undefined') return;
    localStorage.setItem(TOKEN_KEY, JSON.stringify(tokens));
}

export function getTokens(): any | null {
    if (typeof window === 'undefined') return null;
    const stored = localStorage.getItem(TOKEN_KEY);
    if (!stored) return null;
    try {
        return JSON.parse(stored);
    } catch {
        return null;
    }
}
