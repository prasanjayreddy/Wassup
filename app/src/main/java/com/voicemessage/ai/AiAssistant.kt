package com.voicemessage.ai

import com.voicemessage.data.*

/** No provider key lives in the client. A network implementation can call the backend API. */
interface AiAssistant {
    suspend fun reply(context: AiRequestContext): List<AiSuggestion>
    suspend fun rewrite(context: AiRequestContext): String
    suspend fun changeTone(context: AiRequestContext): String
    suspend fun translate(context: AiRequestContext): String
}

/** Deterministic offline behavior keeps the prototype demonstrable without sending private messages anywhere. */
class LocalAiAssistant : AiAssistant {
    override suspend fun reply(context: AiRequestContext): List<AiSuggestion> = (when (context.conversation.relationship) {
        RelationshipType.CLOSE_FRIEND -> listOf("yeah bro I'll be there 😂", "can't make it tomorrow bro, got some work", "what time are you guys meeting?")
        RelationshipType.COLLEAGUE, RelationshipType.MANAGER -> listOf("Yep, I’ll send it shortly.", "Almost done — I’ll share it in a bit.", "I’m on it, will update you soon.")
        RelationshipType.FAMILY -> listOf("on my way, will be home soon", "yeah coming in a bit", "sorry, got held up — leaving now")
        else -> listOf("yeah, sounds good", "I might be a little late", "what time works for you?")
    }).map { AiSuggestion(matchProfile(it, context.profile)) }

    override suspend fun rewrite(context: AiRequestContext): String = naturalize(context.draft, context.conversation.relationship)
    override suspend fun changeTone(context: AiRequestContext): String {
        val raw = naturalize(context.draft, context.conversation.relationship)
        return when (context.tone) {
            "Professional" -> raw.replace("bro", "").replace("😂", "").replaceFirstChar { it.uppercase() }
            "Polite" -> "Hey, $raw"
            "Funny" -> "$raw 😂"
            "Short" -> raw.substringBefore(" because").substringBefore(",")
            "Friendly" -> "$raw :)"
            else -> raw
        }.trim()
    }
    override suspend fun translate(context: AiRequestContext): String {
        val input = context.draft.lowercase()
        return when {
            "repu" in input && "late" in input -> "bro I'll be a little late tomorrow, there's a lot of traffic"
            "kal" in input && "late" in input -> "I'll be a little late tomorrow, there's a lot of traffic"
            "nahi" in input && "aa" in input -> "I can't make it today"
            else -> "${context.draft.trim()}" // Backend provider handles broad translation in real builds.
        }
    }
    private fun naturalize(value: String, relationship: RelationshipType): String {
        val lower = value.trim().lowercase()
        return when {
            "cannot come tomorrow" in lower || "can't come tomorrow" in lower -> if (relationship == RelationshipType.CLOSE_FRIEND) "can't make it tomorrow bro, got some work" else "I can't make it tomorrow, I have some work."
            "i will be late" in lower -> if (relationship == RelationshipType.CLOSE_FRIEND) "gonna be a little late bro" else "I’ll be a little late."
            else -> value.trim()
        }
    }
    private fun matchProfile(text: String, profile: CommunicationProfile): String {
        var styled = text
        if (profile.emojiFrequency == "low") styled = styled.replace("😂", "").trim()
        if (profile.capitalization == "sentence_case") styled = styled.replaceFirstChar { it.uppercase() }
        return styled
    }
}
