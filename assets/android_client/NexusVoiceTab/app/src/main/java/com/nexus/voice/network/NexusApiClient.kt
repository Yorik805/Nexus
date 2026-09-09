package com.nexus.voice.network

import android.util.Log
import com.nexus.voice.model.EventClassifier
import com.nexus.voice.model.NexusEvent
import kotlinx.coroutines.*
import org.json.JSONObject
import java.io.BufferedReader
import java.io.IOException
import java.net.HttpURLConnection
import java.net.URL

class NexusApiClient {

    private val TAG = "NexusApiClient"
    private var pollingJob: Job? = null
    private var activeMessageJob: Job? = null
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

    suspend fun sendMessage(
        serverIp: String,
        runtimePort: Int,
        text: String,
        deviceId: String = "nexus-voice-tab"
    ): Result<String> = withContext(Dispatchers.IO) {
        // Cut off previous in-flight request if a new one is sent
        activeMessageJob?.cancel()

        val cleanIp = serverIp.trim().removePrefix("http://").removePrefix("https://").removeSuffix("/")
        val urlStr = "http://$cleanIp:$runtimePort/message"

        var connection: HttpURLConnection? = null
        try {
            val url = URL(urlStr)
            val jsonPayload = JSONObject().apply {
                put("device_id", deviceId)
                put("text", text)
            }.toString()

            Log.d(TAG, "Sending message to $urlStr: $text")

            connection = (url.openConnection() as HttpURLConnection).apply {
                requestMethod = "POST"
                connectTimeout = 5000
                readTimeout = 35000 // LLM inference may take several seconds
                setRequestProperty("Content-Type", "application/json")
                setRequestProperty("Accept", "application/json")
                doOutput = true
                useCaches = false
            }

            connection.outputStream.use { os ->
                os.write(jsonPayload.toByteArray(Charsets.UTF_8))
                os.flush()
            }

            val responseCode = connection.responseCode
            Log.d(TAG, "Message response code: $responseCode")

            if (responseCode in 200..299) {
                val responseText = connection.inputStream.bufferedReader().use(BufferedReader::readText)
                Log.d(TAG, "Message response body: $responseText")
                val reply = extractReplyText(responseText)
                Result.success(reply)
            } else {
                val errText = connection.errorStream?.bufferedReader()?.use(BufferedReader::readText) ?: "HTTP $responseCode"
                Result.failure(IOException("Server returned $responseCode: $errText"))
            }
        } catch (e: Exception) {
            Log.e(TAG, "Failed to send message to Nexus", e)
            Result.failure(e)
        } finally {
            connection?.disconnect()
        }
    }

    private fun extractReplyText(jsonString: String): String {
        try {
            val root = JSONObject(jsonString)

            // 1. Check pending_messages list
            val pendingArray = root.optJSONArray("pending_messages") ?: root.optJSONArray("pending")
            if (pendingArray != null && pendingArray.length() > 0) {
                for (i in 0 until pendingArray.length()) {
                    val item = pendingArray.optJSONObject(i) ?: continue
                    val directMsg = item.optString("message", "")
                    if (directMsg.isNotBlank()) return directMsg

                    val event = item.optJSONObject("event")
                    if (event != null) {
                        val data = event.optJSONObject("data")
                        val dataMsg = data?.optString("message", "") ?: data?.optString("text", "")
                        if (!dataMsg.isNullOrBlank()) return dataMsg
                    }
                }
            }

            // 2. Check result.response.text
            val result = root.optJSONObject("result") ?: root
            val response = result.optJSONObject("response") ?: result
            val text = response.optString("text", "")
            if (text.isNotBlank()) return text

            val msg = result.optString("message", "")
            if (msg.isNotBlank()) return msg

            return root.optString("message", "")
        } catch (e: Exception) {
            Log.w(TAG, "Failed to extract reply text", e)
            return ""
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
        activeMessageJob?.cancel()
        scope.cancel()
    }
}
