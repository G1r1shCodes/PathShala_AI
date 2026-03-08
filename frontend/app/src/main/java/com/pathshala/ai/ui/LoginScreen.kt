package com.pathshala.ai.ui

import androidx.compose.animation.*
import androidx.compose.animation.core.*
import androidx.compose.foundation.*
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.text.KeyboardActions
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.focus.FocusRequester
import androidx.compose.ui.focus.focusRequester
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.platform.LocalFocusManager
import androidx.compose.ui.text.TextStyle
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.ImeAction
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.lifecycle.viewmodel.compose.viewModel
import android.content.Intent
import android.net.Uri

// ─── LOGIN SCREEN ────────────────────────────────────────────────────────────
@Composable
fun LoginScreen(
    onLoginSuccess: () -> Unit,
    loginVm: LoginViewModel = viewModel()
) {
    val loginState by loginVm.loginState.collectAsState()
    val cooldown by loginVm.resendCooldown.collectAsState()
    var showOnboarding by remember { mutableStateOf(true) }

    // Navigate on verified
    LaunchedEffect(loginState) {
        if (loginState is LoginState.Verified) {
            onLoginSuccess()
        }
    }

    Column(
        modifier = Modifier
            .fillMaxSize()
            .background(Color(0xFFF8F9FA))
    ) {
        // ── Hero Header ─────────────────────────────────────────────────────
        Box(
            modifier = Modifier
                .fillMaxWidth()
                .background(
                    Brush.verticalGradient(
                        colors = listOf(Color(0xFF1A1A2E), Color(0xFF16213E))
                    )
                )
                .padding(top = 60.dp, bottom = 40.dp),
            contentAlignment = Alignment.Center
        ) {
            Column(horizontalAlignment = Alignment.CenterHorizontally) {
                // App icon
                Surface(
                    modifier = Modifier.size(72.dp),
                    shape = RoundedCornerShape(20.dp),
                    color = Saffron,
                    shadowElevation = 12.dp
                ) {
                    Box(contentAlignment = Alignment.Center) {
                        Icon(
                            Icons.Default.AutoStories,
                            contentDescription = null,
                            tint = Color.White,
                            modifier = Modifier.size(36.dp)
                        )
                    }
                }
                Spacer(Modifier.height(16.dp))
                Text(
                    "PathShala AI",
                    fontSize = 28.sp,
                    fontWeight = FontWeight.Bold,
                    color = Color.White,
                    letterSpacing = 1.sp
                )
                Spacer(Modifier.height(6.dp))
                Text(
                    "AI Co-Teacher for Rural India",
                    fontSize = 14.sp,
                    color = Color.White.copy(alpha = 0.7f),
                    letterSpacing = 0.5.sp
                )
            }
        }

        // ── Content Area ────────────────────────────────────────────────────
        Column(
            modifier = Modifier
                .fillMaxSize()
                .verticalScroll(rememberScrollState())
                .padding(horizontal = 24.dp)
                .padding(top = 32.dp),
            horizontalAlignment = Alignment.CenterHorizontally
        ) {
            if (showOnboarding) {
                SandboxOnboardingSection(onNext = { showOnboarding = false })
            } else {
                AnimatedContent(
                    targetState = loginState,
                    transitionSpec = {
                        slideInHorizontally { width -> width } + fadeIn() togetherWith
                                slideOutHorizontally { width -> -width } + fadeOut()
                    },
                    label = "loginTransition"
                ) { state ->
                    when (state) {
                        is LoginState.PhoneEntry,
                        is LoginState.OtpSending -> {
                            PhoneEntrySection(
                                isLoading = state is LoginState.OtpSending,
                                onSendOtp = { loginVm.sendOtp(it) }
                            )
                        }
                        is LoginState.OtpEntry,
                        is LoginState.Verifying -> {
                            OtpEntrySection(
                                phone = (loginState as? LoginState.OtpEntry)?.phone
                                    ?: (loginState as? LoginState.Verifying)?.let { "" } ?: "",
                                isVerifying = state is LoginState.Verifying,
                                cooldown = cooldown,
                                onVerify = { loginVm.verifyOtp(it) },
                                onResend = { loginVm.resendOtp() },
                                onBack = { loginVm.goBackToPhone() }
                            )
                        }
                        is LoginState.Error -> {
                            ErrorSection(
                                message = state.message,
                                onDismiss = { loginVm.dismissError() }
                            )
                        }
                        is LoginState.Verified -> {
                            // Brief success animation before nav
                            VerifiedSection()
                        }
                    }
                }
            }
        }
    }
}

