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
  ChevronUp,
  ChevronDown,
} from 'lucide-react';
import { useState, useEffect } from 'react';
import { useAuth } from '@/hooks/useAuth';
import { UserRole } from '@/types';
import { Avatar, AvatarFallback } from '@/components/ui/avatar';

// =============================================================================
// Navigation Configuration — Grouped Sections
// =============================================================================

interface NavItem {
  href: string;
  label: string;
  icon: React.ElementType;
  roles: UserRole[];
  /** Optional badge dot colour shown on the nav item */
  badge?: 'red' | 'yellow' | 'green';
}

interface NavGroup {
  label: string;
  items: NavItem[];
}

/** Grouped nav sections rendered in collapsible blocks */
const NAV_GROUPS: NavGroup[] = [
  {
    label: 'MANAGE',
    items: [
      {
        href: '/dashboard/organization',
        label: 'Organization',
        icon: Building2,
        roles: ['admin', 'manager'],
      },
      {
        href: '/dashboard/assets',
        label: 'Assets',
        icon: Boxes,
        roles: ['admin', 'manager', 'analyst'],
      },
      {
        href: '/dashboard/risks',
        label: 'Risks',
        icon: AlertTriangle,
        roles: ['admin', 'manager', 'analyst'],
      },
      {
        href: '/dashboard/controls',
        label: 'Controls',
        icon: Shield,
        roles: ['admin', 'manager', 'analyst'],
      },
      {
        href: '/dashboard/tickets',
        label: 'Tickets',
        icon: Ticket,
        roles: ['admin', 'manager', 'analyst'],
      },
    ],
  },
  {
    label: 'COMPLY',
    items: [
      {
        href: '/dashboard/iso27001',
        label: 'ISO 27001',
        icon: ShieldCheck,
        roles: ['admin', 'manager', 'analyst'],
      },
      {
        href: '/dashboard/gap-analysis',
        label: 'Gap Analysis',
        icon: PieChart,
        roles: ['admin', 'manager', 'analyst'],
      },
      {
        href: '/dashboard/evidence',
        label: 'Evidence',
        icon: FileText,
        roles: ['admin', 'manager', 'analyst'],
      },
    ],
  },
  {
    label: 'AUDIT',
    items: [
      {
        href: '/dashboard/audit-preparation',
        label: 'Audit Prep',
        icon: ClipboardCheck,
        roles: ['admin', 'manager', 'analyst'],
      },
      {
        href: '/dashboard/document-analysis',
        label: 'Doc Analysis',
        icon: Microscope,
        roles: ['admin', 'manager', 'analyst'],
      },
      {
        href: '/dashboard/audits',
        label: 'Audit Log',
        icon: Clock,
        roles: ['admin', 'manager'],
      },
      {
        href: '/dashboard/reports',
        label: 'Reports',
        icon: CheckCircle2,
        roles: ['admin', 'manager', 'analyst'],
      },
    ],
  },
];

/** Admin-only items above the user profile card */
const ADMIN_NAV_ITEMS: NavItem[] = [
  {
    href: '/dashboard/users',
    label: 'Users',
    icon: Users,
    roles: ['admin', 'superadmin'],
  },
  {
    href: '/dashboard/settings',
    label: 'Settings',
    icon: Settings,
    roles: ['admin', 'superadmin'],
  },
];

// =============================================================================
// Helpers
// =============================================================================

const ROLE_LABELS: Record<string, string> = {
  superadmin: 'Super Admin',
  admin: 'Admin',
  manager: 'Manager',
  analyst: 'Analyst',
};

const BADGE_CLASSES: Record<string, string> = {
  red: 'bg-destructive',
  yellow: 'bg-yellow-500',
  green: 'bg-emerald-500',
};

// =============================================================================
// Component
// =============================================================================

