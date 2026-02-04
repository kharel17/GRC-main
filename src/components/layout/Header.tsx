'use client';

import { UserProfile } from '@/types/user';
import { Avatar, AvatarFallback } from '@/components/ui/avatar';
import { Bell, HelpCircle } from 'lucide-react';
import { Button } from '@/components/ui/button';

interface HeaderProps {
  user: UserProfile;
  title?: string;
}

export function Header({ user, title }: HeaderProps) {
  const initials = user.fullName
    .split(' ')
    .map((n) => n[0])
    .join('')
    .toUpperCase();

  return (
    <header className="sticky top-0 h-16 bg-white border-b border-slate-200 flex items-center justify-between px-6 md:ml-64">
      <div>
        <h1 className="text-lg font-semibold text-slate-900">{title}</h1>
      </div>

      <div className="flex items-center gap-4">
        <Button variant="ghost" size="icon" className="text-slate-600">
          <HelpCircle className="h-5 w-5" />
        </Button>

        <Button variant="ghost" size="icon" className="text-slate-600 relative">
          <Bell className="h-5 w-5" />
          <span className="absolute top-2 right-2 w-2 h-2 bg-amber-500 rounded-full" />
        </Button>

        <div className="flex items-center gap-3 pl-4 border-l border-slate-200">
          <div className="text-right">
            <p className="text-sm font-medium text-slate-900">{user.fullName}</p>
            <p className="text-xs text-slate-500 capitalize">{user.role}</p>
          </div>
          <Avatar className="h-9 w-9 bg-blue-100">
            <AvatarFallback className="text-blue-600 font-medium">{initials}</AvatarFallback>
          </Avatar>
        </div>
      </div>
    </header>
  );
}
