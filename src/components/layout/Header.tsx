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
        return 'bg-purple-100 text-purple-700';
      case 'analyst':
        return 'bg-blue-100 text-blue-700';
      case 'manager':
        return 'bg-green-100 text-green-700';
      default:
        return 'bg-slate-100 text-slate-700';
    }
  };

  return (
    <header className="sticky top-0 h-16 bg-white border-b border-slate-200 flex items-center justify-between px-4 sm:px-6 pl-16 md:pl-6 z-20">
      <div className="min-w-0 flex-1">
        <h1 className="text-lg font-semibold text-slate-900 truncate">{title}</h1>
      </div>

      <div className="flex items-center gap-2 sm:gap-4">
        <Button 
          variant="ghost" 
          size="icon" 
          className="text-slate-600 h-10 w-10 sm:h-9 sm:w-9"
          aria-label="Help"
        >
          <HelpCircle className="h-5 w-5" />
        </Button>

        <Button 
          variant="ghost" 
          size="icon" 
          className="text-slate-600 relative h-10 w-10 sm:h-9 sm:w-9"
          aria-label="Notifications"
        >
          <Bell className="h-5 w-5" />
          <span className="absolute top-2 right-2 w-2 h-2 bg-amber-500 rounded-full" />
        </Button>

        <div className="flex items-center gap-2 sm:gap-3 pl-2 sm:pl-4 border-l border-slate-200">
          <div className="text-right hidden sm:block">
            <p className="text-sm font-medium text-slate-900">{displayName}</p>
            <span className={`inline-block text-xs px-2 py-0.5 rounded-full font-medium capitalize ${getRoleBadgeColor(user.role)}`}>
              {user.role}
            </span>
          </div>
          <Avatar className="h-10 w-10 sm:h-9 sm:w-9 bg-blue-100">
            <AvatarFallback className="text-blue-600 font-medium text-sm">{initials}</AvatarFallback>
          </Avatar>
        </div>
      </div>
    </header>
  );
}