// ─── SANDBOX ONBOARDING ─────────────────────────────────────────────────────
@Composable
private fun SandboxOnboardingSection(onNext: () -> Unit) {
    val context = LocalContext.current
    val sandboxNumber = "14155238886"   // Twilio Sandbox WhatsApp number
    val sandboxKeyword = "join became-neighbor"

    Column(
        modifier = Modifier.fillMaxWidth(),
        horizontalAlignment = Alignment.CenterHorizontally
    ) {
        Icon(
            Icons.Default.Chat,
            contentDescription = null,
            tint = Color(0xFF25D366),
            modifier = Modifier.size(48.dp)
        )
        Spacer(Modifier.height(16.dp))
        Text(
            "Set Up WhatsApp",
            fontSize = 24.sp,
            fontWeight = FontWeight.Bold,
            color = TextPrimary
        )
        Spacer(Modifier.height(8.dp))
        Text(
            "To receive OTPs and lesson plans directly on WhatsApp, please join our Sandbox using the steps below. You only need to do this once.",
            fontSize = 14.sp,
            color = TextMuted,
            textAlign = TextAlign.Center,
            lineHeight = 20.sp
        )

        Spacer(Modifier.height(24.dp))

        // Card displaying instructions
        Card(
            modifier = Modifier.fillMaxWidth(),
            shape = RoundedCornerShape(16.dp),
            colors = CardDefaults.cardColors(containerColor = Color(0xFFE8F5E9)),
            elevation = CardDefaults.cardElevation(0.dp)
        ) {
            Column(modifier = Modifier.padding(16.dp)) {
                // Step 1
                Row(verticalAlignment = Alignment.CenterVertically) {
                    Surface(
                        shape = CircleShape,
                        color = DeepGreen,
                        modifier = Modifier.size(24.dp)
                    ) {
                        Box(contentAlignment = Alignment.Center) {
                            Text("1", color = Color.White, fontSize = 12.sp, fontWeight = FontWeight.Bold)
                        }
                    }
                    Spacer(Modifier.width(12.dp))
                    Text("Tap the button below to open WhatsApp", fontSize = 14.sp, color = TextPrimary)
                }
                Spacer(Modifier.height(12.dp))

                // Step 2
                Row(verticalAlignment = Alignment.CenterVertically) {
                    Surface(
                        shape = CircleShape,
                        color = DeepGreen,
                        modifier = Modifier.size(24.dp)
                    ) {
                        Box(contentAlignment = Alignment.Center) {
                            Text("2", color = Color.White, fontSize = 12.sp, fontWeight = FontWeight.Bold)
                        }
                    }
                    Spacer(Modifier.width(12.dp))
                    Text("Send the pre-filled message — done! ✅", fontSize = 14.sp, color = TextPrimary)
                }

                Spacer(Modifier.height(20.dp))

                Button(
                    onClick = {
                        val encodedMsg = Uri.encode(sandboxKeyword)
                        val uri = Uri.parse("https://wa.me/$sandboxNumber?text=$encodedMsg")
                        context.startActivity(Intent(Intent.ACTION_VIEW, uri))
                    },
                    modifier = Modifier.fillMaxWidth().height(48.dp),
                    colors = ButtonDefaults.buttonColors(containerColor = Color(0xFF25D366)),
                    shape = RoundedCornerShape(12.dp)
                ) {
                    Icon(Icons.Default.Chat, contentDescription = null, modifier = Modifier.size(20.dp), tint = Color.White)
                    Spacer(Modifier.width(8.dp))
                    Text("Open WhatsApp", fontWeight = FontWeight.Bold, fontSize = 14.sp, color = Color.White)
                }
            }
        }

        Spacer(Modifier.height(32.dp))

        // Next Button
        Button(
            onClick = onNext,
            modifier = Modifier.fillMaxWidth().height(52.dp),
            colors = ButtonDefaults.buttonColors(containerColor = Saffron),
            shape = RoundedCornerShape(12.dp)
        ) {
            Text("Continue to Login", fontWeight = FontWeight.Bold, fontSize = 16.sp)
            Spacer(Modifier.width(8.dp))
            Icon(Icons.Default.ArrowForward, contentDescription = null, modifier = Modifier.size(20.dp))
        }
    }
}

