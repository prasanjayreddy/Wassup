package com.voicemessage

import android.content.Context
import com.voicemessage.data.CommunicationProfile

/** Small on-device profile store; no conversation content is persisted here. */
class ProfileStore(context: Context) {
    private val prefs = context.getSharedPreferences("voice_profile", Context.MODE_PRIVATE)
    fun isOnboarded() = prefs.getBoolean("onboarded", false)
    fun complete(name: String, username: String, language: String) = prefs.edit().putBoolean("onboarded", true).putString("name", name).putString("username", username).putString("language", language).apply()
    fun recordSuggestionSelection(text: String) {
        val emoji = if (text.any { it.code > 10_000 }) 1 else 0
        prefs.edit().putInt("ai_selections", prefs.getInt("ai_selections", 0) + 1).putInt("emoji_selections", prefs.getInt("emoji_selections", 0) + emoji).apply()
    }
    fun recordSentMessage(text: String) {
        val trimmed = text.trim()
        val words = trimmed.lowercase().split(Regex("\\s+")).filter { it.isNotBlank() }
        prefs.edit()
            .putInt("sent_messages", prefs.getInt("sent_messages", 0) + 1)
            .putInt("sent_with_emoji", prefs.getInt("sent_with_emoji", 0) + if (trimmed.any { it.code > 10_000 }) 1 else 0)
            .putString("last_common_word", words.firstOrNull { it.length > 2 } ?: prefs.getString("last_common_word", "bro"))
            .apply()
    }
    fun selectionCount() = prefs.getInt("ai_selections", 0)
    fun profile(): CommunicationProfile {
        val sent = prefs.getInt("sent_messages", 0)
        val withEmoji = prefs.getInt("sent_with_emoji", 0)
        return CommunicationProfile(
            emojiFrequency = if (sent > 0 && withEmoji * 2 >= sent) "high" else "medium",
            commonWords = listOf(prefs.getString("last_common_word", "bro") ?: "bro", "yeah", "got it")
        )
    }
}
