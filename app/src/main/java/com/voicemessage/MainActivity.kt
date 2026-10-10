package com.voicemessage

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.layout.ExperimentalLayoutApi
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material.icons.automirrored.filled.Send
import androidx.compose.material.icons.filled.Add
import androidx.compose.material.icons.filled.AttachFile
import androidx.compose.material.icons.filled.AutoAwesome
import androidx.compose.material.icons.filled.Close
import androidx.compose.material.icons.filled.EmojiEmotions
import androidx.compose.material.icons.filled.MoreVert
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.KeyboardCapitalization
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewmodel.compose.viewModel
import com.voicemessage.ai.PrivateBackendAiAssistant
import com.voicemessage.data.*
import kotlinx.coroutines.delay
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.launch
import java.time.ZoneId
import java.time.format.DateTimeFormatter

private val Ink = Color(0xFF17171B)
private val Purple = Color(0xFF6955D8)
private val SoftPurple = Color(0xFFEDEAFF)
private val Surface = Color(0xFFFAFAFC)

class ChatViewModel : ViewModel() {
    private val repo = LocalMessagingRepository()
    private val ai = PrivateBackendAiAssistant()
    val conversations: StateFlow<List<Conversation>> = repo.conversations
    val messages: StateFlow<List<Message>> = repo.messages
    fun send(id: String, text: String, scope: kotlinx.coroutines.CoroutineScope) {
        if (text.isBlank()) return
        repo.send(id, text)
        scope.launch { // demo inbound delivery; production Repository replaces this with WebSocket events
            delay(900)
            val conversation = conversations.value.first { it.id == id }
            if (conversation.relationship == RelationshipType.CLOSE_FRIEND) repo.receive(id, conversation.participantId, "nicee, see you then 🤝")
        }
    }
    suspend fun suggestions(context: AiRequestContext) = runCatching { ai.reply(context) }.getOrDefault(emptyList())
    suspend fun rewrite(context: AiRequestContext) = runCatching { ai.rewrite(context) }.getOrDefault("")
    suspend fun tone(context: AiRequestContext) = runCatching { ai.changeTone(context) }.getOrDefault("")
    suspend fun translate(context: AiRequestContext) = runCatching { ai.translate(context) }.getOrDefault("")
}

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContent { VoiceApp(ProfileStore(applicationContext)) }
    }
}

@Composable
private fun VoiceApp(profileStore: ProfileStore, vm: ChatViewModel = viewModel()) {
    var onboarded by remember { mutableStateOf(profileStore.isOnboarded()) }
    var selectedId by rememberSaveable { mutableStateOf<String?>(null) }
    MaterialTheme(colorScheme = lightColorScheme(primary = Purple, surface = Surface, onSurface = Ink)) {
        Surface(Modifier.fillMaxSize()) {
            if (!onboarded) Onboarding { name, username, language -> profileStore.complete(name, username, language); onboarded = true }
            else if (selectedId == null) HomeScreen(vm, profileStore) { selectedId = it }
            else {
                val conversation = vm.conversations.collectAsState().value.first { it.id == selectedId }
                ConversationScreen(vm, conversation, profileStore, onBack = { selectedId = null })
            }
        }
    }
}

@Composable
private fun Onboarding(onComplete: (String, String, String) -> Unit) {
    var name by remember { mutableStateOf("") }; var username by remember { mutableStateOf("") }; var language by remember { mutableStateOf("English") }
    Column(Modifier.fillMaxSize().padding(28.dp), verticalArrangement = Arrangement.SpaceBetween) {
        Column {
            Box(Modifier.size(48.dp).clip(RoundedCornerShape(16.dp)).background(Purple), contentAlignment = Alignment.Center) { Icon(Icons.Default.AutoAwesome, null, tint = Color.White) }
            Spacer(Modifier.height(36.dp))
            Text("Your conversations.\nYour voice.", fontSize = 31.sp, fontWeight = FontWeight.Bold, color = Ink, lineHeight = 37.sp)
            Spacer(Modifier.height(12.dp))
            Text("AI that learns how you communicate.", color = Color(0xFF6E6E78), fontSize = 16.sp)
            Spacer(Modifier.height(32.dp))
            OutlinedTextField(name, { name = it }, Modifier.fillMaxWidth(), label = { Text("Your name") }, singleLine = true, shape = RoundedCornerShape(14.dp))
            Spacer(Modifier.height(12.dp))
            OutlinedTextField(username, { username = it.replace(" ", "") }, Modifier.fillMaxWidth(), label = { Text("Username") }, prefix = { Text("@") }, singleLine = true, shape = RoundedCornerShape(14.dp))
            Spacer(Modifier.height(12.dp))
            OutlinedTextField(language, { language = it }, Modifier.fillMaxWidth(), label = { Text("Preferred language") }, singleLine = true, shape = RoundedCornerShape(14.dp))
        }
        Button(onClick = { onComplete(name.ifBlank { "Aman" }, username.ifBlank { "you" }, language) }, Modifier.fillMaxWidth().height(54.dp), shape = RoundedCornerShape(16.dp), colors = ButtonDefaults.buttonColors(containerColor = Purple)) { Text("Start messaging", fontWeight = FontWeight.SemiBold) }
    }
}

