package com.nexus.voice.engine

import android.content.Context
import android.os.Handler
import android.os.Looper
import android.util.Log
import com.nexus.voice.state.VoiceState
import android.content.res.AssetManager
import java.io.File
import java.io.IOException
import org.json.JSONObject
import org.vosk.Model
import org.vosk.Recognizer
import org.vosk.android.RecognitionListener
import org.vosk.android.SpeechService
import org.vosk.android.StorageService

class VoskSpeechManager(
    private val context: Context,
    private val onStateChanged: (VoiceState, String) -> Unit,
    private val onPartialTranscript: (String) -> Unit,
    private val onFinalTranscript: (String) -> Unit
) : RecognitionListener {

    private val TAG = "VoskSpeechManager"
    private val MODEL_NAME = "vosk-model-small-en-in-0.4"
    private val SAMPLE_RATE = 16000.0f
    private val WAKE_SILENCE_TIMEOUT_MS = 5000L

    private var speechService: SpeechService? = null
    private var recognizer: Recognizer? = null
    private var isArmed = false
    private val mainHandler = Handler(Looper.getMainLooper())
    private var silenceRunnable: Runnable? = null

    var isMicActive = false
        private set

    fun initModel() {
        onStateChanged(VoiceState.INITIALIZING, "Unpacking Vosk Indian English Model…")
        StorageService.unpack(
            context,
            MODEL_NAME,
            "model",
            { model: Model ->
                try {
                    recognizer = Recognizer(model, SAMPLE_RATE)
                    speechService = SpeechService(recognizer, SAMPLE_RATE)
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
                val model = Model(targetDir.absolutePath)
                recognizer = Recognizer(model, SAMPLE_RATE)
                speechService = SpeechService(recognizer, SAMPLE_RATE)
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

    fun startListening() {
        if (speechService == null) {
            initModel()
            return
        }

        try {
            isMicActive = true
            isArmed = false
            speechService?.startListening(this)
            onStateChanged(VoiceState.STANDBY, "Listening for 'Hey Nexus' / 'Hi Acces'…")
            Log.d(TAG, "SpeechService started listening.")
        } catch (e: Exception) {
            Log.e(TAG, "Failed to start listening", e)
            onStateChanged(VoiceState.ERROR, "Mic start failed: ${e.localizedMessage}")
        }
    }

    fun stopListening() {
        isMicActive = false
        isArmed = false
        cancelSilenceTimer()
        speechService?.stop()
        onStateChanged(VoiceState.STANDBY, "Microphone paused.")
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

    override fun onPartialResult(hypothesis: String?) {
        val partial = parseText(hypothesis, "partial")
        if (partial.isBlank()) return

        if (!isArmed) {
            val wake = WakeWordDetector.detect(partial)
            if (wake.isDetected) {
                isArmed = true
                startSilenceTimer()
                mainHandler.post {
                    onStateChanged(VoiceState.LISTENING, "Listening to you…")
                    if (wake.trailingCommand.isNotBlank()) {
                        onPartialTranscript(wake.trailingCommand)
                    } else {
                        onPartialTranscript("Listening…")
                    }
                }
            }
        } else {
            startSilenceTimer()
            val clean = WakeWordDetector.stripWakeWord(partial)
            mainHandler.post {
                onPartialTranscript(clean)
            }
        }
    }

    override fun onResult(hypothesis: String?) {
        val text = parseText(hypothesis, "text")
        if (text.isBlank()) return

        if (isArmed) {
            cancelSilenceTimer()
            isArmed = false
            val clean = WakeWordDetector.stripWakeWord(text)
            mainHandler.post {
                if (clean.length >= 2) {
                    onFinalTranscript(clean)
                }
                onPartialTranscript("")
                onStateChanged(VoiceState.STANDBY, "Standby. Say 'Hey Nexus' or 'Hi Acces'")
            }
        } else {
            val wake = WakeWordDetector.detect(text)
            if (wake.isDetected) {
                if (wake.trailingCommand.isNotBlank()) {
                    mainHandler.post {
                        onFinalTranscript(wake.trailingCommand)
                        onPartialTranscript("")
                        onStateChanged(VoiceState.STANDBY, "Standby. Say 'Hey Nexus' or 'Hi Acces'")
                    }
                } else {
                    isArmed = true
                    startSilenceTimer()
                    mainHandler.post {
                        onStateChanged(VoiceState.LISTENING, "Listening to you…")
                        onPartialTranscript("Listening…")
                    }
                }
            }
        }
    }

    override fun onFinalResult(hypothesis: String?) {
        onResult(hypothesis)
    }

    override fun onError(exception: Exception?) {
        Log.e(TAG, "Vosk runtime error", exception)
        mainHandler.post {
            onStateChanged(VoiceState.ERROR, "Vosk error: ${exception?.localizedMessage}")
        }
    }

    override fun onTimeout() {
        Log.d(TAG, "Vosk session timeout, restarting listening loop.")
        if (isMicActive) {
            speechService?.stop()
            speechService?.startListening(this)
        }
    }

    fun release() {
        isMicActive = false
        cancelSilenceTimer()
        speechService?.stop()
        speechService?.shutdown()
        speechService = null
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
