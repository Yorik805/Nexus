package com.nexus.voice.model

data class BackgroundTaskItem(
    val id: String,
    val name: String,
    val type: String,      // e.g. "CRON", "DAEMON", "TIMER"
    val status: String,    // e.g. "RUNNING", "IDLE", "SCHEDULED"
    val intervalOrNext: String
)
