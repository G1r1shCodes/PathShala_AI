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
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.material3.*
import androidx.compose.ui.Modifier
import androidx.core.content.ContextCompat
import com.pathshala.ai.ui.MainViewModel
import com.pathshala.ai.ui.PathShalaScreen
import com.pathshala.ai.ui.theme.PathShalaTheme

class MainActivity : ComponentActivity() {

    private val vm: MainViewModel by viewModels()
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

        setContent {
            PathShalaTheme {
                Surface(
                    modifier = Modifier.fillMaxSize(),
                    color    = MaterialTheme.colorScheme.background
                ) {
                    PathShalaScreen(
                        onMicClick = { onMicPressed() },
                        vm = vm
                    )
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
                vm.generateLesson(best)
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
