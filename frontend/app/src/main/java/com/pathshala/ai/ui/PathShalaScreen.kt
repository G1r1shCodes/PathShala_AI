package com.pathshala.ai.ui

import android.speech.tts.TextToSpeech
import androidx.compose.animation.*
import androidx.compose.animation.core.*
import androidx.compose.foundation.*
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.draw.scale
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.lifecycle.viewmodel.compose.viewModel
import com.pathshala.ai.model.LessonResponse
import com.pathshala.ai.ui.LoginViewModel
import java.util.Locale

// ─── COLOR PALETTE ────────────────────────────────────────────────────────────
val Saffron     = Color(0xFFFF6B00)
val DeepGreen   = Color(0xFF1B6B3A)
val LightGreen  = Color(0xFFE8F5E9)
val CardBg      = Color(0xFFFFFFFF)
val TextPrimary = Color(0xFF212121)
val TextMuted   = Color(0xFF757575)
val TopBarBg    = Color(0xFF121212)

// ─── MAIN SCREEN ─────────────────────────────────────────────────────────────
@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun PathShalaScreen(
    onMicClick: () -> Unit,
    onLogout: () -> Unit,
    vm: MainViewModel = viewModel(),
    loginVm: LoginViewModel = viewModel()
) {
    val uiState by vm.uiState.collectAsState()
    val transcript by vm.transcript.collectAsState()
    val userPhone by loginVm.userPhone.collectAsState()
    val context = LocalContext.current

    // TTS engine
    var tts by remember { mutableStateOf<TextToSpeech?>(null) }
    LaunchedEffect(Unit) {
        tts = TextToSpeech(context) { status ->
            if (status == TextToSpeech.SUCCESS) {
                tts?.setLanguage(Locale("hi", "IN"))
                    ?.let { result ->
                        if (result == TextToSpeech.LANG_MISSING_DATA) {
                            tts?.setLanguage(Locale.ENGLISH)
                        }
                    }
            }
        }
    }
    DisposableEffect(Unit) { onDispose { tts?.shutdown() } }

    var textInput by remember { mutableStateOf("") }

    Scaffold(
        topBar = {
            CenterAlignedTopAppBar(
                title = {
                    Text(
                        "PathShala AI",
                        color = Color.White,
                        fontWeight = FontWeight.Bold,
                        fontSize = 20.sp
                    )
                },
                actions = {
                    IconButton(onClick = onLogout) {
                        Icon(
                            Icons.Default.Logout,
                            contentDescription = "Logout",
                            tint = Color.White
                        )
                    }
                },
                colors = TopAppBarDefaults.centerAlignedTopAppBarColors(
                    containerColor = TopBarBg
                )
            )
        }
    ) { paddingValues ->
        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(paddingValues)
                .background(Color(0xFFF8F9FA))
                .verticalScroll(rememberScrollState())
                .padding(20.dp),
            horizontalAlignment = Alignment.CenterHorizontally
        ) {
            Text(
                "AI Co-Teacher for Rural India",
                fontSize = 14.sp,
                color = TextMuted,
                textAlign = TextAlign.Center,
                modifier = Modifier.padding(bottom = 24.dp)
            )

            // ── Text Input Card ──────────────────────────────────────────────────
            Card(
                modifier = Modifier.fillMaxWidth(),
                colors = CardDefaults.cardColors(containerColor = Color.White),
                elevation = CardDefaults.cardElevation(2.dp),
                shape = RoundedCornerShape(12.dp)
            ) {
                Column(modifier = Modifier.padding(16.dp)) {
                    OutlinedTextField(
                        value = textInput,
                        onValueChange = { textInput = it },
                        modifier = Modifier.fillMaxWidth(),
                        placeholder = { Text("अपना पाठ्यक्रम लिखें / Type your lesson request", fontSize = 14.sp) },
                        colors = OutlinedTextFieldDefaults.colors(
                            focusedBorderColor = Saffron,
                            unfocusedBorderColor = Color(0xFFE0E0E0)
                        ),
                        minLines = 3,
                        shape = RoundedCornerShape(8.dp)
                    )
                    Spacer(Modifier.height(16.dp))
                    Button(
                        onClick = {
                            // Pass user's login phone (with +91) for WhatsApp delivery
                            val whatsapp = "+91$userPhone".takeIf { userPhone.isNotBlank() }
                            vm.generateLesson(textInput, whatsappNumber = whatsapp)
                            textInput = ""
                        },
                        enabled = textInput.isNotBlank() && uiState !is UiState.Processing,
                        modifier = Modifier.fillMaxWidth().height(48.dp),
                        colors = ButtonDefaults.buttonColors(containerColor = Saffron),
                        shape = RoundedCornerShape(8.dp)
                    ) {
                        Icon(Icons.Default.AutoAwesome, contentDescription = null, modifier = Modifier.size(18.dp))
                        Spacer(Modifier.width(8.dp))
                        Text("Generate Lesson Plan", fontWeight = FontWeight.SemiBold)
                    }
                }
            }

            Spacer(Modifier.height(20.dp))
            Text("— या / OR —", color = TextMuted, fontSize = 12.sp)
            Spacer(Modifier.height(20.dp))

            // ── Mic Button ───────────────────────────────────────────────────────
            MicButton(
                state = uiState,
                onClick = onMicClick
            )

            Spacer(Modifier.height(12.dp))
            Text(
                when (uiState) {
                    is UiState.Listening   -> "🔴 सुन रहा हूँ... / Listening..."
                    is UiState.Processing  -> "⚙️ तैयार हो रहा है... / Processing..."
                    else                   -> "🎤 बोलने के लिए दबाएँ / Tap to speak"
                },
                color = if (uiState is UiState.Listening) Color.Red else TextMuted,
                fontSize = 14.sp,
                fontWeight = if (uiState is UiState.Listening) FontWeight.Bold else FontWeight.Normal
            )


            Spacer(Modifier.height(32.dp))

            // ── Loading ──────────────────────────────────────────────────────────
            AnimatedVisibility(
                visible = uiState is UiState.Processing,
                enter = fadeIn() + expandVertically(),
                exit = fadeOut() + shrinkVertically()
            ) {
                Column(horizontalAlignment = Alignment.CenterHorizontally) {
                    CircularProgressIndicator(color = Saffron, strokeWidth = 3.dp)
                    Spacer(Modifier.height(12.dp))
                    Text("Generating lesson plan...", color = Saffron, fontSize = 14.sp)
                }
            }

            // ── Success: Lesson Card ──────────────────────────────────────────────
            AnimatedVisibility(
                visible = uiState is UiState.Success,
                enter = slideInVertically { it / 2 } + fadeIn()
            ) {
                val lesson = (uiState as? UiState.Success)?.lesson
                if (lesson != null) {
                    LessonCard(
                        lesson = lesson,
                        onPlayClick = {
                            lesson.lesson_text?.let { text ->
                                tts?.speak(text, TextToSpeech.QUEUE_FLUSH, null, "LESSON_TTS")
                            }
                        }
                    )
                }
            }

            // ── Error ─────────────────────────────────────────────────────────────
            AnimatedVisibility(visible = uiState is UiState.Error) {
                val errMsg = (uiState as? UiState.Error)?.message ?: ""
                ErrorCard(message = errMsg, onRetry = { vm.retry() })
            }

            Spacer(Modifier.height(40.dp))
        }
    }
}

