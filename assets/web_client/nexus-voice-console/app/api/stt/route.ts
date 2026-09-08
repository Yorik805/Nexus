import { NextRequest, NextResponse } from 'next/server'
import fs from 'node:fs'
import path from 'node:path'

function configuredNexusUrl() {
  if (process.env.NEXUS_URL) return process.env.NEXUS_URL
  try {
    const config = JSON.parse(fs.readFileSync(path.resolve(process.cwd(), '../../../nexus.config.json'), 'utf8')) as { runtime_port?: number }
    return `http://127.0.0.1:${config.runtime_port || 8765}`
  } catch {
    return 'http://127.0.0.1:8765'
  }
}

export async function POST(request: NextRequest) {
  try {
    const audioBlob = await request.blob()
    if (!audioBlob || audioBlob.size === 0) {
      return NextResponse.json({ status: 'ERROR', message: 'Empty audio payload.' }, { status: 400 })
    }

    const nexusUrl = configuredNexusUrl().replace(/\/$/, '')
    const contentType = request.headers.get('content-type') || 'audio/webm'

    const response = await fetch(`${nexusUrl}/stt`, {
      method: 'POST',
      headers: {
        'Content-Type': contentType,
      },
      body: audioBlob,
      cache: 'no-store',
    })

    const body = await response.text()
    return new NextResponse(body, {
      status: response.status,
      headers: { 'Content-Type': 'application/json' },
    })
  } catch (error) {
    return NextResponse.json({ status: 'ERROR', message: String(error) }, { status: 502 })
  }
}
