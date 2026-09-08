'use client'

import {
  AlertTriangle,
  Hand,
  Loader2,
  Mic,
  MicOff,
  RotateCw,
  Square,
  Volume2,
} from 'lucide-react'
import { cn } from '@/lib/utils'
import type { SttMode, VoiceState } from '@/lib/nexus/types'
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
  mic_disabled: { title: 'MICROPHONE DISABLED', subtitle: 'Tap the mic or button to start', accent: 'muted-foreground' },
  error: { title: 'VOICE INPUT ERROR', subtitle: 'Check microphone permissions or HTTPS connection', accent: 'cat-error' },
}

export function VoiceInterface({
  voiceState,
  errorMessage,
  liveTranscript,
  spokenResponse,
  onStopSpeaking,
  onInterrupt,
  onToggleMic,
  micEnabled,
  isStartingMic,
  sttMode = 'web',
  onToggleSttMode,
}: {
  voiceState: VoiceState
  errorMessage?: string
  liveTranscript: string
  spokenResponse: string
  onStopSpeaking: () => void
  onInterrupt: () => void
  onToggleMic?: () => void
  micEnabled?: boolean
  isStartingMic?: boolean
  sttMode?: SttMode
  onToggleSttMode?: () => void
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
      className="flex h-full w-full flex-col items-center justify-center gap-4 px-6 py-5 select-none"
    >
      {/* Central visualization - scaled to moderate proportion */}
      <div className="relative flex size-32 items-center justify-center md:size-36">
        {/* Pulse rings — active listening */}
        {(isListening || isInterruption) && (
          <>
            <span className={cn('absolute size-24 rounded-full border animate-nexus-ring', ringColor(cfg.accent))} />
            <span
              className={cn('absolute size-24 rounded-full border animate-nexus-ring', ringColor(cfg.accent))}
              style={{ animationDelay: '1.2s' }}
            />
          </>
        )}

        {/* Processing arc */}
        {isProcessing && (
          <span
            className={cn(
              'absolute size-28 rounded-full border-2 border-transparent animate-nexus-spin md:size-32',
              'border-t-cat-validator border-r-cat-validator/40',
            )}
          />
        )}

        {/* Core disc - interactive moderate circle */}
        <button
          type="button"
          onClick={onToggleMic}
          disabled={isStartingMic}
          aria-label={
            isStartingMic
              ? 'Starting microphone'
              : micEnabled
              ? 'Mute microphone'
              : 'Enable microphone'
          }
          title={
            isStartingMic
              ? 'Starting microphone…'
              : micEnabled
              ? 'Click to turn mic off'
              : 'Click to turn mic on'
          }
          className={cn(
            'group relative flex size-20 items-center justify-center rounded-full ring-1 transition-all md:size-24 select-none',
            'cursor-pointer hover:scale-105 active:scale-95 focus:outline-none focus-visible:ring-2 focus-visible:ring-primary',
            discClasses(cfg.accent, isListening || isNexusSpeaking),
            isStartingMic && 'animate-pulse ring-primary/60 cursor-wait',
          )}
        >
          <StateIcon
            voiceState={voiceState}
            isStartingMic={isStartingMic}
            className={cn('size-8 md:size-9 transition-transform group-hover:scale-105', textColor(cfg.accent))}
          />
        </button>
      </div>

      {/* State label */}
      <div className="text-center">
        <h2
          className={cn(
            'font-mono text-xs font-semibold tracking-[0.25em] md:text-sm',
            textColor(cfg.accent),
          )}
        >
          {cfg.title}
        </h2>
        <p className="mt-1 font-mono text-[11px] tracking-wide text-muted-foreground">
          {cfg.subtitle}
        </p>
      </div>

      {/* Dynamic content region */}
      <div className="flex min-h-16 w-full max-w-md flex-col items-center justify-center gap-3">
        {(isUserSpeaking || (isListening && hasTranscript)) && (
          <>
            <Waveform active bars={24} colorClass="bg-primary" />
            <p className="text-pretty text-center text-xs md:text-sm text-foreground leading-relaxed">
              {liveTranscript ? (
                <>
                  <span className="text-muted-foreground">“</span>
                  {liveTranscript}
                  <span className="ml-0.5 inline-block h-4 w-[2px] translate-y-0.5 bg-primary animate-nexus-caret" />
                </>
              ) : (
                <span className="text-muted-foreground">Listening for speech…</span>
              )}
            </p>
          </>
        )}

        {isNexusSpeaking && (
          <>
            <Waveform active bars={24} colorClass="bg-cat-event" />
            <p className="text-pretty text-center text-xs md:text-sm text-foreground leading-relaxed">
              {spokenResponse}
            </p>
            <button
              type="button"
              onClick={onStopSpeaking}
              className="flex items-center gap-1.5 rounded-md border border-cat-error/40 bg-cat-error/10 px-3 py-1.5 font-mono text-[11px] tracking-widest text-cat-error transition-colors hover:bg-cat-error/20 cursor-pointer active:scale-95"
            >
              <Square className="size-3 fill-current" />
              STOP SPEAKING
            </button>
            <div className="mt-0.5 flex items-center gap-1.5 font-mono text-[9px] tracking-widest text-primary">
              <span className="relative flex size-1.5">
                <span className="absolute inline-flex size-full rounded-full bg-primary/60 animate-nexus-ring" />
                <span className="relative inline-flex size-1.5 rounded-full bg-primary" />
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
                className="size-2 rounded-full bg-cat-validator animate-nexus-breathe"
                style={{ animationDelay: `${i * 0.2}s` }}
              />
            ))}
          </div>
        )}

        {isInterruption && (
          <p className="text-pretty text-center text-xs text-cat-validator">
            User interrupted while Nexus was speaking. Playback halted; microphone re-engaged.
          </p>
        )}

        {isMuted && (
          <div className="flex flex-col items-center gap-2.5">
            <p className="text-pretty text-center text-xs text-muted-foreground">
              Microphone is off. Continuous listening is paused.
            </p>
            {onToggleMic && (
              <button
                type="button"
                onClick={onToggleMic}
                disabled={isStartingMic}
                className="flex items-center gap-2 rounded-md border border-primary/50 bg-primary/20 px-4 py-2 font-mono text-xs font-semibold tracking-widest text-primary transition-all hover:bg-primary/30 active:scale-95 cursor-pointer shadow-[0_0_12px_rgba(var(--primary-rgb),0.25)]"
              >
                {isStartingMic ? (
                  <Loader2 className="size-3.5 animate-spin" />
                ) : (
                  <Mic className="size-3.5" />
                )}
                {isStartingMic ? 'STARTING MIC…' : 'TURN MIC ON'}
              </button>
            )}
          </div>
        )}

        {isError && (
          <div className="flex flex-col items-center gap-2.5">
            <p className="text-pretty text-center text-xs text-cat-error">
              {errorMessage || 'Unable to start voice capture. Check microphone permissions and try again.'}
            </p>
            {onToggleMic && (
              <button
                type="button"
                onClick={onToggleMic}
                disabled={isStartingMic}
                className="flex items-center gap-1.5 rounded-md border border-cat-error/50 bg-cat-error/20 px-4 py-2 font-mono text-xs font-semibold tracking-widest text-cat-error transition-all hover:bg-cat-error/30 active:scale-95 cursor-pointer"
              >
                {isStartingMic ? (
                  <Loader2 className="size-3.5 animate-spin" />
                ) : (
                  <RotateCw className="size-3.5" />
                )}
                {isStartingMic ? 'STARTING MIC…' : 'RETRY MICROPHONE'}
              </button>
            )}
          </div>
        )}

        {/* STT Engine toggle switch */}
        {onToggleSttMode && (
          <div className="mt-1 flex items-center gap-1.5 rounded-full border border-border/60 bg-card/40 p-1 font-mono text-[10px]">
            <span className="px-2 text-muted-foreground/70 tracking-wider">STT:</span>
            <button
              type="button"
              onClick={sttMode !== 'web' ? onToggleSttMode : undefined}
              className={cn(
                'rounded-full px-2.5 py-0.5 transition-all cursor-pointer',
                sttMode === 'web'
                  ? 'bg-primary/25 text-primary font-semibold shadow-[0_0_8px_rgba(var(--primary-rgb),0.2)]'
                  : 'text-muted-foreground hover:text-foreground',
              )}
            >
              WEB
            </button>
            <button
              type="button"
              onClick={sttMode !== 'server' ? onToggleSttMode : undefined}
              className={cn(
                'rounded-full px-2.5 py-0.5 transition-all cursor-pointer',
                sttMode === 'server'
                  ? 'bg-primary/25 text-primary font-semibold shadow-[0_0_8px_rgba(var(--primary-rgb),0.2)]'
                  : 'text-muted-foreground hover:text-foreground',
              )}
            >
              SERVER (WHISPER)
            </button>
          </div>
        )}
      </div>
    </section>
  )
}

function StateIcon({
  voiceState,
  isStartingMic,
  className,
}: {
  voiceState: VoiceState
  isStartingMic?: boolean
  className?: string
}) {
  if (isStartingMic) {
    return <Loader2 className={cn(className, 'animate-spin text-primary')} />
  }
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
