package com.voicemessage.ai

import com.voicemessage.data.AiRequestContext
import com.voicemessage.data.AiSuggestion

/** The client carries no model credentials. Production implementation calls the private backend. */
interface AiAssistant {
    suspend fun reply(context: AiRequestContext): List<AiSuggestion>
    suspend fun rewrite(context: AiRequestContext): String
    suspend fun changeTone(context: AiRequestContext): String
    suspend fun translate(context: AiRequestContext): String
}

/**
 * Deliberately fails closed until Android is wired to the authenticated, self-hosted backend.
 * It never manufactures text or contacts a hosted model provider.
 */
class PrivateAiUnavailableException : IllegalStateException("Private AI service is not connected")
class PrivateBackendAiAssistant : AiAssistant {
    override suspend fun reply(context: AiRequestContext): List<AiSuggestion> = throw PrivateAiUnavailableException()
    override suspend fun rewrite(context: AiRequestContext): String = throw PrivateAiUnavailableException()
    override suspend fun changeTone(context: AiRequestContext): String = throw PrivateAiUnavailableException()
    override suspend fun translate(context: AiRequestContext): String = throw PrivateAiUnavailableException()
}
