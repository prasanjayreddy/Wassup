package com.voicemessage.data

import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import java.time.Instant
import java.util.UUID

/** Interface is the seam for a REST/WebSocket backed repository in production. */
interface MessagingRepository {
    val conversations: StateFlow<List<Conversation>>
    val messages: StateFlow<List<Message>>
    fun send(conversationId: String, text: String): Message
    fun receive(conversationId: String, senderId: String, text: String)
}

class LocalMessagingRepository : MessagingRepository {
    private val _conversations = MutableStateFlow(DemoData.conversations)
    override val conversations = _conversations.asStateFlow()
    private val _messages = MutableStateFlow(DemoData.messages)
    override val messages = _messages.asStateFlow()

    override fun send(conversationId: String, text: String): Message {
        val message = Message(UUID.randomUUID().toString(), conversationId, DemoData.ME, text.trim(), Instant.now(), MessageStatus.SENT)
        _messages.value += message
        _conversations.value = _conversations.value.map { if (it.id == conversationId) it.copy(unreadCount = 0) else it }
        return message
    }
    override fun receive(conversationId: String, senderId: String, text: String) {
        _messages.value += Message(UUID.randomUUID().toString(), conversationId, senderId, text, Instant.now())
    }
}
