'use client';

import { useState, useEffect, ReactNode } from 'react';
import { Card, CardContent } from '@/components/ui/card';

interface ResponsiveTableProps {
  children: ReactNode;
  mobileCardRenderer?: (item: Record<string, unknown>, index: number) => ReactNode;
  data?: Record<string, unknown>[];
  breakpoint?: number;
}

function useMediaQuery(query: string): boolean {
  const [matches, setMatches] = useState(false);

  useEffect(() => {
    const media = window.matchMedia(query);
    if (media.matches !== matches) {
      setMatches(media.matches);
    }
    const listener = () => setMatches(media.matches);
    media.addEventListener('change', listener);
    return () => media.removeEventListener('change', listener);
  }, [matches, query]);

  return matches;
}

export function ResponsiveTable({ 
  children, 
  mobileCardRenderer, 
  data = [],
  breakpoint = 768 
}: ResponsiveTableProps) {
  const isMobile = useMediaQuery(`(max-width: ${breakpoint}px)`);

  // If mobile view is requested but no card renderer provided, wrap table in scrollable container
  if (isMobile && mobileCardRenderer && data.length > 0) {
    return (
      <div className="space-y-3">
        {data.map((item, index) => mobileCardRenderer(item, index))}
      </div>
    );
  }

  // Default: horizontal scroll wrapper for tables on mobile
  return (
    <div className="overflow-x-auto -mx-4 px-4 sm:mx-0 sm:px-0">
      <div className="min-w-full inline-block align-middle">
        {children}
      </div>
    </div>
  );
}

// Empty state component for lists
interface EmptyStateProps {
  icon?: ReactNode;
  title: string;
  description?: string;
  action?: ReactNode;
}

export function EmptyState({ icon, title, description, action }: EmptyStateProps) {
  return (
    <Card className="border-dashed">
      <CardContent className="py-12 text-center">
        {icon && (
          <div className="mx-auto w-12 h-12 rounded-full bg-slate-100 flex items-center justify-center mb-4">
            {icon}
          </div>
        )}
        <h3 className="text-sm font-medium text-slate-900 mb-1">{title}</h3>
        {description && (
          <p className="text-sm text-slate-500 mb-4">{description}</p>
        )}
        {action}
      </CardContent>
    </Card>
  );
}

// Loading skeleton for lists
export function ListSkeleton({ rows = 5 }: { rows?: number }) {
  return (
    <div className="space-y-3">
      {Array.from({ length: rows }).map((_, i) => (
        <div key={i} className="animate-pulse">
          <div className="h-16 bg-slate-100 rounded-lg" />
        </div>
      ))}
    </div>
  );
}

// Card-based skeleton
export function CardSkeleton({ count = 3 }: { count?: number }) {
  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
      {Array.from({ length: count }).map((_, i) => (
        <Card key={i} className="animate-pulse">
          <CardContent className="pt-6 space-y-3">
            <div className="h-4 bg-slate-100 rounded w-3/4" />
            <div className="h-3 bg-slate-100 rounded w-full" />
            <div className="h-3 bg-slate-100 rounded w-1/2" />
            <div className="flex gap-2 mt-4">
              <div className="h-5 w-16 bg-slate-100 rounded-full" />
              <div className="h-5 w-16 bg-slate-100 rounded-full" />
            </div>
          </CardContent>
        </Card>
      ))}
    </div>
  );
}
