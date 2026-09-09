package com.nexus.voice.state

import com.nexus.voice.model.BackgroundTaskItem
import com.nexus.voice.model.EventCategory
import com.nexus.voice.model.NexusEvent

enum class VoiceState {
    INITIALIZING,
    STANDBY,
    WAKE_DETECTED,
    LISTENING,
    ERROR
}

data class VoiceUiState(
    val voiceState: VoiceState = VoiceState.INITIALIZING,
    val currentPartial: String = "",
    val rawTranscript: String = "",
    val transcriptHistory: List<String> = emptyList(),
    val statusMessage: String = "Initializing Vosk Engine…",
    val isMicActive: Boolean = false,
    val audioLevel: Float = 0f, // 0.0f to 1.0f sound reactive amplitude

    // Server & Networking
    val serverIp: String = "192.168.1.100",
    val isServerConnected: Boolean = false,
    val serverLatencyMs: Long = 0L,

    // Modes & Display
    val isZenMode: Boolean = false,
    val isDebugMode: Boolean = false,
    val showSettingsDialog: Boolean = false,

    // Events & Filtering
    val events: List<NexusEvent> = emptyList(),
    val selectedCategoryFilter: EventCategory? = null, // null = ALL
    val autoScrollEvents: Boolean = true,

    // Background Tasks / Timers
    val backgroundTasks: List<BackgroundTaskItem> = emptyList()
)
