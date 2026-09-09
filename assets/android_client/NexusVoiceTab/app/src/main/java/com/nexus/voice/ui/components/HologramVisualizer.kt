package com.nexus.voice.ui.components

import androidx.compose.animation.core.*
import androidx.compose.foundation.Canvas
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.size
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.geometry.Size
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.StrokeCap
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.graphics.drawscope.rotate
import androidx.compose.ui.unit.Dp
import androidx.compose.ui.unit.dp
import com.nexus.voice.state.VoiceState
import com.nexus.voice.ui.theme.AccentGreen
import com.nexus.voice.ui.theme.ElectricMagenta
import com.nexus.voice.ui.theme.NeonCyan
import kotlin.math.PI
import kotlin.math.cos
import kotlin.math.sin

@Composable
fun HologramVisualizer(
    voiceState: VoiceState,
    audioLevel: Float,
    modifier: Modifier = Modifier,
    size: Dp = 200.dp
) {
    val isListening = voiceState == VoiceState.LISTENING || voiceState == VoiceState.WAKE_DETECTED

    // Smoothly animate the incoming audio level
    val animatedLevel by animateFloatAsState(
        targetValue = if (voiceState == VoiceState.ERROR) 0f else audioLevel.coerceIn(0f, 1f),
        animationSpec = spring(
            dampingRatio = Spring.DampingRatioMediumBouncy,
            stiffness = Spring.StiffnessLow
        ),
        label = "audioLevelSpring"
    )

    val infiniteTransition = rememberInfiniteTransition(label = "hologramInfinite")

    // Rotation speeds up when speaking or listening
    val rotationSpeed = if (isListening) 2200 else 6500
    val rotation by infiniteTransition.animateFloat(
        initialValue = 0f,
        targetValue = 360f,
        animationSpec = infiniteRepeatable(
            animation = tween(durationMillis = rotationSpeed, easing = LinearEasing),
            repeatMode = RepeatMode.Restart
        ),
        label = "rotation"
    )

    val counterRotation by infiniteTransition.animateFloat(
        initialValue = 360f,
        targetValue = 0f,
        animationSpec = infiniteRepeatable(
            animation = tween(durationMillis = if (isListening) 3400 else 8500, easing = LinearEasing),
            repeatMode = RepeatMode.Restart
        ),
        label = "counterRotation"
    )

    val idleBreath by infiniteTransition.animateFloat(
        initialValue = 0.95f,
        targetValue = 1.05f,
        animationSpec = infiniteRepeatable(
            animation = tween(durationMillis = 2000, easing = FastOutSlowInEasing),
            repeatMode = RepeatMode.Reverse
        ),
        label = "idleBreath"
    )

    // Dynamic color theme based on voice state
    val primaryColor = when (voiceState) {
        VoiceState.WAKE_DETECTED -> ElectricMagenta
        VoiceState.LISTENING -> if (animatedLevel > 0.4f) AccentGreen else NeonCyan
        VoiceState.ERROR -> Color(0xFFF87171)
        else -> NeonCyan
    }

    val secondaryColor = when (voiceState) {
        VoiceState.WAKE_DETECTED -> Color.White
        VoiceState.LISTENING -> ElectricMagenta
        else -> ElectricMagenta.copy(alpha = 0.7f)
    }

    Box(modifier = modifier.size(size), contentAlignment = Alignment.Center) {
        Canvas(modifier = Modifier.size(size)) {
            val center = Offset(size.toPx() / 2f, size.toPx() / 2f)
            val maxRadius = (size.toPx() / 2f) * 0.92f

            // Sound amplitude multiplier
            val soundScale = 1.0f + (animatedLevel * 0.45f)
            val baseRadius = maxRadius * 0.65f * idleBreath * soundScale

            // 1. Outermost Ambient Halo Glow
            drawCircle(
                brush = Brush.radialGradient(
                    colors = listOf(
                        primaryColor.copy(alpha = 0.28f + (animatedLevel * 0.35f)),
                        secondaryColor.copy(alpha = 0.12f + (animatedLevel * 0.20f)),
                        Color.Transparent
                    ),
                    center = center,
                    radius = baseRadius * 1.55f
                ),
                radius = baseRadius * 1.55f,
                center = center
            )

            // 2. Sound Reactive Ripple Wave 1 (Expands outward with audio volume)
            val wave1Radius = baseRadius * (1.15f + animatedLevel * 0.35f)
            drawCircle(
                color = primaryColor.copy(alpha = (0.25f + animatedLevel * 0.5f).coerceAtMost(0.85f)),
                radius = wave1Radius,
                center = center,
                style = Stroke(
                    width = (2.dp.toPx() + animatedLevel * 4.dp.toPx()),
                    cap = StrokeCap.Round
                )
            )

            // 3. Sound Reactive Ripple Wave 2 (Secondary harmonic ring)
            if (animatedLevel > 0.08f) {
                val wave2Radius = baseRadius * (1.32f + animatedLevel * 0.45f)
                drawCircle(
                    color = secondaryColor.copy(alpha = (animatedLevel * 0.6f).coerceAtMost(0.7f)),
                    radius = wave2Radius,
                    center = center,
                    style = Stroke(
                        width = (1.5.dp.toPx() + animatedLevel * 3.dp.toPx()),
                        cap = StrokeCap.Round
                    )
                )
            }

            // 4. Inner Cyan Gradient Segmented Arc (Clockwise)
            rotate(rotation, center) {
                drawArc(
                    brush = Brush.sweepGradient(
                        colors = listOf(primaryColor, Color.Transparent, primaryColor)
                    ),
                    startAngle = 15f,
                    sweepAngle = 250f,
                    useCenter = false,
                    topLeft = Offset(center.x - baseRadius, center.y - baseRadius),
                    size = Size(baseRadius * 2f, baseRadius * 2f),
                    style = Stroke(
                        width = if (isListening) 4.5.dp.toPx() else 2.5.dp.toPx(),
                        cap = StrokeCap.Round
                    )
                )

                // Orbiting glowing satellites on the arc
                val satAngleRad = (rotation * PI / 180.0)
                val satX = center.x + (baseRadius * cos(satAngleRad)).toFloat()
                val satY = center.y + (baseRadius * sin(satAngleRad)).toFloat()
                drawCircle(
                    color = Color.White,
                    radius = (3.dp.toPx() + animatedLevel * 3.dp.toPx()),
                    center = Offset(satX, satY)
                )
            }

            // 5. Outer Magenta Arc (Counter-Clockwise)
            rotate(counterRotation, center) {
                val outerRadius = baseRadius * 0.84f
                drawArc(
                    brush = Brush.sweepGradient(
                        colors = listOf(secondaryColor, Color.Transparent, secondaryColor)
                    ),
                    startAngle = 110f,
                    sweepAngle = 210f,
                    useCenter = false,
                    topLeft = Offset(center.x - outerRadius, center.y - outerRadius),
                    size = Size(outerRadius * 2f, outerRadius * 2f),
                    style = Stroke(
                        width = if (isListening) 3.5.dp.toPx() else 2.dp.toPx(),
                        cap = StrokeCap.Round
                    )
                )
            }

            // 6. Sound Wave Cloud / Particle Ring (16 orbital nodes vibrating with audio frequency)
            val numPoints = 16
            for (i in 0 until numPoints) {
                val angleDeg = (i.toFloat() / numPoints) * 360f + (rotation * 0.5f)
                val angleRad = angleDeg * PI / 180f
                // Add sinusoidal displacement multiplied by audio amplitude
                val waveDisp = sin((i * 3 + rotation * 0.1f) * PI / 180f).toFloat() * animatedLevel * 22.dp.toPx()
                val pRadius = (baseRadius * 0.62f) + waveDisp
                val px = center.x + (pRadius * cos(angleRad)).toFloat()
                val py = center.y + (pRadius * sin(angleRad)).toFloat()

                drawCircle(
                    color = if (i % 2 == 0) primaryColor else secondaryColor,
                    radius = (1.8.dp.toPx() + animatedLevel * 2.5.dp.toPx()),
                    center = Offset(px, py)
                )
            }

            // 7. Center Glowing Plasma Core
            val coreRadius = (8.dp.toPx() + animatedLevel * 16.dp.toPx())
            drawCircle(
                brush = Brush.radialGradient(
                    colors = listOf(
                        Color.White,
                        primaryColor,
                        primaryColor.copy(alpha = 0.2f),
                        Color.Transparent
                    ),
                    center = center,
                    radius = coreRadius * 1.6f
                ),
                radius = coreRadius * 1.6f,
                center = center
            )
        }
    }
}
