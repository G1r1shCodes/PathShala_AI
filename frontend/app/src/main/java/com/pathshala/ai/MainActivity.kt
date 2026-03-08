package com.pathshala.ai

import android.Manifest
import android.content.Intent
import android.content.pm.PackageManager
import android.os.Bundle
import android.speech.RecognitionListener
import android.speech.RecognizerIntent
import android.speech.SpeechRecognizer
import android.widget.Toast
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.result.contract.ActivityResultContracts
import androidx.activity.viewModels
import androidx.compose.animation.*
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.core.content.ContextCompat
import com.pathshala.ai.ui.LoginScreen
import com.pathshala.ai.ui.LoginViewModel
import com.pathshala.ai.ui.MainViewModel
import com.pathshala.ai.ui.PathShalaScreen
import com.pathshala.ai.ui.theme.PathShalaTheme

class MainActivity : ComponentActivity() {

    private val vm: MainViewModel by viewModels()
    private val loginVm: LoginViewModel by viewModels()
    private lateinit var speechRecognizer: SpeechRecognizer

    private val permissionLauncher =
        registerForActivityResult(ActivityResultContracts.RequestPermission()) { granted ->
            if (granted) startListening() else {
                Toast.makeText(this, "Mic permission needed for voice input", Toast.LENGTH_SHORT).show()
                vm.setIdle()
            }
        }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setupSpeechRecognizer()

        val prefs = getSharedPreferences("PathShalaPrefs", MODE_PRIVATE)
        val savedPhone = prefs.getString("USER_PHONE", null)

        if (savedPhone != null) {
            loginVm.restoreUserPhone(savedPhone)
        }

        setContent {
            PathShalaTheme {
                var isLoggedIn by remember { mutableStateOf(savedPhone != null) }

                Surface(
                    modifier = Modifier.fillMaxSize(),
                    color    = MaterialTheme.colorScheme.background
                ) {
                    AnimatedContent(
                        targetState = isLoggedIn,
                        transitionSpec = {
                            fadeIn() + slideInHorizontally { it } togetherWith
                                    fadeOut() + slideOutHorizontally { -it }
                        },
                        label = "navTransition"
                    ) { loggedIn ->
                        if (loggedIn) {
                            PathShalaScreen(
                                onMicClick = { onMicPressed() },
                                onLogout = {
                                    prefs.edit().remove("USER_PHONE").apply()
                                    isLoggedIn = false
                                }
                            )
                        } else {
                            LoginScreen(
                                onLoginSuccess = { 
                                    prefs.edit().putString("USER_PHONE", loginVm.userPhone.value).apply()
                                    isLoggedIn = true 
                                }
                            )
                        }
                    }
                }
            }
        }
    }

    private fun onMicPressed() {
        when {
            ContextCompat.checkSelfPermission(this, Manifest.permission.RECORD_AUDIO)
                    == PackageManager.PERMISSION_GRANTED -> startListening()
            else -> permissionLauncher.launch(Manifest.permission.RECORD_AUDIO)
        }
    }

    private fun setupSpeechRecognizer() {
        speechRecognizer = SpeechRecognizer.createSpeechRecognizer(this)
        speechRecognizer.setRecognitionListener(object : RecognitionListener {

            override fun onReadyForSpeech(params: Bundle?) {
                vm.setListening()
            }

            override fun onResults(results: Bundle?) {
                val matches = results?.getStringArrayList(SpeechRecognizer.RESULTS_RECOGNITION)
                val best    = matches?.firstOrNull() ?: return
                // Pass the user's +91 phone number for WhatsApp delivery
                val phone = "+91${loginVm.userPhone.value}"
                vm.generateLesson(best, whatsappNumber = phone.takeIf { loginVm.userPhone.value.isNotBlank() })
            }

            override fun onError(error: Int) {
                val msg = when (error) {
                    SpeechRecognizer.ERROR_NO_MATCH      -> "No speech detected. Please try again."
                    SpeechRecognizer.ERROR_NETWORK       -> "Network error. Check your connection."
                    SpeechRecognizer.ERROR_AUDIO         -> "Audio error. Try again."
                    SpeechRecognizer.ERROR_SPEECH_TIMEOUT -> "No speech input. Tap mic and speak."
                    else                                 -> "Speech recognition failed (code $error)"
                }
                Toast.makeText(this@MainActivity, msg, Toast.LENGTH_SHORT).show()
                vm.setIdle()
            }

            override fun onBeginningOfSpeech()              {}
            override fun onBufferReceived(buffer: ByteArray?) {}
            override fun onEndOfSpeech()                    {}
            override fun onEvent(eventType: Int, params: Bundle?) {}
            override fun onPartialResults(partialResults: Bundle?) {}
            override fun onRmsChanged(rmsdB: Float)         {}
        })
    }

    private fun startListening() {
        val intent = Intent(RecognizerIntent.ACTION_RECOGNIZE_SPEECH).apply {
            putExtra(RecognizerIntent.EXTRA_LANGUAGE,              "hi-IN")
            putExtra(RecognizerIntent.EXTRA_LANGUAGE_MODEL,        RecognizerIntent.LANGUAGE_MODEL_FREE_FORM)
            putExtra(RecognizerIntent.EXTRA_LANGUAGE_PREFERENCE,   "hi-IN")
            putExtra(RecognizerIntent.EXTRA_ONLY_RETURN_LANGUAGE_PREFERENCE, false)
            putExtra(RecognizerIntent.EXTRA_MAX_RESULTS,           3)
        }
        speechRecognizer.startListening(intent)
    }

    override fun onDestroy() {
        super.onDestroy()
        speechRecognizer.destroy()
    }
}
