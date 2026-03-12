import { ApiError } from './api-client';

/**
 * Provides user-friendly error messages based on API responses or unexpected errors.
 * Designed to be used in form catch blocks.
 */
export function handleApiError(error: unknown): string {
  if (error instanceof ApiError) {
    if (error.status === 401) {
      return 'Session expired. Please log in again.';
    }
    if (error.status === 403) {
      return 'You do not have permission to perform this action.';
    }
    if (error.status === 422) {
      return 'Please check your form for errors and try again.';
    }
    if (error.status >= 500) {
      return 'Server error. Please try again shortly.';
    }
    // Return custom backend message if provided, otherwise generic HTTP error
    return error.message;
  }
  
  if (error instanceof Error) {
    // If it's a network error fetch throws TypeError typically
    if (error.name === 'TypeError' || error.message.includes('fetch')) {
      return 'Network error. Please check your connection and try again.';
    }
    if (error.name === 'AbortError') {
      return 'Request timed out. Please try again.';
    }
    return error.message;
  }
  
  return 'An unexpected error occurred.';
}
