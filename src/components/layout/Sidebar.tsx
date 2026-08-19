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
  PanelLeftClose,
  PanelLeftOpen,
} from 'lucide-react';
import { useState, useEffect } from 'react';
import { useAuth } from '@/hooks/useAuth';
import { UserRole } from '@/types';
import { Avatar, AvatarFallback } from '@/components/ui/avatar';
import { useLanguage } from '@/context/LanguageContext';
import { useSidebarCollapse } from '@/context/SidebarContext';

interface NavItem {
  href: string;
  labelKey: string;
  defaultLabel: string;
  icon: React.ElementType;
  roles: UserRole[];
  badge?: 'red' | 'yellow' | 'green';
}

interface NavGroup {
  labelKey: string;
  defaultLabel: string;
  items: NavItem[];
}

const NAV_GROUPS: NavGroup[] = [
  {
    labelKey: 'manage',
    defaultLabel: 'MANAGE',
    items: [
      { href: '/dashboard/organization', labelKey: 'organization', defaultLabel: 'Organization', icon: Building2, roles: ['admin', 'manager'] },
      { href: '/dashboard/assets', labelKey: 'assets', defaultLabel: 'Assets', icon: Boxes, roles: ['admin', 'manager', 'analyst'] },
      { href: '/dashboard/risks', labelKey: 'riskRegister', defaultLabel: 'Risks', icon: AlertTriangle, roles: ['admin', 'manager', 'analyst'] },
      { href: '/dashboard/controls', labelKey: 'controls', defaultLabel: 'Controls', icon: Shield, roles: ['admin', 'manager', 'analyst'] },
      { href: '/dashboard/tickets', labelKey: 'tickets', defaultLabel: 'Tickets', icon: Ticket, roles: ['admin', 'manager', 'analyst'] },
    ],
  },
  {
    labelKey: 'comply',
    defaultLabel: 'COMPLY',
    items: [
      { href: '/dashboard/iso27001', labelKey: 'iso27001', defaultLabel: 'ISO 27001', icon: ShieldCheck, roles: ['admin', 'manager', 'analyst'] },
      { href: '/dashboard/gap-analysis', labelKey: 'gapAnalysis', defaultLabel: 'Gap Analysis', icon: PieChart, roles: ['admin', 'manager', 'analyst'] },
      { href: '/dashboard/evidence', labelKey: 'evidence', defaultLabel: 'Evidence', icon: FileText, roles: ['admin', 'manager', 'analyst'] },
    ],
  },
  {
    labelKey: 'audit',
    defaultLabel: 'AUDIT',
    items: [
      { href: '/dashboard/audit-preparation', labelKey: 'auditPrep', defaultLabel: 'Audit Prep', icon: ClipboardCheck, roles: ['admin', 'manager', 'analyst'] },
      { href: '/dashboard/document-analysis', labelKey: 'docAnalysis', defaultLabel: 'Doc Analysis', icon: Microscope, roles: ['admin', 'manager', 'analyst'] },
      { href: '/dashboard/audits', labelKey: 'auditLog', defaultLabel: 'Audit Log', icon: Clock, roles: ['admin', 'manager'] },
      { href: '/dashboard/reports', labelKey: 'reports', defaultLabel: 'Reports', icon: CheckCircle2, roles: ['admin', 'manager', 'analyst'] },
    ],
  },
];

const ADMIN_NAV_ITEMS: NavItem[] = [
  { href: '/superadmin', labelKey: 'superadmin', defaultLabel: 'Super Admin', icon: Shield, roles: ['superadmin'] },
  { href: '/dashboard/users', labelKey: 'users', defaultLabel: 'Users', icon: Users, roles: ['admin', 'superadmin'] },
  { href: '/dashboard/settings', labelKey: 'settings', defaultLabel: 'Settings', icon: Settings, roles: ['admin', 'superadmin'] },
];

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

