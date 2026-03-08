/**
 * GRC Platform — API Client
 * 
 * Centralized HTTP client for all backend API calls.
 * Handles JWT injection, token refresh, and error mapping.
 * 
 * Set NEXT_PUBLIC_API_URL in .env.local to point to the backend.
 * Set NEXT_PUBLIC_USE_MOCK=true to bypass API and use mock data.
 */

import { getTokens, clearTokens } from './auth';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';
const USE_MOCK = process.env.NEXT_PUBLIC_USE_MOCK === 'true';

export class ApiError extends Error {
  constructor(public status: number, message: string, public body?: unknown) {
    super(message);
    this.name = 'ApiError';
  }
}

interface RequestOptions extends Omit<RequestInit, 'body'> {
  body?: unknown;
  skipAuth?: boolean;
}

/**
 * Make an authenticated API request.
 */
async function request<T>(endpoint: string, options: RequestOptions = {}): Promise<T> {
  const { body, skipAuth = false, headers: extraHeaders, ...rest } = options;

  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(extraHeaders as Record<string, string> || {}),
  };

  // Inject JWT
  if (!skipAuth) {
    const tokens = getTokens();
    if (tokens?.accessToken) {
      headers['Authorization'] = `Bearer ${tokens.accessToken}`;
    }
  }

  const response = await fetch(`${API_BASE_URL}${endpoint}`, {
    ...rest,
    headers,
    credentials: 'include',
    body: body ? JSON.stringify(body) : undefined,
  });

  // Handle 401 — attempt token refresh
  if (response.status === 401) {
    if (skipAuth || endpoint === '/auth/refresh' || endpoint === '/auth/login') {
      clearTokens();
      if (typeof window !== 'undefined' && endpoint !== '/auth/login') {
        window.location.href = '/login';
      }
      throw new ApiError(401, 'Unauthorized');
    }

    try {
      // Import refresh function dynamically to avoid circular dependencies
      const { refreshAccessToken } = await import('./auth');
      const refreshed = await refreshAccessToken();

      if (refreshed) {
        // Retry the original request with the new token
        const newHeaders = { ...headers, 'Authorization': `Bearer ${refreshed.accessToken}` };
        const retryResponse = await fetch(`${API_BASE_URL}${endpoint}`, {
          ...rest,
          headers: newHeaders,
          credentials: 'include',
          body: body ? JSON.stringify(body) : undefined,
        });

        if (retryResponse.ok) {
          return retryResponse.json() as Promise<T>;
        }
      }
    } catch (refreshError) {
      console.error('[API] Refresh failed:', refreshError);
    }

    // If refresh failed or wasn't possible, log out
    clearTokens();
    if (typeof window !== 'undefined') {
      window.location.href = '/login';
    }
    throw new ApiError(401, 'Unauthorized');
  }

  if (!response.ok) {
    let errorBody: unknown;
    try {
      errorBody = await response.json();
    } catch {
      errorBody = await response.text();
    }
    throw new ApiError(
      response.status,
      (errorBody as { detail?: string })?.detail || `HTTP ${response.status}`,
      errorBody,
    );
  }

  // Handle 204 No Content
  if (response.status === 204) {
    return undefined as T;
  }

  return response.json() as Promise<T>;
}

/**
 * Upload a file via multipart/form-data.
 */
async function uploadFile<T>(endpoint: string, file: File, fields?: Record<string, string>): Promise<T> {
  const formData = new FormData();
  formData.append('file', file);
  if (fields) {
    Object.entries(fields).forEach(([key, value]) => formData.append(key, value));
  }

  const headers: Record<string, string> = {};
  // Auth is via httpOnly cookies — no need for Bearer header
  // Do NOT set Content-Type — browser sets it with boundary for multipart

  const response = await fetch(`${API_BASE_URL}${endpoint}`, {
    method: 'POST',
    headers,
    credentials: 'include',
    body: formData,
  });

  if (!response.ok) {
    const errorBody = await response.json().catch(() => ({}));
    throw new ApiError(response.status, (errorBody as { detail?: string }).detail || `Upload failed`, errorBody);
  }

  return response.json() as Promise<T>;
}

// ── Convenience Methods ────────────────────────────────────

export const api = {
  get: <T>(endpoint: string, options?: RequestOptions) =>
    request<T>(endpoint, { ...options, method: 'GET' }),

  post: <T>(endpoint: string, body?: unknown, options?: RequestOptions) =>
    request<T>(endpoint, { ...options, method: 'POST', body }),

  put: <T>(endpoint: string, body?: unknown, options?: RequestOptions) =>
    request<T>(endpoint, { ...options, method: 'PUT', body }),

  delete: <T>(endpoint: string, options?: RequestOptions) =>
    request<T>(endpoint, { ...options, method: 'DELETE' }),

  upload: <T>(endpoint: string, file: File, fields?: Record<string, string>) =>
    uploadFile<T>(endpoint, file, fields),

  /** Whether mock mode is enabled */
  isMock: USE_MOCK,

  /** The base URL for direct use */
  baseUrl: API_BASE_URL,
};
