package com.nexus.voice.ui

import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
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
import com.nexus.voice.state.VoiceState
import com.nexus.voice.state.VoiceUiState
import com.nexus.voice.ui.components.FadingTranscript
import com.nexus.voice.ui.components.HologramVisualizer
import com.nexus.voice.ui.components.TelemetryHeader
import com.nexus.voice.ui.theme.AccentGreen
import com.nexus.voice.ui.theme.BackgroundDark
import com.nexus.voice.ui.theme.CardBorder
import com.nexus.voice.ui.theme.ElectricMagenta
import com.nexus.voice.ui.theme.NeonCyan
import com.nexus.voice.ui.theme.SurfaceDark
import com.nexus.voice.ui.theme.TextPrimary
import com.nexus.voice.ui.theme.TextSecondary

@Composable
fun VoiceScreen(
    state: VoiceUiState,
    onToggleMic: () -> Unit,
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
                statusMessage = state.statusMessage
            )

            // 2. Center Stage (Hologram Visualizer + Fading Typography + Live Raw STT)
            Column(
                modifier = Modifier
                    .fillMaxWidth()
                    .weight(1f),
                horizontalAlignment = Alignment.CenterHorizontally,
                verticalArrangement = Arrangement.Center
            ) {
                HologramVisualizer(
                    voiceState = state.voiceState,
                    size = 170.dp
                )

                Spacer(modifier = Modifier.height(20.dp))

                // Fading 3-tier transcript floating directly below the visualizer
                FadingTranscript(
                    currentPartial = state.currentPartial,
                    history = state.transcriptHistory
                )

                Spacer(modifier = Modifier.height(22.dp))

                // Live Raw STT Debug Section
                RawSttDebugCard(
                    rawTranscript = state.rawTranscript,
                    isMicActive = state.isMicActive
                )
            }

            // 3. Bottom Minimal Controls & Hint
            Row(
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(horizontal = 24.dp, vertical = 16.dp),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically
            ) {
                Text(
                    text = "WAKE WORDS: \"HEY NEXUS\" • \"HI ACCES\" • \"NEXUS\" • \"ACCES\"",
                    fontSize = 11.sp,
                    fontFamily = FontFamily.Monospace,
                    fontWeight = FontWeight.Medium,
                    color = TextSecondary.copy(alpha = 0.6f)
                )

                Button(
                    onClick = onToggleMic,
                    colors = ButtonDefaults.buttonColors(
                        containerColor = if (state.isMicActive) SurfaceDark else NeonCyan,
                        contentColor = if (state.isMicActive) TextPrimary else BackgroundDark
                    )
                ) {
                    Text(
                        text = if (state.isMicActive) "PAUSE MIC" else "START MIC",
                        fontSize = 12.sp,
                        fontFamily = FontFamily.Monospace,
                        fontWeight = FontWeight.Bold
                    )
                }
            }
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
            .fillMaxWidth(0.85f)
            .padding(horizontal = 16.dp),
        shape = RoundedCornerShape(12.dp),
        color = SurfaceDark.copy(alpha = 0.85f),
        border = BorderStroke(
            1.dp,
            if (hasWakeWord) ElectricMagenta.copy(alpha = 0.8f) else CardBorder
        )
    ) {
        Row(
            modifier = Modifier.padding(horizontal = 16.dp, vertical = 10.dp),
            verticalAlignment = Alignment.CenterVertically
        ) {
            // High-tech terminal tag
            Surface(
                shape = RoundedCornerShape(6.dp),
                color = if (hasWakeWord) ElectricMagenta.copy(alpha = 0.2f)
                else if (isMicActive) NeonCyan.copy(alpha = 0.15f)
                else CardBorder
            ) {
                Row(
                    modifier = Modifier.padding(horizontal = 8.dp, vertical = 4.dp),
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Box(
                        modifier = Modifier
                            .size(6.dp)
                            .background(
                                color = if (hasWakeWord) ElectricMagenta
                                else if (isMicActive) AccentGreen
                                else Color.Gray,
                                shape = CircleShape
                            )
                    )
                    Spacer(modifier = Modifier.width(6.dp))
                    Text(
                        text = if (hasWakeWord) "WAKE DETECTED" else "RAW STT",
                        fontSize = 11.sp,
                        fontFamily = FontFamily.Monospace,
                        fontWeight = FontWeight.Bold,
                        color = if (hasWakeWord) ElectricMagenta
                        else if (isMicActive) NeonCyan
                        else TextSecondary
                    )
                }
            }

            Spacer(modifier = Modifier.width(12.dp))

            // The live raw stream
            Text(
                text = if (rawTranscript.isNotBlank()) rawTranscript else "Awaiting speech input… (speak to test local Vosk engine)",
                fontSize = 13.sp,
                fontFamily = FontFamily.Monospace,
                fontWeight = FontWeight.Medium,
                color = if (rawTranscript.isNotBlank()) TextPrimary else TextSecondary.copy(alpha = 0.5f),
                maxLines = 2,
                overflow = TextOverflow.Ellipsis,
                modifier = Modifier.weight(1f)
            )
        }
    }
}
