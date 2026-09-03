import { NextRequest, NextResponse } from 'next/server'

const fishApiUrl = process.env.FISH_AUDIO_API_URL || 'https://api.fish.audio/v1/tts'

export async function POST(request: NextRequest) {
  const apiKey = process.env.FISH_AUDIO_API_KEY
  const referenceId = process.env.FISH_AUDIO_VOICE_ID
  if (!apiKey || !referenceId) {
    return NextResponse.json(
      { status: 'ERROR', message: 'Fish Audio is not configured. Set FISH_AUDIO_API_KEY and FISH_AUDIO_VOICE_ID.' },
      { status: 503 },
    )
  }

  try {
    const body = await request.json() as { text?: string }
    const text = String(body.text || '').trim()
    if (!text) return NextResponse.json({ status: 'ERROR', message: 'text is required.' }, { status: 400 })

    const response = await fetch(fishApiUrl, {
      method: 'POST',
      headers: {
        Authorization: `Bearer ${apiKey}`,
        'Content-Type': 'application/json',
        Accept: 'audio/mpeg',
      },
      body: JSON.stringify({
        text,
        reference_id: referenceId,
        format: 'mp3',
        latency: process.env.FISH_AUDIO_LATENCY || 'normal',
      }),
      cache: 'no-store',
    })
    if (!response.ok) return NextResponse.json({ status: 'ERROR', message: `Fish Audio returned ${response.status}.` }, { status: 502 })
    return new NextResponse(await response.arrayBuffer(), {
      status: 200,
      headers: { 'Content-Type': response.headers.get('content-type') || 'audio/mpeg', 'Cache-Control': 'no-store' },
    })
  } catch (error) {
    return NextResponse.json({ status: 'ERROR', message: String(error) }, { status: 502 })
  }
}