package com.nexus.voice.ui.components

import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.LazyRow
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.lazy.rememberLazyListState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.nexus.voice.model.EventCategory
import com.nexus.voice.model.NexusEvent
import com.nexus.voice.ui.theme.*

@Composable
fun EventMonitorPanel(
    events: List<NexusEvent>,
    rawTranscript: String,
    isDebugMode: Boolean,
    selectedCategory: EventCategory?,
    autoScroll: Boolean,
    onToggleAutoScroll: () -> Unit,
    onSelectCategory: (EventCategory?) -> Unit,
    modifier: Modifier = Modifier
) {
    val filteredEvents = if (selectedCategory == null) {
        events
    } else {
        events.filter { it.category == selectedCategory }
    }

    val displayEvents = filteredEvents.reversed()
    val listState = rememberLazyListState()

    LaunchedEffect(displayEvents.size, autoScroll) {
        if (autoScroll && displayEvents.isNotEmpty()) {
            listState.animateScrollToItem(0)
        }
    }

    Surface(
        modifier = modifier.fillMaxHeight(),
        shape = RoundedCornerShape(12.dp),
        color = SurfaceDark.copy(alpha = 0.85f),
        border = BorderStroke(1.dp, if (isDebugMode) CatValidator.copy(alpha = 0.4f) else CardBorder)
    ) {
        Column(modifier = Modifier.fillMaxSize().padding(12.dp)) {
            // Header
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically
            ) {
                Row(verticalAlignment = Alignment.CenterVertically) {
                    Box(
                        modifier = Modifier
                            .size(7.dp)
                            .background(
                                color = if (isDebugMode) CatValidator else NeonCyan,
                                shape = CircleShape
                            )
                    )
                    Spacer(modifier = Modifier.width(8.dp))
                    Text(
                        text = if (isDebugMode) "DEBUG EVENT FLOW" else "NEXUS EVENTS",
                        fontFamily = FontFamily.Monospace,
                        fontWeight = FontWeight.Bold,
                        fontSize = 11.sp,
                        letterSpacing = 1.sp,
                        color = if (isDebugMode) CatValidator else TextPrimary
                    )
                }

                Row(verticalAlignment = Alignment.CenterVertically) {
                    // Auto-Scroll indicator / button
                    Surface(
                        shape = RoundedCornerShape(4.dp),
                        color = if (autoScroll) CatResult.copy(alpha = 0.15f) else CardBorder,
                        modifier = Modifier.clickable { onToggleAutoScroll() }
                    ) {
                        Row(
                            verticalAlignment = Alignment.CenterVertically,
                            modifier = Modifier.padding(horizontal = 6.dp, vertical = 3.dp)
                        ) {
                            Box(
                                modifier = Modifier
                                    .size(5.dp)
                                    .background(
                                        color = if (autoScroll) CatResult else TextSecondary,
                                        shape = CircleShape
                                    )
                            )
                            Spacer(modifier = Modifier.width(5.dp))
                            Text(
                                text = "AUTO-SCROLL",
                                fontFamily = FontFamily.Monospace,
                                fontSize = 9.sp,
                                fontWeight = FontWeight.Bold,
                                color = if (autoScroll) CatResult else TextSecondary
                            )
                        }
                    }

                    Spacer(modifier = Modifier.width(8.dp))

                    Surface(
                        shape = RoundedCornerShape(4.dp),
                        color = CardBorder
                    ) {
                        Text(
                            text = "${displayEvents.size} EVENTS",
                            fontFamily = FontFamily.Monospace,
                            fontSize = 10.sp,
                            fontWeight = FontWeight.SemiBold,
                            color = CatResult,
                            modifier = Modifier.padding(horizontal = 6.dp, vertical = 2.dp)
                        )
                    }
                }
            }

            Spacer(modifier = Modifier.height(8.dp))

            if (!isDebugMode) {
                // Category Filter Pills (Matching Web Client)
                LazyRow(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.spacedBy(6.dp)
                ) {
                    item {
                        FilterChip(
                            label = "ALL",
                            isSelected = selectedCategory == null,
                            color = NeonCyan,
                            onClick = { onSelectCategory(null) }
                        )
                    }
                    items(EventCategory.values()) { cat ->
                        FilterChip(
                            label = cat.label,
                            isSelected = selectedCategory == cat,
                            color = cat.color,
                            onClick = { onSelectCategory(cat) }
                        )
                    }
                }

                Spacer(modifier = Modifier.height(8.dp))

                // Normal Event List
                if (displayEvents.isEmpty()) {
                    Box(
                        modifier = Modifier
                            .fillMaxSize()
                            .background(BackgroundDark.copy(alpha = 0.5f), RoundedCornerShape(8.dp)),
                        contentAlignment = Alignment.Center
                    ) {
                        Text(
                            text = "Waiting for Nexus events… (polling live backend)",
                            fontFamily = FontFamily.Monospace,
                            fontSize = 11.sp,
                            color = TextSecondary.copy(alpha = 0.6f)
                        )
                    }
                } else {
                    LazyColumn(
                        state = listState,
                        modifier = Modifier.fillMaxSize(),
                        verticalArrangement = Arrangement.spacedBy(4.dp)
                    ) {
                        items(displayEvents, key = { it.id }) { event ->
                            NormalEventRow(event)
                        }
                    }
                }
            } else {
                // Debug Mode: Table format (TIME | TYPE | SOURCE | PAYLOAD)
                Column(modifier = Modifier.fillMaxSize()) {
                    // Table Header
                    Row(
                        modifier = Modifier
                            .fillMaxWidth()
                            .background(BackgroundDark, RoundedCornerShape(4.dp))
                            .padding(horizontal = 8.dp, vertical = 5.dp),
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        Text("TIME", fontFamily = FontFamily.Monospace, fontSize = 9.sp, fontWeight = FontWeight.Bold, color = TextSecondary, modifier = Modifier.width(60.dp))
                        Text("TYPE", fontFamily = FontFamily.Monospace, fontSize = 9.sp, fontWeight = FontWeight.Bold, color = TextSecondary, modifier = Modifier.width(90.dp))
                        Text("SOURCE", fontFamily = FontFamily.Monospace, fontSize = 9.sp, fontWeight = FontWeight.Bold, color = TextSecondary, modifier = Modifier.width(80.dp))
                        Text("PAYLOAD", fontFamily = FontFamily.Monospace, fontSize = 9.sp, fontWeight = FontWeight.Bold, color = TextSecondary, modifier = Modifier.weight(1f))
                    }

                    Spacer(modifier = Modifier.height(4.dp))

                    // Table Rows
                    Box(modifier = Modifier.weight(1f)) {
                        if (displayEvents.isEmpty()) {
                            Box(modifier = Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
                                Text("No debug events received yet.", fontFamily = FontFamily.Monospace, fontSize = 10.sp, color = TextSecondary.copy(alpha = 0.6f))
                            }
                        } else {
                            LazyColumn(state = listState, modifier = Modifier.fillMaxSize()) {
                                items(displayEvents, key = { it.id }) { event ->
                                    DebugTableRow(event)
                                }
                            }
                        }
                    }

                    Spacer(modifier = Modifier.height(6.dp))

                    // Raw STT output footer in debug mode
                    Surface(
                        shape = RoundedCornerShape(6.dp),
                        color = BackgroundDark,
                        border = BorderStroke(1.dp, CardBorder),
                        modifier = Modifier.fillMaxWidth().height(48.dp)
                    ) {
                        Row(
                            modifier = Modifier.padding(horizontal = 8.dp, vertical = 6.dp),
                            verticalAlignment = Alignment.CenterVertically
                        ) {
                            Text(
                                text = "RAW STT:",
                                fontFamily = FontFamily.Monospace,
                                fontSize = 9.sp,
                                fontWeight = FontWeight.Bold,
                                color = CatValidator
                            )
                            Spacer(modifier = Modifier.width(6.dp))
                            Text(
                                text = if (rawTranscript.isNotBlank()) rawTranscript else "Awaiting speech…",
                                fontFamily = FontFamily.Monospace,
                                fontSize = 10.sp,
                                color = if (rawTranscript.isNotBlank()) TextPrimary else TextSecondary.copy(alpha = 0.5f),
                                maxLines = 1,
                                overflow = TextOverflow.Ellipsis
                            )
                        }
                    }
                }
            }
        }
    }
}

