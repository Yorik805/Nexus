'use client'

import { useState } from 'react'
import type { ConsoleMode, NexusStatus } from '@/lib/nexus/types'
import { useNexus } from '@/lib/nexus/use-nexus'
import { ConsoleHeader } from './console-header'
import { VoiceInterface } from './voice-interface'
import { InteractionHistory } from './interaction-history'
import { EventMonitor } from './event-monitor'
import { ConnectionStatus } from './connection-status'
import { DebugFlow } from './debug-flow'
import { StatusBar } from './status-bar'

export function NexusConsole() {
  const nexus = useNexus()
  const [mode, setMode] = useState<ConsoleMode>('normal')

  const status: NexusStatus = {
    connection: nexus.connection,
    endpointLabel: 'Configured Nexus endpoint',
    latencyMs: nexus.latencyMs,
    lastCommunication: nexus.lastCommunication,
  }

  return (
    <div className="flex min-h-dvh flex-col bg-background text-foreground lg:h-dvh lg:overflow-hidden">
      <ConsoleHeader
        connection={nexus.connection}
        micEnabled={nexus.micEnabled}
        mode={mode}
        onRetry={nexus.retry}
        onToggleMic={nexus.toggleMic}
        onModeChange={setMode}
      />

      <main className="flex flex-1 flex-col lg:min-h-0 lg:flex-row">
        {/* Primary column: voice interface */}
        <div className="flex flex-col lg:min-h-0 lg:flex-1">
          <div className="bg-console-grid flex min-h-[58vh] items-center justify-center lg:min-h-0 lg:flex-1">
            <VoiceInterface
              voiceState={nexus.voiceState}
              errorMessage={nexus.voiceError}
              liveTranscript={nexus.liveTranscript}
              spokenResponse={nexus.spokenResponse}
              onStopSpeaking={nexus.stopSpeaking}
              onInterrupt={nexus.triggerInterruption}
            />
          </div>
          <InteractionHistory interactions={nexus.interactions} />
        </div>

        {/* Sidebar: status + monitor */}
        <aside className="flex min-h-0 w-full flex-col overflow-y-auto border-t border-border bg-card/20 lg:w-[360px] lg:border-l lg:border-t-0">
          <ConnectionStatus status={status} />
          {mode === 'debug' && <DebugFlow events={nexus.events} />}
          <div className="min-h-80 flex-1">
            <EventMonitor events={nexus.events} />
          </div>
        </aside>
      </main>

      <StatusBar
        connection={nexus.connection}
        voiceState={nexus.voiceState}
        mode={mode}
        latencyMs={nexus.latencyMs}
      />
    </div>
  )
}