// ─── PHONE ENTRY ────────────────────────────────────────────────────────────
@Composable
private fun PhoneEntrySection(
    isLoading: Boolean,
    onSendOtp: (String) -> Unit
) {
    var phone by remember { mutableStateOf("") }
    val focusManager = LocalFocusManager.current

    Column(
        modifier = Modifier.fillMaxWidth(),
        horizontalAlignment = Alignment.CenterHorizontally
    ) {
        // Title
        Text(
            "Teacher Login",
            fontSize = 24.sp,
            fontWeight = FontWeight.Bold,
            color = TextPrimary
        )
        Spacer(Modifier.height(8.dp))
        Text(
            "शिक्षक लॉगिन • Enter your phone number",
            fontSize = 14.sp,
            color = TextMuted,
            textAlign = TextAlign.Center
        )

        Spacer(Modifier.height(24.dp))

        // Phone Card
        Card(
            modifier = Modifier.fillMaxWidth(),
            shape = RoundedCornerShape(16.dp),
            colors = CardDefaults.cardColors(containerColor = Color.White),
            elevation = CardDefaults.cardElevation(4.dp)
        ) {
            Column(modifier = Modifier.padding(20.dp)) {
                Text(
                    "Mobile Number / मोबाइल नंबर",
                    fontSize = 13.sp,
                    fontWeight = FontWeight.SemiBold,
                    color = TextMuted
                )
                Spacer(Modifier.height(12.dp))

                Row(
                    verticalAlignment = Alignment.CenterVertically,
                    modifier = Modifier.fillMaxWidth()
                ) {
                    // Country code chip
                    Surface(
                        shape = RoundedCornerShape(10.dp),
                        color = Color(0xFFF5F5F5),
                        border = BorderStroke(1.dp, Color(0xFFE0E0E0))
                    ) {
                        Row(
                            modifier = Modifier.padding(horizontal = 12.dp, vertical = 14.dp),
                            verticalAlignment = Alignment.CenterVertically
                        ) {
                            Text("🇮🇳", fontSize = 18.sp)
                            Spacer(Modifier.width(6.dp))
                            Text(
                                "+91",
                                fontWeight = FontWeight.SemiBold,
                                fontSize = 16.sp,
                                color = TextPrimary
                            )
                        }
                    }

                    Spacer(Modifier.width(10.dp))

                    // Phone field
                    OutlinedTextField(
                        value = phone,
                        onValueChange = { if (it.length <= 10 && it.all { c -> c.isDigit() }) phone = it },
                        modifier = Modifier.fillMaxWidth(),
                        placeholder = { Text("XXXXXXXXXX", color = Color(0xFFBDBDBD)) },
                        keyboardOptions = KeyboardOptions(
                            keyboardType = KeyboardType.Number,
                            imeAction = ImeAction.Done
                        ),
                        keyboardActions = KeyboardActions(
                            onDone = {
                                focusManager.clearFocus()
                                onSendOtp(phone)
                            }
                        ),
                        singleLine = true,
                        textStyle = TextStyle(
                            fontSize = 18.sp,
                            fontWeight = FontWeight.Medium,
                            letterSpacing = 2.sp
                        ),
                        colors = OutlinedTextFieldDefaults.colors(
                            focusedBorderColor = Saffron,
                            unfocusedBorderColor = Color(0xFFE0E0E0),
                            cursorColor = Saffron
                        ),
                        shape = RoundedCornerShape(10.dp)
                    )
                }

                Spacer(Modifier.height(24.dp))

                // Send OTP button
                Button(
                    onClick = { onSendOtp(phone) },
                    enabled = phone.length == 10 && !isLoading,
                    modifier = Modifier
                        .fillMaxWidth()
                        .height(52.dp),
                    colors = ButtonDefaults.buttonColors(
                        containerColor = Saffron,
                        disabledContainerColor = Saffron.copy(alpha = 0.4f)
                    ),
                    shape = RoundedCornerShape(12.dp)
                ) {
                    if (isLoading) {
                        CircularProgressIndicator(
                            modifier = Modifier.size(22.dp),
                            color = Color.White,
                            strokeWidth = 2.dp
                        )
                        Spacer(Modifier.width(10.dp))
                        Text("Sending OTP...", fontWeight = FontWeight.Bold, fontSize = 16.sp)
                    } else {
                        Icon(Icons.Default.Sms, contentDescription = null, modifier = Modifier.size(20.dp))
                        Spacer(Modifier.width(10.dp))
                        Text("Send OTP / OTP भेजें", fontWeight = FontWeight.Bold, fontSize = 16.sp)
                    }
                }
            }
        }

        Spacer(Modifier.height(24.dp))

        // Info text
        Surface(
            color = Color(0xFFFFF3E0),
            shape = RoundedCornerShape(12.dp)
        ) {
            Row(
                modifier = Modifier.padding(14.dp),
                verticalAlignment = Alignment.CenterVertically
            ) {
                Icon(
                    Icons.Default.Info,
                    contentDescription = null,
                    tint = Saffron,
                    modifier = Modifier.size(18.dp)
                )
                Spacer(Modifier.width(10.dp))
                Text(
                    "A 4-digit OTP will be sent to your phone\nआपके फ़ोन पर 4 अंकों का OTP भेजा जाएगा",
                    fontSize = 12.sp,
                    color = Color(0xFF795548),
                    lineHeight = 18.sp
                )
            }
        }
    }
}

