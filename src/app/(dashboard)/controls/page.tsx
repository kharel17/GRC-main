'use client';

import { mockControls } from '@/lib/mock-data';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Plus } from 'lucide-react';

export default function ControlsPage() {
  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 mb-1">Controls</h1>
          <p className="text-sm text-slate-600">Manage risk mitigation controls</p>
        </div>
        <Button className="gap-2">
          <Plus className="h-4 w-4" />
          New Control
        </Button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {mockControls.map((control) => (
          <Card key={control.id} className="hover:shadow-md transition-shadow">
            <CardHeader className="pb-3">
              <CardTitle className="text-sm">{control.title}</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              <p className="text-xs text-slate-600">{control.description}</p>
              <div className="flex flex-wrap gap-2">
                <Badge variant="outline" className="text-xs">
                  {control.controlType}
                </Badge>
                <Badge
                  variant="secondary"
                  className="text-xs capitalize"
                >
                  {control.effectiveness}
                </Badge>
                <Badge variant="outline" className="text-xs capitalize">
                  {control.status}
                </Badge>
              </div>
              <p className="text-xs text-slate-500">Owner: {control.ownerName}</p>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  );
}
