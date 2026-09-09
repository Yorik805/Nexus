package com.nexus.voice.ui

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
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.nexus.voice.state.VoiceState
import com.nexus.voice.state.VoiceUiState
import com.nexus.voice.ui.components.FadingTranscript
import com.nexus.voice.ui.components.HologramVisualizer
import com.nexus.voice.ui.components.TelemetryHeader
import com.nexus.voice.ui.theme.BackgroundDark
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

            // 2. Center Stage (Hologram Visualizer + Fading Typography)
            Column(
                modifier = Modifier
                    .fillMaxWidth()
                    .weight(1f),
                horizontalAlignment = Alignment.CenterHorizontally,
                verticalArrangement = Arrangement.Center
            ) {
                HologramVisualizer(
                    voiceState = state.voiceState,
                    size = 180.dp
                )

                Spacer(modifier = Modifier.height(28.dp))

                // Fading 3-tier transcript floating directly below the visualizer
                FadingTranscript(
                    currentPartial = state.currentPartial,
                    history = state.transcriptHistory
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