// ─── OTP ENTRY ──────────────────────────────────────────────────────────────
@Composable
private fun OtpEntrySection(
    phone: String,
    isVerifying: Boolean,
    cooldown: Int,
    onVerify: (String) -> Unit,
    onResend: () -> Unit,
    onBack: () -> Unit
) {
    var otp by remember { mutableStateOf(listOf("", "", "", "")) }
    val focusRequesters = remember { List(4) { FocusRequester() } }
    val focusManager = LocalFocusManager.current

    Column(
        modifier = Modifier.fillMaxWidth(),
        horizontalAlignment = Alignment.CenterHorizontally
    ) {
        // Back + Title
        Row(
            modifier = Modifier.fillMaxWidth(),
            verticalAlignment = Alignment.CenterVertically
        ) {
            IconButton(onClick = onBack) {
                Icon(Icons.Default.ArrowBack, contentDescription = "Back", tint = TextPrimary)
            }
            Column {
                Text("Verify OTP", fontSize = 24.sp, fontWeight = FontWeight.Bold, color = TextPrimary)
                Text(
                    "OTP सत्यापित करें",
                    fontSize = 13.sp,
                    color = TextMuted
                )
            }
        }

        Spacer(Modifier.height(8.dp))
        Text(
            "Sent to +91 $phone",
            fontSize = 14.sp,
            color = DeepGreen,
            fontWeight = FontWeight.Medium
        )

        Spacer(Modifier.height(32.dp))

        // OTP Card
        Card(
            modifier = Modifier.fillMaxWidth(),
            shape = RoundedCornerShape(16.dp),
            colors = CardDefaults.cardColors(containerColor = Color.White),
            elevation = CardDefaults.cardElevation(4.dp)
        ) {
            Column(
                modifier = Modifier.padding(20.dp),
                horizontalAlignment = Alignment.CenterHorizontally
            ) {
                Text(
                    "Enter 4-digit OTP / 4 अंकों का OTP दर्ज करें",
                    fontSize = 13.sp,
                    color = TextMuted,
                    textAlign = TextAlign.Center
                )
                Spacer(Modifier.height(24.dp))

                // OTP boxes
                Row(
                    horizontalArrangement = Arrangement.spacedBy(12.dp),
                    modifier = Modifier.fillMaxWidth(),
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Spacer(Modifier.weight(1f))
                    for (i in 0..3) {
                        OutlinedTextField(
                            value = otp[i],
                            onValueChange = { value ->
                                if (value.length <= 1 && value.all { it.isDigit() }) {
                                    otp = otp.toMutableList().also { it[i] = value }
                                    // Auto-advance focus
                                    if (value.isNotEmpty() && i < 3) {
                                        focusRequesters[i + 1].requestFocus()
                                    }
                                    // Auto-submit when all filled
                                    val fullOtp = otp.toMutableList().also { it[i] = value }.joinToString("")
                                    if (fullOtp.length == 4) {
                                        focusManager.clearFocus()
                                        onVerify(fullOtp)
                                    }
                                }
                            },
                            modifier = Modifier
                                .size(60.dp)
                                .focusRequester(focusRequesters[i]),
                            textStyle = TextStyle(
                                fontSize = 24.sp,
                                fontWeight = FontWeight.Bold,
                                textAlign = TextAlign.Center
                            ),
                            keyboardOptions = KeyboardOptions(
                                keyboardType = KeyboardType.Number,
                                imeAction = if (i < 3) ImeAction.Next else ImeAction.Done
                            ),
                            singleLine = true,
                            colors = OutlinedTextFieldDefaults.colors(
                                focusedBorderColor = Saffron,
                                unfocusedBorderColor = Color(0xFFE0E0E0),
                                cursorColor = Saffron
                            ),
                            shape = RoundedCornerShape(12.dp)
                        )
                    }
                    Spacer(Modifier.weight(1f))
                }

                Spacer(Modifier.height(24.dp))

                // Verify button
                Button(
                    onClick = { onVerify(otp.joinToString("")) },
                    enabled = otp.joinToString("").length == 4 && !isVerifying,
                    modifier = Modifier
                        .fillMaxWidth()
                        .height(52.dp),
                    colors = ButtonDefaults.buttonColors(
                        containerColor = DeepGreen,
                        disabledContainerColor = DeepGreen.copy(alpha = 0.4f)
                    ),
                    shape = RoundedCornerShape(12.dp)
                ) {
                    if (isVerifying) {
                        CircularProgressIndicator(
                            modifier = Modifier.size(22.dp),
                            color = Color.White,
                            strokeWidth = 2.dp
                        )
                        Spacer(Modifier.width(10.dp))
                        Text("Verifying...", fontWeight = FontWeight.Bold, fontSize = 16.sp)
                    } else {
                        Icon(Icons.Default.CheckCircle, contentDescription = null, modifier = Modifier.size(20.dp))
                        Spacer(Modifier.width(10.dp))
                        Text("Verify & Login / लॉगिन करें", fontWeight = FontWeight.Bold, fontSize = 16.sp)
                    }
                }

                Spacer(Modifier.height(16.dp))

                // Resend OTP
                Row(
                    horizontalArrangement = Arrangement.Center,
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Text("Didn't receive OTP? ", fontSize = 13.sp, color = TextMuted)
                    if (cooldown > 0) {
                        Text(
                            "Resend in ${cooldown}s",
                            fontSize = 13.sp,
                            color = TextMuted,
                            fontWeight = FontWeight.SemiBold
                        )
                    } else {
                        TextButton(onClick = onResend) {
                            Text(
                                "Resend OTP",
                                fontSize = 13.sp,
                                color = Saffron,
                                fontWeight = FontWeight.Bold
                            )
                        }
                    }
                }
            }
        }
    }
}

