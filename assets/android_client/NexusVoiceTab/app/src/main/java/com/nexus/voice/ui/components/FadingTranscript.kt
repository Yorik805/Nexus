package com.nexus.voice.ui.components

import androidx.compose.animation.AnimatedVisibility
import androidx.compose.animation.fadeIn
import androidx.compose.animation.fadeOut
import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.alpha
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.nexus.voice.model.TranscriptEntry
import com.nexus.voice.ui.theme.*

@Composable
fun FadingTranscript(
    currentPartial: String,
    history: List<TranscriptEntry>,
    modifier: Modifier = Modifier
) {
    Column(
        modifier = modifier
            .fillMaxWidth()
            .padding(horizontal = 20.dp),
        horizontalAlignment = Alignment.CenterHorizontally,
        verticalArrangement = Arrangement.spacedBy(10.dp)
    ) {
        val hasActiveSpeech = currentPartial.isNotBlank()

        if (hasActiveSpeech) {
            // Live active spoken words stream
            Column(
                horizontalAlignment = Alignment.CenterHorizontally,
                verticalArrangement = Arrangement.spacedBy(4.dp),
                modifier = Modifier.alpha(1.0f)
            ) {
                // Live indicator badge
                Surface(
                    shape = RoundedCornerShape(4.dp),
                    color = Color(0x2400F5FF),
                    border = BorderStroke(1.dp, NeonCyan.copy(alpha = 0.7f))
                ) {
                    Row(
                        modifier = Modifier.padding(horizontal = 8.dp, vertical = 2.dp),
                        verticalAlignment = Alignment.CenterVertically,
                        horizontalArrangement = Arrangement.spacedBy(5.dp)
                    ) {
                        Box(
                            modifier = Modifier
                                .size(5.dp)
                                .background(NeonCyan, CircleShape)
                        )
                        Text(
                            text = "VOICE INPUT",
                            fontSize = 10.sp,
                            fontFamily = FontFamily.Monospace,
                            fontWeight = FontWeight.Bold,
                            color = NeonCyan,
                            letterSpacing = 1.sp
                        )
                    }
                }

                Text(
                    text = "\"$currentPartial\"",
                    fontSize = 22.sp,
                    fontWeight = FontWeight.SemiBold,
                    fontFamily = FontFamily.SansSerif,
                    color = NeonCyan,
                    textAlign = TextAlign.Center,
                    maxLines = 2,
                    overflow = TextOverflow.Ellipsis
                )
            }

            // Up to 2 past utterances fading below active speech
            if (history.isNotEmpty()) {
                DialogueRow(entry = history[0], alpha = 0.55f, isLatest = false)
            }
            if (history.size > 1) {
                DialogueRow(entry = history[1], alpha = 0.30f, isLatest = false)
            }
        } else {
            // Standby state: Display top 3 most recent dialogue utterances with 1.0 -> 0.60 -> 0.32 opacity
            if (history.isEmpty()) {
                Surface(
                    shape = RoundedCornerShape(6.dp),
                    color = Color(0x12FFFFFF),
                    border = BorderStroke(1.dp, CardBorder)
                ) {
                    Row(
                        modifier = Modifier.padding(horizontal = 14.dp, vertical = 6.dp),
                        verticalAlignment = Alignment.CenterVertically,
                        horizontalArrangement = Arrangement.spacedBy(8.dp)
                    ) {
                        Box(
                            modifier = Modifier
                                .size(6.dp)
                                .background(AccentGreen, CircleShape)
                        )
                        Text(
                            text = "ONLINE // Say \"Hey Nexus\" to command",
                            fontSize = 14.sp,
                            fontFamily = FontFamily.Monospace,
                            fontWeight = FontWeight.Normal,
                            color = TextSecondary
                        )
                    }
                }
            } else {
                // Item 0: Latest utterance @ 1.0 opacity
                DialogueRow(entry = history[0], alpha = 1.0f, isLatest = true)

                // Item 1: 2nd utterance @ 0.60 opacity
                if (history.size > 1) {
                    DialogueRow(entry = history[1], alpha = 0.60f, isLatest = false)
                }

                // Item 2: 3rd utterance @ 0.32 opacity
                if (history.size > 2) {
                    DialogueRow(entry = history[2], alpha = 0.32f, isLatest = false)
                }
            }
        }
    }
}

@Composable
private fun DialogueRow(
    entry: TranscriptEntry,
    alpha: Float,
    isLatest: Boolean
) {
    val badgeBg = if (entry.isUser) Color(0x2200F5FF) else Color(0x22FF007F)
    val badgeBorder = if (entry.isUser) NeonCyan.copy(alpha = 0.6f * alpha) else ElectricMagenta.copy(alpha = 0.6f * alpha)
    val badgeColor = if (entry.isUser) NeonCyan else ElectricMagenta
    val badgeText = if (entry.isUser) "YOU" else "NEXUS"
    val textColor = if (entry.isUser) TextPrimary else Color(0xFFE6EDF3)

    Row(
        modifier = Modifier
            .alpha(alpha)
            .widthIn(max = 620.dp),
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.Center
    ) {
        // Futuristic Role Badge Pill
        Surface(
            shape = RoundedCornerShape(4.dp),
            color = badgeBg,
            border = BorderStroke(1.dp, badgeBorder)
        ) {
            Row(
                modifier = Modifier.padding(horizontal = 7.dp, vertical = 2.dp),
                verticalAlignment = Alignment.CenterVertically,
                horizontalArrangement = Arrangement.spacedBy(4.dp)
            ) {
                Box(
                    modifier = Modifier
                        .size(4.dp)
                        .background(badgeColor, CircleShape)
                )
                Text(
                    text = badgeText,
                    fontSize = 9.sp,
                    fontFamily = FontFamily.Monospace,
                    fontWeight = FontWeight.Bold,
                    color = badgeColor,
                    letterSpacing = 0.8.sp
                )
            }
        }

        Spacer(modifier = Modifier.width(10.dp))

        // Dialogue Message
        Text(
            text = entry.text,
            fontSize = if (isLatest) 18.sp else 14.sp,
            fontWeight = if (isLatest) FontWeight.Medium else FontWeight.Normal,
            fontFamily = FontFamily.SansSerif,
            color = textColor,
            textAlign = TextAlign.Start,
            maxLines = if (isLatest) 3 else 2,
            overflow = TextOverflow.Ellipsis,
            lineHeight = if (isLatest) 24.sp else 20.sp
        )
    }
}