@Composable
private fun FilterChip(
    label: String,
    isSelected: Boolean,
    color: Color,
    onClick: () -> Unit
) {
    Surface(
        shape = RoundedCornerShape(4.dp),
        color = if (isSelected) color.copy(alpha = 0.2f) else BackgroundDark,
        border = BorderStroke(1.dp, if (isSelected) color else CardBorder),
        modifier = Modifier.clickable { onClick() }
    ) {
        Text(
            text = label,
            fontFamily = FontFamily.Monospace,
            fontSize = 9.sp,
            fontWeight = if (isSelected) FontWeight.Bold else FontWeight.Medium,
            color = if (isSelected) color else TextSecondary,
            modifier = Modifier.padding(horizontal = 7.dp, vertical = 3.dp)
        )
    }
}

@Composable
private fun NormalEventRow(event: NexusEvent) {
    Surface(
        shape = RoundedCornerShape(6.dp),
        color = BackgroundDark.copy(alpha = 0.8f),
        border = BorderStroke(1.dp, CardBorder.copy(alpha = 0.6f))
    ) {
        Column(modifier = Modifier.fillMaxWidth().padding(horizontal = 8.dp, vertical = 6.dp)) {
            Row(verticalAlignment = Alignment.CenterVertically) {
                if (event.time.isNotBlank()) {
                    Text(
                        text = event.time,
                        fontFamily = FontFamily.Monospace,
                        fontSize = 9.sp,
                        color = TextSecondary.copy(alpha = 0.7f)
                    )
                    Spacer(modifier = Modifier.width(6.dp))
                }

                Surface(
                    shape = RoundedCornerShape(3.dp),
                    color = event.category.color.copy(alpha = 0.15f)
                ) {
                    Text(
                        text = event.category.label,
                        fontFamily = FontFamily.Monospace,
                        fontSize = 8.sp,
                        fontWeight = FontWeight.Bold,
                        color = event.category.color,
                        modifier = Modifier.padding(horizontal = 4.dp, vertical = 1.dp)
                    )
                }

                Spacer(modifier = Modifier.width(6.dp))

                Text(
                    text = event.label,
                    fontFamily = FontFamily.Monospace,
                    fontSize = 10.sp,
                    fontWeight = FontWeight.SemiBold,
                    color = TextPrimary,
                    maxLines = 1,
                    overflow = TextOverflow.Ellipsis
                )
            }

            if (event.description.isNotBlank()) {
                Spacer(modifier = Modifier.height(2.dp))
                Text(
                    text = event.description,
                    fontFamily = FontFamily.Monospace,
                    fontSize = 9.sp,
                    color = TextSecondary,
                    maxLines = 2,
                    overflow = TextOverflow.Ellipsis,
                    modifier = Modifier.padding(start = 4.dp)
                )
            }
        }
    }
}

