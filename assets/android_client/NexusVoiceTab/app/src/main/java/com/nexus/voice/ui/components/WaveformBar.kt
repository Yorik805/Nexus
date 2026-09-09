package com.nexus.voice.ui.components

import androidx.compose.animation.core.*
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.unit.Dp
import androidx.compose.ui.unit.dp
import com.nexus.voice.state.VoiceState
import com.nexus.voice.ui.theme.AccentGreen
import com.nexus.voice.ui.theme.ElectricMagenta
import com.nexus.voice.ui.theme.NeonCyan
import kotlin.math.abs
import kotlin.math.sin

@Composable
fun WaveformBar(
    audioLevel: Float,
    voiceState: VoiceState,
    modifier: Modifier = Modifier,
    bars: Int = 32,
    maxHeight: Dp = 38.dp,
    minHeight: Dp = 4.dp
) {
    val isListening = voiceState == VoiceState.LISTENING || voiceState == VoiceState.WAKE_DETECTED

    val infiniteTransition = rememberInfiniteTransition(label = "waveformAnimation")
    val phase by infiniteTransition.animateFloat(
        initialValue = 0f,
        targetValue = 360f,
        animationSpec = infiniteRepeatable(
            animation = tween(durationMillis = if (isListening) 1200 else 3000, easing = LinearEasing),
            repeatMode = RepeatMode.Restart
        ),
        label = "phase"
    )

    val activeColor = when (voiceState) {
        VoiceState.WAKE_DETECTED -> ElectricMagenta
        VoiceState.LISTENING -> if (audioLevel > 0.4f) AccentGreen else NeonCyan
        VoiceState.ERROR -> Color(0xFFF87171)
        else -> NeonCyan.copy(alpha = 0.5f)
    }

    Row(
        modifier = modifier
            .height(maxHeight)
            .padding(horizontal = 8.dp),
        horizontalArrangement = Arrangement.spacedBy(3.dp),
        verticalAlignment = Alignment.CenterVertically
    ) {
        for (i in 0 until bars) {
            // Bell curve: tallest in the center, tapering toward edges
            val centerDist = abs(i - (bars / 2f)) / (bars / 2f)
            val bellCurve = (1f - (centerDist * 0.75f)).coerceIn(0.2f, 1f)

            // Sinusoidal harmonic wave modulation
            val wave = sin((i * 18f + phase) * (Math.PI / 180f).toFloat())
            val dynamicFactor = 0.15f + (0.85f * (0.5f + 0.5f * wave))

            val levelMultiplier = if (isListening) {
                (0.12f + audioLevel * 1.6f).coerceIn(0.08f, 1f)
            } else {
                0.08f + (0.06f * dynamicFactor)
            }

            val barHeight = minHeight + (maxHeight - minHeight) * bellCurve * levelMultiplier * dynamicFactor

            Box(
                modifier = Modifier
                    .width(3.dp)
                    .height(barHeight.coerceIn(minHeight, maxHeight))
                    .background(
                        color = activeColor.copy(alpha = if (isListening) 0.85f else 0.35f),
                        shape = RoundedCornerShape(2.dp)
                    )
            )
        }
    }
}
