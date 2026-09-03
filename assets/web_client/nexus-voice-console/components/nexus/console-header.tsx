'use client'

import { Mic, MicOff, RotateCw } from 'lucide-react'
import { cn } from '@/lib/utils'
import type { ConnectionState, ConsoleMode } from '@/lib/nexus/types'
import { ConnectionIndicator } from './connection-indicator'

export function ConsoleHeader({
  connection,
  micEnabled,
  mode,
  onRetry,
  onToggleMic,
  onModeChange,
}: {
  connection: ConnectionState
  micEnabled: boolean
  mode: ConsoleMode
  onRetry: () => void
  onToggleMic: () => void
  onModeChange: (mode: ConsoleMode) => void
}) {
  const retrying = connection === 'retrying' || connection === 'connecting'
  return (
    <header className="flex items-center justify-between gap-4 border-b border-border bg-card/40 px-5 py-3 backdrop-blur">
      {/* Left: brand */}
      <div className="flex items-center gap-3">
        <div className="flex size-9 items-center justify-center rounded-md bg-primary/15 ring-1 ring-primary/30">
          <span className="size-2.5 rounded-full bg-primary shadow-[0_0_12px_var(--color-primary)]" />
        </div>
        <div className="leading-none">
          <h1 className="font-mono text-base font-semibold tracking-[0.25em] text-foreground">
            NEXUS
          </h1>
          <p className="mt-1 font-mono text-[10px] tracking-[0.35em] text-muted-foreground">
            VOICE CONSOLE
          </p>
        </div>
      </div>

      {/* Center: mode switch */}
      <ModeSwitch mode={mode} onModeChange={onModeChange} />

      {/* Right: status + controls */}
      <div className="flex items-center gap-3">
        <div className="hidden rounded-md border border-border bg-background/50 px-3 py-2 sm:block">
          <ConnectionIndicator state={connection} />
        </div>

        <button
          type="button"
          onClick={onRetry}
          className="flex items-center gap-2 rounded-md border border-border bg-background/50 px-3 py-2 font-mono text-xs tracking-wide text-muted-foreground transition-colors hover:border-primary/40 hover:text-foreground"
        >
          <RotateCw className={cn('size-3.5', retrying && 'animate-nexus-spin')} />
          <span className="hidden md:inline">RETRY</span>
        </button>

        <button
          type="button"
          onClick={onToggleMic}
          aria-pressed={micEnabled}
          className={cn(
            'flex items-center gap-2 rounded-md border px-3 py-2 font-mono text-xs tracking-wide transition-colors',
            micEnabled
              ? 'border-primary/40 bg-primary/15 text-primary'
              : 'border-border bg-background/50 text-muted-foreground hover:text-foreground',
          )}
        >
          {micEnabled ? <Mic className="size-3.5" /> : <MicOff className="size-3.5" />}
          <span className="hidden md:inline">{micEnabled ? 'MIC ON' : 'MIC OFF'}</span>
        </button>
      </div>
    </header>
  )
}

function ModeSwitch({
  mode,
  onModeChange,
}: {
  mode: ConsoleMode
  onModeChange: (mode: ConsoleMode) => void
}) {
  return (
    <div className="flex items-center rounded-md border border-border bg-background/50 p-0.5">
      {(['normal', 'debug'] as const).map((m) => (
        <button
          key={m}
          type="button"
          onClick={() => onModeChange(m)}
          className={cn(
            'rounded px-3 py-1.5 font-mono text-[11px] font-medium uppercase tracking-widest transition-colors',
            mode === m
              ? 'bg-primary/20 text-primary'
              : 'text-muted-foreground hover:text-foreground',
          )}
        >
          {m}
        </button>
      ))}
    </div>
  )
}
