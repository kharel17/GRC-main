'use client';

import { Avatar, AvatarFallback } from '@/components/ui/avatar';
import { Bell, HelpCircle } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { UserRole } from '@/types/user';

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
  const displayName = user.fullName || user.email.split('@')[0];
  const initials = displayName
    .split(/[\s._-]/)
    .map((n) => n[0])
    .join('')
    .toUpperCase()
    .slice(0, 2);

  const getRoleBadgeColor = (role: string) => {
    switch (role) {
      case 'admin':
        return 'bg-purple-100 text-purple-700 dark:bg-purple-900/30 dark:text-purple-300';
      case 'analyst':
        return 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300';
      case 'manager':
        return 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-300';
      default:
        return 'bg-slate-100 text-slate-700 dark:bg-slate-800 dark:text-slate-300';
    }
  };

  return (
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

        <Button 
          variant="ghost" 
          size="icon" 
          className="text-muted-foreground hover:text-foreground relative h-10 w-10 sm:h-9 sm:w-9"
          aria-label="Notifications"
          onClick={() => {
             // Placeholder for notification logic
             // Could trigger a toast or open a popover
          }}
        >
          <Bell className="h-5 w-5" />
          <span className="absolute top-2.5 right-2.5 w-2 h-2 bg-red-500 rounded-full ring-2 ring-background" />
        </Button>

        <div className="flex items-center gap-2 sm:gap-3 pl-2 sm:pl-4 border-l border-border">
          <div className="text-right hidden sm:block">
            <p className="text-sm font-medium text-foreground">{displayName}</p>
            <span className={`inline-block text-xs px-2 py-0.5 rounded-full font-medium capitalize ${getRoleBadgeColor(user.role)}`}>
              {user.role}
            </span>
          </div>
          <Avatar className="h-10 w-10 sm:h-9 sm:w-9 bg-muted">
            <AvatarFallback className="text-primary font-medium text-sm">{initials}</AvatarFallback>
          </Avatar>
        </div>
      </div>
    </header>
  );
}