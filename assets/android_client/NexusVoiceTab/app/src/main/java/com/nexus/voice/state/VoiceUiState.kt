package com.nexus.voice.state

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
    val isMicActive: Boolean = false
)
