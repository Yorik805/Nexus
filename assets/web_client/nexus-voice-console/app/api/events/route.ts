import { NextRequest, NextResponse } from 'next/server'

const nexusUrl = process.env.NEXUS_URL || 'http://127.0.0.1:8765'

export async function POST(request: NextRequest) {
  try {
    const input = await request.json() as { text?: string; message?: string; source?: string; device_id?: string }
    const text = String(input.text || input.message || '').trim()
    if (!text) {
      return NextResponse.json({ status: 'ERROR', message: 'text must be a non-empty string.' }, { status: 400 })
    }
    const response = await fetch(`${nexusUrl.replace(/\/$/, '')}/message`, {
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