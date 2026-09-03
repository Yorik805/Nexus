import { cn } from '@/lib/utils'
import type { ConnectionState } from '@/lib/nexus/types'

export const CONNECTION_META: Record<
  ConnectionState,
  { label: string; dot: string; text: string; pulse: boolean }
> = {
  connected: { label: 'CONNECTED', dot: 'bg-cat-result', text: 'text-cat-result', pulse: false },
  connecting: { label: 'CONNECTING', dot: 'bg-cat-validator', text: 'text-cat-validator', pulse: true },
  retrying: { label: 'RETRYING', dot: 'bg-cat-validator', text: 'text-cat-validator', pulse: true },
  disconnected: { label: 'DISCONNECTED', dot: 'bg-muted-foreground', text: 'text-muted-foreground', pulse: false },
  error: { label: 'ERROR', dot: 'bg-cat-error', text: 'text-cat-error', pulse: true },
}

export function ConnectionIndicator({
  state,
  className,
  size = 'md',
}: {
  state: ConnectionState
  className?: string
  size?: 'sm' | 'md'
}) {
  const meta = CONNECTION_META[state]
  return (
    <div className={cn('flex items-center gap-2', className)}>
      <span className="relative flex items-center justify-center">
        {meta.pulse && (
          <span
            className={cn('absolute inline-flex rounded-full opacity-60 animate-ping', meta.dot, size === 'sm' ? 'size-2' : 'size-2.5')}
            aria-hidden
          />
        )}
        <span className={cn('relative inline-flex rounded-full', meta.dot, size === 'sm' ? 'size-2' : 'size-2.5')} />
      </span>
      <span
        className={cn(
          'font-mono font-medium tracking-widest',
          meta.text,
          size === 'sm' ? 'text-[10px]' : 'text-xs',
        )}
      >
        {meta.label}
      </span>
    </div>
  )
}