export function Sidebar() {
  const pathname = usePathname();
  const { user, logout } = useAuth();
  const { t } = useLanguage();
  const { collapsed, toggleCollapsed } = useSidebarCollapse();
  const [isMobileOpen, setIsMobileOpen] = useState(false);
  const [collapsedGroups, setCollapsedGroups] = useState<Record<string, boolean>>({});

  useEffect(() => { setIsMobileOpen(false); }, [pathname]);

  useEffect(() => {
    document.body.style.overflow = isMobileOpen ? 'hidden' : '';
    return () => { document.body.style.overflow = ''; };
  }, [isMobileOpen]);

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

  const rawName = (user as any)?.fullName || user?.email?.split('@')[0] || 'User';
  const displayName = rawName.charAt(0).toUpperCase() + rawName.slice(1);
  const initials = rawName.split(/[\s._-]/).map((n: string) => n[0] ?? '').join('').toUpperCase().slice(0, 2);

  // Shared nav link component - handles both collapsed (icon-only) and expanded modes
  const NavLink = ({ item, isAdminItem = false }: { item: NavItem; isAdminItem?: boolean }) => {
    const Icon = item.icon;
    const active = isActive(item.href);
    const label = t(item.labelKey) !== item.labelKey ? t(item.labelKey) : item.defaultLabel;

    return (
      <Link
        href={item.href}
        onClick={() => setIsMobileOpen(false)}
        title={collapsed ? label : undefined}
        className={`
          flex items-center gap-3 rounded-lg transition-all duration-150 group/item relative
          ${collapsed ? 'px-0 py-2.5 justify-center' : 'px-3 py-2.5'}
          ${active
            ? isAdminItem
              ? 'bg-primary/10 text-primary font-medium'
              : 'bg-primary/10 text-primary font-medium'
            : 'text-muted-foreground hover:bg-muted/70 hover:text-foreground'
          }
        `}
      >
        <Icon className="h-[17px] w-[17px] flex-shrink-0" />

        {/* Label — hidden when collapsed on desktop */}
        {!collapsed && (
          <span className="text-sm flex-1 leading-none">{label}</span>
        )}

        {/* Badge dot */}
        {!collapsed && item.badge && (
          <span className={`w-[7px] h-[7px] rounded-full flex-shrink-0 ${BADGE_CLASSES[item.badge]}`} />
        )}

        {/* Tooltip on collapsed mode */}
        {collapsed && (
          <span className="
            absolute left-full ml-2 px-2 py-1 rounded-md text-xs font-medium
            bg-popover text-popover-foreground border border-border shadow-md
            opacity-0 group-hover/item:opacity-100 pointer-events-none
            transition-opacity duration-150 whitespace-nowrap z-50
          ">
            {label}
          </span>
        )}
      </Link>
    );
  };

  return (
    <>
      {/* ── Mobile hamburger ─────────────────────────────────── */}
      <button
        onClick={() => setIsMobileOpen(!isMobileOpen)}
        className="fixed top-4 left-4 z-50 md:hidden p-2.5 bg-background hover:bg-muted rounded-lg shadow-sm border border-border transition-colors"
        aria-label={isMobileOpen ? 'Close menu' : 'Open menu'}
      >
        {isMobileOpen ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
      </button>

      {/* ── Backdrop (mobile) ─────────────────────────────────── */}
      {isMobileOpen && (
        <div
          className="fixed inset-0 bg-black/70 z-30 md:hidden"
          onClick={() => setIsMobileOpen(false)}
          aria-hidden="true"
        />
      )}

      {/* ── Sidebar shell ─────────────────────────────────────── */}
      <aside
        className={`
          ${isMobileOpen ? 'translate-x-0' : '-translate-x-full'}
          md:translate-x-0
          fixed left-0 top-0 h-screen
          flex flex-col
          transition-all duration-300 ease-in-out
          z-40
          bg-card border-r border-border
          shadow-xl md:shadow-none
          ${collapsed ? 'w-[68px]' : 'w-64'}
        `}
      >
        {/* ── Logo + collapse toggle ──────────────────────── */}
        <div className="h-16 flex items-center border-b border-border flex-shrink-0 px-3 overflow-hidden">
          {collapsed ? (
            <button
              onClick={toggleCollapsed}
              title="Expand sidebar"
              className="w-full flex items-center justify-center py-2 rounded-lg hover:bg-muted/60 transition-colors group relative"
            >
              <div className="w-9 h-9 rounded-lg bg-primary flex items-center justify-center flex-shrink-0 shadow-sm group-hover:scale-105 transition-transform">
                <Shield className="w-5 h-5 text-primary-foreground" />
              </div>
            </button>
          ) : (
            <div className="flex items-center justify-between w-full">
              <Link href="/dashboard" className="flex items-center gap-2.5 group min-w-0 pl-1">
                <div className="w-8 h-8 rounded-lg bg-primary flex items-center justify-center flex-shrink-0 shadow-sm group-hover:opacity-90 transition-opacity">
                  <Shield className="w-4 h-4 text-primary-foreground" />
                </div>
                <span className="font-bold text-[17px] tracking-tight text-foreground select-none truncate">
                  GRC<span className="text-primary">Guard</span>
                </span>
              </Link>

              <button
                onClick={toggleCollapsed}
                title="Collapse sidebar"
                className="hidden md:flex items-center justify-center w-7 h-7 rounded-md flex-shrink-0 text-muted-foreground hover:text-foreground hover:bg-muted/60 transition-colors"
              >
                <PanelLeftClose className="h-4 w-4" />
              </button>
            </div>
          )}
        </div>

        {/* ── Scrollable nav body ───────────────────────── */}
        <nav className={`flex-1 overflow-y-auto py-4 scrollbar-hide ${collapsed ? 'px-1.5 space-y-1' : 'px-2.5 space-y-1'}`}>

          {/* Dashboard */}
          <NavLink
            item={{ href: '/dashboard', labelKey: 'dashboard', defaultLabel: 'Dashboard', icon: BarChart3, roles: ['admin', 'manager', 'analyst'] }}
          />

          {/* Grouped sections */}
          {NAV_GROUPS.map((group) => {
            const visibleItems = group.items.filter((item) => item.roles.includes(userRole));
            if (visibleItems.length === 0) return null;
            const isGroupCollapsed = !!collapsedGroups[group.labelKey];
            const groupLabelText = t(group.labelKey) !== group.labelKey ? t(group.labelKey) : group.defaultLabel;

            return (
              <div key={group.labelKey} className={collapsed ? 'mt-2' : ''}>
                {/* Section header — hidden in collapsed mode */}
                {!collapsed && (
                  <button
                    onClick={() => toggleGroup(group.labelKey)}
                    className="w-full flex items-center justify-between px-3 py-1.5 mb-0.5 rounded-md hover:bg-muted/40 transition-colors group/hdr"
                  >
                    <span className="text-[10px] font-bold tracking-widest text-muted-foreground/60 uppercase select-none">
                      {groupLabelText}
                    </span>
                    {isGroupCollapsed
                      ? <ChevronDown className="h-3 w-3 text-muted-foreground/40 group-hover/hdr:text-muted-foreground transition-colors" />
                      : <ChevronUp className="h-3 w-3 text-muted-foreground/40 group-hover/hdr:text-muted-foreground transition-colors" />
                    }
                  </button>
                )}

                {/* Collapsed mode: divider line instead of header */}
                {collapsed && (
                  <div className="border-t border-border/60 my-2 mx-1" />
                )}

                {/* Items */}
                {(!isGroupCollapsed || collapsed) && (
                  <div className={`${collapsed ? 'space-y-1' : 'space-y-0.5 mb-2'}`}>
                    {visibleItems.map((item) => (
                      <NavLink key={item.href} item={item} />
                    ))}
                  </div>
                )}
              </div>
            );
          })}
        </nav>

        {/* ── Bottom pinned area ──────────────────────────── */}
        <div className="flex-shrink-0 border-t border-border">
          {/* Admin items */}
          {(() => {
            const adminVisible = ADMIN_NAV_ITEMS.filter((item) => item.roles.includes(userRole));
            if (adminVisible.length === 0) return null;
            return (
              <div className={`pt-2.5 pb-1 space-y-0.5 ${collapsed ? 'px-1.5' : 'px-2.5'}`}>
                {adminVisible.map((item) => (
                  <NavLink key={item.href} item={item} isAdminItem />
                ))}
              </div>
            );
          })()}

          {/* User profile card */}
          <div className={`p-3 ${collapsed ? 'px-2' : ''}`}>
            <div className={`flex items-center rounded-lg hover:bg-muted/60 transition-colors group/profile cursor-default
              ${collapsed ? 'justify-center px-0 py-2' : 'gap-3 px-3 py-2.5'}`}
            >
              <Avatar className="h-8 w-8 flex-shrink-0">
                <AvatarFallback className="bg-primary text-primary-foreground text-xs font-semibold">
                  {initials}
                </AvatarFallback>
              </Avatar>

              {!collapsed && (
                <>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-foreground leading-tight truncate">{displayName}</p>
                    <p className="text-xs text-muted-foreground leading-tight truncate mt-0.5">{ROLE_LABELS[userRole] ?? userRole}</p>
                  </div>
                  <button
                    onClick={handleLogout}
                    title={t('logout')}
                    aria-label={t('logout')}
                    className="opacity-0 group-hover/profile:opacity-100 transition-opacity duration-150 p-1.5 rounded-md text-muted-foreground hover:bg-destructive/10 hover:text-destructive"
                  >
                    <LogOut className="h-3.5 w-3.5" />
                  </button>
                </>
              )}

              {/* Logout icon visible in collapsed mode */}
              {collapsed && (
                <button
                  onClick={handleLogout}
                  title={t('logout')}
                  aria-label={t('logout')}
                  className="hidden group-hover/profile:flex absolute left-full ml-2 items-center gap-1 px-2 py-1 rounded-md bg-destructive text-destructive-foreground text-xs font-medium shadow-md z-50"
                >
                  <LogOut className="h-3 w-3" />
                  {t('logout')}
                </button>
              )}
            </div>
          </div>
        </div>
      </aside>
    </>
  );
}