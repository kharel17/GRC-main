export type UserRole = 'admin' | 'analyst' | 'manager';

export interface UserProfile {
  id: string;
  email: string;
  fullName: string;
  role: UserRole;
  department?: string;
  createdAt: string;
  updatedAt: string;
}

export interface AuthState {
  user: UserProfile | null;
  isLoading: boolean;
  error: string | null;
}
