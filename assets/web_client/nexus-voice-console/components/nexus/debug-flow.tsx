import type { NexusEvent } from '@/lib/nexus/types'

/** Mirrors the event table in the original Nexus dashboard using live API data. */
export function DebugFlow({ events }: { events: NexusEvent[] }) {
  const visible = events.slice().reverse()

  return (
    <section
      aria-label="Live Nexus events"
      className="border-b border-border px-4 py-3"
    >
      <div className="mb-3 flex items-center justify-between">
        <h3 className="font-mono text-[10px] font-semibold tracking-[0.25em] text-foreground">
          LIVE EVENT STREAM
        </h3>
        <span className="font-mono text-[10px] tracking-widest text-cat-result">
          {visible.length.toString().padStart(2, '0')} EVENTS
        </span>
      </div>
      <div className="max-h-64 overflow-x-auto overflow-y-auto" aria-live="polite">
        <div className="min-w-[28rem] px-2">
          <div className="grid grid-cols-[4.25rem_6.5rem_5rem_minmax(12rem,1fr)] gap-2 border-b border-border pb-2 font-mono text-[9px] tracking-widest text-muted-foreground/60">
            <span>TIME</span>
            <span>TYPE</span>
            <span>SOURCE</span>
            <span>PAYLOAD</span>
          </div>
          {visible.length === 0 ? (
            <p className="py-4 font-mono text-xs text-muted-foreground">Waiting for Nexus events.</p>
          ) : (
            visible.map((event) => (
              <div
                key={event.id}
                className="grid grid-cols-[4.25rem_6.5rem_5rem_minmax(12rem,1fr)] gap-2 border-b border-border/50 py-2 font-mono text-[10px]"
              >
                <span className="text-muted-foreground/70">{event.time || '—'}</span>
                <span className="truncate text-cat-event">{event.kind || event.label}</span>
                <span className="truncate text-foreground/70">{event.source || '—'}</span>
                <span className="truncate text-foreground/90">{event.message || event.description}</span>
              </div>
            ))
          )}
        </div>
      </div>
    </section>
  )
}
