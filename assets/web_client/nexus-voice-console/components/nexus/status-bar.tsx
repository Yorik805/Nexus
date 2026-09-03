'use client'

import { useEffect, useState } from 'react'
import type { ConnectionState, ConsoleMode, VoiceState } from '@/lib/nexus/types'
import { formatClock } from '@/lib/nexus/format'

const VOICE_LABEL: Record<VoiceState, string> = {
  idle: 'STANDBY',
  listening: 'LISTENING',
  user_speaking: 'USER SPEAKING',
  processing: 'PROCESSING',
  nexus_speaking: 'NEXUS SPEAKING',
  interruption: 'INTERRUPTION',
  mic_disabled: 'MIC OFF',
  error: 'ERROR',
}

export function StatusBar({
  connection,
  voiceState,
  mode,
  latencyMs,
}: {
  connection: ConnectionState
  voiceState: VoiceState
  mode: ConsoleMode
  latencyMs: number
}) {
  const [clock, setClock] = useState('')
  useEffect(() => {
    const update = () => setClock(formatClock(Date.now()))
    update()
    const t = setInterval(update, 1000)
    return () => clearInterval(t)
  }, [])

  return (
    <footer className="flex items-center justify-between gap-4 border-t border-border bg-card/40 px-5 py-2 font-mono text-[10px] tracking-widest text-muted-foreground backdrop-blur">
      <div className="flex items-center gap-4">
        <Segment label="MODE" value={mode.toUpperCase()} />
        <Segment label="STATE" value={VOICE_LABEL[voiceState]} />
        <Segment label="LINK" value={connection.toUpperCase()} />
        <Segment
          label="LATENCY"
          value={connection === 'connected' ? `${latencyMs}MS` : '—'}
        />
      </div>
      <div className="flex items-center gap-4">
        <span className="hidden items-center gap-1.5 sm:flex">
          <span className="size-1.5 rounded-full bg-cat-validator" />
          LIVE NEXUS CLIENT
        </span>
        <span className="tabular-nums text-foreground/70">{clock}</span>
      </div>
    </footer>
  )
}

function Segment({ label, value }: { label: string; value: string }) {
  return (
    <span className="flex items-center gap-1.5">
      <span className="text-muted-foreground/50">{label}</span>
      <span className="text-foreground/80">{value}</span>
    </span>
  )
}
