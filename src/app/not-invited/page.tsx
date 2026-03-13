"use client";

import { useRouter } from "next/navigation";
import { ShieldX, ArrowLeft, Mail } from "lucide-react";

export default function NotInvitedPage() {
  const router = useRouter();

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 to-slate-100 flex items-center justify-center p-4">
      <div className="w-full max-w-md text-center">
        <div className="bg-white rounded-2xl shadow-lg border border-slate-200 p-8">
          {/* Icon */}
          <div className="mx-auto w-16 h-16 bg-amber-50 rounded-full flex items-center justify-center mb-6">
            <ShieldX className="h-8 w-8 text-amber-600" />
          </div>

          {/* Title */}
          <h1 className="text-2xl font-bold text-slate-900 mb-2">
            Access Restricted
          </h1>

          {/* Description */}
          <p className="text-slate-600 mb-6 leading-relaxed">
            Your email has not been invited to this platform. 
            Only invited users can access the GRC Platform.
          </p>

          {/* Info box */}
          <div className="bg-slate-50 rounded-lg p-4 mb-6 text-left">
            <p className="text-sm text-slate-700 font-medium mb-2">
              How to get access:
            </p>
            <ul className="text-sm text-slate-600 space-y-1">
              <li className="flex items-start gap-2">
                <Mail className="h-4 w-4 mt-0.5 text-slate-400 flex-shrink-0" />
                Contact your organization administrator
              </li>
              <li className="flex items-start gap-2">
                <Mail className="h-4 w-4 mt-0.5 text-slate-400 flex-shrink-0" />
                Ask them to send you an invitation
              </li>
            </ul>
          </div>

          {/* Back button */}
          <button
            onClick={() => router.push("/login")}
            className="inline-flex items-center gap-2 px-4 py-2 text-sm font-medium text-slate-700 bg-slate-100 hover:bg-slate-200 rounded-lg transition-colors"
          >
            <ArrowLeft className="h-4 w-4" />
            Back to Login
          </button>
        </div>
      </div>
    </div>
  );
}
