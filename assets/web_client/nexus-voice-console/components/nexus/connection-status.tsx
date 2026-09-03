'use client'

import { useEffect, useState } from 'react'
import type { NexusStatus } from '@/lib/nexus/types'
import { formatAgo } from '@/lib/nexus/format'
import { ConnectionIndicator } from './connection-indicator'

/** Compact Nexus status readout. */
export function ConnectionStatus({ status }: { status: NexusStatus }) {
  // Re-render the "time ago" label roughly once per second.
  const [, force] = useState(0)
  useEffect(() => {
    const t = setInterval(() => force((n) => n + 1), 1000)
    return () => clearInterval(t)
  }, [])

  return (
    <section
      aria-label="Nexus status"
      className="border-b border-border px-4 py-4"
    >
      <h3 className="mb-3 font-mono text-[10px] tracking-[0.3em] text-muted-foreground">
        NEXUS STATUS
      </h3>

      <ConnectionIndicator state={status.connection} className="mb-4" />

      <dl className="flex flex-col gap-3">
        <StatusRow label="Endpoint" value={status.endpointLabel} mono />
        <StatusRow
          label="Latency"
          value={status.connection === 'connected' ? `${status.latencyMs} ms` : '—'}
        />
        <StatusRow
          label="Last communication"
          value={
            status.connection !== 'connected'
              ? 'No signal'
              : status.lastCommunication > 0
                ? formatAgo(status.lastCommunication)
                : '—'
          }
        />
      </dl>
    </section>
  )
}

function StatusRow({
  label,
  value,
  mono,
}: {
  label: string
  value: string
  mono?: boolean
}) {
  return (
    <div className="flex items-baseline justify-between gap-3">
      <dt className="font-mono text-[10px] uppercase tracking-widest text-muted-foreground/70">
        {label}
      </dt>
      <dd
        className={
          'truncate text-right text-xs text-foreground/90' + (mono ? ' font-mono' : ' tabular-nums')
        }
      >
        {value}
      </dd>
    </div>
  )
}
