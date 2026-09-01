import { NextResponse } from 'next/server'

const backendUrl = process.env.NEXUS_DASHBOARD_BACKEND_URL || 'http://127.0.0.1:11882'

export async function GET() {
  try {
    const response = await fetch(`${backendUrl}/api/state`, { cache: 'no-store' })
    const body = await response.text()
    return new NextResponse(body, {
      status: response.status,
      headers: { 'Content-Type': response.headers.get('content-type') || 'application/json' },
    })
  } catch (error) {
    return NextResponse.json({ status: 'ERROR', message: String(error) }, { status: 502 })
  }
}
