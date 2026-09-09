package com.nexus.voice.model

import androidx.compose.ui.graphics.Color
import com.nexus.voice.ui.theme.CatError
import com.nexus.voice.ui.theme.CatEvent
import com.nexus.voice.ui.theme.CatOrchestrator
import com.nexus.voice.ui.theme.CatPlugin
import com.nexus.voice.ui.theme.CatResult
import com.nexus.voice.ui.theme.CatValidator

enum class EventCategory(val label: String, val color: Color) {
    EVENT("EVENT", CatEvent),
    ORCHESTRATOR("ORCHESTRATOR", CatOrchestrator),
    VALIDATOR("VALIDATOR", CatValidator),
    PLUGIN("PLUGIN", CatPlugin),
    RESULT("RESULT", CatResult),
    ERROR("ERROR", CatError)
}

data class NexusEvent(
    val id: String,
    val timestamp: Long,
    val category: EventCategory,
    val label: String,
    val description: String,
    val time: String = "",
    val kind: String = "",
    val source: String = "",
    val message: String = ""
)

object EventClassifier {
    fun categorize(kind: String, source: String, message: String): EventCategory {
        val normalized = kind.uppercase()
        val context = "$source $message".uppercase()

        return when {
            normalized == "ERROR" -> EventCategory.ERROR
            normalized == "EXECUTION_RESULT" || context.contains("TERMINAL") || context.contains("PLUGIN") -> EventCategory.PLUGIN
            normalized == "USER_MESSAGE" -> EventCategory.EVENT
            normalized.contains("ORCHESTR") || context.contains("ORCHESTR") || context.contains("PROVIDER") -> EventCategory.ORCHESTRATOR
            normalized.contains("VALID") || context.contains("VALID") -> EventCategory.VALIDATOR
            context.contains("EVENT COMPLETE") || context.contains("COMPLETED") -> EventCategory.RESULT
            else -> EventCategory.EVENT
        }
    }
}
