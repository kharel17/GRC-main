
"use client";

import { ISOControlList } from "@/features/iso27001/ISOControlList";

export default function ISOControlsPage() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-slate-900 mb-1">ISO 27001 Controls</h1>
        <p className="text-sm text-slate-600">
          Manage implementation status for Annex A controls.
        </p>
      </div>

      <ISOControlList />
    </div>
  );
}