@Composable
private fun HomeScreen(vm: ChatViewModel, profileStore: ProfileStore, onOpen: (String) -> Unit) {
    val conversations by vm.conversations.collectAsState()
    val messages by vm.messages.collectAsState()
    var profileOpen by remember { mutableStateOf(false) }
    Column(Modifier.fillMaxSize().background(Surface).statusBarsPadding()) {
        Row(Modifier.fillMaxWidth().padding(20.dp, 18.dp, 20.dp, 8.dp), verticalAlignment = Alignment.CenterVertically) {
            Column(Modifier.weight(1f)) { Text("Messages", fontSize = 29.sp, fontWeight = FontWeight.Bold); Text("Your voice, amplified", color = Color(0xFF777780)) }
            Box(Modifier.size(40.dp).clip(CircleShape).background(SoftPurple).clickable { profileOpen = true }, contentAlignment = Alignment.Center) { Text("A", fontWeight = FontWeight.Bold, color = Purple) }
        }
        LazyColumn(contentPadding = PaddingValues(vertical = 8.dp)) {
            items(conversations, key = { it.id }) { c ->
                val last = messages.filter { it.conversationId == c.id }.maxByOrNull { it.timestamp }
                ConversationRow(c, last, onOpen)
            }
        }
    }
    if (profileOpen) ProfileSheet(profileStore) { profileOpen = false }
}

@Composable
private fun ConversationRow(c: Conversation, last: Message?, onOpen: (String) -> Unit) {
    Row(Modifier.fillMaxWidth().clickable { onOpen(c.id) }.padding(20.dp, 14.dp), verticalAlignment = Alignment.CenterVertically) {
        Avatar(c.avatar, Purple); Spacer(Modifier.width(14.dp))
        Column(Modifier.weight(1f)) {
            Text(c.title, fontWeight = FontWeight.SemiBold, fontSize = 17.sp)
            Text(last?.text ?: "No messages yet", maxLines = 1, overflow = TextOverflow.Ellipsis, color = Color(0xFF777780))
        }
        Column(horizontalAlignment = Alignment.End) {
            Text(last?.let { formatTime(it) } ?: "", fontSize = 12.sp, color = Color(0xFF85858E))
            if (c.unreadCount > 0) Box(Modifier.padding(top = 5.dp).size(19.dp).clip(CircleShape).background(Purple), contentAlignment = Alignment.Center) { Text(c.unreadCount.toString(), fontSize = 11.sp, color = Color.White) }
        }
    }
}

@Composable private fun Avatar(letter: String, color: Color) = Box(Modifier.size(50.dp).clip(CircleShape).background(color.copy(alpha = .14f)), contentAlignment = Alignment.Center) { Text(letter, color = color, fontWeight = FontWeight.Bold, fontSize = 18.sp) }

