'use client';

import { useState, useEffect } from 'react';
import { 
  Popover, 
  PopoverContent, 
  PopoverTrigger 
} from '@/components/ui/popover';
import { Button } from '@/components/ui/button';
import { Bell, Check, Loader2 } from 'lucide-react';
import { NotificationItem } from '@/components/notifications/NotificationItem';
import { 
  fetchNotifications, 
  fetchUnreadCount, 
  markAllRead, 
  markAsRead, 
  deleteNotification 
} from '@/lib/data-service';
import { toast } from 'sonner';
import Link from 'next/link';

export function NotificationPopover() {
  const [notifications, setNotifications] = useState<any[]>([]);
  const [unreadCount, setUnreadCount] = useState(0);
  const [isLoading, setIsLoading] = useState(false);
  const [isOpen, setIsOpen] = useState(false);
  const [filter, setFilter] = useState<'all' | 'unread' | 'ticket' | 'risk' | 'evidence'>('all');

  const loadData = async (showLoading = false) => {
    if (showLoading) setIsLoading(true);
    try {
      const count = await fetchUnreadCount();
      
      // Browser notification logic
      if (count > unreadCount && Notification.permission === 'granted') {
        new Notification('New Notification', {
          body: `You have ${count} unread notifications`,
          icon: '/favicon.ico'
        });
      }
      
      setUnreadCount(count);
      
      if (isOpen || showLoading) {
        const params: any = { limit: 20 };
        if (filter === 'unread') params.unread_only = true;
        else if (filter !== 'all') params.type = filter;
        
        const data = await fetchNotifications(params);
        setNotifications(data);
      }
    } catch (error) {
      console.error('Failed to load notifications', error);
    } finally {
      if (showLoading) setIsLoading(false);
    }
  };

  useEffect(() => {
    loadData();
    const interval = setInterval(() => loadData(false), 30000);
    
    // Request notification permission
    if (typeof window !== 'undefined' && 'Notification' in window) {
      if (Notification.permission === 'default') {
        Notification.requestPermission();
      }
    }
    
    return () => clearInterval(interval);
  }, [unreadCount, filter]); // Added unreadCount to track changes

  useEffect(() => {
    if (isOpen) {
      loadData(true);
    }
  }, [isOpen, filter]);

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

  const handleMarkAsRead = async (id: string) => {
    try {
      await markAsRead(id);
      setNotifications(notifications.map(n => n.id === id ? { ...n, is_read: 1 } : n));
      const count = await fetchUnreadCount();
      setUnreadCount(count);
    } catch (error) {
      console.error('Failed to mark as read', error);
    }
  };

  const handleDelete = async (id: string) => {
    try {
      await deleteNotification(id);
      setNotifications(notifications.filter(n => n.id !== id));
      const count = await fetchUnreadCount();
      setUnreadCount(count);
      toast.success('Notification deleted');
    } catch (error) {
      toast.error('Failed to delete notification');
    }
  };

  const displayCount = unreadCount > 99 ? '99+' : unreadCount;

  return (
    <Popover open={isOpen} onOpenChange={setIsOpen}>
      <PopoverTrigger asChild>
        <Button
          variant="ghost"
          size="icon"
          className="text-muted-foreground hover:text-foreground relative h-10 w-10 sm:h-9 sm:w-9"
          aria-label="Notifications"
        >
          <Bell className="h-5 w-5" />
          {unreadCount > 0 && (
            <span className={`absolute ${unreadCount > 9 ? '-top-1 -right-1 px-1' : 'top-2.5 right-2.5 w-2 h-2'} bg-red-500 text-white rounded-full ring-2 ring-background flex items-center justify-center text-[10px] font-bold`}>
              {unreadCount > 9 ? displayCount : ''}
            </span>
          )}
        </Button>
      </PopoverTrigger>
      <PopoverContent className="w-96 p-0" align="end">
        <div className="flex flex-col border-b">
          <div className="flex items-center justify-between p-4 pb-2">
            <div className="flex items-center gap-2">
              <h4 className="font-semibold text-sm">Notifications</h4>
              {unreadCount > 0 && (
                <span className="bg-primary/10 text-primary text-[10px] px-1.5 py-0.5 rounded-full font-bold">
                  {displayCount}
                </span>
              )}
            </div>
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
          
          <div className="px-4 pb-3 flex flex-wrap gap-1 items-center">
            <span className="text-[10px] text-muted-foreground font-medium uppercase mr-1">Filter:</span>
            {[
              { id: 'all', label: 'All' },
              { id: 'unread', label: 'Unread' },
              { id: 'ticket', label: 'Tickets' },
              { id: 'risk', label: 'Risks' },
              { id: 'evidence', label: 'Evidence' }
            ].map((f) => (
              <Button
                key={f.id}
                variant={filter === f.id ? 'secondary' : 'ghost'}
                size="sm"
                className={`h-6 px-2 text-[10px] font-medium rounded-full ${filter === f.id ? 'bg-primary/10 text-primary border-primary/20 hover:bg-primary/20' : 'text-muted-foreground'}`}
                onClick={() => setFilter(f.id as any)}
              >
                {f.label}
              </Button>
            ))}
          </div>
        </div>

        <div className="max-h-[450px] overflow-y-auto">
          {isLoading ? (
            <div className="flex flex-col items-center justify-center p-12 text-muted-foreground">
              <Loader2 className="h-6 w-6 animate-spin mb-2" />
              <p className="text-xs">Loading alerts...</p>
            </div>
          ) : notifications.length === 0 ? (
            <div className="p-12 text-center text-muted-foreground">
              <p className="text-xs">No notifications yet</p>
            </div>
          ) : (
            <div className="flex flex-col divide-y">
              {notifications.map((n) => (
                <NotificationItem 
                  key={n.id} 
                  notification={n} 
                  onMarkAsRead={handleMarkAsRead}
                  onDelete={handleDelete}
                  onClick={() => setIsOpen(false)}
                />
              ))}
            </div>
          )}
        </div>
        <div className="p-2 border-t text-center">
            <Link href="/dashboard/notifications" className="w-full" onClick={() => setIsOpen(false)}>
              <Button variant="ghost" size="sm" className="w-full text-xs text-muted-foreground hover:text-primary">
                  View all notifications
              </Button>
            </Link>
        </div>
      </PopoverContent>
    </Popover>
  );
}
