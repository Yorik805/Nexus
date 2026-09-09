package com.nexus.voice.ui

import androidx.compose.animation.*
import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.remember
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.nexus.voice.engine.WakeWordDetector
import com.nexus.voice.model.EventCategory
import com.nexus.voice.state.VoiceState
import com.nexus.voice.state.VoiceUiState
import com.nexus.voice.ui.components.*
import com.nexus.voice.ui.theme.*

@Composable
fun VoiceScreen(
    state: VoiceUiState,
    onToggleMic: () -> Unit,
    onToggleZenMode: () -> Unit,
    onToggleDebugMode: () -> Unit,
    onOpenSettings: () -> Unit,
    onDismissSettings: () -> Unit,
    onSaveServerIp: (String) -> Unit,
    onTestPing: suspend (String, Int) -> Pair<Boolean, Long>,
    onToggleAutoScroll: () -> Unit,
    onSelectCategory: (EventCategory?) -> Unit,
    modifier: Modifier = Modifier
) {
    Box(
        modifier = modifier
            .fillMaxSize()
            .background(BackgroundDark)
    ) {
        Column(
            modifier = Modifier.fillMaxSize(),
            verticalArrangement = Arrangement.SpaceBetween
        ) {
            // 1. Top Telemetry Header
            TelemetryHeader(
                voiceState = state.voiceState,
                statusMessage = state.statusMessage,
                serverIp = state.serverIp,
                isServerConnected = state.isServerConnected,
                serverLatencyMs = state.serverLatencyMs,
                isZenMode = state.isZenMode,
                isDebugMode = state.isDebugMode,
                onToggleZenMode = onToggleZenMode,
                onToggleDebugMode = onToggleDebugMode,
                onOpenSettings = onOpenSettings
            )

            // 2. Center Stage (Sound-Reactive Hologram Visualizer + Fading Typography)
            Column(
                modifier = Modifier
                    .fillMaxWidth()
                    .weight(if (state.isZenMode) 1f else 0.58f),
                horizontalAlignment = Alignment.CenterHorizontally,
                verticalArrangement = Arrangement.Center
            ) {
                HologramVisualizer(
                    voiceState = state.voiceState,
                    audioLevel = state.audioLevel,
                    size = if (state.isZenMode) 230.dp else 155.dp
                )

                Spacer(modifier = Modifier.height(if (state.isZenMode) 24.dp else 12.dp))

                // Fading 3-tier transcript floating directly below visualizer
                FadingTranscript(
                    currentPartial = state.currentPartial,
                    history = state.transcriptHistory
                )

                // Live Raw STT Pill (shown in HUD mode when not in debug view)
                if (!state.isZenMode && !state.isDebugMode) {
                    Spacer(modifier = Modifier.height(10.dp))
                    RawSttDebugCard(
                        rawTranscript = state.rawTranscript,
                        isMicActive = state.isMicActive
                    )
                }
            }

            // 3. Bottom Dual Sections (Console / HUD Mode Only)
            AnimatedVisibility(
                visible = !state.isZenMode,
                enter = fadeIn() + expandVertically(),
                exit = fadeOut() + shrinkVertically()
            ) {
                Row(
                    modifier = Modifier
                        .fillMaxWidth()
                        .height(215.dp)
                        .padding(horizontal = 16.dp, vertical = 4.dp),
                    horizontalArrangement = Arrangement.spacedBy(12.dp)
                ) {
                    // Left Section: Background Tasks & Timers
                    BackgroundTasksPanel(
                        tasks = state.backgroundTasks,
                        modifier = Modifier.weight(0.38f)
                    )

                    // Right Section: Nexus Events & Debug Stream
                    EventMonitorPanel(
                        events = state.events,
                        rawTranscript = state.rawTranscript,
                        isDebugMode = state.isDebugMode,
                        selectedCategory = state.selectedCategoryFilter,
                        autoScroll = state.autoScrollEvents,
                        onToggleAutoScroll = onToggleAutoScroll,
                        onSelectCategory = onSelectCategory,
                        modifier = Modifier.weight(0.62f)
                    )
                }
            }

            // 4. Bottom Controls & Hint Bar
            Row(
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(horizontal = 20.dp, vertical = if (state.isZenMode) 16.dp else 8.dp),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically
            ) {
                Text(
                    text = "WAKE WORDS: \"HEY NEXUS\" • \"HI ACCES\" • \"NEXUS\" • \"ACCES\"",
                    fontSize = 10.sp,
                    fontFamily = FontFamily.Monospace,
                    fontWeight = FontWeight.Medium,
                    color = TextSecondary.copy(alpha = 0.6f)
                )

                Button(
                    onClick = onToggleMic,
                    colors = ButtonDefaults.buttonColors(
                        containerColor = if (state.isMicActive) SurfaceDark else NeonCyan,
                        contentColor = if (state.isMicActive) TextPrimary else BackgroundDark
                    ),
                    border = BorderStroke(1.dp, if (state.isMicActive) CardBorder else NeonCyan)
                ) {
                    Text(
                        text = if (state.isMicActive) "PAUSE MIC" else "START MIC",
                        fontSize = 11.sp,
                        fontFamily = FontFamily.Monospace,
                        fontWeight = FontWeight.Bold
                    )
                }
            }
        }

        // Settings Dialog
        if (state.showSettingsDialog) {
            SettingsDialog(
                currentIp = state.serverIp,
                dashboardPort = 11882,
                runtimePort = 8765,
                onTestPing = onTestPing,
                onSave = onSaveServerIp,
                onDismiss = onDismissSettings
            )
        }
    }
}

