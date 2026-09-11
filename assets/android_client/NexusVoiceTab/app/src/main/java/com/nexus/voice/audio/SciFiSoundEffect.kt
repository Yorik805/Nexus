package com.nexus.voice.audio

import android.media.AudioAttributes
import android.media.AudioFormat
import android.media.AudioTrack
import android.util.Log
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlin.math.PI
import kotlin.math.exp
import kotlin.math.sin

object SciFiSoundEffect {

    private const val TAG = "SciFiSoundEffect"
    private const val SAMPLE_RATE = 44100
    private val scope = CoroutineScope(Dispatchers.Default)

    // Pre-synthesized PCM buffer for 0-latency playback
    private val wakeChimePcm: ShortArray by lazy {
        generateWakeChime()
    }

    /**
     * Synthesizes a futuristic two-tone sci-fi activation chirp
     * Tone 1: 987 Hz (B5), Tone 2: 1318 Hz (E6), Tone 3: 1975 Hz (B6)
     * with exponential decay envelope
     */
    private fun generateWakeChime(): ShortArray {
        val durationMs = 180
        val totalSamples = (SAMPLE_RATE * (durationMs / 1000.0)).toInt()
        val buffer = ShortArray(totalSamples)

        val note1End = (totalSamples * 0.28).toInt()
        val note2End = (totalSamples * 0.55).toInt()

        for (i in 0 until totalSamples) {
            val t = i.toDouble() / SAMPLE_RATE

            val freq = when {
                i < note1End -> 987.0
                i < note2End -> 1318.0
                else -> 1975.0
            }

            // Envelope: rapid attack, smooth exponential decay
            val progressInNote = when {
                i < note1End -> i.toDouble() / note1End
                i < note2End -> (i - note1End).toDouble() / (note2End - note1End)
                else -> (i - note2End).toDouble() / (totalSamples - note2End)
            }

            val envelope = exp(-progressInNote * 3.5)
            // Harmonic overtone for metallic sci-fi sheen
            val sample = (0.75 * sin(2.0 * PI * freq * t) + 0.25 * sin(2.0 * PI * (freq * 2.0) * t)) * envelope
            buffer[i] = (sample * 26000.0).toInt().coerceIn(-32767, 32767).toShort()
        }

        return buffer
    }

    fun playWakeChime() {
        scope.launch {
            try {
                val track = AudioTrack.Builder()
                    .setAudioAttributes(
                        AudioAttributes.Builder()
                            .setUsage(AudioAttributes.USAGE_ASSISTANCE_SONIFICATION)
                            .setContentType(AudioAttributes.CONTENT_TYPE_SONIFICATION)
                            .build()
                    )
                    .setAudioFormat(
                        AudioFormat.Builder()
                            .setEncoding(AudioFormat.ENCODING_PCM_16BIT)
                            .setSampleRate(SAMPLE_RATE)
                            .setChannelMask(AudioFormat.CHANNEL_OUT_MONO)
                            .build()
                    )
                    .setBufferSizeInBytes(wakeChimePcm.size * 2)
                    .setTransferMode(AudioTrack.MODE_STATIC)
                    .build()

                track.write(wakeChimePcm, 0, wakeChimePcm.size)
                track.play()
                // Auto release after sound finishes
                Thread.sleep(220)
                track.stop()
                track.release()
            } catch (e: Exception) {
                Log.w(TAG, "Failed to play wake chime", e)
            }
        }
    }
}
