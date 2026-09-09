package com.nexus.voice.engine

data class WakeResult(
    val isDetected: Boolean,
    val trailingCommand: String = ""
)

object WakeWordDetector {

    private val PREFIXES = setOf("hey", "hi", "hello", "ok", "a", "the")
    // Acoustic and phonetic variants commonly recognized by Kaldi for "nexus" and "acces"
    private val TARGETS = setOf(
        "nexus", "nexas", "nexis", "nexes", "texas", "lexus",
        "acces", "access", "axis", "excess", "axes"
    )

    fun isWakeTarget(word: String): Boolean {
        val clean = word.lowercase().replace(Regex("[^a-z]"), "")
        return clean in TARGETS
    }

    fun detect(rawText: String): WakeResult {
        val words = rawText.trim().split(Regex("\\s+")).filter { it.isNotBlank() }
        if (words.isEmpty()) return WakeResult(false)

        for (i in words.indices) {
            val word = words[i].lowercase().replace(Regex("[^a-z]"), "")

            // Case 1: "hey nexus", "hi acces", "ok nexus", etc.
            if (word in PREFIXES && i + 1 < words.size) {
                val nextWord = words[i + 1].lowercase().replace(Regex("[^a-z]"), "")
                if (isWakeTarget(nextWord)) {
                    val trailing = words.drop(i + 2).joinToString(" ").trim()
                    return WakeResult(true, trailing)
                }
            }

            // Case 2: "nexus", "acces", etc. (direct single-word wake)
            if (isWakeTarget(word)) {
                val trailing = words.drop(i + 1).joinToString(" ").trim()
                return WakeResult(true, trailing)
            }
        }

        return WakeResult(false)
    }

    fun stripWakeWord(rawText: String): String {
        val words = rawText.trim().split(Regex("\\s+")).filter { it.isNotBlank() }
        for (i in words.indices) {
            val word = words[i].lowercase().replace(Regex("[^a-z]"), "")
            if (word in PREFIXES && i + 1 < words.size) {
                val nextWord = words[i + 1].lowercase().replace(Regex("[^a-z]"), "")
                if (isWakeTarget(nextWord)) {
                    return words.drop(i + 2).joinToString(" ").trim()
                }
            }
            if (isWakeTarget(word)) {
                return words.drop(i + 1).joinToString(" ").trim()
            }
        }
        return rawText.trim()
    }
}
