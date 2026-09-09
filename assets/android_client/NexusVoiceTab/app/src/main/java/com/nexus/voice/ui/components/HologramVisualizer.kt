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
import androidx.compose.ui.graphics.PathEffect
import androidx.compose.ui.graphics.StrokeCap
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.graphics.drawscope.rotate
import androidx.compose.ui.unit.Dp
import androidx.compose.ui.unit.dp
import com.nexus.voice.state.VoiceState
import com.nexus.voice.ui.theme.AccentGreen
import com.nexus.voice.ui.theme.ElectricMagenta
import com.nexus.voice.ui.theme.NeonCyan
import com.nexus.voice.ui.theme.TextSecondary
import kotlin.math.*

@Composable
fun HologramVisualizer(
    voiceState: VoiceState,
    audioLevel: Float,
    modifier: Modifier = Modifier,
    size: Dp = 220.dp
) {
    val isListening = voiceState == VoiceState.LISTENING || voiceState == VoiceState.WAKE_DETECTED

    // Smooth physics-based spring animation on voice volume
    val smoothedLevel by animateFloatAsState(
        targetValue = if (voiceState == VoiceState.ERROR) 0f else audioLevel.coerceIn(0f, 1f),
        animationSpec = spring(
            dampingRatio = Spring.DampingRatioMediumBouncy,
            stiffness = Spring.StiffnessMedium
        ),
        label = "voiceLevelSpring"
    )

    val infiniteTransition = rememberInfiniteTransition(label = "hologramCore")

    // Primary clockwise rotation
    val primaryRotation by infiniteTransition.animateFloat(
        initialValue = 0f,
        targetValue = 360f,
        animationSpec = infiniteRepeatable(
            animation = tween(durationMillis = if (isListening) 4000 else 12000, easing = LinearEasing),
            repeatMode = RepeatMode.Restart
        ),
        label = "primaryRotation"
    )

    // Counter-clockwise orbital rotation
    val counterRotation by infiniteTransition.animateFloat(
        initialValue = 360f,
        targetValue = 0f,
        animationSpec = infiniteRepeatable(
            animation = tween(durationMillis = if (isListening) 5500 else 16000, easing = LinearEasing),
            repeatMode = RepeatMode.Restart
        ),
        label = "counterRotation"
    )

    // Harmonic wave phase for radial frequency oscillation
    val wavePhase by infiniteTransition.animateFloat(
        initialValue = 0f,
        targetValue = 360f,
        animationSpec = infiniteRepeatable(
            animation = tween(durationMillis = if (isListening) 1600 else 4000, easing = LinearEasing),
            repeatMode = RepeatMode.Restart
        ),
        label = "wavePhase"
    )

    // Idle organic breathing
    val idleBreathe by infiniteTransition.animateFloat(
        initialValue = 0.96f,
        targetValue = 1.04f,
        animationSpec = infiniteRepeatable(
            animation = tween(durationMillis = 2400, easing = FastOutSlowInEasing),
            repeatMode = RepeatMode.Reverse
        ),
        label = "idleBreathe"
    )

    // Dynamic color assignment
    val primaryColor = when (voiceState) {
        VoiceState.WAKE_DETECTED -> ElectricMagenta
        VoiceState.LISTENING -> if (smoothedLevel > 0.45f) AccentGreen else NeonCyan
        VoiceState.ERROR -> Color(0xFFF87171)
        else -> NeonCyan
    }

    val secondaryColor = when (voiceState) {
        VoiceState.WAKE_DETECTED -> Color.White
        VoiceState.LISTENING -> ElectricMagenta
        else -> Color(0xFF4F46E5) // Electric Indigo
    }

    Box(modifier = modifier.size(size), contentAlignment = Alignment.Center) {
        Canvas(modifier = Modifier.size(size)) {
            val center = Offset(size.toPx() / 2f, size.toPx() / 2f)
            val maxRadius = size.toPx() / 2f

            val baseRadius = maxRadius * 0.55f * idleBreathe
            val activeBoost = smoothedLevel * 0.35f

            // 1. Outer Tech Reticle Ticks (60 precision radial tick marks)
            val totalTicks = 60
            for (i in 0 until totalTicks) {
                val angleDeg = i * (360f / totalTicks)
                val angleRad = angleDeg * (PI / 180f).toFloat()

                val isMajor = i % 5 == 0
                val tickLen = if (isMajor) 7.dp.toPx() else 3.5.dp.toPx()
                val tickStartR = maxRadius * 0.90f
                val tickEndR = tickStartR + tickLen

                val p1 = Offset(center.x + tickStartR * cos(angleRad), center.y + tickStartR * sin(angleRad))
                val p2 = Offset(center.x + tickEndR * cos(angleRad), center.y + tickEndR * sin(angleRad))

                drawLine(
                    color = if (isMajor) primaryColor.copy(alpha = 0.6f) else TextSecondary.copy(alpha = 0.25f),
                    start = p1,
                    end = p2,
                    strokeWidth = if (isMajor) 1.5.dp.toPx() else 1.dp.toPx(),
                    cap = StrokeCap.Round
                )
            }

            // 2. Segmented Outer Gyro Arc (Clockwise)
            rotate(primaryRotation, center) {
                val gyroRadius = maxRadius * 0.82f
                // Draw 3 segmented arcs
                for (arcIndex in 0..2) {
                    drawArc(
                        brush = Brush.sweepGradient(
                            listOf(primaryColor.copy(alpha = 0.9f), Color.Transparent, primaryColor.copy(alpha = 0.9f))
                        ),
                        startAngle = arcIndex * 120f + 10f,
                        sweepAngle = 90f,
                        useCenter = false,
                        topLeft = Offset(center.x - gyroRadius, center.y - gyroRadius),
                        size = Size(gyroRadius * 2f, gyroRadius * 2f),
                        style = Stroke(width = 2.dp.toPx(), cap = StrokeCap.Round)
                    )
                }

                // 3 Satellite node beacons
                for (arcIndex in 0..2) {
                    val satAngle = (arcIndex * 120f + 10f) * (PI / 180f).toFloat()
                    drawCircle(
                        color = Color.White,
                        radius = 2.5.dp.toPx(),
                        center = Offset(center.x + gyroRadius * cos(satAngle), center.y + gyroRadius * sin(satAngle))
                    )
                }
            }

            // 3. Counter-Rotating Dashed Compass Ring
            rotate(counterRotation, center) {
                val compassRadius = maxRadius * 0.70f
                drawCircle(
                    color = secondaryColor.copy(alpha = 0.45f),
                    radius = compassRadius,
                    center = center,
                    style = Stroke(
                        width = 1.2.dp.toPx(),
                        pathEffect = PathEffect.dashPathEffect(floatArrayOf(14f, 10f), 0f)
                    )
                )
            }

            // 4. RADIAL 360° EQUALIZER SPECTRUM (54 radial audio frequency bars)
            val numBars = 54
            val eqBaseRadius = baseRadius * 0.92f

            for (i in 0 until numBars) {
                val angleDeg = i * (360f / numBars)
                val angleRad = angleDeg * (PI / 180f).toFloat()

                // Harmonic ripple formula
                val waveVal = sin((i * 4f + wavePhase) * (PI / 180f).toFloat())
                val dynamicBarHeight = if (isListening) {
                    (4.dp.toPx() + (smoothedLevel * 28.dp.toPx() * (0.35f + 0.65f * abs(waveVal))))
                } else {
                    (2.5.dp.toPx() + (2.5.dp.toPx() * (0.5f + 0.5f * waveVal)))
                }

                val barStartR = eqBaseRadius
                val barEndR = eqBaseRadius + dynamicBarHeight

                val startP = Offset(center.x + barStartR * cos(angleRad), center.y + barStartR * sin(angleRad))
                val endP = Offset(center.x + barEndR * cos(angleRad), center.y + barEndR * sin(angleRad))

                // Radial frequency bar line
                drawLine(
                    brush = Brush.linearGradient(
                        colors = listOf(primaryColor, secondaryColor),
                        start = startP,
                        end = endP
                    ),
                    start = startP,
                    end = endP,
                    strokeWidth = 2.dp.toPx(),
                    cap = StrokeCap.Round
                )

                // Glowing neon tip dot when active
                if (isListening && dynamicBarHeight > 8.dp.toPx()) {
                    drawCircle(
                        color = Color.White,
                        radius = 1.8.dp.toPx(),
                        center = endP
                    )
                }
            }

            // 5. Sound-Reactive Plasma Aura (Radial Gradient)
            val auraRadius = baseRadius * (1.1f + activeBoost)
            drawCircle(
                brush = Brush.radialGradient(
                    colors = listOf(
                        primaryColor.copy(alpha = 0.35f + smoothedLevel * 0.45f),
                        secondaryColor.copy(alpha = 0.15f + smoothedLevel * 0.25f),
                        Color.Transparent
                    ),
                    center = center,
                    radius = auraRadius
                ),
                radius = auraRadius,
                center = center
            )

            // 6. High-Energy Quantum Core (Central Glowing Orb)
            val coreRadius = (10.dp.toPx() + smoothedLevel * 14.dp.toPx())
            drawCircle(
                brush = Brush.radialGradient(
                    colors = listOf(
                        Color.White,
                        primaryColor,
                        secondaryColor.copy(alpha = 0.4f),
                        Color.Transparent
                    ),
                    center = center,
                    radius = coreRadius * 1.8f
                ),
                radius = coreRadius * 1.8f,
                center = center
            )

            // Center solid bright node
            drawCircle(
                color = Color.White,
                radius = coreRadius * 0.55f,
                center = center
            )
        }
    }
}
