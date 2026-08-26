'use client';

import { Avatar, AvatarFallback } from '@/components/ui/avatar';
import { HelpCircle } from 'lucide-react';
import { NotificationPopover } from '@/features/dashboard/NotificationPopover';
import { Button } from '@/components/ui/button';
import { UserRole } from '@/types';

interface HeaderUser {
  email: string;
  role: UserRole;
  fullName?: string;
}

interface HeaderProps {
  user: HeaderUser;
  title?: string;
}

export function Header({ user, title }: HeaderProps) {
  // Generate initials from email or fullName
  const displayName = user.fullName || user.email?.split('@')[0] || 'User';
  const initials = displayName
    .split(/[\s._-]/)
    .map((n) => n[0])
    .join('')
    .toUpperCase()
    .slice(0, 2);

  const getRoleBadgeColor = (role: string) => {
    const colors: Record<string, string> = {
      superadmin: 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-300',
      admin: 'bg-purple-100 text-purple-700 dark:bg-purple-900/30 dark:text-purple-300',
      manager: 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300',
      analyst: 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-300',
    };
    return colors[role] || 'bg-slate-100 text-slate-700 dark:bg-slate-800 dark:text-slate-300';
  };

  const getRoleDisplayName = (role: string) => {
    const names: Record<string, string> = {
      superadmin: 'Super Admin',
      admin: 'Administrator',
      manager: 'Manager',
      analyst: 'Risk Analyst',
    };
    return names[role] || role;
  };


  const isImpersonating = typeof window !== 'undefined' && Boolean(sessionStorage.getItem('support_access_token'));

  const handleExitSupportSession = () => {
    sessionStorage.removeItem('support_access_token');
    window.location.href = '/superadmin';
  };

  return (
    <>
      {isImpersonating && (
        <div className="bg-amber-500 text-amber-950 px-4 py-1.5 text-xs font-semibold flex items-center justify-between shadow-sm z-30 sticky top-0">
          <div className="flex items-center gap-2">
            <span className="inline-block w-2 h-2 rounded-full bg-amber-900 animate-pulse" />
            <span>SUPPORT IMPERSONATION ACTIVE: You are viewing this tenant via a temporary 15-minute support token.</span>
          </div>
          <button
            onClick={handleExitSupportSession}
            className="bg-amber-950 text-amber-100 hover:bg-amber-900 px-2.5 py-0.5 rounded text-[11px] font-medium transition-colors"
          >
            Exit Support Session
          </button>
        </div>
      )}
      <header className="sticky top-0 h-16 bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60 border-b border-border flex items-center justify-between px-4 sm:px-6 pl-16 md:pl-6 z-20">
        <div className="min-w-0 flex-1">
          <h1 className="text-lg font-semibold text-foreground truncate">{title}</h1>
        </div>

        <div className="flex items-center gap-2 sm:gap-4">
          <Button
            variant="ghost"
            size="icon"
            className="text-muted-foreground hover:text-foreground h-10 w-10 sm:h-9 sm:w-9"
            aria-label="Help"
          >
            <HelpCircle className="h-5 w-5" />
          </Button>

          <NotificationPopover />

          <div className="flex items-center gap-2 sm:gap-3 pl-2 sm:pl-4 border-l border-border">
            <div className="text-right hidden sm:block">
              <p className="text-sm font-medium text-foreground">{displayName}</p>
              <span className={`inline-block text-xs px-2 py-0.5 rounded-full font-medium ${getRoleBadgeColor(user.role)}`}>
                {getRoleDisplayName(user.role)}
              </span>
            </div>
            <Avatar className="h-10 w-10 sm:h-9 sm:w-9 bg-muted">
              <AvatarFallback className="text-primary font-medium text-sm">{initials}</AvatarFallback>
            </Avatar>
          </div>
        </div>
      </header>
    </>
  );
}