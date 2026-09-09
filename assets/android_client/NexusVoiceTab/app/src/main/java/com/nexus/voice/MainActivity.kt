package com.nexus.voice

import android.Manifest
import android.content.pm.PackageManager
import android.os.Bundle
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

class MainActivity : ComponentActivity() {

    private lateinit var speechManager: VoskSpeechManager
    private lateinit var prefs: NexusPreferences
    private val apiClient = NexusApiClient()

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

        speechManager = VoskSpeechManager(
            context = this,
            onStateChanged = { state, msg ->
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
                val updatedHistory = listOf(finalPhrase) + uiState.transcriptHistory
                uiState = uiState.copy(
                    currentPartial = "",
                    transcriptHistory = updatedHistory.take(5)
                )
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
        speechManager.release()
        apiClient.release()
    }
}
