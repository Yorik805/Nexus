'use client'

import { useCallback, useEffect, useRef, useState } from 'react'
import type { ConnectionState, Interaction, NexusEvent, VoiceState } from './types'

type ApiEvent = { time: string; kind: string; source: string; message: string }
type ApiState = { events?: ApiEvent[] }
type VoicePayload = { type?: string; state?: VoiceState; text?: string; command?: string; interrupt?: boolean; message?: string }

const MAX_EVENTS = 100
const MAX_INTERACTIONS = 6
const ACTIVE_LISTENING_TIMEOUT_MS = 90_000
const INTERRUPTION_GRACE_MS = 1_800
const POST_TTS_IGNORE_MS = 1_200
const WAKE_ONLY_AFTER_TTS_MS = 2_000

function categoryFor(kind: string, source: string, message: string): NexusEvent['category'] {
  const normalized = kind.toUpperCase()
  const context = `${source} ${message}`.toUpperCase()
  if (normalized === 'ERROR') return 'error'
  if (normalized === 'EXECUTION_RESULT' || context.includes('TERMINAL') || context.includes('PLUGIN')) return 'plugin'
  if (normalized === 'USER_MESSAGE') return 'event'
  if (normalized.includes('ORCHESTR') || context.includes('ORCHESTR') || context.includes('PROVIDER')) return 'orchestrator'
  if (normalized.includes('VALID') || context.includes('VALID')) return 'validator'
  if (context.includes('COMPLETED') || context.includes('SUCCESS')) return 'result'
  return 'event'
}

function mapEvents(events: ApiEvent[]): NexusEvent[] {
  return events.slice(-MAX_EVENTS).map((event, index) => ({
    id: `${event.time}-${event.kind}-${index}`,
    timestamp: Date.parse(`1970-01-01T${event.time}Z`) || Date.now(),
    category: categoryFor(event.kind, event.source, event.message),
    label: event.kind,
    description: `${event.source}: ${event.message}`,
    time: event.time,
    kind: event.kind,
    source: event.source,
    message: event.message,
  }))
}

function responseText(value: unknown): string {
  if (!value || typeof value !== 'object') return ''
  const record = value as Record<string, unknown>
  const pending = Array.isArray(record.pending_messages) ? record.pending_messages : []
  for (const item of pending) {
    if (!item || typeof item !== 'object') continue
    const pendingRecord = item as Record<string, unknown>
    if (typeof pendingRecord.message === 'string' && pendingRecord.message.trim()) return pendingRecord.message
    const event = pendingRecord.event
    const data = event && typeof event === 'object' ? (event as Record<string, unknown>).data : null
    if (data && typeof data === 'object' && typeof (data as Record<string, unknown>).message === 'string') return (data as Record<string, string>).message
  }
  const nested = record.result && typeof record.result === 'object' ? record.result as Record<string, unknown> : record
  const response = nested.response && typeof nested.response === 'object' ? nested.response as Record<string, unknown> : nested
  return typeof response.text === 'string' ? response.text : typeof nested.message === 'string' ? nested.message : ''
}

function meaningful(value: string): boolean { return value.trim().length >= 3 && /[a-z]{2,}/i.test(value) }

