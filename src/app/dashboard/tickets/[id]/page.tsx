'use client';

import { useParams } from 'next/navigation';
import { mockTickets, mockAuditLogs } from '@/lib/mock-data';
import { TicketDetail } from '@/features/tickets/TicketDetail';
import { Card, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { ArrowLeft, Ticket } from 'lucide-react';
import Link from 'next/link';

export default function TicketDetailPage() {
  const params = useParams();
  const ticketId = params.id as string;

  const ticket = mockTickets.find(t => t.id === ticketId);
  const sourceAuditLog = ticket
    ? mockAuditLogs.find(log => log.id === ticket.sourceAuditLogId)
    : undefined;

  if (!ticket) {
    return (
      <div className="space-y-4">
        <Link
          href="/dashboard/tickets"
          className="inline-flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground transition-colors"
        >
          <ArrowLeft className="h-4 w-4" />
          Back to Tickets
        </Link>
        <Card className="border-dashed">
          <CardContent className="py-16 text-center">
            <Ticket className="h-12 w-12 text-muted-foreground/30 mx-auto mb-4" />
            <h3 className="text-lg font-medium text-foreground mb-2">Ticket Not Found</h3>
            <p className="text-sm text-muted-foreground mb-4">
              The ticket you&apos;re looking for doesn&apos;t exist or has been removed.
            </p>
            <Link href="/dashboard/tickets">
              <Button variant="outline">View All Tickets</Button>
            </Link>
          </CardContent>
        </Card>
      </div>
    );
  }

  return <TicketDetail ticket={ticket} sourceAuditLog={sourceAuditLog} />;
}
