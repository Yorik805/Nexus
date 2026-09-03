import { NextRequest, NextResponse } from 'next/server'
import fs from 'node:fs'
import path from 'node:path'

function configuredNexusUrl() {
  if (process.env.NEXUS_URL) return process.env.NEXUS_URL
  try {
    const config = JSON.parse(fs.readFileSync(path.resolve(process.cwd(), '../../../nexus.config.json'), 'utf8')) as { host?: string; runtime_port?: number; protocol?: string }
    return `${config.protocol || 'http'}://${config.host || '127.0.0.1'}:${config.runtime_port || 8765}`
  } catch {
    return 'http://127.0.0.1:8765'
  }
}

export async function POST(request: NextRequest) {
  try {
    const input = await request.json() as { text?: string; message?: string; source?: string; device_id?: string }
    const text = String(input.text || input.message || '').trim()
    if (!text) {
      return NextResponse.json({ status: 'ERROR', message: 'text must be a non-empty string.' }, { status: 400 })
    }
    const response = await fetch(`${configuredNexusUrl().replace(/\/$/, '')}/message`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        device_id: input.device_id || input.source || 'web-client',
        text,
      }),
      cache: 'no-store',
    })
    const body = await response.text()
    return new NextResponse(body, {
      status: response.status,
      headers: { 'Content-Type': response.headers.get('content-type') || 'application/json' },
    })
  } catch (error) {
    return NextResponse.json({ status: 'ERROR', message: String(error) }, { status: 502 })
  }
}