'use client';

import { useState, useEffect } from 'react';
import { 
  fetchNotifications, 
  markAllRead, 
  markAsRead, 
  deleteNotification,
  fetchUnreadCount
} from '@/lib/data-service';
import { NotificationItem } from '@/components/notifications/NotificationItem';
import { Button } from '@/components/ui/button';
import { 
  Bell, 
  Check, 
  Loader2, 
  Filter,
  Trash2,
  RefreshCw,
  Inbox
} from 'lucide-react';
import { toast } from 'sonner';
import Link from 'next/link';
import { 
  Tabs, 
  TabsContent, 
  TabsList, 
  TabsTrigger 
} from '@/components/ui/tabs';

export default function NotificationsPage() {
  const [notifications, setNotifications] = useState<any[]>([]);
  const [unreadCount, setUnreadCount] = useState(0);
  const [isLoading, setIsLoading] = useState(true);
  const [activeTab, setActiveTab] = useState('all');
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  const [page, setPage] = useState(1);
  const [hasMore, setHasMore] = useState(true);

  const loadData = async (resetPage = false) => {
    const targetPage = resetPage ? 1 : page;
    if (resetPage) setPage(1);
    
    setIsLoading(true);
    try {
      const params: any = { 
        limit: 20, 
        offset: (targetPage - 1) * 20 
      };
      if (activeTab === 'unread') {
        params.unread_only = true;
      }
      
      const [data, count] = await Promise.all([
        fetchNotifications(params),
        fetchUnreadCount()
      ]);
      
      setNotifications(data);
      setUnreadCount(count);
      setHasMore(data.length === 20);
    } catch (error) {
      console.error('Failed to load notifications', error);
      toast.error('Failed to load notifications');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadData(true);
  }, [activeTab]);

  useEffect(() => {
    loadData();
  }, [page]);

  const toggleSelection = (id: string) => {
    const next = new Set(selectedIds);
    if (next.has(id)) next.delete(id);
    else next.add(id);
    setSelectedIds(next);
  };

  const toggleAll = () => {
    if (selectedIds.size === notifications.length) {
      setSelectedIds(new Set());
    } else {
      setSelectedIds(new Set(notifications.map(n => n.id)));
    }
  };

  const handleMarkSelectedRead = async () => {
    if (selectedIds.size === 0) return;
    try {
      await Promise.all(Array.from(selectedIds).map(id => markAsRead(id)));
      setNotifications(notifications.map(n => selectedIds.has(n.id) ? { ...n, is_read: 1 } : n));
      setSelectedIds(new Set());
      const count = await fetchUnreadCount();
      setUnreadCount(count);
      toast.success('Selected notifications marked as read');
    } catch (error) {
      toast.error('Failed to update notifications');
    }
  };

  const handleDeleteSelected = async () => {
    if (selectedIds.size === 0) return;
    try {
      await Promise.all(Array.from(selectedIds).map(id => deleteNotification(id)));
      setNotifications(notifications.filter(n => !selectedIds.has(n.id)));
      setSelectedIds(new Set());
      const count = await fetchUnreadCount();
      setUnreadCount(count);
      toast.success('Selected notifications deleted');
    } catch (error) {
      toast.error('Failed to delete notifications');
    }
  };

  const handleMarkAsRead = async (id: string) => {
    try {
      await markAsRead(id);
      setNotifications(notifications.map(n => n.id === id ? { ...n, is_read: 1 } : n));
      setUnreadCount(prev => Math.max(0, prev - 1));
    } catch (error) {
      console.error('Failed to mark as read', error);
    }
  };

  const handleDelete = async (id: string) => {
    try {
      await deleteNotification(id);
      const deleted = notifications.find(n => n.id === id);
      setNotifications(notifications.filter(n => n.id !== id));
      if (deleted && !deleted.is_read) {
        setUnreadCount(prev => Math.max(0, prev - 1));
      }
      toast.success('Notification deleted');
    } catch (error) {
      toast.error('Failed to delete notification');
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h2 className="text-2xl font-bold tracking-tight">Notifications</h2>
          <p className="text-muted-foreground text-sm">
            Stay updated with the latest activities and alerts.
          </p>
        </div>
        <div className="flex items-center gap-2">
          {selectedIds.size > 0 && (
            <div className="flex items-center gap-2 mr-4 bg-muted p-1 rounded-md px-2 border">
                <span className="text-xs font-medium">{selectedIds.size} selected</span>
                <Button variant="ghost" size="sm" className="h-7 text-xs px-2" onClick={handleMarkSelectedRead}>
                    Mark read
                </Button>
                <Button variant="ghost" size="sm" className="h-7 text-xs px-2 text-destructive" onClick={handleDeleteSelected}>
                    Delete
                </Button>
            </div>
          )}
          <Button variant="ghost" size="icon" onClick={() => loadData(true)} disabled={isLoading}>
            <RefreshCw className={`h-4 w-4 ${isLoading ? 'animate-spin' : ''}`} />
          </Button>
        </div>
      </div>

      <Tabs defaultValue="all" className="w-full" onValueChange={setActiveTab}>
        <div className="flex items-center justify-between border-b pb-0.5 mb-4">
          <TabsList className="bg-transparent h-auto p-0 gap-6">
            <TabsTrigger 
              value="all" 
              className="px-0 py-2 border-b-2 border-transparent data-[state=active]:border-primary data-[state=active]:bg-transparent rounded-none transition-none h-10"
            >
              All Notifications
            </TabsTrigger>
            <TabsTrigger 
              value="unread"
              className="px-0 py-2 border-b-2 border-transparent data-[state=active]:border-primary data-[state=active]:bg-transparent rounded-none transition-none h-10 flex gap-2 items-center"
            >
              Unread
              {unreadCount > 0 && (
                <span className="bg-primary/10 text-primary text-[10px] px-1.5 py-0.5 rounded-full font-bold">
                  {unreadCount}
                </span>
              )}
            </TabsTrigger>
          </TabsList>
          
          {notifications.length > 0 && (
            <Button variant="ghost" size="sm" className="text-xs h-8" onClick={toggleAll}>
                {selectedIds.size === notifications.length ? 'Deselect all' : 'Select all'}
            </Button>
          )}
        </div>

        <TabsContent value="all" className="mt-0 border rounded-lg bg-card overflow-hidden">
          {isLoading && notifications.length === 0 ? (
            <div className="flex flex-col items-center justify-center p-20 text-muted-foreground font-vibrant">
              <Loader2 className="h-10 w-10 animate-spin mb-4 text-primary" />
              <p className="text-sm">Fetching all notifications...</p>
            </div>
          ) : notifications.length === 0 ? (
            <div className="flex flex-col items-center justify-center p-20 text-muted-foreground text-center">
              <div className="h-16 w-16 bg-muted rounded-full flex items-center justify-center mb-4">
                <Inbox className="h-8 w-8 text-muted-foreground/50" />
              </div>
              <h3 className="text-lg font-medium text-foreground">No notifications</h3>
              <p className="text-sm max-w-[250px]">
                You're all caught up! When you have new alerts, they will appear here.
              </p>
            </div>
          ) : (
            <>
              <div className="flex flex-col divide-y">
                {notifications.map((n) => (
                  <div key={n.id} className="flex items-center gap-2 pl-4">
                    <input 
                      type="checkbox" 
                      className="h-4 w-4 rounded border-gray-300 text-primary focus:ring-primary"
                      checked={selectedIds.has(n.id)}
                      onChange={() => toggleSelection(n.id)}
                    />
                    <div className="flex-1">
                      <NotificationItem 
                        notification={n} 
                        onMarkAsRead={handleMarkAsRead}
                        onDelete={handleDelete}
                      />
                    </div>
                  </div>
                ))}
              </div>
              <div className="p-4 border-t flex items-center justify-between bg-muted/20">
                <p className="text-xs text-muted-foreground">
                    Showing {(page-1)*20 + 1}-{Math.min(page*20, page*20)} of many
                </p>
                <div className="flex items-center gap-2">
                    <Button 
                        variant="outline" 
                        size="sm" 
                        disabled={page === 1 || isLoading}
                        onClick={() => setPage(page - 1)}
                    >
                        Previous
                    </Button>
                    <Button 
                        variant="outline" 
                        size="sm" 
                        disabled={!hasMore || isLoading}
                        onClick={() => setPage(page + 1)}
                    >
                        Next
                    </Button>
                </div>
              </div>
            </>
          )}
        </TabsContent>

        <TabsContent value="unread" className="mt-0 border rounded-lg bg-card overflow-hidden">
            {/* Same structure as above, ideally extracted to a component but keeping it here for simplicity now */}
          {isLoading && notifications.length === 0 ? (
            <div className="flex flex-col items-center justify-center p-20 text-muted-foreground">
              <Loader2 className="h-10 w-10 animate-spin mb-4 text-primary" />
              <p className="text-sm">Filtering unread alerts...</p>
            </div>
          ) : notifications.length === 0 ? (
            <div className="flex flex-col items-center justify-center p-20 text-muted-foreground text-center">
                <div className="h-16 w-16 bg-muted rounded-full flex items-center justify-center mb-4">
                    <Check className="h-8 w-8 text-muted-foreground/50" />
                </div>
              <h3 className="text-lg font-medium text-foreground">Zero unread labels</h3>
              <p className="text-sm">You have read all your notifications.</p>
              <Button variant="link" className="mt-2 text-primary" onClick={() => setActiveTab('all')}>
                View all notifications
              </Button>
            </div>
          ) : (
            <>
              <div className="flex flex-col divide-y">
                {notifications.map((n) => (
                  <div key={n.id} className="flex items-center gap-2 pl-4">
                    <input 
                      type="checkbox" 
                      className="h-4 w-4 rounded border-gray-300 text-primary focus:ring-primary"
                      checked={selectedIds.has(n.id)}
                      onChange={() => toggleSelection(n.id)}
                    />
                    <div className="flex-1">
                      <NotificationItem 
                        notification={n} 
                        onMarkAsRead={handleMarkAsRead}
                        onDelete={handleDelete}
                      />
                    </div>
                  </div>
                ))}
              </div>
              <div className="p-4 border-t flex items-center justify-between bg-muted/20">
                <p className="text-xs text-muted-foreground">
                    Page {page}
                </p>
                <div className="flex items-center gap-2">
                    <Button 
                        variant="outline" 
                        size="sm" 
                        disabled={page === 1 || isLoading}
                        onClick={() => setPage(page - 1)}
                    >
                        Previous
                    </Button>
                    <Button 
                        variant="outline" 
                        size="sm" 
                        disabled={!hasMore || isLoading}
                        onClick={() => setPage(page + 1)}
                    >
                        Next
                    </Button>
                </div>
              </div>
            </>
          )}
        </TabsContent>
      </Tabs>
    </div>
  );
}
