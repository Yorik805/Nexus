package com.nexus.voice.ui

import androidx.compose.animation.*
import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.nexus.voice.model.EventCategory
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
        Column(modifier = Modifier.fillMaxSize()) {
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

            // 2. Main Horizontal Body (Left: Next-Gen Voice Console, Right: Full Height Event/Debug Stream)
            Row(
                modifier = Modifier
                    .fillMaxWidth()
                    .weight(1f)
                    .padding(start = 16.dp, end = 16.dp, bottom = 10.dp),
                horizontalArrangement = Arrangement.spacedBy(16.dp)
            ) {
                // LEFT STAGE: Voice Interface & Holographic Core
                Column(
                    modifier = Modifier
                        .fillMaxHeight()
                        .weight(if (state.isZenMode) 1f else 0.58f),
                    verticalArrangement = Arrangement.SpaceBetween,
                    horizontalAlignment = Alignment.CenterHorizontally
                ) {
                    // Center Visualizer + Waveform + Fading Dialogue
                    Column(
                        modifier = Modifier
                            .fillMaxWidth()
                            .weight(1f),
                        horizontalAlignment = Alignment.CenterHorizontally,
                        verticalArrangement = Arrangement.Center
                    ) {
                        // Next-Level Holographic Radial Spectrum Visualizer
                        HologramVisualizer(
                            voiceState = state.voiceState,
                            audioLevel = state.audioLevel,
                            size = if (state.isZenMode) 260.dp else 195.dp
                        )

                        Spacer(modifier = Modifier.height(14.dp))

                        // Live Equalizer Sound Waveform Bar (like web console)
                        WaveformBar(
                            audioLevel = state.audioLevel,
                            voiceState = state.voiceState,
                            bars = 32,
                            maxHeight = 32.dp
                        )

                        Spacer(modifier = Modifier.height(16.dp))

                        // Floating 3-tier Fading Transcript (1.0 -> 0.6 -> 0.3 opacity, no box)
                        FadingTranscript(
                            currentPartial = state.currentPartial,
                            history = state.transcriptHistory
                        )
                    }

                    // Bottom Bar in Left Stage: Background Tasks Pill + Wake Hint + Mic Button
                    Row(
                        modifier = Modifier
                            .fillMaxWidth()
                            .padding(vertical = 4.dp),
                        horizontalArrangement = Arrangement.SpaceBetween,
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        // Background Tasks Compact Indicator Pill
                        Surface(
                            shape = RoundedCornerShape(6.dp),
                            color = SurfaceDark,
                            border = BorderStroke(1.dp, CardBorder)
                        ) {
                            Row(
                                modifier = Modifier.padding(horizontal = 10.dp, vertical = 6.dp),
                                verticalAlignment = Alignment.CenterVertically
                            ) {
                                Text(
                                    text = "BACKGROUND TASKS:",
                                    fontSize = 9.sp,
                                    fontFamily = FontFamily.Monospace,
                                    fontWeight = FontWeight.Bold,
                                    color = CatPlugin
                                )
                                Spacer(modifier = Modifier.width(6.dp))
                                Text(
                                    text = if (state.backgroundTasks.isEmpty()) "0 ACTIVE (STANDBY)" else "${state.backgroundTasks.size} RUNNING",
                                    fontSize = 9.sp,
                                    fontFamily = FontFamily.Monospace,
                                    color = TextSecondary
                                )
                            }
                        }

                        // Wake Word Quick Reference
                        Text(
                            text = "\"HEY NEXUS\" • \"HI ACCES\"",
                            fontSize = 10.sp,
                            fontFamily = FontFamily.Monospace,
                            fontWeight = FontWeight.SemiBold,
                            color = TextSecondary.copy(alpha = 0.5f)
                        )

                        // Start / Pause Mic Button
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

                // RIGHT STAGE: Full-Height Nexus Event Monitor & Debug Stream (matching web console layout)
                AnimatedVisibility(
                    visible = !state.isZenMode,
                    enter = fadeIn() + expandHorizontally(),
                    exit = fadeOut() + shrinkHorizontally(),
                    modifier = Modifier
                        .fillMaxHeight()
                        .weight(0.42f)
                ) {
                    EventMonitorPanel(
                        events = state.events,
                        rawTranscript = state.rawTranscript,
                        isDebugMode = state.isDebugMode,
                        selectedCategory = state.selectedCategoryFilter,
                        autoScroll = state.autoScrollEvents,
                        onToggleAutoScroll = onToggleAutoScroll,
                        onSelectCategory = onSelectCategory,
                        modifier = Modifier.fillMaxSize()
                    )
                }
            }
        }

        // Settings Dialog Modal
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
