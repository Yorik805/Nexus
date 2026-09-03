/**
 * Nexus Voice Console — domain model
 * -----------------------------------
 * These types describe the shape of the data the console works with.
 *
 * These types are used by the live client and browser voice controls:
 *
 *   ConnectionState  <-  real Nexus HTTP health / handshake
 *   VoiceState       <-  real mic input + speech recognition + TTS playback
 *   NexusEvent       <-  real Nexus runtime event stream (SSE / WebSocket)
 *   Interaction      <-  real request/response pairs to the Nexus HTTP API
 *   NexusStatus      <-  real endpoint config, latency, last-communication ping
 */

/** High-level link state between this client and the Nexus runtime. */
export type ConnectionState =
  | 'connected'
  | 'connecting'
  | 'disconnected'
  | 'retrying'
  | 'error'

/** The voice-interaction lifecycle shown in the main panel. */
export type VoiceState =
  | 'idle'
  | 'listening'
  | 'user_speaking'
  | 'processing'
  | 'nexus_speaking'
  | 'interruption'
  | 'mic_disabled'
  | 'error'

/** Category of a Nexus runtime event, used for color coding + filtering. */
export type EventCategory =
  | 'event'
  | 'orchestrator'
  | 'validator'
  | 'plugin'
  | 'result'
  | 'error'

export interface NexusEvent {
  id: string
  /** Epoch ms — formatted for display in the monitor. */
  timestamp: number
  category: EventCategory
  /** Short machine-style label, e.g. "USER_EVENT", "terminal.EXECUTE". */
  label: string
  /** Human-readable one-line description. */
  description: string
  /** Original dashboard event fields, preserved for the debug stream. */
  time?: string
  kind?: string
  source?: string
  message?: string
}

export interface Interaction {
  id: string
  role: 'user' | 'nexus'
  text: string
  timestamp: number
}

export interface NexusStatus {
  connection: ConnectionState
  /** Display label for the server-side configured endpoint. */
  endpointLabel: string
  /** Round-trip latency in ms. */
  latencyMs: number
  /** Epoch ms of last successful communication. */
  lastCommunication: number
}

/** UI display mode toggle. */
export type ConsoleMode = 'normal' | 'debug'

export const EVENT_FILTERS: { id: EventCategory | 'all'; label: string }[] = [
  { id: 'all', label: 'ALL' },
  { id: 'event', label: 'EVENT' },
  { id: 'orchestrator', label: 'ORCHESTRATOR' },
  { id: 'validator', label: 'VALIDATOR' },
  { id: 'plugin', label: 'PLUGIN' },
  { id: 'result', label: 'RESULT' },
  { id: 'error', label: 'ERROR' },
]

/** Tailwind text-color token per category (see globals.css `--cat-*`). */
export const CATEGORY_COLOR: Record<EventCategory, string> = {
  event: 'text-cat-event',
  orchestrator: 'text-cat-orchestrator',
  validator: 'text-cat-validator',
  plugin: 'text-cat-plugin',
  result: 'text-cat-result',
  error: 'text-cat-error',
}

export const CATEGORY_LABEL: Record<EventCategory, string> = {
  event: 'EVENT',
  orchestrator: 'ORCHESTRATOR',
  validator: 'VALIDATOR',
  plugin: 'PLUGIN',
  result: 'RESULT',
  error: 'ERROR',
}
