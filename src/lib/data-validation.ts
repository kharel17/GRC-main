
import { ISOControl, ISOEvidence } from '@/types/iso27001';
import { UserRole } from '@/types/user';

export const MAX_FILE_SIZE = 10 * 1024 * 1024; // 10MB
export const ALLOWED_FILE_TYPES = ['application/pdf', 'application/msword', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document', 'image/png', 'image/jpeg'];

export class DataValidator {
  
  static validateEvidence(file: File): { valid: boolean; error?: string } {
    if (file.size > MAX_FILE_SIZE) {
      return { valid: false, error: `File size exceeds limit of ${MAX_FILE_SIZE / (1024 * 1024)}MB` };
    }
    if (!ALLOWED_FILE_TYPES.includes(file.type)) {
      return { valid: false, error: 'Invalid file type. Allowed: PDF, DOCX, PNG, JPG' };
    }
    return { valid: true };
  }

  static validateControlUpdate(control: ISOControl, userRole: UserRole): { valid: boolean; error?: string } {
    // Basic integrity check
    if (!control.id || !control.title) {
      return { valid: false, error: 'Control ID and Title are required' };
    }

    // Role-based validation for status changes
    if (userRole === 'department_manager' && control.status !== 'not_started') { // Example restriction
       // Managers can view reports but typically don't update controls?
       // Based on table: Manager cannot update status.
       return { valid: false, error: 'Managers cannot update control status' };
    }

    return { valid: true };
  }

  static canUploadEvidence(userRole: UserRole): boolean {
    return ['admin', 'analyst'].includes(userRole);
  }

  static canUpdateControl(userRole: UserRole): boolean {
    return ['admin', 'analyst'].includes(userRole);
  }

  static canManageFramework(userRole: UserRole): boolean {
    return userRole === 'admin';
  }
}
