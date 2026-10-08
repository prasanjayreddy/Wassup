package com.voicemessage.data

import java.time.Instant

enum class RelationshipType { CLOSE_FRIEND, FAMILY, COLLEAGUE, MANAGER, PARTNER, ACQUAINTANCE }
enum class MessageStatus { SENDING, SENT, READ }

data class CommunicationProfile(
    val preferredMessageLength: String = "short",
    val capitalization: String = "mostly_lowercase",
    val emojiFrequency: String = "high",
    val commonEmojis: List<String> = listOf("😂", "😭", "🤝"),
    val languageStyle: String = "hinglish",
    val preferredTone: String = "casual",
    val commonWords: List<String> = listOf("bro", "yeah", "got it")
)

data class User(val id: String, val username: String, val displayName: String, val preferredLanguage: String, val profile: CommunicationProfile)
data class Conversation(val id: String, val title: String, val avatar: String, val relationship: RelationshipType, val participantId: String, val unreadCount: Int = 0, val typing: Boolean = false)
data class Message(val id: String, val conversationId: String, val senderId: String, val text: String, val timestamp: Instant, val status: MessageStatus = MessageStatus.SENT)

data class AiRequestContext(val conversation: Conversation, val messages: List<Message>, val profile: CommunicationProfile, val draft: String = "", val tone: String? = null)
data class AiSuggestion(val text: String, val reason: String = "")

object DemoData {
    const val ME = "me"
    val user = User(ME, "you", "Aman", "English", CommunicationProfile())
    val conversations = listOf(
        Conversation("rahul", "Rahul", "R", RelationshipType.CLOSE_FRIEND, "rahul", 1),
        Conversation("priya", "Priya", "P", RelationshipType.COLLEAGUE, "priya"),
        Conversation("family", "Family", "F", RelationshipType.FAMILY, "family")
    )
    private val now = Instant.now()
    val messages = listOf(
        Message("r1", "rahul", "rahul", "bro what are you doing tonight?", now.minusSeconds(7200)),
        Message("r2", "rahul", ME, "nothing much bro, what's up?", now.minusSeconds(7100)),
        Message("r3", "rahul", "rahul", "we're going out", now.minusSeconds(3600)),
        Message("r4", "rahul", "rahul", "bro are you coming tomorrow?", now.minusSeconds(180)),
        Message("p1", "priya", "priya", "Hey, did you finish the presentation?", now.minusSeconds(1500)),
        Message("f1", "family", "family", "Where are you? Come home early today.", now.minusSeconds(4500))
    )
}
