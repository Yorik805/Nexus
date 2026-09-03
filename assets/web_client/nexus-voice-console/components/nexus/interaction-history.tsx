'use client'

import { cn } from '@/lib/utils'
import type { Interaction } from '@/lib/nexus/types'
import { formatClock } from '@/lib/nexus/format'

/**
 * Shows only the three most recent request/response conversations.
 * Intentionally NOT a full-screen chat log — this is a status surface.
 * Replace `interactions` with real Nexus request/response data.
 */
export function InteractionHistory({ interactions }: { interactions: Interaction[] }) {
  const recent = interactions.slice(-6).reverse()
  return (
    <section
      aria-label="Recent interaction"
      className="border-t border-border bg-card/30 px-6 py-4"
    >
      <div className="mb-3 flex items-center justify-between">
        <h3 className="font-mono text-[10px] tracking-[0.3em] text-muted-foreground">
          LATEST INTERACTION
        </h3>
        <span className="font-mono text-[10px] tracking-widest text-muted-foreground/60">
          {Math.ceil(interactions.length / 2)} CONVERSATIONS
        </span>
      </div>

      <div className="flex flex-col gap-2.5">
        {recent.length === 0 && (
          <p className="font-mono text-xs text-muted-foreground">No interactions yet.</p>
        )}
        {recent.map((it) => (
          <div key={it.id} className="flex gap-3">
            <span
              className={cn(
                'mt-0.5 shrink-0 font-mono text-[10px] font-semibold tracking-widest',
                it.role === 'user' ? 'text-primary' : 'text-cat-event',
              )}
            >
              {it.role === 'user' ? 'YOU' : 'NEXUS'}
            </span>
            <p className="min-w-0 flex-1 text-pretty text-sm leading-relaxed text-foreground/90">
              {it.text}
            </p>
            <span className="mt-0.5 shrink-0 font-mono text-[10px] text-muted-foreground/60">
              {formatClock(it.timestamp)}
            </span>
          </div>
        ))}
      </div>
    </section>
  )
}