@Composable
fun MicButton(state: UiState, onClick: () -> Unit) {
    val isListening = state is UiState.Listening
    val infiniteTransition = rememberInfiniteTransition(label = "pulse")
    val scale by infiniteTransition.animateFloat(
        initialValue = 1f,
        targetValue  = if (isListening) 1.2f else 1f,
        animationSpec = infiniteRepeatable(tween(800, easing = LinearEasing), RepeatMode.Reverse),
        label = "micScale"
    )
    val alpha by infiniteTransition.animateFloat(
        initialValue = 0.4f,
        targetValue  = 0f,
        animationSpec = infiniteRepeatable(tween(1200, easing = FastOutSlowInEasing), RepeatMode.Restart),
        label = "micAlpha"
    )

    Box(contentAlignment = Alignment.Center) {
        if (isListening) {
            // Animated ripple effect
            Box(
                modifier = Modifier
                    .size(120.dp)
                    .scale(scale * 1.2f)
                    .clip(CircleShape)
                    .background(Saffron.copy(alpha = alpha))
            )
        }
        
        Surface(
            onClick = onClick,
            enabled = state !is UiState.Processing,
            shape = CircleShape,
            color = if (isListening) Color.Red else Saffron,
            tonalElevation = 8.dp,
            shadowElevation = 4.dp,
            modifier = Modifier.size(80.dp)
        ) {
            Box(contentAlignment = Alignment.Center) {
                Icon(
                    imageVector = Icons.Default.Mic,
                    contentDescription = "Speak",
                    tint = Color.White,
                    modifier = Modifier.size(36.dp)
                )
            }
        }
    }
}

