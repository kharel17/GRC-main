export type UserRole =
  | 'admin'
  | 'manager'
  | 'analyst'
  | 'control_owner'
  | 'risk_owner'
  | 'compliance_officer'
  | 'department_manager'
  | 'executive'
  | 'auditor';

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
