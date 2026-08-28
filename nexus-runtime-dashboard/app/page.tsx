'use client'

import { useEffect, useMemo, useRef, useState } from 'react'
import { Activity, ArrowDown, CheckCircle2, CircleAlert, Copy, ExternalLink, Gauge, Globe, Info, Lock, Radio, Server, Terminal, Unlock, X } from 'lucide-react'

type EventKind = 'USER_MESSAGE' | 'EXECUTION_RESULT' | 'ERROR' | 'SYSTEM'
type AiResponse = { model: string; status: number; latency: string; tokens: string; detail: string }
type RuntimeEvent = { time: string; kind: EventKind; source: string; message: string; response?: AiResponse }
type ApiState = {
  events: RuntimeEvent[]
  iteration: number
  activeActions: number
  provider: { name: string; model: string; status: string; latency?: string }
  uptime: string
  progress: number
}

const initialState: ApiState = {
  events: [],
  iteration: 0,
  activeActions: 0,
  provider: { name: '\u2014', model: '\u2014', status: 'OFFLINE' },
  uptime: '00:00:00:00',
  progress: 0,
}

function copyText(value: string) { navigator.clipboard?.writeText(value) }

export default function Page() {
  const [state, setState] = useState<ApiState>(initialState)
  const [locked, setLocked] = useState(true)
  const [selected, setSelected] = useState<RuntimeEvent | null>(null)
  const [sync, setSync] = useState('\u2014')
  const streamRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    setSync(new Date().toLocaleTimeString('en-US', { hour12: false }))
    const clock = window.setInterval(() => setSync(new Date().toLocaleTimeString('en-US', { hour12: false })), 1000)
    const poll = window.setInterval(async () => {
      try {
        const res = await fetch('/api/state')
        if (res.ok) {
          const data = await res.json()
          setState({
            events: data.events || [],
            iteration: data.iteration || 0,
            activeActions: data.activeActions || 0,
            provider: data.provider || initialState.provider,
            uptime: data.uptime || '00:00:00:00',
            progress: data.progress || 0,
          })
        }
      } catch {
        // keep previous state on network error
      }
    }, 2000)
    return () => { window.clearInterval(clock); window.clearInterval(poll) }
  }, [])

  useEffect(() => { if (locked && streamRef.current) streamRef.current.scrollTop = 0 }, [state.events, locked])

  const { events, iteration, activeActions, provider, uptime, progress } = state
  const decisionColor = activeActions > 0 ? 'continue' : 'complete'

  return <main className="nexus-shell">
    <header className="topbar"><div className="brand-block"><div className="brand-mark"><Terminal size={17} /></div><div><h1>NEXUS RUNTIME</h1><p>LOCAL INTELLIGENCE CORE <span>/</span> v2.4.1</p></div></div><div className="topbar-meta"><div className="live-status"><span className="status-dot" /> ONLINE</div><div className="timestamp"><span>UPTIME</span> {uptime}</div><div className="timestamp"><span>SYNC</span> {sync}</div></div></header>
    <section className="dashboard-grid"><section className="panel event-panel"><div className="panel-heading"><div><span className="eyebrow"><Radio size={12} /> TELEMETRY / 01</span><h2>Event Stream</h2><p className="helper-text">Click a Gemini/Ollama response event to inspect its output.</p></div><div className="stream-tools"><span className="event-count">{events.length.toString().padStart(2, '0')} EVENTS</span><button className={`lock-button ${locked ? 'active' : ''}`} onClick={() => setLocked(!locked)} aria-label={locked ? 'Unlock scroll' : 'Lock scroll'}>{locked ? <Lock size={13} /> : <Unlock size={13} />} {locked ? 'LOCKED' : 'FREE'}</button></div></div><div className="event-columns"><span>TIME</span><span>TYPE</span><span>SOURCE</span><span>PAYLOAD</span></div><div className="event-stream" ref={streamRef} aria-live="polite">{[...events].reverse().map((event, index) => <button className={`event-row ${event.response ? 'clickable' : ''}`} key={`${event.time}-${index}`} onClick={() => event.response && setSelected(event)} aria-label={event.response ? `Inspect response at ${event.time}` : undefined}><span className="event-time">{event.time}</span><span className={`event-kind ${event.kind.toLowerCase()}`}>{event.kind}</span><span className="event-source">{event.source}</span><span className="event-message">{event.message}</span>{event.response && <ExternalLink size={13} className="inspect-icon" />}</button>)}</div><div className="stream-footer"><span><span className="pulse-line" /> STREAMING LIVE</span><span>CLICK RESPONSE TO INSPECT <ArrowDown size={12} /></span></div></section>
      <aside className="side-stack"><section className="panel metric-card"><div className="panel-heading compact"><span className="eyebrow"><Activity size={12} /> PROCESS / 02</span><span className="card-index">A-01</span></div><h2>Current Iteration</h2><div className="iteration-line"><strong>#{iteration}</strong><span className={`decision ${decisionColor}`}><span /> {decisionColor === 'continue' ? 'CONTINUE' : 'IDLE'}</span></div><div className="progress-meta"><span>ACTION QUEUE</span><b>{activeActions} ACTIVE</b></div><div className="progress-track"><div style={{ width: `${progress}%` }} /></div><div className="card-foot"><span>{iteration > 0 ? 'HEALTHY' : 'IDLE'}</span><span>{progress}% CONTEXT</span></div></section><section className="panel metric-card"><div className="panel-heading compact"><span className="eyebrow"><Globe size={12} /> HTTP / 03</span><span className="card-index">API</span></div><h2>Send Events</h2><div className="api-contract"><code>POST /api/nexus/events</code><span>Content-Type: application/json</span><span>Authorization: Bearer &lt;token&gt;</span></div><div className="api-guide"><span className="label">EVENT BODY</span><code>{`{"type":"user.message","source":"dashboard","message":"Hello Nexus"}`}</code><span className="label">RESPONSE</span><code>202 Accepted Â· event added to stream</code></div><p className="console-note"><Info size={12} /> Send events to the Nexus runtime. Events appear in the stream after the runtime processes them.</p></section><section className="panel metric-card"><div className="panel-heading compact"><span className="eyebrow"><Server size={12} /> INFERENCE / 04</span><span className="card-index">L-01</span></div><h2>Provider Status</h2><div className="provider-row"><div><span className="label">PROVIDER</span><strong>{provider.name}</strong></div><div className="provider-online"><span className="status-dot" /> {provider.status}</div></div><div className="detail-grid"><div><span className="label">MODEL</span><strong>{provider.model}</strong></div><div><span className="label">LATENCY</span><strong>{provider.latency || '\u2014'}</strong></div></div></section></aside></section>
    <footer className="status-footer"><span><Gauge size={13} /> CPU â€” <i /> MEM â€” <i /> TOKENS â€”</span><span>NEXUS / LOCAL RUNTIME</span></footer>
    {selected?.response && <div className="inspector-backdrop" role="presentation" onClick={() => setSelected(null)}><section className="inspector" role="dialog" aria-modal="true" aria-labelledby="response-title" onClick={e => e.stopPropagation()}><div className="inspector-header"><div><span className="eyebrow"><Terminal size={12} /> LLM RESPONSE</span><h2 id="response-title">Model Output</h2></div><button className="close-button" onClick={() => setSelected(null)} aria-label="Close response inspector"><X size={17} /></button></div><div className="exchange-meta"><span className="method-pill">AI OUTPUT</span><code>{selected.response.model}</code><span className="badge success"><CheckCircle2 size={12} /> {selected.response.status} OK</span><span className="latency">{selected.response.latency}</span><span className="latency">{selected.response.tokens} TOKENS</span></div><div className="terminal-output"><div className="code-title">TERMINAL OUTPUT / MODEL RESPONSE <button onClick={() => copyText(selected.response!.detail)}><Copy size={12} /> COPY</button></div><pre>{selected.response.detail}</pre></div><div className="exchange-note"><Info size={13} /><span>This panel opens when you click a provider response event in the stream.</span></div></section></div>}
  </main>
}
