'use client'

import { useCallback, useEffect, useRef, useState } from 'react'
import type { ConnectionState, Interaction, NexusEvent, VoiceState } from './types'

type ApiEvent = { time: string; kind: string; source: string; message: string }
type ApiState = {
  events?: ApiEvent[]
  provider?: { name?: string; model?: string; status?: string; latency?: string }
}

declare global {
  interface Window {
    webkitSpeechRecognition?: new () => SpeechRecognition
    SpeechRecognition?: new () => SpeechRecognition
  }
  interface SpeechRecognition extends EventTarget {
    continuous: boolean
    interimResults: boolean
    lang: string
    start(): void
    stop(): void
    onresult: ((event: SpeechRecognitionEvent) => void) | null
    onerror: ((event: Event & { error?: string }) => void) | null
    onend: (() => void) | null
  }
  interface SpeechRecognitionEvent extends Event {
    resultIndex: number
    results: SpeechRecognitionResultList
  }
}

const MAX_EVENTS = 100
const MAX_INTERACTIONS = 6
const WAKE_WORD = 'hey nexus'
const ACTIVE_LISTENING_TIMEOUT_MS = 90_000
const INTERRUPTION_GRACE_MS = 1_800
const TTS_RESTART_DELAY_MS = 450
const POST_TTS_IGNORE_MS = 1_200
const WAKE_ONLY_AFTER_TTS_MS = 2_000
const RECOGNITION_RESTART_DELAY_MS = 700
const MAX_RECOGNITION_RESTART_ATTEMPTS = 8

function categoryFor(kind: string, source: string, message: string): NexusEvent['category'] {
  const normalized = kind.toUpperCase()
  const context = `${source} ${message}`.toUpperCase()
  if (normalized === 'ERROR') return 'error'
  if (normalized === 'EXECUTION_RESULT' || context.includes('TERMINAL') || context.includes('PLUGIN')) return 'plugin'
  if (normalized === 'USER_MESSAGE') return 'event'
  if (normalized.includes('ORCHESTR') || context.includes('ORCHESTR') || context.includes('PROVIDER')) return 'orchestrator'
  if (normalized.includes('VALID') || context.includes('VALID')) return 'validator'
  if (context.includes('EVENT COMPLETE') || context.includes('COMPLETED')) return 'result'
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
    if (event && typeof event === 'object') {
      const data = (event as Record<string, unknown>).data
      if (data && typeof data === 'object' && typeof (data as Record<string, unknown>).message === 'string') {
        return (data as Record<string, string>).message
      }
    }
  }
  const nested = record.result && typeof record.result === 'object' ? record.result as Record<string, unknown> : record
  const response = nested.response && typeof nested.response === 'object' ? nested.response as Record<string, unknown> : nested
  return typeof response.text === 'string' ? response.text : typeof nested.message === 'string' ? nested.message : ''
}

function normalizeSpeech(value: string): string {
  return value.toLowerCase().replace(/[^a-z0-9 ]/g, ' ').replace(/\s+/g, ' ').trim()
}

function editDistance(left: string, right: string): number {
  const row = Array.from({ length: right.length + 1 }, (_, index) => index)
  for (let leftIndex = 1; leftIndex <= left.length; leftIndex += 1) {
    let diagonal = row[0]
    row[0] = leftIndex
    for (let rightIndex = 1; rightIndex <= right.length; rightIndex += 1) {
      const above = row[rightIndex]
      row[rightIndex] = left[leftIndex - 1] === right[rightIndex - 1]
        ? diagonal
        : 1 + Math.min(diagonal, above, row[rightIndex - 1])
      diagonal = above
    }
  }
  return row[right.length]
}

function wakeCommand(value: string): string | null {
  const normalized = normalizeSpeech(value)
  const words = normalized.split(' ')
  for (let index = 0; index < words.length; index += 1) {
    if (!['hey', 'hay', 'he'].includes(words[index])) continue
    if (index === words.length - 1) return ''
    for (let count = 1; count <= 3 && index + count < words.length; count += 1) {
      const phrase = words.slice(index + 1, index + count + 1).join('')
      const isConsonantForm = ['nxs', 'ncx', 'nxc', 'nex', 'nexus'].includes(phrase)
      if (isConsonantForm || editDistance(phrase, 'nexus') <= 2) {
        return words.slice(index + count + 1).join(' ').trim()
      }
    }
  }
  return null
}

function meaningfulCommand(value: string): string {
  return value.replace(/^[,.:;!?\s-]+/, '').trim()
}

