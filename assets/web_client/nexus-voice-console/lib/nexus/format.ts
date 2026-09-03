/** Formatting helpers for the console UI. */

/** HH:MM:SS from an epoch-ms timestamp. */
export function formatClock(ts: number): string {
  const d = new Date(ts)
  return d.toLocaleTimeString('en-GB', { hour12: false })
}

/** Relative "time ago" label for last-communication style fields. */
export function formatAgo(ts: number, now = Date.now()): string {
  const diff = Math.max(0, now - ts)
  const s = Math.round(diff / 1000)
  if (s < 2) return 'Just now'
  if (s < 60) return `${s}s ago`
  const m = Math.floor(s / 60)
  if (m < 60) return `${m}m ago`
  const h = Math.floor(m / 60)
  return `${h}h ago`
}
