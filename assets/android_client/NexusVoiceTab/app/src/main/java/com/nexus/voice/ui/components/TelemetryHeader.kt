package com.nexus.voice.ui.components

import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.nexus.voice.state.VoiceState
import com.nexus.voice.ui.theme.AccentGreen
import com.nexus.voice.ui.theme.CardBorder
import com.nexus.voice.ui.theme.ElectricMagenta
import com.nexus.voice.ui.theme.NeonCyan
import com.nexus.voice.ui.theme.SurfaceDark
import com.nexus.voice.ui.theme.TextPrimary
import com.nexus.voice.ui.theme.TextSecondary

@Composable
fun TelemetryHeader(
    voiceState: VoiceState,
    statusMessage: String,
    modifier: Modifier = Modifier
) {
    Row(
        modifier = modifier
            .fillMaxWidth()
            .padding(horizontal = 20.dp, vertical = 14.dp),
        horizontalArrangement = Arrangement.SpaceBetween,
        verticalAlignment = Alignment.CenterVertically
    ) {
        // Left: Branding & Status Dot
        Row(verticalAlignment = Alignment.CenterVertically) {
            Box(
                modifier = Modifier
                    .size(8.dp)
                    .clip(CircleShape)
                    .background(
                        when (voiceState) {
                            VoiceState.LISTENING, VoiceState.WAKE_DETECTED -> NeonCyan
                            VoiceState.ERROR -> ElectricMagenta
                            VoiceState.STANDBY -> AccentGreen
                            VoiceState.INITIALIZING -> Color(0xFFFFB300)
                        }
                    )
            )
            Spacer(modifier = Modifier.width(10.dp))
            Text(
                text = "NEXUS VOICE // v2.4",
                fontSize = 13.sp,
                fontWeight = FontWeight.Bold,
                fontFamily = FontFamily.Monospace,
                color = TextPrimary
            )
        }

        // Center: Live Status Subtext
        Text(
            text = statusMessage,
            fontSize = 12.sp,
            fontFamily = FontFamily.Monospace,
            color = TextSecondary
        )

        // Right: Badges
        Row(
            verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.spacedBy(8.dp)
        ) {
            Badge(text = "OFFLINE VOSK [EN-IN 0.4]", color = CardBorder, textColor = TextSecondary)
            Badge(
                text = when (voiceState) {
                    VoiceState.INITIALIZING -> "INITIALIZING"
                    VoiceState.STANDBY -> "STANDBY"
                    VoiceState.WAKE_DETECTED -> "WAKE DETECTED"
                    VoiceState.LISTENING -> "LISTENING"
                    VoiceState.ERROR -> "ERROR"
                },
                color = when (voiceState) {
                    VoiceState.LISTENING, VoiceState.WAKE_DETECTED -> NeonCyan.copy(alpha = 0.2f)
                    VoiceState.ERROR -> ElectricMagenta.copy(alpha = 0.2f)
                    else -> CardBorder
                },
                textColor = when (voiceState) {
                    VoiceState.LISTENING, VoiceState.WAKE_DETECTED -> NeonCyan
                    VoiceState.ERROR -> ElectricMagenta
                    else -> TextSecondary
                }
            )
        }
    }
}

@Composable
private fun Badge(text: String, color: Color, textColor: Color) {
    Box(
        modifier = Modifier
            .clip(RoundedCornerShape(4.dp))
            .background(color)
            .border(1.dp, CardBorder, RoundedCornerShape(4.dp))
            .padding(horizontal = 8.dp, vertical = 4.dp)
    ) {
        Text(
            text = text,
            fontSize = 10.sp,
            fontWeight = FontWeight.SemiBold,
            fontFamily = FontFamily.Monospace,
            color = textColor
        )
    }
}
