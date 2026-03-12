'use client';

import { useState, useEffect } from 'react';
import { 
  Popover, 
  PopoverContent, 
  PopoverTrigger 
} from '@/components/ui/popover';
import { Button } from '@/components/ui/button';
import { Bell, Check, Loader2 } from 'lucide-react';
import { fetchNotifications, fetchUnreadCount, markAllRead } from '@/lib/data-service';
import { toast } from 'sonner';
import { formatDistanceToNow } from 'date-fns';
import Link from 'next/link';

export function NotificationPopover() {
  const [notifications, setNotifications] = useState<any[]>([]);
  const [unreadCount, setUnreadCount] = useState(0);
  const [isLoading, setIsLoading] = useState(false);
  const [isOpen, setIsOpen] = useState(false);

  const loadData = async () => {
    try {
      const count = await fetchUnreadCount();
      setUnreadCount(count);
      if (isOpen) {
        const data = await fetchNotifications();
        setNotifications(data);
      }
    } catch (error) {
      console.error('Failed to load notifications', error);
    }
  };

  useEffect(() => {
    loadData();
    // Poll for unread count every 30 seconds
    const interval = setInterval(loadData, 30000);
    return () => clearInterval(interval);
  }, []);

  useEffect(() => {
    if (isOpen) {
      setIsLoading(true);
      fetchNotifications().then(data => {
        setNotifications(data);
        setIsLoading(false);
      });
    }
  }, [isOpen]);

  const handleMarkAllRead = async () => {
    try {
      await markAllRead();
      setUnreadCount(0);
      setNotifications(notifications.map(n => ({ ...n, is_read: 1 })));
      toast.success('All notifications marked as read');
    } catch (error) {
      toast.error('Failed to mark notifications as read');
    }
  };

  return (
    <Popover open={isOpen} onOpenChange={setIsOpen}>
      <PopoverTrigger asChild>
        <Button
          variant="ghost"
          size="icon"
          className="text-muted-foreground hover:text-foreground relative h-10 w-10 sm:h-9 sm:w-9"
          aria-label="Notifications"
        >
          < Bell className="h-5 w-5" />
          {unreadCount > 0 && (
            <span className="absolute top-2.5 right-2.5 w-2 h-2 bg-red-500 rounded-full ring-2 ring-background" />
          )}
        </Button>
      </PopoverTrigger>
      <PopoverContent className="w-80 p-0" align="end">
        <div className="flex items-center justify-between p-4 border-b">
          <h4 className="font-semibold text-sm">Notifications</h4>
          {unreadCount > 0 && (
            <Button 
              variant="ghost" 
              size="sm" 
              className="h-8 text-[10px] uppercase font-bold text-muted-foreground hover:text-primary gap-1"
              onClick={handleMarkAllRead}
            >
              <Check className="h-3 w-3" />
              Mark all read
            </Button>
          )}
        </div>
        <div className="max-h-[300px] overflow-y-auto">
          {isLoading ? (
            <div className="flex flex-col items-center justify-center p-8 text-muted-foreground">
              <Loader2 className="h-6 w-6 animate-spin mb-2" />
              <p className="text-xs">Loading alerts...</p>
            </div>
          ) : notifications.length === 0 ? (
            <div className="p-8 text-center text-muted-foreground">
              <p className="text-xs">No notifications yet</p>
            </div>
          ) : (
            <div className="flex flex-col">
              {notifications.map((n) => (
                <Link
                  key={n.id}
                  href={n.ticket_id ? `/dashboard/tickets/${n.ticket_id}` : '#'}
                  className={`flex flex-col gap-1 p-4 border-b hover:bg-muted/50 transition-colors ${!n.is_read ? 'bg-primary/5' : ''}`}
                  onClick={() => setIsOpen(false)}
                >
                  <div className="flex justify-between items-start gap-2">
                    <span className="text-xs font-semibold uppercase tracking-tight text-primary">
                      {n.type?.replace('_', ' ')}
                    </span>
                    <span className="text-[10px] text-muted-foreground">
                      {formatDistanceToNow(new Date(n.created_at), { addSuffix: true })}
                    </span>
                  </div>
                  <p className="text-xs leading-normal text-foreground line-clamp-2">
                    {n.message}
                  </p>
                </Link>
              ))}
            </div>
          )}
        </div>
        <div className="p-2 border-t text-center">
            <Button variant="ghost" size="sm" className="w-full text-xs text-muted-foreground" disabled>
                View all notifications
            </Button>
        </div>
      </PopoverContent>
    </Popover>
  );
}
