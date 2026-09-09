package com.nexus.voice.ui.components

import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
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
import com.nexus.voice.ui.theme.*

@Composable
fun TelemetryHeader(
    voiceState: VoiceState,
    statusMessage: String,
    serverIp: String,
    isServerConnected: Boolean,
    serverLatencyMs: Long,
    isZenMode: Boolean,
    isDebugMode: Boolean,
    onToggleZenMode: () -> Unit,
    onToggleDebugMode: () -> Unit,
    onOpenSettings: () -> Unit,
    modifier: Modifier = Modifier
) {
    Row(
        modifier = modifier
            .fillMaxWidth()
            .padding(horizontal = 18.dp, vertical = 10.dp),
        horizontalArrangement = Arrangement.SpaceBetween,
        verticalAlignment = Alignment.CenterVertically
    ) {
        // Left: Branding, Ping dot, & Server IP link
        Row(verticalAlignment = Alignment.CenterVertically) {
            Box(
                modifier = Modifier
                    .size(8.dp)
                    .clip(CircleShape)
                    .background(
                        when {
                            voiceState == VoiceState.LISTENING || voiceState == VoiceState.WAKE_DETECTED -> NeonCyan
                            voiceState == VoiceState.ERROR -> ElectricMagenta
                            isServerConnected -> AccentGreen
                            else -> Color(0xFFFFB300)
                        }
                    )
            )
            Spacer(modifier = Modifier.width(8.dp))
            Text(
                text = "NEXUS VOICE",
                fontSize = 13.sp,
                fontWeight = FontWeight.Bold,
                fontFamily = FontFamily.Monospace,
                color = TextPrimary
            )

            Spacer(modifier = Modifier.width(10.dp))

            // Server connection indicator / button
            Box(
                modifier = Modifier
                    .clip(RoundedCornerShape(4.dp))
                    .background(if (isServerConnected) AccentGreen.copy(alpha = 0.12f) else CardBorder.copy(alpha = 0.6f))
                    .border(1.dp, if (isServerConnected) AccentGreen.copy(alpha = 0.4f) else CardBorder, RoundedCornerShape(4.dp))
                    .clickable { onOpenSettings() }
                    .padding(horizontal = 7.dp, vertical = 3.dp)
            ) {
                Row(verticalAlignment = Alignment.CenterVertically) {
                    Text(
                        text = if (isServerConnected) "$serverIp (${serverLatencyMs}ms)" else if (serverIp.isNotBlank()) "$serverIp [OFFLINE]" else "SERVER [UNSET]",
                        fontSize = 9.sp,
                        fontFamily = FontFamily.Monospace,
                        fontWeight = FontWeight.SemiBold,
                        color = if (isServerConnected) AccentGreen else TextSecondary
                    )
                }
            }
        }

        // Center: Status Subtext (hidden in Zen mode if screen is compact)
        if (!isZenMode) {
            Text(
                text = statusMessage,
                fontSize = 11.sp,
                fontFamily = FontFamily.Monospace,
                color = TextSecondary.copy(alpha = 0.8f)
            )
        }

        // Right: Mode Switches & Badges
        Row(
            verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.spacedBy(6.dp)
        ) {
            // Zen Mode Toggle Button
            ModeToggleButton(
                label = if (isZenMode) "ZEN MODE [ON]" else "ZEN MODE",
                isActive = isZenMode,
                activeColor = NeonCyan,
                onClick = onToggleZenMode
            )

            // Debug Mode Toggle Button (visible in console mode)
            if (!isZenMode) {
                ModeToggleButton(
                    label = if (isDebugMode) "DEBUG [ON]" else "DEBUG",
                    isActive = isDebugMode,
                    activeColor = CatValidator,
                    onClick = onToggleDebugMode
                )
            }

            // Settings Button
            Box(
                modifier = Modifier
                    .clip(RoundedCornerShape(4.dp))
                    .background(CardBorder)
                    .border(1.dp, CardBorder, RoundedCornerShape(4.dp))
                    .clickable { onOpenSettings() }
                    .padding(horizontal = 8.dp, vertical = 4.dp)
            ) {
                Text(
                    text = "⚙ CONFIG",
                    fontSize = 10.sp,
                    fontWeight = FontWeight.Bold,
                    fontFamily = FontFamily.Monospace,
                    color = NeonCyan
                )
            }

            // Voice State Badge
            Box(
                modifier = Modifier
                    .clip(RoundedCornerShape(4.dp))
                    .background(
                        when (voiceState) {
                            VoiceState.LISTENING, VoiceState.WAKE_DETECTED -> NeonCyan.copy(alpha = 0.2f)
                            VoiceState.ERROR -> ElectricMagenta.copy(alpha = 0.2f)
                            else -> CardBorder
                        }
                    )
                    .border(1.dp, CardBorder, RoundedCornerShape(4.dp))
                    .padding(horizontal = 7.dp, vertical = 4.dp)
            ) {
                Text(
                    text = when (voiceState) {
                        VoiceState.INITIALIZING -> "INIT"
                        VoiceState.STANDBY -> "STANDBY"
                        VoiceState.WAKE_DETECTED -> "WAKE"
                        VoiceState.LISTENING -> "LISTENING"
                        VoiceState.ERROR -> "ERROR"
                    },
                    fontSize = 9.sp,
                    fontWeight = FontWeight.Bold,
                    fontFamily = FontFamily.Monospace,
                    color = when (voiceState) {
                        VoiceState.LISTENING, VoiceState.WAKE_DETECTED -> NeonCyan
                        VoiceState.ERROR -> ElectricMagenta
                        else -> TextSecondary
                    }
                )
            }
        }
    }
}

@Composable
private fun ModeToggleButton(
    label: String,
    isActive: Boolean,
    activeColor: Color,
    onClick: () -> Unit
) {
    Box(
        modifier = Modifier
            .clip(RoundedCornerShape(4.dp))
            .background(if (isActive) activeColor.copy(alpha = 0.2f) else CardBorder)
            .border(1.dp, if (isActive) activeColor else CardBorder, RoundedCornerShape(4.dp))
            .clickable { onClick() }
            .padding(horizontal = 7.dp, vertical = 4.dp)
    ) {
        Text(
            text = label,
            fontSize = 9.sp,
            fontWeight = FontWeight.Bold,
            fontFamily = FontFamily.Monospace,
            color = if (isActive) activeColor else TextSecondary
        )
    }
}
