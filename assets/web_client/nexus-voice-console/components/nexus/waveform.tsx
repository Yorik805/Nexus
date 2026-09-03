'use client'

import { useEffect, useRef, useState } from 'react'
import { cn } from '@/lib/utils'

/** Visual activity indicator for microphone and speech playback. */
export function Waveform({
  active,
  bars = 28,
  className,
  colorClass = 'bg-primary',
}: {
  active: boolean
  bars?: number
  className?: string
  colorClass?: string
}) {
  const [amps, setAmps] = useState<number[]>(() => Array(bars).fill(0.15))
  const raf = useRef<number | null>(null)

  useEffect(() => {
    if (!active) {
      setAmps(Array(bars).fill(0.12))
      return
    }
    let last = 0
    const tick = (t: number) => {
      if (t - last > 80) {
        last = t
        setAmps((prev) =>
          prev.map((_, i) => {
            const center = 1 - Math.abs(i - bars / 2) / (bars / 2)
            return 0.15 + Math.random() * (0.35 + center * 0.6)
          }),
        )
      }
      raf.current = requestAnimationFrame(tick)
    }
    raf.current = requestAnimationFrame(tick)
    return () => {
      if (raf.current) cancelAnimationFrame(raf.current)
    }
  }, [active, bars])

  return (
    <div className={cn('flex h-16 items-center justify-center gap-[3px]', className)} aria-hidden>
      {amps.map((a, i) => (
        <span
          key={i}
          className={cn('w-1 rounded-full transition-[height] duration-100 ease-out', colorClass)}
          style={{ height: `${Math.max(6, a * 100)}%`, opacity: active ? 0.5 + a * 0.5 : 0.3 }}
        />
      ))}
    </div>
  )
}
