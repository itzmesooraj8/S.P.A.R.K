/**
 * useActivityTracker — "What changed since last look"
 *
 * Tracks newly-seen events using IntersectionObserver.
 * When an event row scrolls into the viewport, its ID is marked as seen.
 * Returns helpers to attach observation refs and check if an event is NEW.
 */
import { useCallback, useEffect, useRef } from 'react';
import { useMonitorStore } from '@/store/useMonitorStore';

export function useActivityTracker() {
  const newEventIds  = useMonitorStore((s) => s.newEventIds);
  const markAsSeen   = useMonitorStore((s) => s.markAsSeen);
  const observerRef  = useRef<IntersectionObserver | null>(null);
  const pendingSeen  = useRef<string[]>([]);
  const flushTimer   = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Flush pending "seen" IDs in a batch every 500 ms
  const flush = useCallback(() => {
    if (pendingSeen.current.length > 0) {
      markAsSeen([...pendingSeen.current]);
      pendingSeen.current = [];
    }
  }, [markAsSeen]);

  useEffect(() => {
    observerRef.current = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            const id = (entry.target as HTMLElement).dataset.eventId;
            if (id) pendingSeen.current.push(id);
          }
        });
        if (flushTimer.current) clearTimeout(flushTimer.current);
        flushTimer.current = setTimeout(flush, 500);
      },
      { threshold: 0.5 }
    );
    return () => {
      observerRef.current?.disconnect();
      if (flushTimer.current) clearTimeout(flushTimer.current);
    };
  }, [flush]);

  /** Attach this ref callback to any element that represents an event row */
  const observe = useCallback((el: HTMLElement | null, eventId: string) => {
    if (!el || !observerRef.current) return;
    el.dataset.eventId = eventId;
    observerRef.current.observe(el);
    return () => observerRef.current?.unobserve(el);
  }, []);

  /** Returns true if the event ID is newly fetched and not yet seen */
  const isNew = useCallback(
    (id: string) => newEventIds.includes(id),
    [newEventIds]
  );

  return { isNew, observe, newCount: newEventIds.length };
}
