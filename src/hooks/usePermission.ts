import { useAuth } from './useAuth';
import { PERMISSIONS } from '@/lib/permissions';

export function usePermission(permission: keyof typeof PERMISSIONS) {
  const { user } = useAuth();
  const role = user?.role || 'analyst';
  
  return PERMISSIONS[permission]?.includes(role) ?? false;
}
