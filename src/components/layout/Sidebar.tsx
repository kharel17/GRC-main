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
  ShieldCheck,
  Ticket,
  Building2,
  Boxes,
  Microscope,
  PieChart,
  ClipboardCheck,
} from 'lucide-react';
import { useState, useEffect } from 'react';
import { Button } from '@/components/ui/button';
import { useAuth } from '@/hooks/useAuth';
import { UserRole } from '@/types';

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
    roles: ['admin', 'manager', 'analyst'] 
  },
  { 
    href: '/dashboard/organization', 
    label: 'Organization', 
    icon: Building2, 
    roles: ['admin', 'manager'] 
  },
  { 
    href: '/dashboard/assets', 
    label: 'Assets', 
    icon: Boxes, 
    roles: ['admin', 'manager', 'analyst'] 
  },
  { 
    href: '/dashboard/risks', 
    label: 'Risks', 
    icon: AlertTriangle, 
    roles: ['admin', 'manager', 'analyst'] 
  },
  { 
    href: '/dashboard/controls', 
    label: 'Controls', 
    icon: Shield, 
    roles: ['admin', 'manager', 'analyst'] 
  },
  { 
    href: '/dashboard/iso27001', 
    label: 'ISO 27001', 
    icon: ShieldCheck, 
    roles: ['admin', 'manager', 'analyst'] 
  },
  { 
    href: '/dashboard/evidence', 
    label: 'Evidence', 
    icon: FileText, 
    roles: ['admin', 'manager', 'analyst'] 
  },
  { 
    href: '/dashboard/document-analysis', 
    label: 'Doc Analysis', 
    icon: Microscope, 
    roles: ['admin', 'manager', 'analyst'] 
  },
  { 
    href: '/dashboard/gap-analysis', 
    label: 'Gap Analysis', 
    icon: PieChart, 
    roles: ['admin', 'manager', 'analyst'] 
  },
  { 
    href: '/dashboard/audit-preparation', 
    label: 'Audit Prep', 
    icon: ClipboardCheck, 
    roles: ['admin', 'manager'] 
  },
  { 
    href: '/dashboard/tickets', 
    label: 'Tickets', 
    icon: Ticket, 
    roles: ['admin', 'manager', 'analyst'] 
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
    roles: ['admin', 'manager', 'analyst'] 
  },
];

const ADMIN_NAV_ITEMS: NavItem[] = [
  { 
    href: '/dashboard/users', 
    label: 'Users', 
    icon: Users, 
    roles: ['admin', 'superadmin'] 
  },
  { 
    href: '/dashboard/settings', 
    label: 'Settings', 
    icon: Settings, 
    roles: ['admin', 'superadmin'] 
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
  const userRole = user?.role || 'analyst';
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

  // Role badge color mapping
  const getRoleBadgeStyle = (role: UserRole): string => {
    const styles: Record<string, string> = {
      superadmin: 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-300',
      admin: 'bg-purple-100 text-purple-700 dark:bg-purple-900/30 dark:text-purple-300',
      manager: 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300',
      analyst: 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-300',
    };
    return styles[role] || styles.analyst;
  };

  // Human-readable role label
  const getRoleLabel = (role: UserRole): string => {
    const labels: Record<string, string> = {
      superadmin: 'Super Admin',
      admin: 'Administrator',
      manager: 'Manager',
      analyst: 'Risk Analyst',
    };
    return labels[role] || role;
  };


  return (
    <>
      {/* Mobile Menu Toggle Button */}
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="fixed top-4 left-4 z-50 md:hidden p-2.5 bg-background hover:bg-muted rounded-lg shadow-sm border border-border transition-colors"
        aria-label={isOpen ? 'Close menu' : 'Open menu'}
      >
        {isOpen ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
      </button>

      {/* Backdrop Overlay (mobile only) */}
      {isOpen && (
        <div
          className="fixed inset-0 bg-black/80 z-30 md:hidden transition-opacity"
          onClick={closeSidebar}
          aria-hidden="true"
        />
      )}

      {/* Sidebar */}
      <aside
        className={`${
          isOpen ? 'translate-x-0' : '-translate-x-full'
        } md:translate-x-0 fixed left-0 top-0 h-screen w-64 transition-transform duration-300 ease-in-out z-40 shadow-lg md:shadow-none bg-card border-r border-border`}
      >
        <div className="h-full flex flex-col">
          {/* Logo */}
          <div className="h-16 flex items-center px-6 border-b border-border">
            <Link href="/dashboard" className="flex items-center gap-2">
              <div className="w-8 h-8 rounded-lg bg-primary flex items-center justify-center">
                <Shield className="w-5 h-5 text-primary-foreground" />
              </div>
              <span className="font-bold text-xl tracking-tight text-foreground">
                GRC<span className="text-primary">Guard</span>
              </span>
            </Link>
          </div>
          {/* Role indicator */}
          <div className="p-6 border-b border-border">
            <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium ${getRoleBadgeStyle(userRole)}`}>
              {getRoleLabel(userRole)}
            </span>
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
                      ? 'bg-primary/10 text-primary font-medium shadow-sm'
                      : 'text-muted-foreground hover:bg-muted/50 hover:text-foreground active:bg-muted'
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
                  <p className="px-4 text-xs font-semibold text-muted-foreground uppercase tracking-wider">
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
                          ? 'bg-primary/10 text-primary font-medium shadow-sm'
                          : 'text-muted-foreground hover:bg-muted/50 hover:text-foreground active:bg-muted'
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
  
          <div className="p-4 border-t border-border">
            <Button
              onClick={handleLogout}
              variant="ghost"
              className="w-full justify-start text-muted-foreground hover:bg-destructive/10 hover:text-destructive py-3.5 min-h-[48px] active:bg-destructive/20"
            >
              <LogOut className="h-5 w-5 mr-3 flex-shrink-0" />
              <span className="text-sm">Logout</span>
            </Button>
          </div>
        </div>
      </aside>
    </>
  );
}