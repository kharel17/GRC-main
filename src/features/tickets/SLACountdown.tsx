'use client';

import { useState, useEffect } from 'react';
import { differenceInSeconds, parseISO } from 'date-fns';

interface SLACountdownProps {
  dueDate: string;
}

export function SLACountdown({ dueDate }: SLACountdownProps) {
  const [timeLeft, setTimeLeft] = useState<string>('00:00:00');
  const [isUrgent, setIsUrgent] = useState(false);

  useEffect(() => {
    const timer = setInterval(() => {
      const now = new Date();
      const due = parseISO(dueDate);
      const diff = differenceInSeconds(due, now);

      if (diff <= 0) {
        setTimeLeft('00:00:00');
        setIsUrgent(true);
        clearInterval(timer);
        return;
      }

      const hours = Math.floor(diff / 3600);
      const minutes = Math.floor((diff % 3600) / 60);
      const seconds = diff % 60;

      const display = [
        hours.toString().padStart(2, '0'),
        minutes.toString().padStart(2, '0'),
        seconds.toString().padStart(2, '0')
      ].join(':');

      setTimeLeft(display);
      setIsUrgent(hours < 24);
    }, 1000);

    return () => clearInterval(timer);
  }, [dueDate]);

  return (
    <div className="text-right">
      <span className={`text-[10px] uppercase font-bold tracking-wider ${isUrgent ? 'text-red-600' : 'text-slate-500'}`}>
        Remaining
      </span>
      <div className={`text-xs font-mono font-bold tabular-nums ${isUrgent ? 'text-red-700' : 'text-slate-700'}`}>
        {timeLeft}
      </div>
    </div>
  );
}