@Composable
private fun DebugTableRow(event: NexusEvent) {
    Row(
        modifier = Modifier
            .fillMaxWidth()
            .padding(horizontal = 8.dp, vertical = 4.dp),
        verticalAlignment = Alignment.CenterVertically
    ) {
        Text(
            text = if (event.time.isNotBlank()) event.time else "—",
            fontFamily = FontFamily.Monospace,
            fontSize = 9.sp,
            color = TextSecondary.copy(alpha = 0.7f),
            modifier = Modifier.width(60.dp),
            maxLines = 1
        )
        Text(
            text = event.kind.ifBlank { event.label },
            fontFamily = FontFamily.Monospace,
            fontSize = 9.sp,
            fontWeight = FontWeight.SemiBold,
            color = event.category.color,
            modifier = Modifier.width(90.dp),
            maxLines = 1,
            overflow = TextOverflow.Ellipsis
        )
        Text(
            text = event.source.ifBlank { "—" },
            fontFamily = FontFamily.Monospace,
            fontSize = 9.sp,
            color = TextSecondary,
            modifier = Modifier.width(80.dp),
            maxLines = 1,
            overflow = TextOverflow.Ellipsis
        )
        Text(
            text = event.message.ifBlank { event.description },
            fontFamily = FontFamily.Monospace,
            fontSize = 9.sp,
            color = TextPrimary,
            modifier = Modifier.weight(1f),
            maxLines = 1,
            overflow = TextOverflow.Ellipsis
        )
    }
}
