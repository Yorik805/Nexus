'use client'

import {
  AlertTriangle,
  Hand,
  Mic,
  MicOff,
  Square,
  Volume2,
} from 'lucide-react'
import { cn } from '@/lib/utils'
import type { VoiceState } from '@/lib/nexus/types'
import { Waveform } from './waveform'

interface StateConfig {
  title: string
  subtitle: string
  /** token color name suffix, e.g. "primary" | "cat-error" */
  accent: string
}

const STATE_CONFIG: Record<VoiceState, StateConfig> = {
  idle: { title: 'STANDBY', subtitle: 'Mic is ready — say “Hey Nexus”', accent: 'muted-foreground' },
  listening: { title: 'LISTENING', subtitle: 'Waiting for speech…', accent: 'primary' },
  user_speaking: { title: 'USER SPEAKING', subtitle: 'Transcribing input', accent: 'primary' },
  processing: { title: 'PROCESSING', subtitle: 'Nexus is handling the event…', accent: 'cat-validator' },
  nexus_speaking: { title: 'NEXUS SPEAKING', subtitle: 'Responding via text-to-speech', accent: 'cat-event' },
  interruption: { title: 'INTERRUPTION DETECTED', subtitle: 'Nexus speech paused — listening to user', accent: 'cat-validator' },
  mic_disabled: { title: 'MICROPHONE DISABLED', subtitle: 'Enable the mic to talk to Nexus', accent: 'muted-foreground' },
  error: { title: 'VOICE INPUT ERROR', subtitle: 'Browser speech recognition is unavailable', accent: 'cat-error' },
}

export function VoiceInterface({
  voiceState,
  errorMessage,
  liveTranscript,
  spokenResponse,
  onStopSpeaking,
  onInterrupt,
}: {
  voiceState: VoiceState
  errorMessage?: string
  liveTranscript: string
  spokenResponse: string
  onStopSpeaking: () => void
  onInterrupt: () => void
}) {
  const cfg = STATE_CONFIG[voiceState]
  const isListening = voiceState === 'listening'
  const isUserSpeaking = voiceState === 'user_speaking'
  const hasTranscript = Boolean(liveTranscript.trim())
  const isProcessing = voiceState === 'processing'
  const isNexusSpeaking = voiceState === 'nexus_speaking'
  const isError = voiceState === 'error'
  const isMuted = voiceState === 'mic_disabled'
  const isInterruption = voiceState === 'interruption'

  return (
    <section
      aria-label="Voice interface"
      className="flex h-full w-full flex-col items-center justify-center gap-8 px-6 py-8"
    >
      {/* Central visualization */}
      <div className="relative flex size-56 items-center justify-center md:size-64">
        {/* Pulse rings — active listening */}
        {(isListening || isInterruption) && (
          <>
            <span className={cn('absolute size-40 rounded-full border animate-nexus-ring', ringColor(cfg.accent))} />
            <span
              className={cn('absolute size-40 rounded-full border animate-nexus-ring', ringColor(cfg.accent))}
              style={{ animationDelay: '1.2s' }}
            />
          </>
        )}

        {/* Processing arc */}
        {isProcessing && (
          <span
            className={cn(
              'absolute size-52 rounded-full border-2 border-transparent animate-nexus-spin md:size-60',
              'border-t-cat-validator border-r-cat-validator/40',
            )}
          />
        )}

        {/* Core disc */}
        <div
          className={cn(
            'relative flex size-40 items-center justify-center rounded-full ring-1 transition-colors md:size-44',
            discClasses(cfg.accent, isListening || isNexusSpeaking),
          )}
        >
          <StateIcon
            voiceState={voiceState}
            className={cn('size-16 md:size-20', textColor(cfg.accent))}
          />
        </div>
      </div>

      {/* State label */}
      <div className="text-center">
        <h2
          className={cn(
            'font-mono text-xl font-semibold tracking-[0.2em] md:text-2xl',
            textColor(cfg.accent),
          )}
        >
          {cfg.title}
        </h2>
        <p className="mt-2 font-mono text-xs tracking-wide text-muted-foreground">
          {cfg.subtitle}
        </p>
      </div>

      {/* Dynamic content region */}
      <div className="flex min-h-24 w-full max-w-xl flex-col items-center justify-center gap-4">
        {(isUserSpeaking || (isListening && hasTranscript)) && (
          <>
            <Waveform active bars={32} colorClass="bg-primary" />
            <p className="text-pretty text-center text-lg text-foreground">
              {liveTranscript ? (
                <>
                  <span className="text-muted-foreground">“</span>
                  {liveTranscript}
                  <span className="ml-0.5 inline-block h-5 w-[2px] translate-y-1 bg-primary animate-nexus-caret" />
                </>
              ) : (
                <span className="text-muted-foreground">Listening for speech…</span>
              )}
            </p>
          </>
        )}

        {isNexusSpeaking && (
          <>
            <Waveform active bars={32} colorClass="bg-cat-event" />
            <p className="text-pretty text-center text-lg text-foreground">
              {spokenResponse}
            </p>
            <button
              type="button"
              onClick={onStopSpeaking}
              className="flex items-center gap-2 rounded-md border border-cat-error/40 bg-cat-error/10 px-4 py-2 font-mono text-xs tracking-widest text-cat-error transition-colors hover:bg-cat-error/20"
            >
              <Square className="size-3.5 fill-current" />
              STOP SPEAKING
            </button>
            <div className="mt-1 flex items-center gap-2 font-mono text-[10px] tracking-widest text-primary">
              <span className="relative flex size-2">
                <span className="absolute inline-flex size-full rounded-full bg-primary/60 animate-nexus-ring" />
                <span className="relative inline-flex size-2 rounded-full bg-primary" />
              </span>
              MIC LIVE — SAY “HEY NEXUS” TO INTERRUPT
            </div>
          </>
        )}

        {isProcessing && (
          <div className="flex items-center gap-1.5">
            {[0, 1, 2].map((i) => (
              <span
                key={i}
                className="size-2.5 rounded-full bg-cat-validator animate-nexus-breathe"
                style={{ animationDelay: `${i * 0.2}s` }}
              />
            ))}
          </div>
        )}

        {isInterruption && (
          <p className="text-pretty text-center text-sm text-cat-validator">
            User interrupted while Nexus was speaking. Playback halted; microphone re-engaged.
          </p>
        )}

        {isMuted && (
          <p className="text-pretty text-center text-sm text-muted-foreground">
            The microphone is off. Voice capture and continuous listening are paused.
          </p>
        )}

        {isError && (
          <p className="text-pretty text-center text-sm text-cat-error">
            {errorMessage || 'Unable to start voice capture. Check microphone permissions and try again.'}
          </p>
        )}
      </div>
    </section>
  )
}