@Composable
private fun ConversationScreen(vm: ChatViewModel, conversation: Conversation, profileStore: ProfileStore, onBack: () -> Unit) {
    val allMessages by vm.messages.collectAsState(); val messages = allMessages.filter { it.conversationId == conversation.id }
    var draft by rememberSaveable(conversation.id) { mutableStateOf("") }
    var aiSheet by remember { mutableStateOf(false) }; val scope = rememberCoroutineScope()
    Column(Modifier.fillMaxSize().background(Surface).statusBarsPadding()) {
        Row(Modifier.fillMaxWidth().height(64.dp).padding(horizontal = 12.dp), verticalAlignment = Alignment.CenterVertically) {
            IconButton(onBack) { Icon(Icons.AutoMirrored.Filled.ArrowBack, "Back") }; Avatar(conversation.avatar, Purple); Spacer(Modifier.width(11.dp))
            Column(Modifier.weight(1f)) { Text(conversation.title, fontWeight = FontWeight.Bold, fontSize = 18.sp); Text(relationshipLabel(conversation.relationship), fontSize = 12.sp, color = Color(0xFF7B7B85)) }
            IconButton({}) { Icon(Icons.Default.MoreVert, "More") }
        }
        LazyColumn(Modifier.weight(1f).fillMaxWidth(), reverseLayout = true, contentPadding = PaddingValues(horizontal = 16.dp, vertical = 14.dp)) {
            items(messages.reversed(), key = { it.id }) { message -> MessageBubble(message, message.senderId == DemoData.ME) }
        }
        Composer(draft, { draft = it }, { aiSheet = true }) { profileStore.recordSentMessage(draft); vm.send(conversation.id, draft, scope); draft = "" }
    }
    if (aiSheet) AiSheet(conversation, messages, draft, vm, profileStore, onDismiss = { aiSheet = false }, onUse = { draft = it; aiSheet = false })
}

@Composable
private fun MessageBubble(message: Message, mine: Boolean) {
    Row(Modifier.fillMaxWidth().padding(vertical = 3.dp), horizontalArrangement = if (mine) Arrangement.End else Arrangement.Start) {
        Column(horizontalAlignment = if (mine) Alignment.End else Alignment.Start) {
            Text(message.text, Modifier.clip(RoundedCornerShape(if (mine) 18.dp else 18.dp)).background(if (mine) Purple else Color.White).padding(horizontal = 14.dp, vertical = 10.dp), color = if (mine) Color.White else Ink, fontSize = 16.sp)
            Text(formatTime(message), Modifier.padding(horizontal = 4.dp, vertical = 2.dp), fontSize = 10.sp, color = Color(0xFF92929B))
        }
    }
}

@Composable
private fun Composer(draft: String, onDraft: (String) -> Unit, onAi: () -> Unit, onSend: () -> Unit) {
    Row(Modifier.navigationBarsPadding().fillMaxWidth().padding(12.dp), verticalAlignment = Alignment.CenterVertically) {
        Surface(Modifier.weight(1f), color = Color.White, shape = RoundedCornerShape(24.dp), shadowElevation = 1.dp) {
            Row(Modifier.padding(start = 5.dp, end = 6.dp), verticalAlignment = Alignment.CenterVertically) {
                IconButton({}) { Icon(Icons.Default.AttachFile, "Attachment", tint = Color(0xFF777780)) }
                OutlinedTextField(draft, onDraft, Modifier.weight(1f), placeholder = { Text("Type a message...") }, maxLines = 4, colors = OutlinedTextFieldDefaults.colors(unfocusedBorderColor = Color.Transparent, focusedBorderColor = Color.Transparent), keyboardOptions = KeyboardOptions(capitalization = KeyboardCapitalization.Sentences))
                IconButton(onAi) { Icon(Icons.Default.AutoAwesome, "AI assist", tint = Purple) }
            }
        }
        Spacer(Modifier.width(8.dp)); FloatingActionButton(onSend, Modifier.size(48.dp), containerColor = if (draft.isBlank()) Color(0xFFDBD9E6) else Purple) { Icon(Icons.AutoMirrored.Filled.Send, "Send", tint = Color.White) }
    }
}

private enum class AiMode { MENU, REPLY, REWRITE, TONE, TRANSLATE }

