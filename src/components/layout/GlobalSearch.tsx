'use client';

import * as React from 'react';
import { useRouter } from 'next/navigation';
import {
  CommandDialog,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
  CommandSeparator,
} from '@/components/ui/command';
import { 
  Shield, 
  AlertTriangle, 
  FileText, 
  Search, 
  Settings, 
  Home,
  CheckCircle2,
  Clock
} from 'lucide-react';
import { fetchRisks, fetchControls } from '@/lib/data-service';
import { Risk, Control } from '@/types';
import { Badge } from '@/components/ui/badge';

export function GlobalSearch() {
  const [open, setOpen] = React.useState(false);
  const [risks, setRisks] = React.useState<Risk[]>([]);
  const [controls, setControls] = React.useState<Control[]>([]);
  const [loading, setLoading] = React.useState(false);
  const router = useRouter();

  React.useEffect(() => {
    const down = (e: KeyboardEvent) => {
      if (e.key === 'k' && (e.metaKey || e.ctrlKey)) {
        e.preventDefault();
        setOpen((open) => !open);
      }
    };

    document.addEventListener('keydown', down);
    return () => document.removeEventListener('keydown', down);
  }, []);

  React.useEffect(() => {
    if (open && risks.length === 0) {
      setLoading(true);
      Promise.all([fetchRisks(), fetchControls()]).then(([r, c]) => {
        setRisks(r);
        setControls(c);
        setLoading(false);
      });
    }
  }, [open, risks.length]);

  const runCommand = React.useCallback((command: () => void) => {
    setOpen(false);
    command();
  }, []);

  return (
    <>
      <button
        onClick={() => setOpen(true)}
        className="hidden md:flex items-center gap-2 px-3 py-1.5 text-sm text-slate-500 bg-slate-100 dark:bg-slate-800 dark:text-slate-400 rounded-md border border-transparent hover:border-slate-300 dark:hover:border-slate-600 transition-all w-64 group"
      >
        <Search className="h-4 w-4 group-hover:text-slate-900 dark:group-hover:text-white transition-colors" />
        <span>Search platform...</span>
        <kbd className="ml-auto pointer-events-none inline-flex h-5 select-none items-center gap-1 rounded border bg-white dark:bg-slate-900 px-1.5 font-mono text-[10px] font-medium opacity-100">
          <span className="text-xs">⌘</span>K
        </kbd>
      </button>

      <CommandDialog open={open} onOpenChange={setOpen}>
        <CommandInput placeholder="Type a command or search..." />
        <CommandList>
          <CommandEmpty>No results found.</CommandEmpty>
          
          <CommandGroup heading="Navigation">
            <CommandItem onSelect={() => runCommand(() => router.push('/dashboard'))}>
              <Home className="mr-2 h-4 w-4" />
              <span>Dashboard</span>
            </CommandItem>
            <CommandItem onSelect={() => runCommand(() => router.push('/dashboard/risks'))}>
              <AlertTriangle className="mr-2 h-4 w-4 text-amber-500" />
              <span>Risk Management</span>
            </CommandItem>
            <CommandItem onSelect={() => runCommand(() => router.push('/dashboard/controls'))}>
              <Shield className="mr-2 h-4 w-4 text-blue-500" />
              <span>Control Inventory</span>
            </CommandItem>
            <CommandItem onSelect={() => runCommand(() => router.push('/dashboard/settings'))}>
              <Settings className="mr-2 h-4 w-4" />
              <span>Settings</span>
            </CommandItem>
          </CommandGroup>

          {risks.length > 0 && (
            <>
              <CommandSeparator />
              <CommandGroup heading="Risks">
                {risks.slice(0, 5).map((risk) => (
                  <CommandItem 
                    key={risk.id}
                    onSelect={() => runCommand(() => router.push(`/dashboard/risks/${risk.id}`))}
                    className="flex justify-between items-center"
                  >
                    <div className="flex items-center">
                      <AlertTriangle className="mr-2 h-4 w-4 text-slate-400" />
                      <span>{risk.title}</span>
                    </div>
                    <Badge variant="outline" className="text-[10px] h-4">
                      {risk.status}
                    </Badge>
                  </CommandItem>
                ))}
                {risks.length > 5 && (
                  <CommandItem onSelect={() => runCommand(() => router.push('/dashboard/risks'))}>
                    <span className="text-blue-600 text-xs ml-6">View all {risks.length} risks...</span>
                  </CommandItem>
                )}
              </CommandGroup>
            </>
          )}

          {controls.length > 0 && (
            <>
              <CommandSeparator />
              <CommandGroup heading="Controls">
                {controls.slice(0, 5).map((control) => (
                  <CommandItem 
                    key={control.id}
                    onSelect={() => runCommand(() => router.push(`/dashboard/controls/${control.id}`))}
                    className="flex justify-between items-center"
                  >
                    <div className="flex items-center">
                      <Shield className="mr-2 h-4 w-4 text-slate-400" />
                      <span>
                        <span className="font-semibold mr-1">{control.code}</span>
                        {control.title}
                      </span>
                    </div>
                    {control.status === 'implemented' && (
                      <CheckCircle2 className="h-3 w-3 text-green-500" />
                    )}
                  </CommandItem>
                ))}
                {controls.length > 5 && (
                  <CommandItem onSelect={() => runCommand(() => router.push('/dashboard/controls'))}>
                    <span className="text-blue-600 text-xs ml-6">View all {controls.length} controls...</span>
                  </CommandItem>
                )}
              </CommandGroup>
            </>
          )}
        </CommandList>
      </CommandDialog>
    </>
  );
}