// ─── ERROR ──────────────────────────────────────────────────────────────────
@Composable
private fun ErrorSection(message: String, onDismiss: () -> Unit) {
    Column(
        modifier = Modifier.fillMaxWidth(),
        horizontalAlignment = Alignment.CenterHorizontally
    ) {
        Spacer(Modifier.height(40.dp))
        Card(
            modifier = Modifier.fillMaxWidth(),
            shape = RoundedCornerShape(16.dp),
            colors = CardDefaults.cardColors(containerColor = Color(0xFFFFEBEE)),
            elevation = CardDefaults.cardElevation(2.dp)
        ) {
            Column(
                modifier = Modifier.padding(24.dp),
                horizontalAlignment = Alignment.CenterHorizontally
            ) {
                Icon(
                    Icons.Default.ErrorOutline,
                    contentDescription = null,
                    tint = Color(0xFFD32F2F),
                    modifier = Modifier.size(40.dp)
                )
                Spacer(Modifier.height(12.dp))
                Text(
                    message,
                    fontSize = 14.sp,
                    color = Color(0xFFD32F2F),
                    textAlign = TextAlign.Center,
                    fontWeight = FontWeight.Medium
                )
                Spacer(Modifier.height(16.dp))
                Button(
                    onClick = onDismiss,
                    colors = ButtonDefaults.buttonColors(containerColor = Color(0xFFD32F2F)),
                    shape = RoundedCornerShape(8.dp)
                ) {
                    Text("Try Again", fontWeight = FontWeight.Bold)
                }
            }
        }
    }
}

// ─── VERIFIED SUCCESS ───────────────────────────────────────────────────────
@Composable
private fun VerifiedSection() {
    val infiniteTransition = rememberInfiniteTransition(label = "check")
    val scale by infiniteTransition.animateFloat(
        initialValue = 0.8f,
        targetValue = 1.1f,
        animationSpec = infiniteRepeatable(
            tween(600, easing = FastOutSlowInEasing),
            RepeatMode.Reverse
        ),
        label = "checkScale"
    )

    Column(
        modifier = Modifier
            .fillMaxWidth()
            .padding(top = 60.dp),
        horizontalAlignment = Alignment.CenterHorizontally
    ) {
        Surface(
            modifier = Modifier
                .size(80.dp)
                .clip(CircleShape),
            color = DeepGreen
        ) {
            Box(contentAlignment = Alignment.Center) {
                Icon(
                    Icons.Default.CheckCircle,
                    contentDescription = "Verified",
                    tint = Color.White,
                    modifier = Modifier.size(48.dp)
                )
            }
        }
        Spacer(Modifier.height(20.dp))
        Text(
            "✅ Login Successful!",
            fontSize = 22.sp,
            fontWeight = FontWeight.Bold,
            color = DeepGreen
        )
        Spacer(Modifier.height(8.dp))
        Text(
            "Welcome, Teacher • स्वागत है शिक्षक",
            fontSize = 14.sp,
            color = TextMuted
        )
    }
}