@Composable
fun LessonCard(lesson: LessonResponse, onPlayClick: () -> Unit) {
    Card(
        modifier  = Modifier.fillMaxWidth(),
        shape     = RoundedCornerShape(20.dp),
        colors    = CardDefaults.cardColors(containerColor = CardBg),
        elevation = CardDefaults.cardElevation(6.dp)
    ) {
        Column(modifier = Modifier.padding(20.dp)) {
            Row(verticalAlignment = Alignment.CenterVertically) {
                Surface(
                    color = LightGreen,
                    shape = RoundedCornerShape(8.dp)
                ) {
                    Icon(
                        Icons.Default.MenuBook, 
                        contentDescription = null, 
                        tint = DeepGreen,
                        modifier = Modifier.padding(6.dp).size(20.dp)
                    )
                }
                Spacer(Modifier.width(12.dp))
                Text("Lesson Plan", fontWeight = FontWeight.Bold, fontSize = 20.sp, color = TextPrimary)
                Spacer(Modifier.weight(1f))
                lesson.latency_ms?.let {
                    Text("⚡ ${it}ms", fontSize = 11.sp, color = TextMuted)
                }
            }

            Spacer(Modifier.height(16.dp))
            HorizontalDivider(color = Color(0xFFF0F0F0))
            Spacer(Modifier.height(16.dp))

            if (lesson.lesson_structured != null && lesson.lesson_structured.sections.isNotEmpty()) {
                lesson.lesson_structured.sections.forEach { section ->
                    Text(
                        "${section.grade} • ${section.subject}",
                        fontWeight = FontWeight.Bold,
                        fontSize   = 14.sp,
                        color      = Saffron,
                        modifier = Modifier.background(Saffron.copy(alpha = 0.1f), RoundedCornerShape(4.dp)).padding(horizontal = 8.dp, vertical = 2.dp)
                    )
                    Spacer(Modifier.height(16.dp))
                    
                    section.activities.forEachIndexed { idx, activityDesc ->
                        Row(modifier = Modifier.padding(vertical = 4.dp)) {
                            Text("${idx + 1}.", fontWeight = FontWeight.Bold, color = DeepGreen, fontSize = 14.sp)
                            Spacer(Modifier.width(8.dp))
                            Text(activityDesc, fontSize = 14.sp, color = TextPrimary, lineHeight = 20.sp)
                        }
                    }
                    
                    Spacer(Modifier.height(16.dp))
                    Card(
                        colors = CardDefaults.cardColors(containerColor = LightGreen),
                        shape = RoundedCornerShape(12.dp)
                    ) {
                        Row(modifier = Modifier.padding(12.dp), verticalAlignment = Alignment.CenterVertically) {
                            Icon(Icons.Default.Lightbulb, contentDescription = null, tint = DeepGreen, modifier = Modifier.size(20.dp))
                            Spacer(Modifier.width(8.dp))
                            Text(
                                "Teacher Tip: ${section.tip}",
                                fontSize  = 13.sp,
                                color     = DeepGreen,
                                fontWeight = FontWeight.Medium
                            )
                        }
                    }
                }
            } else {
                // Fallback: show raw lesson text when structured sections are unavailable
                Text(
                    lesson.lesson_text ?: "No lesson generated.",
                    fontSize = 15.sp,
                    color    = TextPrimary,
                    lineHeight = 22.sp
                )
            }

            // WhatsApp automatic delivery confirmation badge
            Row(
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(top = 16.dp)
                    .background(Color(0xFFE8F5E9), RoundedCornerShape(10.dp))
                    .padding(horizontal = 14.dp, vertical = 10.dp),
                verticalAlignment = Alignment.CenterVertically
            ) {
                Icon(
                    imageVector = Icons.Default.CheckCircle,
                    contentDescription = null,
                    tint = Color(0xFF2E7D32),
                    modifier = Modifier.size(20.dp)
                )
                Spacer(Modifier.width(10.dp))
                Column {
                    Text(
                        "📲 WhatsApp पर भेजा गया",
                        fontSize = 13.sp,
                        fontWeight = FontWeight.Bold,
                        color = Color(0xFF1B5E20)
                    )
                    Text(
                        "Lesson delivered automatically",
                        fontSize = 11.sp,
                        color = Color(0xFF388E3C)
                    )
                }
            }

            Spacer(Modifier.height(24.dp))

            Button(
                onClick  = onPlayClick,
                modifier = Modifier.fillMaxWidth().height(52.dp),
                colors   = ButtonDefaults.buttonColors(containerColor = DeepGreen),
                shape = RoundedCornerShape(12.dp)
            ) {
                Icon(Icons.Default.VolumeUp, contentDescription = null)
                Spacer(Modifier.width(10.dp))
                Text("🔊 सुनें / Play Audio Lesson", fontWeight = FontWeight.Bold)
            }
        }
    }
}

@Composable
fun ErrorCard(message: String, onRetry: () -> Unit) {
    Card(
        modifier  = Modifier.fillMaxWidth(),
        shape     = RoundedCornerShape(16.dp),
        colors    = CardDefaults.cardColors(containerColor = Color(0xFFFFEBEE)),
        elevation = CardDefaults.cardElevation(0.dp)
    ) {
        Column(modifier = Modifier.padding(20.dp), horizontalAlignment = Alignment.CenterHorizontally) {
            Icon(Icons.Default.ErrorOutline, contentDescription = null, tint = Color.Red, modifier = Modifier.size(32.dp))
            Spacer(Modifier.height(8.dp))
            Text("Oops! Something went wrong", fontWeight = FontWeight.Bold, color = Color.Black)
            Spacer(Modifier.height(4.dp))
            Text(message, fontSize = 13.sp, color = TextMuted, textAlign = TextAlign.Center)
            Spacer(Modifier.height(16.dp))
            Button(
                onClick = onRetry,
                colors = ButtonDefaults.buttonColors(containerColor = Color.Red),
                shape = RoundedCornerShape(8.dp)
            ) {
                Text("Retry")
            }
        }
    }
}
