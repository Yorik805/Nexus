package com.nexus.voice.ui.components

import androidx.compose.animation.AnimatedVisibility
import androidx.compose.animation.fadeIn
import androidx.compose.animation.fadeOut
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.alpha
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.nexus.voice.ui.theme.NeonCyan
import com.nexus.voice.ui.theme.TextPrimary

@Composable
fun FadingTranscript(
    currentPartial: String,
    history: List<String>,
    modifier: Modifier = Modifier
) {
    Column(
        modifier = modifier
            .fillMaxWidth()
            .padding(horizontal = 24.dp),
        horizontalAlignment = Alignment.CenterHorizontally,
        verticalArrangement = Arrangement.spacedBy(8.dp)
    ) {
        val hasActiveSpeech = currentPartial.isNotBlank()

        if (hasActiveSpeech) {
            // Active streaming transcript at 1.0 opacity
            Text(
                text = "\"$currentPartial\"",
                fontSize = 24.sp,
                fontWeight = FontWeight.SemiBold,
                fontFamily = FontFamily.SansSerif,
                color = NeonCyan,
                textAlign = TextAlign.Center,
                modifier = Modifier.alpha(1.0f)
            )

            // Past history lines fading down: 2nd line @ 0.6, 3rd line @ 0.3
            if (history.isNotEmpty()) {
                Text(
                    text = history[0],
                    fontSize = 18.sp,
                    fontWeight = FontWeight.Normal,
                    fontFamily = FontFamily.SansSerif,
                    color = TextPrimary,
                    textAlign = TextAlign.Center,
                    modifier = Modifier.alpha(0.6f)
                )
            }
            if (history.size > 1) {
                Text(
                    text = history[1],
                    fontSize = 15.sp,
                    fontWeight = FontWeight.Normal,
                    fontFamily = FontFamily.SansSerif,
                    color = TextPrimary,
                    textAlign = TextAlign.Center,
                    modifier = Modifier.alpha(0.3f)
                )
            }
        } else {
            // When in standby, display the 3 most recent utterances with 1.0 -> 0.6 -> 0.3 opacity
            if (history.isEmpty()) {
                Text(
                    text = "\"Say 'Hey Nexus' or 'Hi Acces' to begin\"",
                    fontSize = 20.sp,
                    fontWeight = FontWeight.Normal,
                    fontFamily = FontFamily.SansSerif,
                    color = TextPrimary,
                    textAlign = TextAlign.Center,
                    modifier = Modifier.alpha(0.45f)
                )
            } else {
                // Item 0 (most recent finalized command) @ 1.0 opacity
                Text(
                    text = "\"${history[0]}\"",
                    fontSize = 22.sp,
                    fontWeight = FontWeight.Medium,
                    fontFamily = FontFamily.SansSerif,
                    color = TextPrimary,
                    textAlign = TextAlign.Center,
                    modifier = Modifier.alpha(1.0f)
                )

                // Item 1 @ 0.6 opacity
                if (history.size > 1) {
                    Text(
                        text = history[1],
                        fontSize = 18.sp,
                        fontWeight = FontWeight.Normal,
                        fontFamily = FontFamily.SansSerif,
                        color = TextPrimary,
                        textAlign = TextAlign.Center,
                        modifier = Modifier.alpha(0.6f)
                    )
                }

                // Item 2 @ 0.3 opacity
                if (history.size > 2) {
                    Text(
                        text = history[2],
                        fontSize = 15.sp,
                        fontWeight = FontWeight.Normal,
                        fontFamily = FontFamily.SansSerif,
                        color = TextPrimary,
                        textAlign = TextAlign.Center,
                        modifier = Modifier.alpha(0.3f)
                    )
                }
            }
        }
    }
}
