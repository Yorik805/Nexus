package com.nexus.voice.engine

import android.content.Context
import android.content.res.AssetManager
import android.media.AudioFormat
import android.media.AudioRecord
import android.media.MediaRecorder
import android.os.Handler
import android.os.Looper
import android.util.Log
import com.nexus.voice.state.VoiceState
import org.json.JSONObject
import org.vosk.Model
import org.vosk.Recognizer
import org.vosk.android.StorageService
import java.io.File
import java.io.IOException
import kotlin.math.sqrt

class VoskSpeechManager(
    private val context: Context,
    private val onStateChanged: (VoiceState, String) -> Unit,
    private val onPartialTranscript: (String) -> Unit,
    private val onFinalTranscript: (String) -> Unit,
    private val onRawTranscript: (String) -> Unit = {},
    private val onAudioLevel: (Float) -> Unit = {}
) {

    private val TAG = "VoskSpeechManager"
    private val MODEL_NAME = "vosk-model-small-en-in-0.4"
    private val SAMPLE_RATE = 16000.0f
    private val WAKE_SILENCE_TIMEOUT_MS = 5000L

    private var model: Model? = null
    private var recognizer: Recognizer? = null
    private var isArmed = false
    private val mainHandler = Handler(Looper.getMainLooper())
    private var silenceRunnable: Runnable? = null

    private var audioRecord: AudioRecord? = null
    private var audioThread: Thread? = null

    @Volatile
    var isMicActive = false
        private set

    fun initModel() {
        onStateChanged(VoiceState.INITIALIZING, "Unpacking Vosk Indian English Model…")
        StorageService.unpack(
            context,
            MODEL_NAME,
            "model",
            { loadedModel: Model ->
                try {
                    model = loadedModel
                    recognizer = Recognizer(loadedModel, SAMPLE_RATE)
                    Log.d(TAG, "Vosk model successfully loaded via StorageService.")
                    mainHandler.post {
                        onStateChanged(VoiceState.STANDBY, "Engine Ready. Say 'Hey Nexus' or 'Hi Acces'")
                    }
                } catch (e: Exception) {
                    Log.e(TAG, "Failed to initialize Vosk recognizer, trying internal fallback", e)
                    initModelInternalFallback()
                }
            },
            { exception: IOException ->
                Log.w(TAG, "StorageService unpack failed, trying internal fallback: ${exception.localizedMessage}")
                initModelInternalFallback()
            }
        )
    }

    private fun initModelInternalFallback() {
        Thread {
            try {
                val targetDir = File(context.filesDir, MODEL_NAME)
                val acousticModel = File(targetDir, "am/final.mdl")
                if (!acousticModel.exists()) {
                    targetDir.mkdirs()
                    copyAssetFolder(context.assets, MODEL_NAME, targetDir)
                }
                val loadedModel = Model(targetDir.absolutePath)
                model = loadedModel
                recognizer = Recognizer(loadedModel, SAMPLE_RATE)
                Log.d(TAG, "Vosk model successfully loaded via internal fallback.")
                mainHandler.post {
                    onStateChanged(VoiceState.STANDBY, "Engine Ready. Say 'Hey Nexus' or 'Hi Acces'")
                }
            } catch (e: Exception) {
                Log.e(TAG, "Both StorageService and internal fallback failed", e)
                mainHandler.post {
                    onStateChanged(VoiceState.ERROR, "Model unpack failed: ${e.localizedMessage}")
                }
            }
        }.start()
    }

    private fun copyAssetFolder(assetManager: AssetManager, sourcePath: String, targetDir: File) {
        val files = assetManager.list(sourcePath) ?: return
        if (!targetDir.exists()) targetDir.mkdirs()

        for (file in files) {
            val sourceChild = if (sourcePath.isEmpty()) file else "$sourcePath/$file"
            val targetChild = File(targetDir, file)
            val subFiles = assetManager.list(sourceChild)
            if (!subFiles.isNullOrEmpty()) {
                copyAssetFolder(assetManager, sourceChild, targetChild)
            } else {
                assetManager.open(sourceChild).use { input ->
                    targetChild.outputStream().use { output ->
                        input.copyTo(output)
                    }
                }
            }
        }
    }

    @Synchronized
    fun startListening() {
        if (recognizer == null) {
            initModel()
            return
        }

        if (isMicActive) return

        try {
            val sampleRateInt = SAMPLE_RATE.toInt()
            val minBufSize = AudioRecord.getMinBufferSize(
                sampleRateInt,
                AudioFormat.CHANNEL_IN_MONO,
                AudioFormat.ENCODING_PCM_16BIT
            )
            val chunkShorts = 1600 // 100ms chunks at 16kHz for responsive 10Hz-30Hz volume updates
            val recordBufferSize = maxOf(minBufSize, chunkShorts * 2 * 2)

            audioRecord = AudioRecord(
                MediaRecorder.AudioSource.VOICE_RECOGNITION,
                sampleRateInt,
                AudioFormat.CHANNEL_IN_MONO,
                AudioFormat.ENCODING_PCM_16BIT,
                recordBufferSize
            )

            if (audioRecord?.state != AudioRecord.STATE_INITIALIZED) {
                audioRecord?.release()
                audioRecord = null
                onStateChanged(VoiceState.ERROR, "Microphone initialization failed.")
                return
            }

            audioRecord?.startRecording()
            isMicActive = true
            isArmed = false
            onStateChanged(VoiceState.STANDBY, "Listening for 'Hey Nexus' / 'Hi Acces'…")

            audioThread = Thread({
                val buffer = ShortArray(chunkShorts)
                var smoothedLevel = 0f

                while (isMicActive && !Thread.currentThread().isInterrupted) {
                    val nread = audioRecord?.read(buffer, 0, buffer.size) ?: -1
                    if (nread > 0) {
                        // 1. Sound level (RMS) calculation
                        var sum = 0.0
                        for (i in 0 until nread) {
                            val sample = buffer[i].toDouble()
                            sum += sample * sample
                        }
                        val rms = sqrt(sum / nread).toFloat()
                        // Conversational speech amplitude typically ranges from 150 to 2500 RMS
                        val rawNormalized = ((rms - 120f) / 1800f).coerceIn(0f, 1f)
                        smoothedLevel = smoothedLevel * 0.35f + rawNormalized * 0.65f
                        mainHandler.post { onAudioLevel(smoothedLevel) }

                        // 2. Feed into Vosk Recognizer
                        val rec = recognizer ?: break
                        if (rec.acceptWaveForm(buffer, nread)) {
                            val resultJson = rec.result
                            mainHandler.post { handleResult(resultJson) }
                        } else {
                            val partialJson = rec.partialResult
                            mainHandler.post { handlePartialResult(partialJson) }
                        }
                    } else if (nread < 0) {
                        break
                    }
                }

                mainHandler.post { onAudioLevel(0f) }
            }, "NexusAudioRecordThread").apply {
                priority = Thread.MAX_PRIORITY
                start()
            }

            Log.d(TAG, "Audio recording and recognition thread started.")
        } catch (e: Exception) {
            Log.e(TAG, "Failed to start audio recording", e)
            isMicActive = false
            onStateChanged(VoiceState.ERROR, "Mic start failed: ${e.localizedMessage}")
        }
    }

    @Synchronized
    fun stopListening() {
        isMicActive = false
        isArmed = false
        cancelSilenceTimer()

        try {
            audioThread?.interrupt()
            audioThread = null
            audioRecord?.stop()
            audioRecord?.release()
            audioRecord = null
        } catch (e: Exception) {
            Log.w(TAG, "Error stopping audioRecord", e)
        }

        mainHandler.post {
            onAudioLevel(0f)
            onStateChanged(VoiceState.STANDBY, "Microphone paused.")
        }
    }

    private fun startSilenceTimer() {
        cancelSilenceTimer()
        silenceRunnable = Runnable {
            if (isArmed) {
                isArmed = false
                onStateChanged(VoiceState.STANDBY, "Standby. Say 'Hey Nexus' or 'Hi Acces'")
                onPartialTranscript("")
            }
        }
        mainHandler.postDelayed(silenceRunnable!!, WAKE_SILENCE_TIMEOUT_MS)
    }

    private fun cancelSilenceTimer() {
        silenceRunnable?.let { mainHandler.removeCallbacks(it) }
        silenceRunnable = null
    }

    private fun handlePartialResult(hypothesis: String?) {
        val partial = parseText(hypothesis, "partial")
        if (partial.isBlank()) return

        onRawTranscript(partial)

        if (!isArmed) {
            val wake = WakeWordDetector.detect(partial)
            if (wake.isDetected) {
                isArmed = true
                startSilenceTimer()
                onStateChanged(VoiceState.LISTENING, "Listening to you…")
                if (wake.trailingCommand.isNotBlank()) {
                    onPartialTranscript(wake.trailingCommand)
                } else {
                    onPartialTranscript("Listening…")
                }
            }
        } else {
            startSilenceTimer()
            val clean = WakeWordDetector.stripWakeWord(partial)
            onPartialTranscript(clean)
        }
    }

    private fun handleResult(hypothesis: String?) {
        val text = parseText(hypothesis, "text")
        if (text.isBlank()) return

        onRawTranscript(text)

        if (isArmed) {
            cancelSilenceTimer()
            isArmed = false
            val clean = WakeWordDetector.stripWakeWord(text)
            if (clean.length >= 2) {
                onFinalTranscript(clean)
            }
            onPartialTranscript("")
            onStateChanged(VoiceState.STANDBY, "Standby. Say 'Hey Nexus' or 'Hi Acces'")
        } else {
            val wake = WakeWordDetector.detect(text)
            if (wake.isDetected) {
                if (wake.trailingCommand.isNotBlank()) {
                    onFinalTranscript(wake.trailingCommand)
                    onPartialTranscript("")
                    onStateChanged(VoiceState.STANDBY, "Standby. Say 'Hey Nexus' or 'Hi Acces'")
                } else {
                    isArmed = true
                    startSilenceTimer()
                    onStateChanged(VoiceState.LISTENING, "Listening to you…")
                    onPartialTranscript("Listening…")
                }
            }
        }
    }

    fun release() {
        stopListening()
        recognizer?.close()
        recognizer = null
    }

    private fun parseText(jsonString: String?, key: String): String {
        if (jsonString.isNullOrBlank()) return ""
        return try {
            JSONObject(jsonString).optString(key, "").trim()
        } catch (e: Exception) {
            ""
        }
    }
}