@OptIn(ExperimentalMaterial3Api::class, ExperimentalLayoutApi::class)
@Composable
private fun AiSheet(
    conversation: Conversation,
    messages: List<Message>,
    draft: String,
    vm: ChatViewModel,
    profileStore: ProfileStore,
    onDismiss: () -> Unit,
    onUse: (String) -> Unit
) {
    var mode by remember { mutableStateOf(AiMode.MENU) }
    var result by remember { mutableStateOf<List<AiSuggestion>>(emptyList()) }
    var working by remember { mutableStateOf(false) }
    var input by remember { mutableStateOf(draft) }
    var chosenTone by remember { mutableStateOf("Casual") }
    val scope = rememberCoroutineScope()
    val context = { value: String = input, tone: String? = chosenTone -> AiRequestContext(conversation, messages, profileStore.profile(), value, tone) }

    ModalBottomSheet(onDismissRequest = onDismiss, containerColor = Color.White, sheetState = rememberModalBottomSheetState(skipPartiallyExpanded = true)) {
        Column(Modifier.fillMaxWidth().padding(horizontal = 22.dp).padding(bottom = 28.dp)) {
            Row(verticalAlignment = Alignment.CenterVertically) {
                Box(Modifier.size(36.dp).clip(RoundedCornerShape(12.dp)).background(SoftPurple), contentAlignment = Alignment.Center) { Icon(Icons.Default.AutoAwesome, null, tint = Purple, modifier = Modifier.size(19.dp)) }
                Spacer(Modifier.width(10.dp)); Column(Modifier.weight(1f)) { Text("Voice assist", fontSize = 19.sp, fontWeight = FontWeight.Bold); Text("Keeps it sounding like you", fontSize = 13.sp, color = Color(0xFF777780)) }
                if (mode != AiMode.MENU) IconButton({ mode = AiMode.MENU; result = emptyList() }) { Icon(Icons.Default.Close, "Close tool") }
            }
            Spacer(Modifier.height(20.dp))
            when (mode) {
                AiMode.MENU -> AiMenu { mode = it }
                AiMode.REPLY -> {
                    Text("Reply ideas", fontWeight = FontWeight.SemiBold)
                    Spacer(Modifier.height(8.dp))
                    LaunchedEffect(Unit) { working = true; result = vm.suggestions(context()); working = false }
                    Suggestions(result, working) { profileStore.recordSuggestionSelection(it); onUse(it) }
                }
                AiMode.REWRITE -> TransformTool("Rewrite", "Make your draft sound more natural", input, { input = it }, working, result.firstOrNull()?.text) {
                    scope.launch { working = true; result = listOf(AiSuggestion(vm.rewrite(context()))); working = false }
                } { onUse(it) }
                AiMode.TONE -> {
                    Text("Change tone", fontWeight = FontWeight.SemiBold); Spacer(Modifier.height(10.dp))
                    FlowRow(horizontalArrangement = Arrangement.spacedBy(8.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) { listOf("Casual", "Friendly", "Polite", "Professional", "Funny", "Short").forEach { tone -> FilterChip(selected = chosenTone == tone, onClick = { chosenTone = tone }, label = { Text(tone) }) } }
                    TransformTool("", "", input, { input = it }, working, result.firstOrNull()?.text) { scope.launch { working = true; result = listOf(AiSuggestion(vm.tone(context()))); working = false } } { onUse(it) }
                }
                AiMode.TRANSLATE -> TransformTool("Translate naturally", "Telugu, Hindi, Hinglish → conversational English", input, { input = it }, working, result.firstOrNull()?.text) { scope.launch { working = true; result = listOf(AiSuggestion(vm.translate(context()))); working = false } } { onUse(it) }
            }
        }
    }
}

@Composable private fun AiMenu(open: (AiMode) -> Unit) {
    Text("What do you need?", fontWeight = FontWeight.SemiBold); Spacer(Modifier.height(8.dp))
    AiAction("Reply", "Three quick replies for this chat", Icons.Default.EmojiEmotions) { open(AiMode.REPLY) }
    AiAction("Rewrite", "Say it more naturally", Icons.Default.AutoAwesome) { open(AiMode.REWRITE) }
    AiAction("Tone", "Casual, polite, funny, short…", Icons.Default.Add) { open(AiMode.TONE) }
    AiAction("Translate", "Your thought, natural English", Icons.Default.EmojiEmotions) { open(AiMode.TRANSLATE) }
}
@Composable private fun AiAction(title: String, detail: String, icon: androidx.compose.ui.graphics.vector.ImageVector, click: () -> Unit) {
    Row(Modifier.fillMaxWidth().clip(RoundedCornerShape(14.dp)).clickable(click).padding(10.dp), verticalAlignment = Alignment.CenterVertically) { Box(Modifier.size(38.dp).clip(RoundedCornerShape(12.dp)).background(SoftPurple), contentAlignment = Alignment.Center) { Icon(icon, null, tint = Purple, modifier = Modifier.size(19.dp)) }; Spacer(Modifier.width(12.dp)); Column { Text(title, fontWeight = FontWeight.SemiBold); Text(detail, color = Color(0xFF777780), fontSize = 13.sp) } }
}
@Composable private fun Suggestions(result: List<AiSuggestion>, working: Boolean, use: (String) -> Unit) {
    if (working) { LinearProgressIndicator(Modifier.fillMaxWidth()); Text("Thinking in your voice…", Modifier.padding(vertical = 12.dp), color = Color(0xFF777780)) }
    result.forEach { suggestion -> Surface(Modifier.fillMaxWidth().padding(vertical = 5.dp).clickable { use(suggestion.text) }, shape = RoundedCornerShape(15.dp), color = Surface, border = ButtonDefaults.outlinedButtonBorder) { Text(suggestion.text, Modifier.padding(15.dp), fontSize = 16.sp) } }
}
@Composable private fun TransformTool(title: String, subtitle: String, input: String, update: (String) -> Unit, working: Boolean, output: String?, generate: () -> Unit, use: (String) -> Unit) {
    if (title.isNotBlank()) { Text(title, fontWeight = FontWeight.SemiBold); if (subtitle.isNotBlank()) Text(subtitle, color = Color(0xFF777780), fontSize = 13.sp); Spacer(Modifier.height(10.dp)) }
    OutlinedTextField(input, update, Modifier.fillMaxWidth(), placeholder = { Text("Type your thought…") }, minLines = 2, shape = RoundedCornerShape(14.dp))
    Button(generate, Modifier.padding(top = 10.dp).fillMaxWidth(), enabled = input.isNotBlank() && !working, colors = ButtonDefaults.buttonColors(containerColor = Purple)) { if (working) CircularProgressIndicator(Modifier.size(18.dp), color = Color.White, strokeWidth = 2.dp) else Text("Generate") }
    output?.let { Spacer(Modifier.height(12.dp)); Text("Your voice", fontSize = 13.sp, color = Color(0xFF777780)); Surface(Modifier.fillMaxWidth().padding(top = 4.dp).clickable { use(it) }, color = SoftPurple, shape = RoundedCornerShape(14.dp)) { Text(it, Modifier.padding(14.dp), color = Ink) } }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable private fun ProfileSheet(profileStore: ProfileStore, dismiss: () -> Unit) {
    ModalBottomSheet(onDismissRequest = dismiss, containerColor = Color.White) {
        val profile = profileStore.profile()
        Column(Modifier.fillMaxWidth().padding(24.dp).padding(bottom = 28.dp)) {
            Text("Your communication style", fontWeight = FontWeight.Bold, fontSize = 20.sp)
            Text("Built from choices you make in Voice. You stay in control.", Modifier.padding(top = 5.dp), color = Color(0xFF72727C), fontSize = 14.sp)
            Spacer(Modifier.height(18.dp))
            StyleLine("Preferred tone", profile.preferredTone.replaceFirstChar { it.uppercase() })
            StyleLine("Message length", profile.preferredMessageLength.replaceFirstChar { it.uppercase() })
            StyleLine("Language mix", profile.languageStyle.replaceFirstChar { it.uppercase() })
            StyleLine("Usual emojis", profile.commonEmojis.joinToString("  "))
            StyleLine("AI choices recorded", profileStore.selectionCount().toString())
            Text("Only style signals are stored locally in this prototype — not prompts or message logs.", Modifier.padding(top = 16.dp), fontSize = 12.sp, color = Color(0xFF777780))
        }
    }
}
@Composable private fun StyleLine(label: String, value: String) = Row(Modifier.fillMaxWidth().padding(vertical = 9.dp), horizontalArrangement = Arrangement.SpaceBetween) { Text(label, color = Color(0xFF707079)); Text(value, fontWeight = FontWeight.Medium) }

private fun formatTime(message: Message): String = DateTimeFormatter.ofPattern("h:mm a").withZone(ZoneId.systemDefault()).format(message.timestamp)
private fun relationshipLabel(type: RelationshipType) = type.name.lowercase().replace('_', ' ').replaceFirstChar { it.uppercase() }
