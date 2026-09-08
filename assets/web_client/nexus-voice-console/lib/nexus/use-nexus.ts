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
const MAX_INTERACTIONS = 3
const WAKE_WORD = 'hey'
const WAKE_SILENCE_TIMEOUT_MS = 5_000
const SPEECH_PAUSE_TIMEOUT_MS = 1_400
const INTERRUPTION_GRACE_MS = 1_800
const TTS_RESTART_DELAY_MS = 450
const RECOGNITION_RESTART_DELAY_MS = 800
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

function extractWakeWord(value: string): { detected: boolean; trailingText: string } {
  const normalized = normalizeSpeech(value).toLowerCase()
  const words = normalized.split(' ').filter(Boolean)
  for (let index = 0; index < Math.min(words.length, 3); index += 1) {
    if (words[index] === 'hey' && index + 1 < words.length) {
      const target = words[index + 1]
      if (['nexus', 'nex', 'nx', 'nxx', 'nex us'].includes(target) || editDistance(target, 'nexus') <= 2) {
        return { detected: true, trailingText: words.slice(index + 2).join(' ').trim() }
      }
    }
    if (['nexus', 'nex', 'nx', 'nxx'].includes(words[index]) || editDistance(words[index], 'nexus') <= 1) {
      return { detected: true, trailingText: words.slice(index + 1).join(' ').trim() }
    }
  }
  return { detected: false, trailingText: '' }
}

