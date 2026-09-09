'use client';

import { useState } from 'react';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import {
  Lock,
  Laptop,
  Smartphone,
  Monitor,
  LogOut as RevokeIcon,
} from 'lucide-react';
import { toast } from 'sonner';
import { LucideIcon } from 'lucide-react';

interface SessionInfo {
  id: string;
  device: string;
  ip: string;
  location: string;
  lastActive: string;
  isCurrent: boolean;
  icon: LucideIcon;
}

interface SessionsDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

const INITIAL_SESSIONS: SessionInfo[] = [
  {
    id: 'session-1',
    device: 'Chrome on Windows 11',
    ip: '182.93.84.12',
    location: 'Kathmandu, Nepal',
    lastActive: 'Active now',
    isCurrent: true,
    icon: Laptop,
  },
  {
    id: 'session-2',
    device: 'Safari on iPhone 15 Pro',
    ip: '110.44.115.90',
    location: 'Lalitpur, Nepal',
    lastActive: '2 hours ago',
    isCurrent: false,
    icon: Smartphone,
  },
  {
    id: 'session-3',
    device: 'Firefox on macOS Sonoma',
    ip: '202.70.76.5',
    location: 'Pokhara, Nepal',
    lastActive: '3 days ago',
    isCurrent: false,
    icon: Monitor,
  },
];

export function SessionsDialog({ open, onOpenChange }: SessionsDialogProps) {
  const [sessions, setSessions] = useState<SessionInfo[]>(INITIAL_SESSIONS);

  const handleRevokeSession = (sessionId: string) => {
    setSessions((prev) => prev.filter((s) => s.id !== sessionId));
    toast.success('Session revoked successfully.');
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[550px]">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Lock className="h-5 w-5 text-primary" />
            Active Sessions
          </DialogTitle>
          <DialogDescription>
            These devices are currently signed into your account. Revoke any session you do not recognize.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-3 py-3 max-h-[60vh] overflow-y-auto">
          {sessions.map((sess) => {
            const DeviceIcon = sess.icon;
            return (
              <div key={sess.id} className="flex items-center justify-between p-3.5 border rounded-lg bg-card hover:bg-muted/40 transition-colors">
                <div className="flex items-center gap-3.5">
                  <div className="p-2.5 rounded-full bg-primary/10 text-primary shrink-0">
                    <DeviceIcon className="h-5 w-5" />
                  </div>
                  <div className="space-y-0.5">
                    <div className="flex items-center gap-2">
                      <p className="font-semibold text-sm">{sess.device}</p>
                      {sess.isCurrent && (
                        <Badge variant="outline" className="bg-emerald-50 text-emerald-700 border-emerald-300 text-[10px] py-0 px-1.5 font-medium">
                          Current Device
                        </Badge>
                      )}
                    </div>
                    <p className="text-xs text-muted-foreground">
                      {sess.ip} • {sess.location}
                    </p>
                    <p className="text-[11px] text-slate-500">
                      Last active: <span className="font-medium">{sess.lastActive}</span>
                    </p>
                  </div>
                </div>

                {!sess.isCurrent && (
                  <Button
                    variant="ghost"
                    size="sm"
                    className="text-destructive hover:bg-destructive/10 hover:text-destructive gap-1 text-xs"
                    onClick={() => handleRevokeSession(sess.id)}
                  >
                    <RevokeIcon className="h-3.5 w-3.5" />
                    Revoke
                  </Button>
                )}
              </div>
            );
          })}
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Close
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