function isMeaningfulCommand(value: string): boolean {
  const clean = meaningfulCommand(value)
  return clean.length >= 3 && /[a-z]{2,}/i.test(clean)
}

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
  const recognitionRef = useRef<SpeechRecognition | null>(null)
  const streamRef = useRef<MediaStream | null>(null)
  const listeningRef = useRef(false)
  const speakingRef = useRef(false)
  const armedRef = useRef(false)
  const silenceTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const interruptionTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const responseRef = useRef('')
  const resumeOffsetRef = useRef(0)
  const interruptionCommandRef = useRef(false)
  const recognitionRestartRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const ignoreRecognitionUntilRef = useRef(0)
  const fishAudioRef = useRef<HTMLAudioElement | null>(null)
  const wakeOnlyUntilRef = useRef(0)
  const recognitionStartingRef = useRef(false)
  const recognitionRestartAttemptsRef = useRef(0)
  const recognitionTextRef = useRef('')

  const addInteraction = useCallback((role: Interaction['role'], text: string) => {
    setInteractions((current) => [...current, { id: `${Date.now()}-${role}`, role, text, timestamp: Date.now() }].slice(-MAX_INTERACTIONS))
  }, [])

  const refresh = useCallback(async () => {
    const started = performance.now()
    try {
      const response = await fetch('/api/state', { cache: 'no-store' })
      if (!response.ok) throw new Error(`Dashboard API returned ${response.status}`)
      const data = await response.json() as ApiState
      setEvents(mapEvents(data.events || []))
      setLatencyMs(Math.round(performance.now() - started))
      setLastCommunication(Date.now())
      setConnection('connected')
    } catch {
      setConnection('error')
    }
  }, [])

  const resetActiveListeningTimeout = useCallback(() => {
    if (silenceTimerRef.current) clearTimeout(silenceTimerRef.current)
    silenceTimerRef.current = setTimeout(() => {
      armedRef.current = false
      setLiveTranscript('')
      if (listeningRef.current && !speakingRef.current) setVoiceState('idle')
    }, ACTIVE_LISTENING_TIMEOUT_MS)
  }, [])

  const armForCommand = useCallback(() => {
    armedRef.current = true
    setVoiceState('listening')
    resetActiveListeningTimeout()
  }, [resetActiveListeningTimeout])

  const speakBrowser = useCallback((text: string, offset = 0) => {
    if (!text) return
    if (!('speechSynthesis' in window)) {
      setSpokenResponse('')
      if (listeningRef.current) setVoiceState('idle')
      return
    }
    window.speechSynthesis.cancel()
    responseRef.current = text
    resumeOffsetRef.current = Math.max(0, Math.min(offset, text.length))
    const remaining = text.slice(resumeOffsetRef.current)
    if (!remaining.trim()) return
    const utterance = new SpeechSynthesisUtterance(remaining)
    const utteranceOffset = resumeOffsetRef.current
    utterance.onstart = () => {
      speakingRef.current = true
      setSpokenResponse(text)
      setVoiceState('nexus_speaking')
    }
    utterance.onboundary = (event) => {
      if (typeof event.charIndex === 'number') resumeOffsetRef.current = utteranceOffset + event.charIndex
    }
    utterance.onend = () => {
      speakingRef.current = false
      resumeOffsetRef.current = 0
      setSpokenResponse('')
      ignoreRecognitionUntilRef.current = Date.now() + POST_TTS_IGNORE_MS
      wakeOnlyUntilRef.current = Date.now() + WAKE_ONLY_AFTER_TTS_MS
      if (listeningRef.current) {
        window.setTimeout(() => armForCommand(), TTS_RESTART_DELAY_MS)
      }
    }
    utterance.onerror = () => {
      if (!speakingRef.current) return
      speakingRef.current = false
      setSpokenResponse('')
      setVoiceState('error')
    }
    window.speechSynthesis.speak(utterance)
  }, [armForCommand])

  const speak = useCallback(async (text: string, offset = 0) => {
    if (!text) return
    responseRef.current = text
    try {
      const response = await fetch('/api/tts', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text }),
        cache: 'no-store',
      })
      if (!response.ok) {
        speakBrowser(text, offset)
        return
      }
      const audio = new Audio(URL.createObjectURL(await response.blob()))
      fishAudioRef.current?.pause()
      fishAudioRef.current = audio
      audio.onplay = () => {
        speakingRef.current = true
        setSpokenResponse(text)
        setVoiceState('nexus_speaking')
      }
      audio.ontimeupdate = () => {
        if (audio.duration > 0) resumeOffsetRef.current = Math.round((audio.currentTime / audio.duration) * text.length)
      }
      audio.onended = () => {
        speakingRef.current = false
        setSpokenResponse('')
        if (listeningRef.current) armForCommand()
        URL.revokeObjectURL(audio.src)
      }
      audio.onerror = () => {
        speakingRef.current = false
        setSpokenResponse('')
        setVoiceError('Fish Audio playback failed. Check the Fish Audio configuration.')
        setVoiceState('error')
      }
      await audio.play()
    } catch {
      speakBrowser(text, offset)
    }
  }, [armForCommand, speakBrowser])

  const sendText = useCallback(async (text: string) => {
    const clean = text.trim()
    if (!clean) return
    setVoiceState('processing')
    addInteraction('user', clean)
    const started = performance.now()
    try {
      const response = await fetch('/api/events', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ type: 'USER_MESSAGE', source: 'web-client', message: clean }),
      })
      const data = await response.json()
      if (!response.ok) throw new Error(data.message || `Request returned ${response.status}`)
      const textResponse = responseText(data)
      setLatencyMs(Math.round(performance.now() - started))
      setLastCommunication(Date.now())
      armedRef.current = false
      if (silenceTimerRef.current) clearTimeout(silenceTimerRef.current)
      if (textResponse) { addInteraction('nexus', textResponse); speak(textResponse) }
      else if (listeningRef.current) setVoiceState('idle')
      await refresh()
    } catch {
      setConnection('error')
      setVoiceState('error')
    }
  }, [addInteraction, refresh, speak])

  const toggleMic = useCallback(async () => {
    if (micEnabled) {
      listeningRef.current = false
      armedRef.current = false
      setVoiceError('')
      if (silenceTimerRef.current) clearTimeout(silenceTimerRef.current)
      if (recognitionRestartRef.current) clearTimeout(recognitionRestartRef.current)
      recognitionRef.current?.stop()
      streamRef.current?.getTracks().forEach((track) => track.stop())
      streamRef.current = null
      setMicEnabled(false)
      setVoiceState('mic_disabled')
      return
    }
    try {
      setVoiceError('')
      if (!navigator.mediaDevices?.getUserMedia) throw new Error('This browser does not provide microphone access. Use HTTPS or localhost and a supported browser.')
      streamRef.current = await navigator.mediaDevices.getUserMedia({ audio: { echoCancellation: true, noiseSuppression: true } })
      const Recognition = window.SpeechRecognition || window.webkitSpeechRecognition
      if (!Recognition) throw new Error('Speech recognition is not supported by this browser.')
      const recognition = new Recognition()
      recognition.continuous = true
      recognition.interimResults = true
      recognition.lang = navigator.language?.startsWith('en') ? navigator.language : 'en-US'
      recognition.onresult = (event) => {
        let interim = ''
        let finalText = ''
        for (let index = event.resultIndex; index < event.results.length; index += 1) {
          const text = event.results[index][0].transcript
          if (event.results[index].isFinal) finalText += text
          else interim += text
        }
        const transcript = `${finalText} ${interim}`.trim()
        if (finalText.trim()) {
          recognitionTextRef.current = `${recognitionTextRef.current} ${finalText}`.trim().slice(-160)
        }
        const accumulatedTranscript = `${recognitionTextRef.current} ${interim}`.trim()
        const command = wakeCommand(accumulatedTranscript)
        if (command !== null) {
          if (speakingRef.current) {
            window.speechSynthesis.cancel()
            fishAudioRef.current?.pause()
            speakingRef.current = false
            interruptionCommandRef.current = false
            setVoiceState('interruption')
            if (interruptionTimerRef.current) clearTimeout(interruptionTimerRef.current)
            interruptionTimerRef.current = setTimeout(() => {
              if (!interruptionCommandRef.current) speak(responseRef.current, resumeOffsetRef.current)
            }, INTERRUPTION_GRACE_MS)
          }
          armForCommand()
          const cleanCommand = meaningfulCommand(command)
          recognitionTextRef.current = ''
          setLiveTranscript(cleanCommand || 'Hey Nexus')
          if (cleanCommand) setVoiceState('user_speaking')
          if (finalText.trim() && isMeaningfulCommand(cleanCommand)) {
            if (interruptionTimerRef.current) clearTimeout(interruptionTimerRef.current)
            interruptionCommandRef.current = true
            setLiveTranscript('')
            void sendText(cleanCommand)
          }
          return
        }
        if (Date.now() < ignoreRecognitionUntilRef.current) return
        if (!armedRef.current) return
        resetActiveListeningTimeout()
        setLiveTranscript(transcript)
        if (transcript) setVoiceState('user_speaking')
        if (finalText.trim()) {
          const cleanCommand = meaningfulCommand(finalText)
          setLiveTranscript('')
          if (normalizeSpeech(cleanCommand) === 'nexus' || normalizeSpeech(cleanCommand) === 'nex us') {
            recognitionTextRef.current = ''
            setVoiceState('listening')
            return
          }
          if (Date.now() < wakeOnlyUntilRef.current) {
            recognitionTextRef.current = ''
            setVoiceState('listening')
            return
          }
          if (isMeaningfulCommand(cleanCommand)) {
            interruptionCommandRef.current = true
            recognitionTextRef.current = ''
            void sendText(cleanCommand)
          } else {
            setVoiceState('listening')
          }
        }
      }
      recognition.onerror = (event) => {
        const code = event.error || 'unknown'
        if (code === 'no-speech' || code === 'aborted') return
        if (code === 'network') {
          setVoiceError('The current browser speech service is unavailable. Open this client in Chrome or Edge, then allow microphone access.')
          if (listeningRef.current) setVoiceState('idle')
          return
        }
        const message = code === 'not-allowed'
          ? 'Microphone or speech-recognition permission was denied. Allow microphone access in the browser and try again.'
          : `Speech recognition error: ${code}.`
        setVoiceError(message)
        if (code === 'not-allowed' || code === 'service-not-allowed') {
          listeningRef.current = false
          setMicEnabled(false)
          streamRef.current?.getTracks().forEach((track) => track.stop())
          streamRef.current = null
        }
        if (listeningRef.current) setVoiceState('error')
      }
      recognition.onend = () => {
        if (!listeningRef.current) return
        if (recognitionRestartRef.current) clearTimeout(recognitionRestartRef.current)
        const restart = (attempt: number) => {
          if (!listeningRef.current || attempt > MAX_RECOGNITION_RESTART_ATTEMPTS) {
            setVoiceError('Speech recognition stopped. Tap MIC OFF, then MIC ON to restart voice listening.')
            setVoiceState('error')
            return
          }
          recognitionRestartRef.current = setTimeout(() => {
            if (recognitionStartingRef.current || !listeningRef.current) return
            recognitionRestartAttemptsRef.current = attempt
            recognitionStartingRef.current = true
            try {
              recognition.start()
              recognitionStartingRef.current = false
              recognitionRestartAttemptsRef.current = 0
            } catch {
              recognitionStartingRef.current = false
              restart(attempt + 1)
            }
          }, RECOGNITION_RESTART_DELAY_MS * Math.max(1, attempt))
        }
        restart(recognitionRestartAttemptsRef.current + 1)
      }
      recognitionRef.current = recognition
      listeningRef.current = true
      recognitionRestartAttemptsRef.current = 0
      recognitionTextRef.current = ''
      setMicEnabled(true)
      setVoiceState('idle')
      recognitionStartingRef.current = true
      recognition.start()
      recognitionStartingRef.current = false
    } catch (error) {
      streamRef.current?.getTracks().forEach((track) => track.stop())
      setVoiceError(error instanceof Error ? error.message : 'Microphone setup failed.')
      setVoiceState('error')
      setMicEnabled(false)
    }
  }, [armForCommand, micEnabled, resetActiveListeningTimeout, sendText, speak])

  const stopSpeaking = useCallback(() => {
    if ('speechSynthesis' in window) window.speechSynthesis.cancel()
    fishAudioRef.current?.pause()
    speakingRef.current = false
    resumeOffsetRef.current = 0
    setSpokenResponse('')
    if (listeningRef.current) setVoiceState(armedRef.current ? 'listening' : 'idle')
  }, [])

  const retry = useCallback(() => { setConnection('retrying'); void refresh() }, [refresh])

  useEffect(() => {
    void refresh()
    const interval = window.setInterval(() => void refresh(), 2000)
    return () => {
      window.clearInterval(interval)
      recognitionRef.current?.stop()
      recognitionTextRef.current = ''
      if (recognitionRestartRef.current) clearTimeout(recognitionRestartRef.current)
      streamRef.current?.getTracks().forEach((track) => track.stop())
      window.speechSynthesis?.cancel()
      if (silenceTimerRef.current) clearTimeout(silenceTimerRef.current)
      if (interruptionTimerRef.current) clearTimeout(interruptionTimerRef.current)
    }
  }, [refresh])

  return { connection, micEnabled, voiceState, voiceError, liveTranscript, spokenResponse, events, interactions, latencyMs, lastCommunication, toggleMic, retry, stopSpeaking, triggerInterruption: stopSpeaking, sendText }
}

export type NexusClient = ReturnType<typeof useNexus>