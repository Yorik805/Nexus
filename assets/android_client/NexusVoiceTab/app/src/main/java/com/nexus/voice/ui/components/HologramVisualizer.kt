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
    size: Dp = 230.dp
) {
    val isListening = voiceState == VoiceState.LISTENING || voiceState == VoiceState.WAKE_DETECTED
    val isWakeBurst = voiceState == VoiceState.WAKE_DETECTED

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

    // Rotation speeds: vortex burst during wake detection
    val primarySpeed = when {
        isWakeBurst -> 800
        isListening -> 3500
        else -> 10000
    }
    val primaryRotation by infiniteTransition.animateFloat(
        initialValue = 0f,
        targetValue = 360f,
        animationSpec = infiniteRepeatable(
            animation = tween(durationMillis = primarySpeed, easing = LinearEasing),
            repeatMode = RepeatMode.Restart
        ),
        label = "primaryRotation"
    )

    val counterRotation by infiniteTransition.animateFloat(
        initialValue = 360f,
        targetValue = 0f,
        animationSpec = infiniteRepeatable(
            animation = tween(durationMillis = if (isWakeBurst) 1100 else if (isListening) 4800 else 14000, easing = LinearEasing),
            repeatMode = RepeatMode.Restart
        ),
        label = "counterRotation"
    )

    // Harmonic wave phase for radial frequency oscillation
    val wavePhase by infiniteTransition.animateFloat(
        initialValue = 0f,
        targetValue = 360f,
        animationSpec = infiniteRepeatable(
            animation = tween(durationMillis = if (isListening) 1200 else 3600, easing = LinearEasing),
            repeatMode = RepeatMode.Restart
        ),
        label = "wavePhase"
    )

    // Idle organic breathing
    val idleBreathe by infiniteTransition.animateFloat(
        initialValue = 0.95f,
        targetValue = 1.05f,
        animationSpec = infiniteRepeatable(
            animation = tween(durationMillis = 2200, easing = FastOutSlowInEasing),
            repeatMode = RepeatMode.Reverse
        ),
        label = "idleBreathe"
    )

    // Wake Shockwave Ring (expands continuously during wake or listening)
    val shockwaveProgress by infiniteTransition.animateFloat(
        initialValue = 0.4f,
        targetValue = 1.25f,
        animationSpec = infiniteRepeatable(
            animation = tween(durationMillis = if (isWakeBurst) 600 else if (isListening) 1400 else 2800, easing = FastOutSlowInEasing),
            repeatMode = RepeatMode.Restart
        ),
        label = "shockwaveProgress"
    )

    // Dynamic color theme based on voice state
    val primaryColor = when (voiceState) {
        VoiceState.WAKE_DETECTED -> ElectricMagenta
        VoiceState.LISTENING -> if (smoothedLevel > 0.45f) AccentGreen else NeonCyan
        VoiceState.ERROR -> Color(0xFFF87171)
        else -> NeonCyan
    }

    val secondaryColor = when (voiceState) {
        VoiceState.WAKE_DETECTED -> Color.White
        VoiceState.LISTENING -> ElectricMagenta
        else -> Color(0xFF38BDF8) // Sky Blue
    }

    Box(modifier = modifier.size(size), contentAlignment = Alignment.Center) {
        Canvas(modifier = Modifier.size(size)) {
            val center = Offset(size.toPx() / 2f, size.toPx() / 2f)
            val maxRadius = size.toPx() / 2f

            val baseRadius = maxRadius * 0.52f * idleBreathe
            val activeBoost = smoothedLevel * 0.38f

            // 0. Shockwave Warp Ring (Fires outward during wake word / listening)
            val shockwaveR = maxRadius * shockwaveProgress
            val shockwaveAlpha = (1f - (shockwaveProgress - 0.4f) / 0.85f).coerceIn(0f, 1f) * if (isWakeBurst) 0.85f else if (isListening) 0.45f else 0.15f
            drawCircle(
                color = primaryColor.copy(alpha = shockwaveAlpha),
                radius = shockwaveR,
                center = center,
                style = Stroke(width = if (isWakeBurst) 3.5.dp.toPx() else 1.5.dp.toPx())
            )

            // 1. Outer Tech Reticle Ticks (64 precision radial gauge tick marks)
            val totalTicks = 64
            for (i in 0 until totalTicks) {
                val angleDeg = i * (360f / totalTicks)
                val angleRad = angleDeg * (PI / 180f).toFloat()

                val isCardinal = i % 16 == 0
                val isMajor = i % 4 == 0
                val tickLen = if (isCardinal) 10.dp.toPx() else if (isMajor) 6.dp.toPx() else 3.dp.toPx()
                val tickStartR = maxRadius * 0.88f
                val tickEndR = tickStartR + tickLen

                val p1 = Offset(center.x + tickStartR * cos(angleRad), center.y + tickStartR * sin(angleRad))
                val p2 = Offset(center.x + tickEndR * cos(angleRad), center.y + tickEndR * sin(angleRad))

                drawLine(
                    color = when {
                        isCardinal -> if (isListening) Color.White else primaryColor
                        isMajor -> primaryColor.copy(alpha = 0.7f)
                        else -> TextSecondary.copy(alpha = 0.2f)
                    },
                    start = p1,
                    end = p2,
                    strokeWidth = if (isCardinal) 2.dp.toPx() else if (isMajor) 1.5.dp.toPx() else 1.dp.toPx(),
                    cap = StrokeCap.Round
                )
            }

            // 2. Segmented Outer Gyro Arc (Clockwise)
            rotate(primaryRotation, center) {
                val gyroRadius = maxRadius * 0.80f
                for (arcIndex in 0..2) {
                    drawArc(
                        brush = Brush.sweepGradient(
                            listOf(primaryColor, Color.Transparent, primaryColor)
                        ),
                        startAngle = arcIndex * 120f + 15f,
                        sweepAngle = 80f,
                        useCenter = false,
                        topLeft = Offset(center.x - gyroRadius, center.y - gyroRadius),
                        size = Size(gyroRadius * 2f, gyroRadius * 2f),
                        style = Stroke(width = if (isWakeBurst) 3.dp.toPx() else 2.dp.toPx(), cap = StrokeCap.Round)
                    )
                }

                // Satellite glowing beacons
                for (arcIndex in 0..2) {
                    val satAngle = (arcIndex * 120f + 15f) * (PI / 180f).toFloat()
                    drawCircle(
                        color = Color.White,
                        radius = (3.dp.toPx() + smoothedLevel * 3.dp.toPx()),
                        center = Offset(center.x + gyroRadius * cos(satAngle), center.y + gyroRadius * sin(satAngle))
                    )
                }
            }

            // 3. Counter-Rotating Dashed Compass Ring
            rotate(counterRotation, center) {
                val compassRadius = maxRadius * 0.68f
                drawCircle(
                    color = secondaryColor.copy(alpha = if (isWakeBurst) 0.8f else 0.5f),
                    radius = compassRadius,
                    center = center,
                    style = Stroke(
                        width = 1.5.dp.toPx(),
                        pathEffect = PathEffect.dashPathEffect(floatArrayOf(16f, 12f), 0f)
                    )
                )
            }

            // 4. RADIAL 360° EQUALIZER SPECTRUM (56 radial audio frequency bars)
            val numBars = 56
            val eqBaseRadius = baseRadius * 0.88f

            for (i in 0 until numBars) {
                val angleDeg = i * (360f / numBars)
                val angleRad = angleDeg * (PI / 180f).toFloat()

                val waveVal = sin((i * 4f + wavePhase) * (PI / 180f).toFloat())
                val dynamicBarHeight = if (isListening) {
                    (5.dp.toPx() + (smoothedLevel * 34.dp.toPx() * (0.35f + 0.65f * abs(waveVal))))
                } else {
                    (3.dp.toPx() + (3.dp.toPx() * (0.5f + 0.5f * waveVal)))
                }

                val barStartR = eqBaseRadius
                val barEndR = eqBaseRadius + dynamicBarHeight

                val startP = Offset(center.x + barStartR * cos(angleRad), center.y + barStartR * sin(angleRad))
                val endP = Offset(center.x + barEndR * cos(angleRad), center.y + barEndR * sin(angleRad))

                drawLine(
                    brush = Brush.linearGradient(
                        colors = listOf(primaryColor, secondaryColor),
                        start = startP,
                        end = endP
                    ),
                    start = startP,
                    end = endP,
                    strokeWidth = (2.2.dp.toPx() + smoothedLevel * 1.5.dp.toPx()),
                    cap = StrokeCap.Round
                )

                // Tip firefly beacons on speech peaks
                if (isListening && dynamicBarHeight > 9.dp.toPx()) {
                    drawCircle(
                        color = Color.White,
                        radius = (1.8.dp.toPx() + smoothedLevel * 2.dp.toPx()),
                        center = endP
                    )
                }
            }

            // 5. Sound-Reactive Plasma Aura (Radial Glow)
            val auraRadius = baseRadius * (1.15f + activeBoost)
            drawCircle(
                brush = Brush.radialGradient(
                    colors = listOf(
                        primaryColor.copy(alpha = if (isWakeBurst) 0.65f else 0.38f + smoothedLevel * 0.45f),
                        secondaryColor.copy(alpha = if (isWakeBurst) 0.35f else 0.18f + smoothedLevel * 0.25f),
                        Color.Transparent
                    ),
                    center = center,
                    radius = auraRadius
                ),
                radius = auraRadius,
                center = center
            )

            // 6. High-Energy Quantum Core (Central Glowing Orb)
            val coreRadius = (12.dp.toPx() + smoothedLevel * 16.dp.toPx() + if (isWakeBurst) 8.dp.toPx() else 0.dp.toPx())
            drawCircle(
                brush = Brush.radialGradient(
                    colors = listOf(
                        Color.White,
                        primaryColor,
                        secondaryColor.copy(alpha = 0.5f),
                        Color.Transparent
                    ),
                    center = center,
                    radius = coreRadius * 1.9f
                ),
                radius = coreRadius * 1.9f,
                center = center
            )

            // Center bright cyber-reticle
            drawCircle(
                color = Color.White,
                radius = coreRadius * 0.52f,
                center = center
            )

            // Crosshair inside core
            val crossSize = 5.dp.toPx()
            drawLine(
                color = primaryColor,
                start = Offset(center.x - crossSize, center.y),
                end = Offset(center.x + crossSize, center.y),
                strokeWidth = 1.5.dp.toPx()
            )
            drawLine(
                color = primaryColor,
                start = Offset(center.x, center.y - crossSize),
                end = Offset(center.x, center.y + crossSize),
                strokeWidth = 1.5.dp.toPx()
            )
        }
    }
}
