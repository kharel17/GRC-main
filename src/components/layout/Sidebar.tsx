'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import {
  BarChart3,
  AlertTriangle,
  Shield,
  FileText,
  CheckCircle2,
  Clock,
  Settings,
  LogOut,
  Menu,
  X,
  Users,
} from 'lucide-react';
import { useState, useEffect } from 'react';
import { Button } from '@/components/ui/button';
import { useAuth } from '@/hooks/useAuth';
import { UserRole } from '@/types/user';

// =============================================================================
// Navigation Configuration
// Centralized menu config for easy scalability
// =============================================================================

interface NavItem {
  href: string;
  label: string;
  icon: React.ElementType;
  roles: UserRole[];
}

const NAV_ITEMS: NavItem[] = [
  { 
    href: '/dashboard', 
    label: 'Dashboard', 
    icon: BarChart3, 
    roles: ['admin', 'analyst', 'manager'] 
  },
  { 
    href: '/dashboard/risks', 
    label: 'Risks', 
    icon: AlertTriangle, 
    roles: ['admin', 'analyst'] 
  },
  { 
    href: '/dashboard/controls', 
    label: 'Controls', 
    icon: Shield, 
    roles: ['admin', 'analyst'] 
  },
  { 
    href: '/dashboard/evidence', 
    label: 'Evidence', 
    icon: FileText, 
    roles: ['admin', 'analyst'] 
  },
  { 
    href: '/dashboard/audits', 
    label: 'Audit Log', 
    icon: Clock, 
    roles: ['admin', 'manager'] 
  },
  { 
    href: '/dashboard/reports', 
    label: 'Reports', 
    icon: CheckCircle2, 
    roles: ['admin', 'analyst', 'manager'] 
  },
];

const ADMIN_NAV_ITEMS: NavItem[] = [
  { 
    href: '/dashboard/users', 
    label: 'Users', 
    icon: Users, 
    roles: ['admin'] 
  },
  { 
    href: '/dashboard/settings', 
    label: 'Settings', 
    icon: Settings, 
    roles: ['admin'] 
  },
];

// =============================================================================
// Component
// =============================================================================

export function Sidebar() {
  const pathname = usePathname();
  const { user, logout } = useAuth();
  const [isOpen, setIsOpen] = useState(false);

  // Close sidebar on route change
  useEffect(() => {
    setIsOpen(false);
  }, [pathname]);

  // Prevent body scroll when sidebar is open on mobile
  useEffect(() => {
    if (isOpen) {
      document.body.style.overflow = 'hidden';
    } else {
      document.body.style.overflow = '';
    }
    return () => {
      document.body.style.overflow = '';
    };
  }, [isOpen]);

  // Filter nav items based on user role
  const userRole = user?.role || 'manager';
  const visibleItems = NAV_ITEMS.filter((item) => item.roles.includes(userRole));
  const visibleAdminItems = ADMIN_NAV_ITEMS.filter((item) => item.roles.includes(userRole));

  const isActive = (href: string) => {
    if (href === '/dashboard') {
      return pathname === href;
    }
    return pathname === href || pathname.startsWith(href + '/');
  };

  const handleLogout = () => {
    // Clear cookie for middleware
    document.cookie = 'grc_access_token=; path=/; max-age=0';
    logout();
  };

  const closeSidebar = () => setIsOpen(false);

  return (
    <>
      {/* Mobile Menu Toggle Button */}
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="fixed top-4 left-4 z-50 md:hidden p-2.5 bg-white hover:bg-slate-100 rounded-lg shadow-sm border border-slate-200 transition-colors"
        aria-label={isOpen ? 'Close menu' : 'Open menu'}
      >
        {isOpen ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
      </button>

      {/* Backdrop Overlay (mobile only) */}
      {isOpen && (
        <div
          className="fixed inset-0 bg-black/50 z-30 md:hidden transition-opacity"
          onClick={closeSidebar}
          aria-hidden="true"
        />
      )}

      {/* Sidebar */}
      <aside
        className={`${
          isOpen ? 'translate-x-0' : '-translate-x-full'
        } md:translate-x-0 fixed left-0 top-0 h-screen w-64 bg-white border-r border-slate-200 transition-transform duration-300 ease-in-out z-40 flex flex-col shadow-lg md:shadow-none`}
      >
        <div className="p-6 border-b border-slate-200">
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 bg-blue-600 rounded-lg flex items-center justify-center">
              <span className="text-white font-bold text-sm">GRC</span>
            </div>
            <span className="font-semibold text-lg text-slate-900">GRC Platform</span>
          </div>
          {/* Role indicator */}
          <div className="mt-2">
            <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium ${
              userRole === 'admin' 
                ? 'bg-blue-100 text-blue-700' 
                : userRole === 'analyst' 
                  ? 'bg-green-100 text-green-700' 
                  : 'bg-purple-100 text-purple-700'
            }`}>
              {userRole.charAt(0).toUpperCase() + userRole.slice(1)}
            </span>
          </div>
        </div>

        <nav className="flex-1 p-4 space-y-1 overflow-y-auto">
          {visibleItems.map((item) => {
            const Icon = item.icon;
            const active = isActive(item.href);

            return (
              <Link
                key={item.href}
                href={item.href}
                onClick={closeSidebar}
                className={`flex items-center gap-3 px-4 py-3.5 rounded-lg transition-all duration-200 min-h-[48px] ${
                  active
                    ? 'bg-blue-50 text-blue-600 font-medium shadow-sm'
                    : 'text-slate-600 hover:bg-slate-50 hover:text-slate-900 active:bg-slate-100'
                }`}
              >
                <Icon className="h-5 w-5 flex-shrink-0" />
                <span className="text-sm">{item.label}</span>
              </Link>
            );
          })}

          {/* Admin section separator */}
          {visibleAdminItems.length > 0 && (
            <>
              <div className="pt-4 pb-2">
                <p className="px-4 text-xs font-semibold text-slate-400 uppercase tracking-wider">
                  Administration
                </p>
              </div>
              {visibleAdminItems.map((item) => {
                const Icon = item.icon;
                const active = isActive(item.href);

                return (
                  <Link
                    key={item.href}
                    href={item.href}
                    onClick={closeSidebar}
                    className={`flex items-center gap-3 px-4 py-3.5 rounded-lg transition-all duration-200 min-h-[48px] ${
                      active
                        ? 'bg-blue-50 text-blue-600 font-medium shadow-sm'
                        : 'text-slate-600 hover:bg-slate-50 hover:text-slate-900 active:bg-slate-100'
                    }`}
                  >
                    <Icon className="h-5 w-5 flex-shrink-0" />
                    <span className="text-sm">{item.label}</span>
                  </Link>
                );
              })}
            </>
          )}
        </nav>

        <div className="p-4 border-t border-slate-200">
          <Button
            onClick={handleLogout}
            variant="ghost"
            className="w-full justify-start text-slate-600 hover:bg-red-50 hover:text-red-600 py-3.5 min-h-[48px] active:bg-red-100"
          >
            <LogOut className="h-5 w-5 mr-3 flex-shrink-0" />
            <span className="text-sm">Logout</span>
          </Button>
        </div>
      </aside>
    </>
  );
}