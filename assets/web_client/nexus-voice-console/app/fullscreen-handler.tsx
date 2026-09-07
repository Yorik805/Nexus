'use client'

import { useEffect } from 'react'

export function FullscreenOnDoubleTap() {
  useEffect(() => {
    let lastTap = 0

    const toggleFullscreen = async () => {
      try {
        if (!document.fullscreenElement) {
          await document.documentElement.requestFullscreen()
        } else {
          await document.exitFullscreen()
        }
      } catch (error) {
        console.error('Fullscreen failed:', error)
      }
    }

    const handleTouchEnd = () => {
      const now = Date.now()

      if (now - lastTap < 300) {
        toggleFullscreen()
      }

      lastTap = now
    }

    const handleDoubleClick = () => {
      toggleFullscreen()
    }

    document.addEventListener('touchend', handleTouchEnd)
    document.addEventListener('dblclick', handleDoubleClick)

    return () => {
      document.removeEventListener('touchend', handleTouchEnd)
      document.removeEventListener('dblclick', handleDoubleClick)
    }
  }, [])

  return null
}