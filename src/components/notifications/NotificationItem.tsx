'use client';

import { formatDistanceToNow } from 'date-fns';
import { 
  Bell, 
  Ticket, 
  AlertTriangle, 
  ShieldCheck, 
  FileText, 
  UserPlus,
  Circle,
  MoreHorizontal,
  Trash2,
  ExternalLink,
  ArrowRight,
  Check
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { 
  DropdownMenu, 
  DropdownMenuContent, 
  DropdownMenuItem, 
  DropdownMenuTrigger 
} from '@/components/ui/dropdown-menu';
import Link from 'next/link';

interface NotificationItemProps {
  notification: any;
  onMarkAsRead: (id: string) => void;
  onDelete: (id: string) => void;
  onClick?: () => void;
}

export function NotificationItem({ 
  notification: n, 
  onMarkAsRead, 
  onDelete,
  onClick
}: NotificationItemProps) {
  
  const getIcon = (type: string) => {
    switch (type) {
      case 'TICKET_ASSIGNMENT':
      case 'TICKET_ESCALATION':
      case 'EVIDENCE_REQUESTED':
      case 'TICKET_OVERDUE':
        return <Ticket className="h-4 w-4 text-blue-500" />;
      case 'HIGH_RISK_ALERT':
      case 'EVIDENCE_REJECTED':
      case 'EVIDENCE_REVIEW_REQUIRED':
        return <AlertTriangle className="h-4 w-4 text-amber-500" />;
      case 'RISK_ASSIGNMENT':
        return <AlertTriangle className="h-4 w-4 text-orange-500" />;
      case 'CONTROL_ASSIGNMENT':
      case 'CONTROL_IMPLEMENTED':
        return <ShieldCheck className="h-4 w-4 text-purple-500" />;
      case 'EVIDENCE_VERIFIED':
        return <FileText className="h-4 w-4 text-green-500" />;
      case 'WELCOME':
      case 'USER_JOINED':
        return <UserPlus className="h-4 w-4 text-indigo-500" />;
      default:
        return <Bell className="h-4 w-4 text-slate-500" />;
    }
  };

  const getLink = (n: any) => {
    if (n.link_url) return n.link_url;
    if (n.ticket_id) return `/dashboard/tickets/${n.ticket_id}`;
    if (n.entity_type === 'risk') return `/dashboard/risks/${n.entity_id}`;
    if (n.entity_type === 'control') return `/dashboard/controls/${n.entity_id}`;
    if (n.entity_type === 'evidence') return `/dashboard/evidence`;
    return '#';
  };

  return (
    <div 
      className={`group flex items-start gap-3 p-4 border-b hover:bg-muted/50 transition-colors relative ${!n.is_read ? 'bg-primary/5' : ''}`}
      onClick={onClick}
    >
      <div className="mt-1 flex-shrink-0 relative">
        {getIcon(n.type)}
        <div className={`absolute -top-1 -left-1 w-2 h-2 rounded-full ring-1 ring-background ${!n.is_read ? 'bg-blue-500' : 'bg-slate-300'}`} />
      </div>
      
      <div className="flex-1 min-w-0 pr-8">
        <div className="flex justify-between items-start gap-1 mb-0.5">
          <span className="text-xs font-semibold uppercase tracking-tight text-primary truncate">
             {n.title || n.type?.replace(/_/g, ' ')}
          </span>
          <span className="text-[10px] text-muted-foreground whitespace-nowrap">
            {formatDistanceToNow(new Date(n.created_at), { addSuffix: true })}
          </span>
        </div>
        
        <p className={`text-xs leading-normal text-foreground mb-2 line-clamp-2 ${!n.is_read ? 'font-medium' : 'text-muted-foreground'}`}>
          {n.message}
        </p>

        <div className="flex items-center justify-between">
            <Link 
              href={getLink(n)} 
              className="text-[10px] font-medium text-primary hover:underline flex items-center gap-1"
              onClick={(e) => {
                e.stopPropagation();
                onMarkAsRead(n.id);
                if (onClick) onClick();
              }}
            >
              View detail
            </Link>
            <ArrowRight className="h-3 w-3 text-muted-foreground opacity-0 group-hover:opacity-100 transition-opacity" />
        </div>
      </div>

      <div className="absolute right-2 top-4">
        <DropdownMenu>
          <DropdownMenuTrigger asChild onClick={(e) => e.stopPropagation()}>
            <Button variant="ghost" size="icon" className="h-6 w-6 opacity-0 group-hover:opacity-100 transition-opacity">
              <MoreHorizontal className="h-3 w-3" />
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end">
            {!n.is_read && (
              <DropdownMenuItem onClick={() => onMarkAsRead(n.id)}>
                <Check className="mr-2 h-4 w-4" />
                <span>Mark as read</span>
              </DropdownMenuItem>
            )}
            <DropdownMenuItem onClick={() => onDelete(n.id)} className="text-destructive focus:text-destructive">
              <Trash2 className="mr-2 h-4 w-4" />
              <span>Delete</span>
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </div>
    </div>
  );
}
