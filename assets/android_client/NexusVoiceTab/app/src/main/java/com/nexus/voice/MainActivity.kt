package com.nexus.voice

import android.Manifest
import android.content.pm.PackageManager
import android.os.Bundle
import android.speech.tts.TextToSpeech
import android.util.Log
import android.view.WindowManager
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.setValue
import androidx.core.content.ContextCompat
import com.nexus.voice.config.NexusPreferences
import com.nexus.voice.engine.VoskSpeechManager
import com.nexus.voice.network.NexusApiClient
import com.nexus.voice.state.VoiceState
import com.nexus.voice.state.VoiceUiState
import com.nexus.voice.ui.VoiceScreen
import com.nexus.voice.ui.theme.NexusVoiceTheme
import kotlinx.coroutines.*
import java.util.Locale

class MainActivity : ComponentActivity() {

    private val TAG = "MainActivity"

    private lateinit var speechManager: VoskSpeechManager
    private lateinit var prefs: NexusPreferences
    private val apiClient = NexusApiClient()

    private var tts: TextToSpeech? = null
    private val activityScope = CoroutineScope(Dispatchers.Main + SupervisorJob())
    private var inFlightMessageJob: Job? = null
    private var pendingRequestText: String? = null
    private var currentRequestId: Long = 0L

    private var uiState by mutableStateOf(VoiceUiState())

