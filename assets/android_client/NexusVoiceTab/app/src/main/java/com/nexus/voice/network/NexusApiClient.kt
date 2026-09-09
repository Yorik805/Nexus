package com.nexus.voice.network

import android.util.Log
import com.nexus.voice.model.EventClassifier
import com.nexus.voice.model.NexusEvent
import kotlinx.coroutines.*
import org.json.JSONObject
import java.io.BufferedReader
import java.io.InputStreamReader
import java.net.HttpURLConnection
import java.net.URL

class NexusApiClient {

    private val TAG = "NexusApiClient"
    private var pollingJob: Job? = null
    private val scope = CoroutineScope(Dispatchers.IO + SupervisorJob())

    fun startPolling(
        serverIp: String,
        port: Int,
        intervalMs: Long = 1500L,
        onUpdate: (isSuccess: Boolean, latencyMs: Long, events: List<NexusEvent>) -> Unit
    ) {
        stopPolling()
        if (serverIp.isBlank()) {
            onUpdate(false, 0L, emptyList())
            return
        }

        pollingJob = scope.launch {
            while (isActive) {
                val (success, latency, events) = pollOnce(serverIp, port)
                withContext(Dispatchers.Main) {
                    onUpdate(success, latency, events)
                }
                delay(intervalMs)
            }
        }
    }

    fun stopPolling() {
        pollingJob?.cancel()
        pollingJob = null
    }

    suspend fun testConnection(serverIp: String, port: Int): Pair<Boolean, Long> = withContext(Dispatchers.IO) {
        val (success, latency, _) = pollOnce(serverIp, port)
        Pair(success, latency)
    }

    private fun pollOnce(serverIp: String, port: Int): Triple<Boolean, Long, List<NexusEvent>> {
        val cleanIp = serverIp.trim().removePrefix("http://").removePrefix("https://").removeSuffix("/")
        val urlStr = "http://$cleanIp:$port/api/state"
        val startTime = System.currentTimeMillis()

        var connection: HttpURLConnection? = null
        return try {
            val url = URL(urlStr)
            connection = (url.openConnection() as HttpURLConnection).apply {
                requestMethod = "GET"
                connectTimeout = 2000
                readTimeout = 2000
                setRequestProperty("Accept", "application/json")
                useCaches = false
            }

            val responseCode = connection.responseCode
            val latency = System.currentTimeMillis() - startTime

            if (responseCode in 200..299) {
                val responseText = connection.inputStream.bufferedReader().use(BufferedReader::readText)
                val events = parseEvents(responseText)
                Triple(true, latency, events)
            } else {
                Triple(false, latency, emptyList())
            }
        } catch (e: Exception) {
            val latency = System.currentTimeMillis() - startTime
            Triple(false, latency, emptyList())
        } finally {
            connection?.disconnect()
        }
    }

    private fun parseEvents(jsonString: String): List<NexusEvent> {
        val result = mutableListOf<NexusEvent>()
        try {
            val root = JSONObject(jsonString)
            val eventsArray = root.optJSONArray("events") ?: return emptyList()

            for (i in 0 until eventsArray.length()) {
                val item = eventsArray.optJSONObject(i) ?: continue
                val time = item.optString("time", "")
                val kind = item.optString("kind", "")
                val source = item.optString("source", "")
                val message = item.optString("message", "")

                val category = EventClassifier.categorize(kind, source, message)
                val label = kind.ifBlank { "EVENT" }
                val description = if (source.isNotBlank()) "$source: $message" else message

                result.add(
                    NexusEvent(
                        id = "$time-$kind-$i",
                        timestamp = System.currentTimeMillis(),
                        category = category,
                        label = label,
                        description = description,
                        time = time,
                        kind = kind,
                        source = source,
                        message = message
                    )
                )
            }
        } catch (e: Exception) {
            Log.w(TAG, "Failed to parse Nexus events JSON", e)
        }
        return result
    }

    fun release() {
        stopPolling()
        scope.cancel()
    }
}