export function useNexus() {
  const [connection, setConnection] = useState<ConnectionState>('connecting')
  const [micEnabled, setMicEnabled] = useState(false)
  const [voiceState, setVoiceState] = useState<VoiceState>('idle')
  const [liveTranscript, setLiveTranscript] = useState('')
  const [spokenResponse, setSpokenResponse] = useState('')
  const [events, setEvents] = useState<NexusEvent[]>([])
  const [interactions, setInteractions] = useState<Interaction[]>([])
  const [latencyMs, setLatencyMs] = useState(0)
  const [lastCommunication, setLastCommunication] = useState(0)
  const [voiceError, setVoiceError] = useState('')
  const [activeListening, setActiveListening] = useState(false)
  const socketRef = useRef<WebSocket | null>(null)
  const streamRef = useRef<MediaStream | null>(null)
  const contextRef = useRef<AudioContext | null>(null)
  const processorRef = useRef<ScriptProcessorNode | null>(null)
  const fishAudioRef = useRef<HTMLAudioElement | null>(null)
  const speakingRef = useRef(false)
  const responseRef = useRef('')
  const resumeOffsetRef = useRef(0)
  const silenceTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const interruptionTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const ignoreUntilRef = useRef(0)
  const wakeOnlyUntilRef = useRef(0)
  const interruptionCommandRef = useRef(false)

  const addInteraction = useCallback((role: Interaction['role'], text: string) => {
    setInteractions((current) => [...current, { id: `${Date.now()}-${role}`, role, text, timestamp: Date.now() }].slice(-MAX_INTERACTIONS))
  }, [])

  const resetListeningTimeout = useCallback(() => {
    if (silenceTimerRef.current) clearTimeout(silenceTimerRef.current)
    silenceTimerRef.current = setTimeout(() => { setActiveListening(false); setLiveTranscript(''); if (micEnabled && !speakingRef.current) setVoiceState('idle') }, ACTIVE_LISTENING_TIMEOUT_MS)
  }, [micEnabled])

  const armListening = useCallback(() => { setActiveListening(true); setVoiceState('listening'); resetListeningTimeout() }, [resetListeningTimeout])

  const speak = useCallback(async (text: string, offset = 0) => {
    if (!text) return
    responseRef.current = text
    try {
      const response = await fetch('/api/tts', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ text }), cache: 'no-store' })
      if (!response.ok) throw new Error('Fish Audio unavailable')
      const audio = new Audio(URL.createObjectURL(await response.blob()))
      fishAudioRef.current = audio
      audio.onplay = () => { speakingRef.current = true; socketRef.current?.send(JSON.stringify({ type: 'control', speaking: true })); setSpokenResponse(text); setVoiceState('nexus_speaking') }
      audio.ontimeupdate = () => { if (audio.duration > 0) resumeOffsetRef.current = Math.round((audio.currentTime / audio.duration) * text.length) }
      audio.onended = () => { speakingRef.current = false; socketRef.current?.send(JSON.stringify({ type: 'control', speaking: false })); setSpokenResponse(''); ignoreUntilRef.current = Date.now() + POST_TTS_IGNORE_MS; wakeOnlyUntilRef.current = Date.now() + WAKE_ONLY_AFTER_TTS_MS; armListening(); URL.revokeObjectURL(audio.src) }
      audio.onerror = () => { speakingRef.current = false; setVoiceError('TTS playback failed.'); setVoiceState('error') }
      await audio.play()
    } catch {
      if (!('speechSynthesis' in window)) { setVoiceError('No TTS engine is available.'); setVoiceState('error'); return }
      window.speechSynthesis.cancel()
      const utterance = new SpeechSynthesisUtterance(text.slice(offset))
      utterance.onstart = () => { speakingRef.current = true; socketRef.current?.send(JSON.stringify({ type: 'control', speaking: true })); setSpokenResponse(text); setVoiceState('nexus_speaking') }
      utterance.onboundary = (event) => { resumeOffsetRef.current = offset + event.charIndex }
      utterance.onend = () => { speakingRef.current = false; socketRef.current?.send(JSON.stringify({ type: 'control', speaking: false })); setSpokenResponse(''); ignoreUntilRef.current = Date.now() + POST_TTS_IGNORE_MS; wakeOnlyUntilRef.current = Date.now() + WAKE_ONLY_AFTER_TTS_MS; armListening() }
      window.speechSynthesis.speak(utterance)
    }
  }, [armListening])

  const refresh = useCallback(async () => {
    const started = performance.now()
    try { const response = await fetch('/api/state', { cache: 'no-store' }); if (!response.ok) throw new Error(); const data = await response.json() as ApiState; setEvents(mapEvents(data.events || [])); setLatencyMs(Math.round(performance.now() - started)); setLastCommunication(Date.now()); setConnection('connected') } catch { setConnection('error') }
  }, [])

  const sendText = useCallback(async (text: string) => {
    const clean = text.trim()
    if (!meaningful(clean)) return
    setVoiceState('processing'); setActiveListening(false); addInteraction('user', clean)
    try {
      const response = await fetch('/api/events', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ type: 'USER_MESSAGE', source: 'web-client', message: clean }) })
      const data = await response.json()
      if (!response.ok) throw new Error(data.message || `Request returned ${response.status}`)
      const textResponse = responseText(data)
      if (textResponse) { addInteraction('nexus', textResponse); void speak(textResponse) } else setVoiceState('idle')
      setLatencyMs(0); setLastCommunication(Date.now()); await refresh()
    } catch { setConnection('error'); setVoiceError('Nexus request failed.'); setVoiceState('error') }
  }, [addInteraction, refresh, speak])

  const toggleMic = useCallback(async () => {
    if (micEnabled) {
      setMicEnabled(false); setActiveListening(false); socketRef.current?.close(); processorRef.current?.disconnect(); void contextRef.current?.close(); streamRef.current?.getTracks().forEach((track) => track.stop()); setVoiceState('mic_disabled'); return
    }
    try {
      setVoiceError('')
      const stream = await navigator.mediaDevices.getUserMedia({ audio: { echoCancellation: true, noiseSuppression: true } })
      streamRef.current = stream
      const scheme = window.location.protocol === 'https:' ? 'wss' : 'ws'
      const socket = new WebSocket(`${scheme}://${window.location.hostname}:8767`)
      socketRef.current = socket
      socket.onmessage = (message) => {
        const payload = JSON.parse(message.data) as VoicePayload
        if (payload.type === 'error') { setVoiceError(payload.message || 'Server-side Whisper failed.'); setVoiceState('error'); return }
        if (payload.type === 'state') { if (payload.state) setVoiceState(payload.state); return }
        if (payload.type === 'wake') {
          if (speakingRef.current && payload.interrupt) { window.speechSynthesis?.cancel(); speakingRef.current = false; setVoiceState('interruption'); interruptionCommandRef.current = false; if (interruptionTimerRef.current) clearTimeout(interruptionTimerRef.current); interruptionTimerRef.current = setTimeout(() => { if (!interruptionCommandRef.current) void speak(responseRef.current, resumeOffsetRef.current) }, INTERRUPTION_GRACE_MS) }
          armListening()
          if (payload.command && meaningful(payload.command)) { interruptionCommandRef.current = true; void sendText(payload.command) }
          return
        }
        if (payload.type === 'transcript' && payload.text) {
          if (Date.now() < ignoreUntilRef.current) return
          if (activeListening && payload.command && meaningful(payload.command)) { interruptionCommandRef.current = true; void sendText(payload.command) }
          else if (activeListening) { resetListeningTimeout(); setLiveTranscript(payload.text); setVoiceState('user_speaking') }
        }
      }
      socket.onerror = () => { setVoiceError('Could not connect to server-side Whisper on port 8767.'); setVoiceState('error') }
      const audioContext = new AudioContext({ sampleRate: 16000 })
      const source = audioContext.createMediaStreamSource(stream)
      const processor = audioContext.createScriptProcessor(4096, 1, 1)
      processor.onaudioprocess = (event) => {
        if (socket.readyState !== WebSocket.OPEN) return
        const input = event.inputBuffer.getChannelData(0)
        const ratio = event.inputBuffer.sampleRate / 16000
        const pcm = new Int16Array(Math.max(1, Math.floor(input.length / ratio)))
        for (let index = 0; index < pcm.length; index += 1) pcm[index] = Math.max(-1, Math.min(1, input[Math.min(input.length - 1, Math.floor(index * ratio))])) * 32767
        socket.send(pcm.buffer)
      }
      source.connect(processor); processor.connect(audioContext.destination); contextRef.current = audioContext; processorRef.current = processor
      setMicEnabled(true); setVoiceState('idle')
    } catch (error) { setVoiceError(error instanceof Error ? error.message : 'Microphone setup failed.'); setVoiceState('error'); setMicEnabled(false) }
  }, [activeListening, armListening, micEnabled, resetListeningTimeout, sendText, speak])

  const stopSpeaking = useCallback(() => { window.speechSynthesis?.cancel(); fishAudioRef.current?.pause(); speakingRef.current = false; socketRef.current?.send(JSON.stringify({ type: 'control', speaking: false })); setSpokenResponse(''); if (micEnabled) armListening() }, [armListening, micEnabled])
  const retry = useCallback(() => { setConnection('retrying'); void refresh() }, [refresh])

  useEffect(() => { void refresh(); const interval = window.setInterval(() => void refresh(), 2000); return () => { window.clearInterval(interval); socketRef.current?.close(); processorRef.current?.disconnect(); void contextRef.current?.close(); streamRef.current?.getTracks().forEach((track) => track.stop()); window.speechSynthesis?.cancel(); if (silenceTimerRef.current) clearTimeout(silenceTimerRef.current); if (interruptionTimerRef.current) clearTimeout(interruptionTimerRef.current) } }, [refresh])

  return { connection, micEnabled, voiceState, voiceError, liveTranscript, spokenResponse, events, interactions, latencyMs, lastCommunication, toggleMic, retry, stopSpeaking, triggerInterruption: stopSpeaking, sendText }
}

export type NexusClient = ReturnType<typeof useNexus>