export function Sidebar() {
  const pathname = usePathname();
  const { user, logout } = useAuth();
  const [isOpen, setIsOpen] = useState(false);

  // All groups open by default
  const [collapsedGroups, setCollapsedGroups] = useState<Record<string, boolean>>({});

  // ── Close on route change (mobile) ──────────────────────────────────────────
  useEffect(() => {
    setIsOpen(false);
  }, [pathname]);

  // ── Lock body scroll when mobile drawer is open ──────────────────────────────
  useEffect(() => {
    document.body.style.overflow = isOpen ? 'hidden' : '';
    return () => {
      document.body.style.overflow = '';
    };
  }, [isOpen]);

  // ── Derived state ────────────────────────────────────────────────────────────
  const userRole = (user?.role as UserRole) || 'analyst';

  const isActive = (href: string) => {
    if (href === '/dashboard') return pathname === href;
    return pathname === href || pathname.startsWith(href + '/');
  };

  const toggleGroup = (label: string) =>
    setCollapsedGroups((prev) => ({ ...prev, [label]: !prev[label] }));

  const handleLogout = () => {
    document.cookie = 'grc_access_token=; path=/; max-age=0';
    logout();
  };

  const closeSidebar = () => setIsOpen(false);

  // ── User display ─────────────────────────────────────────────────────────────
  const rawName = (user as any)?.fullName || user?.email?.split('@')[0] || 'User';
  const displayName = rawName.charAt(0).toUpperCase() + rawName.slice(1);
  const initials = rawName
    .split(/[\s._-]/)
    .map((n: string) => n[0] ?? '')
    .join('')
    .toUpperCase()
    .slice(0, 2);

  // ── Render ───────────────────────────────────────────────────────────────────
  return (
    <>
      {/* ── Mobile hamburger ─────────────────────────────────────────────── */}
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="fixed top-4 left-4 z-50 md:hidden p-2.5 bg-background hover:bg-muted rounded-lg shadow-sm border border-border transition-colors"
        aria-label={isOpen ? 'Close menu' : 'Open menu'}
      >
        {isOpen ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
      </button>

      {/* ── Backdrop (mobile) ─────────────────────────────────────────────── */}
      {isOpen && (
        <div
          className="fixed inset-0 bg-black/70 z-30 md:hidden"
          onClick={closeSidebar}
          aria-hidden="true"
        />
      )}

      {/* ── Sidebar shell ─────────────────────────────────────────────────── */}
      <aside
        className={`
          ${isOpen ? 'translate-x-0' : '-translate-x-full'}
          md:translate-x-0
          fixed left-0 top-0 h-screen w-64
          flex flex-col
          transition-transform duration-300 ease-in-out
          z-40
          bg-card border-r border-border
          shadow-xl md:shadow-none
        `}
      >
        {/* ── Logo ──────────────────────────────────────────────────────── */}
        <div className="h-16 flex items-center gap-3 px-5 border-b border-border flex-shrink-0">
          <Link
            href="/dashboard"
            className="flex items-center gap-2.5 group"
            onClick={closeSidebar}
          >
            <div className="w-8 h-8 rounded-lg bg-primary flex items-center justify-center flex-shrink-0 shadow-sm group-hover:opacity-90 transition-opacity">
              <Shield className="w-4 h-4 text-primary-foreground" />
            </div>
            <span className="font-bold text-[17px] tracking-tight text-foreground select-none">
              GRC<span className="text-primary">Guard</span>
            </span>
          </Link>
        </div>

        {/* ── Scrollable nav body ───────────────────────────────────────── */}
        <nav className="flex-1 overflow-y-auto py-4 px-2.5 space-y-1 scrollbar-hide">

          {/* Dashboard — standalone hero item */}
          <Link
            href="/dashboard"
            onClick={closeSidebar}
            className={`
              flex items-center gap-3 px-3 py-2.5 rounded-lg
              transition-all duration-200 mb-3 group
              ${
                isActive('/dashboard')
                  ? 'bg-foreground text-background font-semibold shadow-sm'
                  : 'text-muted-foreground hover:bg-muted/70 hover:text-foreground'
              }
            `}
          >
            <BarChart3 className="h-[17px] w-[17px] flex-shrink-0" />
            <span className="text-sm">Dashboard</span>
          </Link>

          {/* Grouped sections */}
          {NAV_GROUPS.map((group) => {
            const visibleItems = group.items.filter((item) =>
              item.roles.includes(userRole),
            );
            if (visibleItems.length === 0) return null;

            const collapsed = !!collapsedGroups[group.label];

            return (
              <div key={group.label}>
                {/* Group header / toggle */}
                <button
                  onClick={() => toggleGroup(group.label)}
                  className="w-full flex items-center justify-between px-3 py-1.5 mb-0.5 rounded-md hover:bg-muted/40 transition-colors group/hdr"
                >
                  <span className="text-[10px] font-bold tracking-widest text-muted-foreground/60 uppercase select-none">
                    {group.label}
                  </span>
                  {collapsed ? (
                    <ChevronDown className="h-3 w-3 text-muted-foreground/40 group-hover/hdr:text-muted-foreground transition-colors" />
                  ) : (
                    <ChevronUp className="h-3 w-3 text-muted-foreground/40 group-hover/hdr:text-muted-foreground transition-colors" />
                  )}
                </button>

                {/* Group items */}
                {!collapsed && (
                  <div className="space-y-0.5 mb-2">
                    {visibleItems.map((item) => {
                      const Icon = item.icon;
                      const active = isActive(item.href);

                      return (
                        <Link
                          key={item.href}
                          href={item.href}
                          onClick={closeSidebar}
                          className={`
                            flex items-center gap-3 px-3 py-2.5 rounded-lg
                            transition-all duration-150
                            ${
                              active
                                ? 'bg-primary/10 text-primary font-medium'
                                : 'text-muted-foreground hover:bg-muted/70 hover:text-foreground'
                            }
                          `}
                        >
                          <Icon className="h-[16px] w-[16px] flex-shrink-0" />
                          <span className="text-sm flex-1 leading-none">{item.label}</span>

                          {/* Notification dot */}
                          {item.badge && (
                            <span
                              className={`w-[7px] h-[7px] rounded-full flex-shrink-0 ${BADGE_CLASSES[item.badge]}`}
                            />
                          )}
                        </Link>
                      );
                    })}
                  </div>
                )}
              </div>
            );
          })}
        </nav>

        {/* ── Bottom pinned area ────────────────────────────────────────── */}
        <div className="flex-shrink-0 border-t border-border">

          {/* Admin items (Users, Settings) */}
          {(() => {
            const adminVisible = ADMIN_NAV_ITEMS.filter((item) =>
              item.roles.includes(userRole),
            );
            if (adminVisible.length === 0) return null;
            return (
              <div className="px-2.5 pt-3 pb-1 space-y-0.5">
                {adminVisible.map((item) => {
                  const Icon = item.icon;
                  const active = isActive(item.href);
                  return (
                    <Link
                      key={item.href}
                      href={item.href}
                      onClick={closeSidebar}
                      className={`
                        flex items-center gap-3 px-3 py-2.5 rounded-lg
                        transition-all duration-150
                        ${
                          active
                            ? 'bg-primary/10 text-primary font-medium'
                            : 'text-muted-foreground hover:bg-muted/70 hover:text-foreground'
                        }
                      `}
                    >
                      <Icon className="h-[16px] w-[16px] flex-shrink-0" />
                      <span className="text-sm">{item.label}</span>
                    </Link>
                  );
                })}
              </div>
            );
          })()}

          {/* User profile card */}
          <div className="p-3">
            <div className="flex items-center gap-3 px-3 py-2.5 rounded-lg hover:bg-muted/60 transition-colors group/profile cursor-default">
              {/* Avatar */}
              <Avatar className="h-8 w-8 flex-shrink-0">
                <AvatarFallback className="bg-primary text-primary-foreground text-xs font-semibold">
                  {initials}
                </AvatarFallback>
              </Avatar>

              {/* Name + role */}
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium text-foreground leading-tight truncate">
                  {displayName}
                </p>
                <p className="text-xs text-muted-foreground leading-tight truncate mt-0.5">
                  {ROLE_LABELS[userRole] ?? userRole}
                </p>
              </div>

              {/* Logout — revealed on hover */}
              <button
                onClick={handleLogout}
                title="Logout"
                aria-label="Logout"
                className="
                  opacity-0 group-hover/profile:opacity-100
                  transition-opacity duration-150
                  p-1.5 rounded-md
                  text-muted-foreground
                  hover:bg-destructive/10 hover:text-destructive
                "
              >
                <LogOut className="h-3.5 w-3.5" />
              </button>
            </div>
          </div>

        </div>
      </aside>
    </>
  );
}