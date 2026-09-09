package com.nexus.voice.ui.components

import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.compose.ui.window.Dialog
import com.nexus.voice.ui.theme.*
import kotlinx.coroutines.launch

@Composable
fun SettingsDialog(
    currentIp: String,
    dashboardPort: Int,
    runtimePort: Int,
    onTestPing: suspend (String, Int) -> Pair<Boolean, Long>,
    onSave: (String) -> Unit,
    onDismiss: () -> Unit
) {
    var ipInput by remember { mutableStateOf(currentIp) }
    var isPinging by remember { mutableStateOf(false) }
    var pingResult by remember { mutableStateOf<Pair<Boolean, Long>?>(null) }
    val coroutineScope = rememberCoroutineScope()

    Dialog(onDismissRequest = onDismiss) {
        Surface(
            modifier = Modifier
                .fillMaxWidth(0.92f)
                .wrapContentHeight(),
            shape = RoundedCornerShape(16.dp),
            color = SurfaceDark,
            border = BorderStroke(1.dp, NeonCyan.copy(alpha = 0.5f))
        ) {
            Column(
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(24.dp)
            ) {
                // Header
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.SpaceBetween,
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Text(
                        text = "NEXUS SERVER CONFIG",
                        fontFamily = FontFamily.Monospace,
                        fontWeight = FontWeight.Bold,
                        fontSize = 15.sp,
                        color = NeonCyan
                    )

                    Surface(
                        shape = RoundedCornerShape(4.dp),
                        color = CardBorder
                    ) {
                        Text(
                            text = "LAN / WI-FI",
                            fontFamily = FontFamily.Monospace,
                            fontSize = 10.sp,
                            fontWeight = FontWeight.SemiBold,
                            color = TextSecondary,
                            modifier = Modifier.padding(horizontal = 8.dp, vertical = 3.dp)
                        )
                    }
                }

                Spacer(modifier = Modifier.height(18.dp))

                // Server IP input
                Text(
                    text = "SERVER IP ADDRESS",
                    fontFamily = FontFamily.Monospace,
                    fontSize = 11.sp,
                    color = TextSecondary
                )
                Spacer(modifier = Modifier.height(6.dp))
                OutlinedTextField(
                    value = ipInput,
                    onValueChange = {
                        ipInput = it
                        pingResult = null
                    },
                    placeholder = {
                        Text(
                            text = "e.g. 192.168.1.100",
                            color = TextSecondary.copy(alpha = 0.4f),
                            fontFamily = FontFamily.Monospace,
                            fontSize = 13.sp
                        )
                    },
                    singleLine = true,
                    colors = OutlinedTextFieldDefaults.colors(
                        focusedBorderColor = NeonCyan,
                        unfocusedBorderColor = CardBorder,
                        focusedTextColor = TextPrimary,
                        unfocusedTextColor = TextPrimary,
                        cursorColor = NeonCyan
                    ),
                    modifier = Modifier.fillMaxWidth()
                )

                Spacer(modifier = Modifier.height(14.dp))

                // Ports information
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.spacedBy(12.dp)
                ) {
                    PortBadge(label = "DASHBOARD API", port = dashboardPort.toString(), modifier = Modifier.weight(1f))
                    PortBadge(label = "RUNTIME API", port = runtimePort.toString(), modifier = Modifier.weight(1f))
                }

                Spacer(modifier = Modifier.height(16.dp))

                // Ping Test Row
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.SpaceBetween,
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Button(
                        onClick = {
                            isPinging = true
                            pingResult = null
                            coroutineScope.launch {
                                val res = onTestPing(ipInput, dashboardPort)
                                pingResult = res
                                isPinging = false
                            }
                        },
                        enabled = !isPinging && ipInput.isNotBlank(),
                        colors = ButtonDefaults.buttonColors(
                            containerColor = SurfaceGlass,
                            contentColor = NeonCyan
                        ),
                        border = BorderStroke(1.dp, CardBorder)
                    ) {
                        Text(
                            text = if (isPinging) "PINGING…" else "TEST PING",
                            fontFamily = FontFamily.Monospace,
                            fontWeight = FontWeight.Bold,
                            fontSize = 11.sp
                        )
                    }

                    // Ping Status Display
                    if (pingResult != null) {
                        val (success, latency) = pingResult!!
                        Row(verticalAlignment = Alignment.CenterVertically) {
                            Box(
                                modifier = Modifier
                                    .size(8.dp)
                                    .background(
                                        color = if (success) AccentGreen else CatError,
                                        shape = CircleShape
                                    )
                            )
                            Spacer(modifier = Modifier.width(6.dp))
                            Text(
                                text = if (success) "CONNECTED (${latency}ms)" else "UNREACHABLE",
                                fontFamily = FontFamily.Monospace,
                                fontSize = 11.sp,
                                fontWeight = FontWeight.Bold,
                                color = if (success) AccentGreen else CatError
                            )
                        }
                    }
                }

                Spacer(modifier = Modifier.height(24.dp))

                // Action Buttons
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.End,
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    TextButton(onClick = onDismiss) {
                        Text(
                            text = "CANCEL",
                            fontFamily = FontFamily.Monospace,
                            color = TextSecondary,
                            fontSize = 12.sp
                        )
                    }
                    Spacer(modifier = Modifier.width(12.dp))
                    Button(
                        onClick = {
                            onSave(ipInput.trim())
                            onDismiss()
                        },
                        colors = ButtonDefaults.buttonColors(
                            containerColor = NeonCyan,
                            contentColor = BackgroundDark
                        )
                    ) {
                        Text(
                            text = "SAVE & CONNECT",
                            fontFamily = FontFamily.Monospace,
                            fontWeight = FontWeight.Bold,
                            fontSize = 12.sp
                        )
                    }
                }
            }
        }
    }
}

@Composable
private fun PortBadge(
    label: String,
    port: String,
    modifier: Modifier = Modifier
) {
    Surface(
        modifier = modifier,
        shape = RoundedCornerShape(8.dp),
        color = BackgroundDark,
        border = BorderStroke(1.dp, CardBorder)
    ) {
        Column(modifier = Modifier.padding(10.dp)) {
            Text(
                text = label,
                fontSize = 9.sp,
                fontFamily = FontFamily.Monospace,
                color = TextSecondary
            )
            Spacer(modifier = Modifier.height(2.dp))
            Text(
                text = ":$port",
                fontSize = 13.sp,
                fontFamily = FontFamily.Monospace,
                fontWeight = FontWeight.Bold,
                color = NeonCyan
            )
        }
    }
}