@Composable
private fun RawSttDebugCard(
    rawTranscript: String,
    isMicActive: Boolean,
    modifier: Modifier = Modifier
) {
    val wakeResult = remember(rawTranscript) {
        if (rawTranscript.isNotBlank()) WakeWordDetector.detect(rawTranscript) else null
    }
    val hasWakeWord = wakeResult?.isDetected == true

    Surface(
        modifier = modifier
            .fillMaxWidth(0.75f)
            .padding(horizontal = 8.dp),
        shape = RoundedCornerShape(10.dp),
        color = SurfaceDark.copy(alpha = 0.85f),
        border = BorderStroke(
            1.dp,
            if (hasWakeWord) ElectricMagenta.copy(alpha = 0.8f) else CardBorder
        )
    ) {
        Row(
            modifier = Modifier.padding(horizontal = 12.dp, vertical = 6.dp),
            verticalAlignment = Alignment.CenterVertically
        ) {
            Surface(
                shape = RoundedCornerShape(4.dp),
                color = if (hasWakeWord) ElectricMagenta.copy(alpha = 0.2f)
                else if (isMicActive) NeonCyan.copy(alpha = 0.15f)
                else CardBorder
            ) {
                Row(
                    modifier = Modifier.padding(horizontal = 6.dp, vertical = 3.dp),
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Box(
                        modifier = Modifier
                            .size(5.dp)
                            .background(
                                color = if (hasWakeWord) ElectricMagenta
                                else if (isMicActive) AccentGreen
                                else Color.Gray,
                                shape = CircleShape
                            )
                    )
                    Spacer(modifier = Modifier.width(5.dp))
                    Text(
                        text = if (hasWakeWord) "WAKE DETECTED" else "RAW STT",
                        fontSize = 9.sp,
                        fontFamily = FontFamily.Monospace,
                        fontWeight = FontWeight.Bold,
                        color = if (hasWakeWord) ElectricMagenta
                        else if (isMicActive) NeonCyan
                        else TextSecondary
                    )
                }
            }

            Spacer(modifier = Modifier.width(10.dp))

            Text(
                text = if (rawTranscript.isNotBlank()) rawTranscript else "Awaiting speech input… (speak to test local Vosk engine)",
                fontSize = 11.sp,
                fontFamily = FontFamily.Monospace,
                fontWeight = FontWeight.Medium,
                color = if (rawTranscript.isNotBlank()) TextPrimary else TextSecondary.copy(alpha = 0.5f),
                maxLines = 1,
                overflow = TextOverflow.Ellipsis,
                modifier = Modifier.weight(1f)
            )
        }
    }
}
