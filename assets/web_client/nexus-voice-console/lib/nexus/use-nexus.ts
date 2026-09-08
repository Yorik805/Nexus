'use client'

import { useCallback, useEffect, useRef, useState } from 'react'
import type { ConnectionState, Interaction, NexusEvent, SttMode, VoiceState } from './types'

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
const RECOGNITION_RESTART_DELAY_MS = 300
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
  const [sttMode, setSttMode] = useState<SttMode>('web')
  
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
  const recognitionTextRef = useRef('')
  const notAllowedRetryRef = useRef(0)

  // Server-side STT refs
  const mediaRecorderRef = useRef<MediaRecorder | null>(null)
  const audioContextRef = useRef<AudioContext | null>(null)
  const analyserRef = useRef<AnalyserNode | null>(null)
  const vadIntervalRef = useRef<ReturnType<typeof setInterval> | null>(null)
  const serverAudioChunksRef = useRef<Blob[]>([])
  const isTranscribingRef = useRef(false)
  const lastVoiceTimeRef = useRef(0)
  const serverSpeakingRef = useRef(false)
  const lastInterimSentTimeRef = useRef(0)

  useEffect(() => {
    if (typeof window !== 'undefined') {
      const saved = localStorage.getItem('nexus_stt_mode')
      if (saved === 'web' || saved === 'server') {
        setSttMode(saved)
      }
    }
  }, [])

  const toggleSttMode = useCallback(() => {
    setSttMode((prev) => {
      const next = prev === 'web' ? 'server' : 'web'
      if (typeof window !== 'undefined') {
        localStorage.setItem('nexus_stt_mode', next)
      }
      return next
    })
  }, [])

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

  const commitCommand = useCallback((overrideText?: string) => {
    if (speechPauseTimerRef.current) {
      clearTimeout(speechPauseTimerRef.current)
      speechPauseTimerRef.current = null
    }
    if (silenceTimerRef.current) {
      clearTimeout(silenceTimerRef.current)
      silenceTimerRef.current = null
    }

    if (isSendingRef.current) return

    const candidate = (overrideText !== undefined ? overrideText : speechBufferRef.current).trim()
    const clean = meaningfulCommand(candidate)

    armedRef.current = false
    isUserSpeakingRef.current = false
    speechBufferRef.current = ''
    sessionFinalRef.current = ''
    recognitionTextRef.current = ''
    serverAudioChunksRef.current = []

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

  const stopServerStt = useCallback(() => {
    if (vadIntervalRef.current) {
      clearInterval(vadIntervalRef.current)
      vadIntervalRef.current = null
    }
    try {
      if (mediaRecorderRef.current && mediaRecorderRef.current.state !== 'inactive') {
        mediaRecorderRef.current.stop()
      }
    } catch {}
    mediaRecorderRef.current = null
    try {
      audioContextRef.current?.close()
    } catch {}
    audioContextRef.current = null
    analyserRef.current = null
    serverAudioChunksRef.current = []
    serverSpeakingRef.current = false
    isTranscribingRef.current = false
  }, [])

  const startServerSttSession = useCallback(() => {
    if (!listeningRef.current || !streamRef.current) return
    stopServerStt()

    try {
      const stream = streamRef.current
      const AudioContextClass = window.AudioContext || (window as unknown as { webkitAudioContext: typeof AudioContext }).webkitAudioContext
      if (!AudioContextClass) {
        setVoiceError('Web Audio API is not supported in this browser.')
        return
      }

      const audioCtx = new AudioContextClass()
      const source = audioCtx.createMediaStreamSource(stream)
      const analyser = audioCtx.createAnalyser()
      analyser.fftSize = 512
      source.connect(analyser)

      audioContextRef.current = audioCtx
      analyserRef.current = analyser

      const mimeType = typeof MediaRecorder !== 'undefined' && MediaRecorder.isTypeSupported('audio/webm;codecs=opus')
        ? 'audio/webm;codecs=opus'
        : typeof MediaRecorder !== 'undefined' && MediaRecorder.isTypeSupported('audio/webm')
        ? 'audio/webm'
        : typeof MediaRecorder !== 'undefined' && MediaRecorder.isTypeSupported('audio/mp4')
        ? 'audio/mp4'
        : ''

      const recorder = new MediaRecorder(stream, mimeType ? { mimeType } : undefined)
      recorder.ondataavailable = (event) => {
        if (event.data && event.data.size > 0) {
          serverAudioChunksRef.current.push(event.data)
        }
      }
      recorder.start(250)
      mediaRecorderRef.current = recorder

      vadIntervalRef.current = setInterval(async () => {
        if (!analyserRef.current || !listeningRef.current) return

        const buffer = new Float32Array(analyserRef.current.fftSize)
        analyserRef.current.getFloatTimeDomainData(buffer)
        let sum = 0
        for (let i = 0; i < buffer.length; i++) {
          sum += buffer[i] * buffer[i]
        }
        const rms = Math.sqrt(sum / buffer.length)
        const isVoice = rms > 0.025

        const now = Date.now()

        if (isVoice) {
          lastVoiceTimeRef.current = now
          if (speakingRef.current) {
            window.speechSynthesis?.cancel()
            fishAudioRef.current?.pause()
            speakingRef.current = false
            setVoiceState('interruption')
          }

          if (!serverSpeakingRef.current) {
            serverSpeakingRef.current = true
            if (armedRef.current) {
              isUserSpeakingRef.current = true
              setVoiceState('user_speaking')
              if (silenceTimerRef.current) {
                clearTimeout(silenceTimerRef.current)
                silenceTimerRef.current = null
              }
            }
          }

          // Request interim transcription every 600ms while user is speaking
          if (!isTranscribingRef.current && now - lastInterimSentTimeRef.current >= 600 && serverAudioChunksRef.current.length > 0) {
            lastInterimSentTimeRef.current = now
            isTranscribingRef.current = true
            const blob = new Blob(serverAudioChunksRef.current, { type: recorder.mimeType || 'audio/webm' })

            try {
              const res = await fetch('/api/stt', {
                method: 'POST',
                headers: { 'Content-Type': blob.type },
                body: blob,
              })
              if (res.ok) {
                const data = await res.json()
                const text = String(data.text || '').trim()
                if (text) {
                  setRawTranscript(text)
                  if (!armedRef.current) {
                    const wake = extractWakeWord(text)
                    if (wake.detected) {
                      serverAudioChunksRef.current = []
                      activateListening(wake.trailingText)
                    }
                  } else {
                    const clean = stripWakeWord(text)
                    if (clean) {
                      isUserSpeakingRef.current = true
                      speechBufferRef.current = clean
                      setLiveTranscript(clean)
                      setVoiceState('user_speaking')
                    }
                  }
                }
              }
            } catch (err) {
              console.warn('Server STT interim error:', err)
            } finally {
              isTranscribingRef.current = false
            }
          }
        } else {
          // Silence detected
          if (serverSpeakingRef.current && now - lastVoiceTimeRef.current >= 1200) {
            serverSpeakingRef.current = false

            if (armedRef.current) {
              // User stopped speaking their command! Perform final transcription
              if (serverAudioChunksRef.current.length > 0) {
                const finalBlob = new Blob(serverAudioChunksRef.current, { type: recorder.mimeType || 'audio/webm' })
                serverAudioChunksRef.current = []
                isTranscribingRef.current = true
                try {
                  const res = await fetch('/api/stt', {
                    method: 'POST',
                    headers: { 'Content-Type': finalBlob.type },
                    body: finalBlob,
                  })
                  if (res.ok) {
                    const data = await res.json()
                    const finalText = String(data.text || '').trim()
                    const clean = stripWakeWord(finalText)
                    commitCommand(clean)
                  } else {
                    commitCommand()
                  }
                } catch {
                  commitCommand()
                } finally {
                  isTranscribingRef.current = false
                }
              } else {
                commitCommand()
              }
            } else {
              // In standby, reset accumulated chunks periodically if silent
              if (serverAudioChunksRef.current.length > 20) {
                serverAudioChunksRef.current = serverAudioChunksRef.current.slice(-6)
              }
            }
          }
        }
      }, 100)
    } catch (err) {
      console.error('Server STT startup failed:', err)
      setVoiceError('Failed to initialize server STT audio recorder.')
    }
  }, [activateListening, commitCommand, stopServerStt])

  const startRecognitionSession = useCallback(() => {
    if (!listeningRef.current) return
    stopServerStt()

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
      let sessionFinal = ''
      let sessionInterim = ''
      for (let i = 0; i < event.results.length; i++) {
        const item = event.results[i]
        if (item.isFinal) {
          sessionFinal += (sessionFinal ? ' ' : '') + item[0].transcript.trim()
        } else {
          sessionInterim += (sessionInterim ? ' ' : '') + item[0].transcript.trim()
        }
      }

      const transcript = `${sessionFinal} ${sessionInterim}`.trim()
      if (transcript) {
        setRawTranscript(transcript)
      }

      // If Nexus is speaking and user speaks, interrupt playback
      if (speakingRef.current && transcript) {
        window.speechSynthesis?.cancel()
        fishAudioRef.current?.pause()
        speakingRef.current = false
        setVoiceState('interruption')
      }

      // 1. STANDBY MODE (listening for wake word)
      if (!armedRef.current) {
        const wake = extractWakeWord(transcript)
        if (wake.detected) {
          recognitionTextRef.current = ''
          activateListening(wake.trailingText)
          return
        }

        const accumulated = `${recognitionTextRef.current} ${transcript}`.trim()
        const wakeAcc = extractWakeWord(accumulated)
        if (wakeAcc.detected) {
          recognitionTextRef.current = ''
          activateListening(wakeAcc.trailingText)
          return
        }

        if (sessionFinal) {
          recognitionTextRef.current = sessionFinal.slice(-80)
        }
        return
      }

      // 2. ARMED / LISTENING MODE (capturing user command)
      if (silenceTimerRef.current) {
        clearTimeout(silenceTimerRef.current)
        silenceTimerRef.current = null
      }

      const cleanCommand = stripWakeWord(transcript)
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
        setVoiceError('The browser speech service is unavailable. Check your connection or browser settings.')
        if (listeningRef.current && !armedRef.current) setVoiceState('idle')
        return
      }

      if (code === 'not-allowed' || code === 'service-not-allowed') {
        if (listeningRef.current && notAllowedRetryRef.current < 3) {
          notAllowedRetryRef.current += 1
          console.warn(`Speech recognition not-allowed on restart, retrying (${notAllowedRetryRef.current}/3)`)
          if (recognitionRestartRef.current) clearTimeout(recognitionRestartRef.current)
          recognitionRestartRef.current = setTimeout(() => {
            if (listeningRef.current) startRecognitionSession()
          }, 600)
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
      if (!listeningRef.current) return

      // If speech was in progress and recognition ended, commit the buffered command
      if (armedRef.current && isUserSpeakingRef.current && speechBufferRef.current.trim()) {
        commitCommand()
      }

      if (recognitionRestartRef.current) clearTimeout(recognitionRestartRef.current)
      recognitionRestartRef.current = setTimeout(() => {
        if (listeningRef.current && sttMode === 'web') startRecognitionSession()
      }, RECOGNITION_RESTART_DELAY_MS)
    }

    recognitionRef.current = recognition
    try {
      recognition.start()
    } catch (err) {
      console.warn('Recognition start warning:', err)
    }
  }, [activateListening, commitCommand, resetSpeechPauseTimer, stopServerStt, sttMode])

  useEffect(() => {
    if (listeningRef.current) {
      if (sttMode === 'server') {
        if (recognitionRef.current) {
          try {
            recognitionRef.current.onresult = null
            recognitionRef.current.onerror = null
            recognitionRef.current.onend = null
            recognitionRef.current.stop()
          } catch {}
          recognitionRef.current = null
        }
        startServerSttSession()
      } else {
        stopServerStt()
        startRecognitionSession()
      }
    }
  }, [sttMode, startRecognitionSession, startServerSttSession, stopServerStt])

  const toggleMic = useCallback(async () => {
    if (micEnabled) {
      listeningRef.current = false
      armedRef.current = false
      isUserSpeakingRef.current = false
      isSendingRef.current = false
      speechBufferRef.current = ''
      sessionFinalRef.current = ''
      setVoiceError('')
      stopServerStt()
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
      recognitionTextRef.current = ''
      setRawTranscript('')
      setLiveTranscript('')
      setMicEnabled(true)
      setVoiceState('idle')

      if (sttMode === 'server') {
        startServerSttSession()
      } else {
        const Recognition = window.SpeechRecognition || window.webkitSpeechRecognition
        if (!Recognition) throw new Error('Speech recognition is not supported by this browser. Please switch to Server STT or use Chrome.')
        startRecognitionSession()
      }
    } catch (error) {
      console.error('MIC START FAILED:', error)
      stopServerStt()
      streamRef.current?.getTracks().forEach((track) => track.stop())
      streamRef.current = null
      setVoiceError(error instanceof Error ? error.message : 'Microphone setup failed.')
      setVoiceState('error')
      setMicEnabled(false)
      listeningRef.current = false
    } finally {
      setIsStartingMic(false)
    }
  }, [micEnabled, startRecognitionSession, startServerSttSession, stopServerStt, sttMode])

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
      stopServerStt()
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
  }, [refresh, stopServerStt])

  return {
    connection,
    micEnabled,
    isStartingMic,
    voiceState,
    voiceError,
    liveTranscript,
    spokenResponse,
    events,
    interactions,
    latencyMs,
    lastCommunication,
    rawTranscript,
    sttMode,
    toggleSttMode,
    setSttMode,
    toggleMic,
    retry,
    stopSpeaking,
    triggerInterruption: stopSpeaking,
    sendText,
  }
}

export type NexusClient = ReturnType<typeof useNexus>