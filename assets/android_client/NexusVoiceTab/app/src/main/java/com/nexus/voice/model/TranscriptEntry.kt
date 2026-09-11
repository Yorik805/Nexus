package com.nexus.voice.model

import java.util.UUID

data class TranscriptEntry(
    val id: String = UUID.randomUUID().toString(),
    val text: String,
    val isUser: Boolean,
    val timestamp: Long = System.currentTimeMillis()
)