    private val permissionLauncher =
        registerForActivityResult(ActivityResultContracts.RequestPermission()) { granted ->
            if (granted) {
                speechManager.initModel()
                speechManager.startListening()
            } else {
                uiState = uiState.copy(
                    voiceState = VoiceState.ERROR,
                    statusMessage = "Microphone permission denied. Grant permission in Settings."
                )
            }
        }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)

        // Always keep the tablet display on while plugged in / running
        window.addFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON)

        prefs = NexusPreferences(this)
        uiState = uiState.copy(
            serverIp = prefs.serverIp,
            isZenMode = prefs.isZenMode,
            isDebugMode = prefs.isDebugMode
        )

        // Initialize Android Text-to-Speech
        initTts()

        speechManager = VoskSpeechManager(
            context = this,
            onStateChanged = { state, msg ->
                // If user triggered wake word while TTS is speaking, interrupt TTS immediately
                if (state == VoiceState.LISTENING || state == VoiceState.WAKE_DETECTED) {
                    stopTts()
                }
                uiState = uiState.copy(
                    voiceState = state,
                    statusMessage = msg,
                    isMicActive = speechManager.isMicActive
                )
            },
            onPartialTranscript = { partial ->
                uiState = uiState.copy(currentPartial = partial)
            },
            onFinalTranscript = { finalPhrase ->
                handleSpokenCommand(finalPhrase)
            },
            onRawTranscript = { raw ->
                uiState = uiState.copy(rawTranscript = raw)
            },
            onAudioLevel = { level ->
                uiState = uiState.copy(audioLevel = level)
            }
        )

        // Start polling Nexus backend
        startBackendPolling(prefs.serverIp)

        setContent {
            NexusVoiceTheme {
                VoiceScreen(
                    state = uiState,
                    onToggleMic = {
                        if (speechManager.isMicActive) {
                            speechManager.stopListening()
                        } else {
                            checkPermissionAndStart()
                        }
                    },
                    onToggleZenMode = {
                        val next = !uiState.isZenMode
                        prefs.isZenMode = next
                        uiState = uiState.copy(isZenMode = next)
                    },
                    onToggleDebugMode = {
                        val next = !uiState.isDebugMode
                        prefs.isDebugMode = next
                        uiState = uiState.copy(isDebugMode = next)
                    },
                    onOpenSettings = {
                        uiState = uiState.copy(showSettingsDialog = true)
                    },
                    onDismissSettings = {
                        uiState = uiState.copy(showSettingsDialog = false)
                    },
                    onSaveServerIp = { newIp ->
                        prefs.serverIp = newIp
                        uiState = uiState.copy(serverIp = newIp)
                        startBackendPolling(newIp)
                    },
                    onTestPing = { ip, port ->
                        apiClient.testConnection(ip, port)
                    },
                    onToggleAutoScroll = {
                        uiState = uiState.copy(autoScrollEvents = !uiState.autoScrollEvents)
                    },
                    onSelectCategory = { cat ->
                        uiState = uiState.copy(selectedCategoryFilter = cat)
                    }
                )
            }
        }

        checkPermissionAndStart()
    }

    private fun handleSpokenCommand(finalPhrase: String) {
        val clean = finalPhrase.trim()
        if (clean.isBlank()) return

        // 1. Cut off any active TTS playback immediately
        stopTts()

        // 2. Check if a previous command was still in flight waiting for response
        val wasWaiting = inFlightMessageJob?.isActive == true
        if (wasWaiting) {
            inFlightMessageJob?.cancel()
            // Flush server pending queue so stale response is purged
            apiClient.flushPending(prefs.serverIp, prefs.runtimePort)
        }

        // 3. If previous request was still pending without a reply, REMOVE it from dialogue history
        val baseHistory = if (wasWaiting && pendingRequestText != null) {
            uiState.transcriptHistory.filterNot { it == pendingRequestText }
        } else {
            uiState.transcriptHistory
        }

        pendingRequestText = clean
        val thisRequestId = System.currentTimeMillis()
        currentRequestId = thisRequestId

        // 4. Put new command into dialogue history
        val updatedHistory = listOf(clean) + baseHistory
        uiState = uiState.copy(
            currentPartial = "",
            statusMessage = "Sending to Nexus: \"$clean\"…",
            transcriptHistory = updatedHistory.take(8)
        )

        // 5. POST the message to Nexus runtime (/message)
        inFlightMessageJob = activityScope.launch {
            val result = apiClient.sendMessage(
                serverIp = prefs.serverIp,
                runtimePort = prefs.runtimePort,
                text = clean
            )

            // If a newer command arrived while waiting, ignore this response entirely
            if (currentRequestId != thisRequestId) return@launch

            result.onSuccess { replyText ->
                if (currentRequestId != thisRequestId) return@launch
                pendingRequestText = null

                if (replyText.isNotBlank()) {
                    val withReply = listOf(replyText) + uiState.transcriptHistory
                    uiState = uiState.copy(
                        statusMessage = "Nexus responded.",
                        transcriptHistory = withReply.take(8)
                    )
                    speakTts(replyText)
                } else {
                    uiState = uiState.copy(statusMessage = "Command executed by Nexus.")
                }
            }.onFailure { err ->
                if (currentRequestId != thisRequestId) return@launch
                pendingRequestText = null
                Log.w(TAG, "Failed to reach Nexus server", err)
                uiState = uiState.copy(
                    statusMessage = "Server error: ${err.localizedMessage ?: "Unreachable"}"
                )
            }
        }
    }

    private fun initTts() {
        tts = TextToSpeech(this) { status ->
            if (status == TextToSpeech.SUCCESS) {
                tts?.language = Locale.ENGLISH
                Log.d(TAG, "Android TextToSpeech initialized successfully.")
            } else {
                Log.w(TAG, "Failed to initialize Android TextToSpeech.")
            }
        }
    }

    private fun speakTts(text: String) {
        tts?.speak(text, TextToSpeech.QUEUE_FLUSH, null, "nexus_voice_reply")
    }

    private fun stopTts() {
        if (tts?.isSpeaking == true) {
            tts?.stop()
        }
    }

    private fun startBackendPolling(ip: String) {
        apiClient.startPolling(
            serverIp = ip,
            port = prefs.dashboardPort,
            intervalMs = 1500L
        ) { success, latency, events ->
            uiState = uiState.copy(
                isServerConnected = success,
                serverLatencyMs = latency,
                events = if (events.isNotEmpty()) events else uiState.events
            )
        }
    }

    private fun checkPermissionAndStart() {
        val permission = Manifest.permission.RECORD_AUDIO
        if (ContextCompat.checkSelfPermission(this, permission) == PackageManager.PERMISSION_GRANTED) {
            speechManager.startListening()
        } else {
            permissionLauncher.launch(permission)
        }
    }

    override fun onDestroy() {
        super.onDestroy()
        stopTts()
        tts?.shutdown()
        tts = null
        activityScope.cancel()
        speechManager.release()
        apiClient.release()
    }
}