function StateIcon({
  voiceState,
  className,
}: {
  voiceState: VoiceState
  className?: string
}) {
  switch (voiceState) {
    case 'mic_disabled':
      return <MicOff className={className} />
    case 'nexus_speaking':
      return <Volume2 className={className} />
    case 'error':
      return <AlertTriangle className={className} />
    case 'interruption':
      return <Hand className={className} />
    default:
      return <Mic className={cn(className, voiceState === 'listening' && 'animate-nexus-breathe')} />
  }
}

/* --- token → class helpers (kept explicit so Tailwind can see them) --- */
function textColor(accent: string): string {
  const map: Record<string, string> = {
    primary: 'text-primary',
    'cat-error': 'text-cat-error',
    'cat-event': 'text-cat-event',
    'cat-validator': 'text-cat-validator',
    'muted-foreground': 'text-muted-foreground',
  }
  return map[accent] ?? 'text-foreground'
}

function ringColor(accent: string): string {
  const map: Record<string, string> = {
    primary: 'border-primary/40',
    'cat-error': 'border-cat-error/40',
    'cat-event': 'border-cat-event/40',
    'cat-validator': 'border-cat-validator/40',
    'muted-foreground': 'border-muted-foreground/40',
  }
  return map[accent] ?? 'border-border'
}

function discClasses(accent: string, glow: boolean): string {
  const bg: Record<string, string> = {
    primary: 'bg-primary/10 ring-primary/30',
    'cat-error': 'bg-cat-error/10 ring-cat-error/30',
    'cat-event': 'bg-cat-event/10 ring-cat-event/30',
    'cat-validator': 'bg-cat-validator/10 ring-cat-validator/30',
    'muted-foreground': 'bg-muted/40 ring-border',
  }
  return cn(bg[accent] ?? 'bg-muted/40 ring-border', glow && 'shadow-[0_0_60px_-12px_currentColor]')
}