function stripWakeWord(value: string): string {
  const normalized = normalizeSpeech(value).toLowerCase()
  const words = normalized.split(' ').filter(Boolean)
  for (let index = 0; index < Math.min(words.length, 3); index += 1) {
    if (words[index] === 'hey' && index + 1 < words.length) {
      const target = words[index + 1]
      if (['nexus', 'nex', 'nx', 'nxx', 'nex us'].includes(target) || editDistance(target, 'nexus') <= 2) {
        return words.slice(index + 2).join(' ').trim()
      }
    }
    if (['nexus', 'nex', 'nx', 'nxx'].includes(words[index]) || editDistance(words[index], 'nexus') <= 1) {
      return words.slice(index + 1).join(' ').trim()
    }
  }
  return value.trim()
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
  const [isStartingMic, setIsStartingMic] = useState(false)
  const [voiceState, setVoiceState] = useState<VoiceState>('mic_disabled')
  const [liveTranscript, setLiveTranscript] = useState('')
  const [spokenResponse, setSpokenResponse] = useState('')
  const [events, setEvents] = useState<NexusEvent[]>([])
  const [interactions, setInteractions] = useState<Interaction[]>([])
  const [latencyMs, setLatencyMs] = useState(0)
  const [lastCommunication, setLastCommunication] = useState(0)
  const [voiceError, setVoiceError] = useState('')
  const [rawTranscript, setRawTranscript] = useState('')
  
  const recognitionRef = useRef<SpeechRecognition | null>(null)
  const streamRef = useRef<MediaStream | null>(null)
  const listeningRef = useRef(false)
  const speakingRef = useRef(false)
  const armedRef = useRef(false)
  const isUserSpeakingRef = useRef(false)
  const speechBufferRef = useRef('')
  const sessionFinalRef = useRef('')
  const isSendingRef = useRef(false)
  const silenceTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const speechPauseTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const interruptionTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const responseRef = useRef('')
  const resumeOffsetRef = useRef(0)
  const interruptionCommandRef = useRef(false)
  const recognitionRestartRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const fishAudioRef = useRef<HTMLAudioElement | null>(null)
  const recognitionStartingRef = useRef(false)
  const recognitionRestartAttemptsRef = useRef(0)
  const notAllowedRetryRef = useRef(0)
  const utteranceStartIndexRef = useRef(0)
  const recognitionActiveRef = useRef(false)

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
      if (listeningRef.current) {
        setVoiceState('idle')
      }
    }
    utterance.onerror = () => {
      if (!speakingRef.current) return
      speakingRef.current = false
      setSpokenResponse('')
      setVoiceState('error')
    }
    window.speechSynthesis.speak(utterance)
  }, [])

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
        if (listeningRef.current) setVoiceState('idle')
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
  }, [speakBrowser])

  const sendText = useCallback(async (text: string) => {
    const clean = text.trim()
    if (!clean) return
    isSendingRef.current = true
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
      if (textResponse) {
        addInteraction('nexus', textResponse)
        void speak(textResponse)
      } else if (listeningRef.current) {
        setVoiceState('idle')
      }
      await refresh()
    } catch {
      setConnection('error')
      if (listeningRef.current) setVoiceState('idle')
    } finally {
      isSendingRef.current = false
    }
  }, [addInteraction, refresh, speak])

  const commitCommand = useCallback(() => {
    if (speechPauseTimerRef.current) {
      clearTimeout(speechPauseTimerRef.current)
      speechPauseTimerRef.current = null
    }
    if (silenceTimerRef.current) {
      clearTimeout(silenceTimerRef.current)
      silenceTimerRef.current = null
    }

    if (isSendingRef.current) return

    const candidate = speechBufferRef.current.trim()
    const clean = meaningfulCommand(candidate)

    armedRef.current = false
    isUserSpeakingRef.current = false
    speechBufferRef.current = ''
    sessionFinalRef.current = ''
    utteranceStartIndexRef.current = 999999

    if (isMeaningfulCommand(clean)) {
      setLiveTranscript(clean)
      void sendText(clean)
    } else {
      setLiveTranscript('')
      if (listeningRef.current) {
        setVoiceState('idle')
      }
    }
  }, [sendText])

  const resetSpeechPauseTimer = useCallback(() => {
    if (speechPauseTimerRef.current) {
      clearTimeout(speechPauseTimerRef.current)
      speechPauseTimerRef.current = null
    }
    speechPauseTimerRef.current = setTimeout(() => {
      commitCommand()
    }, SPEECH_PAUSE_TIMEOUT_MS)
  }, [commitCommand])

  const activateListening = useCallback((initialText = '') => {
    if (silenceTimerRef.current) {
      clearTimeout(silenceTimerRef.current)
      silenceTimerRef.current = null
    }
    if (speechPauseTimerRef.current) {
      clearTimeout(speechPauseTimerRef.current)
      speechPauseTimerRef.current = null
    }

    armedRef.current = true
    isSendingRef.current = false
    sessionFinalRef.current = ''
    speechBufferRef.current = ''

    const cleanInitial = meaningfulCommand(initialText)

    if (isMeaningfulCommand(cleanInitial)) {
      isUserSpeakingRef.current = true
      sessionFinalRef.current = cleanInitial
      speechBufferRef.current = cleanInitial
      setLiveTranscript(cleanInitial)
      setVoiceState('user_speaking')
      resetSpeechPauseTimer()
    } else {
      isUserSpeakingRef.current = false
      setLiveTranscript('Listening…')
      setVoiceState('listening')
      silenceTimerRef.current = setTimeout(() => {
        if (armedRef.current && !isUserSpeakingRef.current) {
          armedRef.current = false
          setLiveTranscript('')
          recognitionTextRef.current = ''
          if (listeningRef.current) {
            setVoiceState('idle')
          }
        }
      }, WAKE_SILENCE_TIMEOUT_MS)
    }
  }, [resetSpeechPauseTimer])

  const startRecognitionSession = useCallback(() => {
    if (!listeningRef.current) return
    if (recognitionActiveRef.current) return

    if (recognitionRestartRef.current) {
      clearTimeout(recognitionRestartRef.current)
      recognitionRestartRef.current = null
    }

    if (recognitionRef.current) {
      try {
        recognitionRef.current.onresult = null
        recognitionRef.current.onerror = null
        recognitionRef.current.onend = null
        recognitionRef.current.stop()
      } catch {}
      recognitionRef.current = null
    }

    const Recognition = window.SpeechRecognition || window.webkitSpeechRecognition
    if (!Recognition) return

    const recognition = new Recognition()
    recognition.continuous = true
    recognition.interimResults = true
    recognition.lang = navigator.language?.startsWith('en') ? navigator.language : 'en-US'

    recognition.onresult = (event) => {
      notAllowedRetryRef.current = 0

      if (utteranceStartIndexRef.current > event.results.length) {
        utteranceStartIndexRef.current = 0
      }

      // Reconstruct the clean, unified speech phrase since current utterance started
      let currentSpeech = ''
      for (let i = utteranceStartIndexRef.current; i < event.results.length; i++) {
        const item = event.results[i]
        if (item && item[0]) {
          currentSpeech += (currentSpeech ? ' ' : '') + item[0].transcript.trim()
        }
      }
      currentSpeech = currentSpeech.trim()

      if (currentSpeech) {
        setRawTranscript(currentSpeech)
      }

      // If Nexus is speaking and user speaks, interrupt playback
      if (speakingRef.current && currentSpeech.length > 0) {
        window.speechSynthesis?.cancel()
        fishAudioRef.current?.pause()
        speakingRef.current = false
        setSpokenResponse('')
        setVoiceState('interruption')
      }

      // 1. STANDBY MODE (listening for wake word)
      if (!armedRef.current) {
        const wake = extractWakeWord(currentSpeech)
        if (wake.detected) {
          activateListening(wake.trailingText)
          return
        }

        // In standby mode, advance the utterance index once older phrases finalize
        if (event.results[event.results.length - 1]?.isFinal) {
          utteranceStartIndexRef.current = event.results.length
        }
        return
      }

      // 2. ARMED / LISTENING MODE (capturing user command)
      if (silenceTimerRef.current) {
        clearTimeout(silenceTimerRef.current)
        silenceTimerRef.current = null
      }

      const cleanCommand = stripWakeWord(currentSpeech)
      if (cleanCommand) {
        isUserSpeakingRef.current = true
        speechBufferRef.current = cleanCommand
        setLiveTranscript(cleanCommand)
        setVoiceState('user_speaking')
        resetSpeechPauseTimer()
      }
    }

    recognition.onerror = (event) => {
      const code = event.error || 'unknown'
      if (code === 'no-speech' || code === 'aborted') return
      if (code === 'network') {
        setVoiceError('The browser speech service is temporarily unavailable. Retrying...')
        if (listeningRef.current && !armedRef.current) setVoiceState('idle')
        return
      }

      if (code === 'not-allowed' || code === 'service-not-allowed') {
        if (listeningRef.current && notAllowedRetryRef.current < 3) {
          notAllowedRetryRef.current += 1
          console.warn(`Speech recognition not-allowed on restart, retrying (${notAllowedRetryRef.current}/3)`)
          if (recognitionRestartRef.current) clearTimeout(recognitionRestartRef.current)
          recognitionRestartRef.current = setTimeout(() => {
            if (listeningRef.current && !recognitionActiveRef.current) startRecognitionSession()
          }, 800)
          return
        }

        listeningRef.current = false
        setMicEnabled(false)
        streamRef.current?.getTracks().forEach((track) => track.stop())
        streamRef.current = null
        setVoiceError('Microphone permission was denied. Please allow microphone access in your browser settings.')
        setVoiceState('error')
        return
      }

      setVoiceError(`Speech recognition error: ${code}`)
      if (listeningRef.current) setVoiceState('error')
    }

    recognition.onend = () => {
      recognitionActiveRef.current = false
      if (!listeningRef.current) return

      // If speech was in progress and recognition ended, commit the buffered command
      if (armedRef.current && isUserSpeakingRef.current && speechBufferRef.current.trim()) {
        commitCommand()
      }

      // Do not restart while Nexus is speaking (prevents feedback loops & chimes)
      if (speakingRef.current) return

      utteranceStartIndexRef.current = 0

      if (recognitionRestartRef.current) clearTimeout(recognitionRestartRef.current)
      recognitionRestartRef.current = setTimeout(() => {
        if (listeningRef.current && !speakingRef.current && !recognitionActiveRef.current) {
          startRecognitionSession()
        }
      }, RECOGNITION_RESTART_DELAY_MS)
    }

    recognitionRef.current = recognition
    try {
      recognition.start()
      recognitionActiveRef.current = true
    } catch (err) {
      console.warn('Recognition start warning:', err)
      recognitionActiveRef.current = false
    }
  }, [activateListening, commitCommand, resetSpeechPauseTimer])

  const toggleMic = useCallback(async () => {
    if (micEnabled) {
      listeningRef.current = false
      armedRef.current = false
      isUserSpeakingRef.current = false
      isSendingRef.current = false
      speechBufferRef.current = ''
      sessionFinalRef.current = ''
      recognitionActiveRef.current = false
      setVoiceError('')
      if (silenceTimerRef.current) clearTimeout(silenceTimerRef.current)
      if (speechPauseTimerRef.current) clearTimeout(speechPauseTimerRef.current)
      if (recognitionRestartRef.current) clearTimeout(recognitionRestartRef.current)
      try {
        if (recognitionRef.current) {
          recognitionRef.current.onresult = null
          recognitionRef.current.onerror = null
          recognitionRef.current.onend = null
          recognitionRef.current.stop()
        }
      } catch {}
      recognitionRef.current = null
      streamRef.current?.getTracks().forEach((track) => track.stop())
      streamRef.current = null
      setMicEnabled(false)
      setVoiceState('mic_disabled')
      setLiveTranscript('')
      return
    }

    setIsStartingMic(true)
    try {
      setVoiceError('')
      if (typeof window !== 'undefined' && !window.isSecureContext && window.location.hostname !== 'localhost' && window.location.hostname !== '127.0.0.1') {
        throw new Error('Microphone access requires HTTPS or localhost. If connecting from a tablet or phone, use Tailscale HTTPS or a secure tunnel.')
      }

      const Recognition = window.SpeechRecognition || window.webkitSpeechRecognition
      if (!Recognition) throw new Error('Speech recognition is not supported by this browser. Please use Chrome, Edge, or Safari.')

      // KEEP the media stream active while mic is enabled to maintain persistent audio capture permission
      if (navigator.mediaDevices?.getUserMedia) {
        streamRef.current = await navigator.mediaDevices.getUserMedia({
          audio: { echoCancellation: true, noiseSuppression: true }
        })
      }

      listeningRef.current = true
      armedRef.current = false
      isUserSpeakingRef.current = false
      isSendingRef.current = false
      speechBufferRef.current = ''
      sessionFinalRef.current = ''
      notAllowedRetryRef.current = 0
      utteranceStartIndexRef.current = 0
      setRawTranscript('')
      setLiveTranscript('')
      setMicEnabled(true)
      setVoiceState('idle')

      startRecognitionSession()
    } catch (error) {
      console.error('MIC START FAILED:', error)
      streamRef.current?.getTracks().forEach((track) => track.stop())
      streamRef.current = null
      setVoiceError(error instanceof Error ? error.message : 'Microphone setup failed.')
      setVoiceState('error')
      setMicEnabled(false)
      listeningRef.current = false
    } finally {
      setIsStartingMic(false)
    }
  }, [micEnabled, startRecognitionSession])

  const stopSpeaking = useCallback(() => {
    if ('speechSynthesis' in window) window.speechSynthesis.cancel()
    fishAudioRef.current?.pause()
    speakingRef.current = false
    resumeOffsetRef.current = 0
    setSpokenResponse('')
    if (listeningRef.current) setVoiceState('idle')
  }, [])

  const retry = useCallback(() => { setConnection('retrying'); void refresh() }, [refresh])

  useEffect(() => {
    void refresh()
    const interval = window.setInterval(() => void refresh(), 2000)
    return () => {
      window.clearInterval(interval)
      listeningRef.current = false
      armedRef.current = false
      isUserSpeakingRef.current = false
      isSendingRef.current = false
      speechBufferRef.current = ''
      sessionFinalRef.current = ''
      if (recognitionRestartRef.current) clearTimeout(recognitionRestartRef.current)
      if (silenceTimerRef.current) clearTimeout(silenceTimerRef.current)
      if (speechPauseTimerRef.current) clearTimeout(speechPauseTimerRef.current)
      if (interruptionTimerRef.current) clearTimeout(interruptionTimerRef.current)
      try {
        if (recognitionRef.current) {
          recognitionRef.current.onresult = null
          recognitionRef.current.onerror = null
          recognitionRef.current.onend = null
          recognitionRef.current.stop()
        }
      } catch {}
      recognitionRef.current = null
      streamRef.current?.getTracks().forEach((track) => track.stop())
      streamRef.current = null
      window.speechSynthesis?.cancel()
      fishAudioRef.current?.pause()
    }
  }, [refresh])

  return { connection, micEnabled, isStartingMic, voiceState, voiceError, liveTranscript, spokenResponse, events, interactions, latencyMs, lastCommunication, rawTranscript, toggleMic, retry, stopSpeaking, triggerInterruption: stopSpeaking, sendText }
}

export type NexusClient = ReturnType<typeof useNexus>