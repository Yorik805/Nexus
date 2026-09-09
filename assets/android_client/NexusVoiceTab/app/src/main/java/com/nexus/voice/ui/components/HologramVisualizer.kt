package com.nexus.voice.ui.components

import androidx.compose.animation.core.FastOutSlowInEasing
import androidx.compose.animation.core.LinearEasing
import androidx.compose.animation.core.RepeatMode
import androidx.compose.animation.core.animateFloat
import androidx.compose.animation.core.infiniteRepeatable
import androidx.compose.animation.core.rememberInfiniteTransition
import androidx.compose.animation.core.tween
import androidx.compose.foundation.Canvas
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.size
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.StrokeCap
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.graphics.drawscope.rotate
import androidx.compose.ui.unit.Dp
import androidx.compose.ui.unit.dp
import com.nexus.voice.state.VoiceState
import com.nexus.voice.ui.theme.ElectricMagenta
import com.nexus.voice.ui.theme.NeonCyan

@Composable
fun HologramVisualizer(
    voiceState: VoiceState,
    modifier: Modifier = Modifier,
    size: Dp = 190.dp
) {
    val isListening = voiceState == VoiceState.LISTENING || voiceState == VoiceState.WAKE_DETECTED

    val infiniteTransition = rememberInfiniteTransition(label = "hologram")

    val rotation by infiniteTransition.animateFloat(
        initialValue = 0f,
        targetValue = 360f,
        animationSpec = infiniteRepeatable(
            animation = tween(durationMillis = if (isListening) 2400 else 6000, easing = LinearEasing),
            repeatMode = RepeatMode.Restart
        ),
        label = "rotation"
    )

    val counterRotation by infiniteTransition.animateFloat(
        initialValue = 360f,
        targetValue = 0f,
        animationSpec = infiniteRepeatable(
            animation = tween(durationMillis = if (isListening) 3200 else 8000, easing = LinearEasing),
            repeatMode = RepeatMode.Restart
        ),
        label = "counterRotation"
    )

    val pulseScale by infiniteTransition.animateFloat(
        initialValue = 0.88f,
        targetValue = if (isListening) 1.12f else 1.02f,
        animationSpec = infiniteRepeatable(
            animation = tween(durationMillis = if (isListening) 650 else 1800, easing = FastOutSlowInEasing),
            repeatMode = RepeatMode.Reverse
        ),
        label = "pulse"
    )

    Box(modifier = modifier.size(size), contentAlignment = Alignment.Center) {
        Canvas(modifier = Modifier.size(size)) {
            val center = Offset(size.toPx() / 2f, size.toPx() / 2f)
            val baseRadius = (size.toPx() / 2f) * 0.72f * pulseScale

            // Outer ambient glow ring
            drawCircle(
                brush = Brush.radialGradient(
                    colors = listOf(
                        if (isListening) NeonCyan.copy(alpha = 0.35f) else NeonCyan.copy(alpha = 0.12f),
                        if (isListening) ElectricMagenta.copy(alpha = 0.20f) else ElectricMagenta.copy(alpha = 0.05f),
                        Color.Transparent
                    ),
                    center = center,
                    radius = baseRadius * 1.35f
                ),
                radius = baseRadius * 1.35f,
                center = center
            )

            // Inner cyan gradient arc
            rotate(rotation, center) {
                drawArc(
                    brush = Brush.sweepGradient(
                        colors = listOf(NeonCyan, Color.Transparent, NeonCyan)
                    ),
                    startAngle = 0f,
                    sweepAngle = 260f,
                    useCenter = false,
                    topLeft = Offset(center.x - baseRadius, center.y - baseRadius),
                    size = androidx.compose.ui.geometry.Size(baseRadius * 2f, baseRadius * 2f),
                    style = Stroke(width = if (isListening) 5.dp.toPx() else 3.dp.toPx(), cap = StrokeCap.Round)
                )
            }

            // Outer magenta gradient arc
            rotate(counterRotation, center) {
                val outerRadius = baseRadius * 0.86f
                drawArc(
                    brush = Brush.sweepGradient(
                        colors = listOf(ElectricMagenta, Color.Transparent, ElectricMagenta)
                    ),
                    startAngle = 90f,
                    sweepAngle = 220f,
                    useCenter = false,
                    topLeft = Offset(center.x - outerRadius, center.y - outerRadius),
                    size = androidx.compose.ui.geometry.Size(outerRadius * 2f, outerRadius * 2f),
                    style = Stroke(width = if (isListening) 4.5.dp.toPx() else 2.5.dp.toPx(), cap = StrokeCap.Round)
                )
            }

            // Center core orb
            drawCircle(
                color = if (isListening) NeonCyan.copy(alpha = 0.85f) else NeonCyan.copy(alpha = 0.35f),
                radius = 7.dp.toPx(),
                center = center
            )
        }
    }
}
