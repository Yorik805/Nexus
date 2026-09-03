'use client'

import { useEffect, useRef, useState } from 'react'
import { cn } from '@/lib/utils'
import {
  CATEGORY_LABEL,
  EVENT_FILTERS,
  type EventCategory,
  type NexusEvent,
} from '@/lib/nexus/types'
import { formatClock } from '@/lib/nexus/format'

const CATEGORY_BADGE: Record<EventCategory, string> = {
  event: 'bg-cat-event/12 text-cat-event',
  orchestrator: 'bg-cat-orchestrator/12 text-cat-orchestrator',
  validator: 'bg-cat-validator/12 text-cat-validator',
  plugin: 'bg-cat-plugin/12 text-cat-plugin',
  result: 'bg-cat-result/12 text-cat-result',
  error: 'bg-cat-error/12 text-cat-error',
}

/** Compact runtime event monitor fed by the live Nexus dashboard API. */
export function EventMonitor({
  events,
  className,
}: {
  events: NexusEvent[]
  className?: string
}) {
  const [filter, setFilter] = useState<EventCategory | 'all'>('all')
  const [autoScroll, setAutoScroll] = useState(true)
  const scrollRef = useRef<HTMLDivElement>(null)

  const visible = events
    .filter((e) => filter === 'all' || e.category === filter)
    .slice()
    .reverse()

  useEffect(() => {
    if (autoScroll && scrollRef.current) {
      scrollRef.current.scrollTop = 0
    }
  }, [visible.length, autoScroll])

  return (
    <div className={cn('flex h-full min-h-0 flex-col', className)}>
      {/* Header */}
      <div className="flex items-center justify-between border-b border-border px-4 py-3">
        <h3 className="font-mono text-xs font-semibold tracking-[0.25em] text-foreground">
          NEXUS EVENTS
        </h3>
        <button
          type="button"
          onClick={() => setAutoScroll((v) => !v)}
          className={cn(
            'flex items-center gap-1.5 font-mono text-[10px] tracking-widest transition-colors',
            autoScroll ? 'text-cat-result' : 'text-muted-foreground hover:text-foreground',
          )}
          aria-pressed={autoScroll}
        >
          <span className={cn('size-1.5 rounded-full', autoScroll ? 'bg-cat-result' : 'bg-muted-foreground')} />
          AUTO-SCROLL
        </button>
      </div>

      {/* Filters */}
      <div className="flex flex-wrap items-center gap-1 border-b border-border px-3 py-2">
        {EVENT_FILTERS.map((f) => (
          <button
            key={f.id}
            type="button"
            onClick={() => setFilter(f.id)}
            className={cn(
              'rounded px-2 py-1 font-mono text-[10px] tracking-widest transition-colors',
              filter === f.id
                ? 'bg-secondary text-foreground'
                : 'text-muted-foreground hover:bg-secondary/50 hover:text-foreground',
            )}
          >
            {f.label}
          </button>
        ))}
      </div>

      {/* Event list */}
      <div ref={scrollRef} className="min-h-0 flex-1 overflow-y-auto px-2 py-2">
        {visible.length === 0 ? (
          <p className="px-2 py-4 font-mono text-xs text-muted-foreground">
            No events for this filter.
          </p>
        ) : (
          <ul className="flex flex-col gap-1">
            {visible.map((e) => (
              <li
                key={e.id}
                className="group rounded-md px-2 py-1.5 transition-colors hover:bg-secondary/40"
              >
                <div className="flex items-center gap-2">
                  <span className="font-mono text-[10px] tabular-nums text-muted-foreground/70">
                    {formatClock(e.timestamp)}
                  </span>
                  <span
                    className={cn(
                      'rounded-sm px-1.5 py-0.5 font-mono text-[9px] font-semibold tracking-wider',
                      CATEGORY_BADGE[e.category],
                    )}
                  >
                    {CATEGORY_LABEL[e.category]}
                  </span>
                  <span className="truncate font-mono text-[11px] text-foreground/80">
                    {e.label}
                  </span>
                </div>
                <p className="mt-0.5 pl-[3.75rem] font-mono text-[11px] text-muted-foreground">
                  {e.description}
                </p>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  )
}
