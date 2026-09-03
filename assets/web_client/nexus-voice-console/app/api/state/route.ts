import { NextResponse } from 'next/server'
import fs from 'node:fs'
import path from 'node:path'

function configuredBackendUrl() {
  if (process.env.NEXUS_DASHBOARD_BACKEND_URL) return process.env.NEXUS_DASHBOARD_BACKEND_URL
  try {
    const config = JSON.parse(fs.readFileSync(path.resolve(process.cwd(), '../../../nexus.config.json'), 'utf8')) as { host?: string; dashboard_port?: number }
    return `http://${config.host || '127.0.0.1'}:${config.dashboard_port || 11882}`
  } catch {
    return 'http://127.0.0.1:11882'
  }
}

export async function GET() {
  try {
    const response = await fetch(`${configuredBackendUrl()}/api/state`, { cache: 'no-store' })
    const body = await response.text()
    return new NextResponse(body, {
      status: response.status,
      headers: { 'Content-Type': response.headers.get('content-type') || 'application/json' },
    })
  } catch (error) {
    return NextResponse.json({ status: 'ERROR', message: String(error) }, { status: 502 })
  }
}