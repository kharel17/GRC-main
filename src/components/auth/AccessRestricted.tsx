'use client';

import Link from 'next/link';
import { ShieldAlert, ArrowLeft } from 'lucide-react';
import { Button } from '@/components/ui/button';

export function AccessRestricted() {
  return (
    <div className="flex flex-col items-center justify-center min-h-[60vh] text-center px-4">
      <div className="w-16 h-16 bg-red-100 rounded-full flex items-center justify-center mb-6">
        <ShieldAlert className="h-8 w-8 text-red-600" />
      </div>
      <h1 className="text-2xl font-bold text-slate-900 mb-2">Access Restricted</h1>
      <p className="text-slate-600 mb-8 max-w-md">
        You don't have permission to access this feature. 
        Please contact your administrator if you believe this is an error.
      </p>
      <div className="flex flex-col sm:flex-row gap-3">
        <Button asChild variant="outline">
          <Link href="/dashboard" className="gap-2">
            <ArrowLeft className="h-4 w-4" />
            Go to Dashboard
          </Link>
        </Button>
      </div>
    </div>
  );
}
