package com.nexus.voice.config

import android.content.Context
import android.content.SharedPreferences

class NexusPreferences(context: Context) {

    private val prefs: SharedPreferences =
        context.getSharedPreferences("nexus_voice_tab_prefs", Context.MODE_PRIVATE)

    var serverIp: String
        get() = prefs.getString(KEY_SERVER_IP, "192.168.1.100") ?: "192.168.1.100"
        set(value) = prefs.edit().putString(KEY_SERVER_IP, value.trim()).apply()

    var dashboardPort: Int
        get() = prefs.getInt(KEY_DASHBOARD_PORT, 11882)
        set(value) = prefs.edit().putInt(KEY_DASHBOARD_PORT, value).apply()

    var runtimePort: Int
        get() = prefs.getInt(KEY_RUNTIME_PORT, 8765)
        set(value) = prefs.edit().putInt(KEY_RUNTIME_PORT, value).apply()

    var isZenMode: Boolean
        get() = prefs.getBoolean(KEY_ZEN_MODE, false)
        set(value) = prefs.edit().putBoolean(KEY_ZEN_MODE, value).apply()

    var isDebugMode: Boolean
        get() = prefs.getBoolean(KEY_DEBUG_MODE, false)
        set(value) = prefs.edit().putBoolean(KEY_DEBUG_MODE, value).apply()

    companion object {
        private const val KEY_SERVER_IP = "server_ip"
        private const val KEY_DASHBOARD_PORT = "dashboard_port"
        private const val KEY_RUNTIME_PORT = "runtime_port"
        private const val KEY_ZEN_MODE = "zen_mode"
        private const val KEY_DEBUG_MODE = "debug_mode"
    }
}
