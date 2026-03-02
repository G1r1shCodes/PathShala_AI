package com.pathshala.ai.ui

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.pathshala.ai.network.ApiService
import com.pathshala.ai.network.RetrofitClient
import com.pathshala.ai.model.*
import kotlinx.coroutines.delay
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.launch

sealed class UiState {
    object Idle : UiState()
    object Listening : UiState()
    object Processing : UiState()
    data class Success(val lesson: LessonResponse) : UiState()
    data class Error(val message: String) : UiState()
}

class MainViewModel : ViewModel() {

    private val _uiState = MutableStateFlow<UiState>(UiState.Idle)
    val uiState: StateFlow<UiState> = _uiState

    private val _transcript = MutableStateFlow("")
    val transcript: StateFlow<String> = _transcript

    private val api: ApiService = RetrofitClient.instance

    // Set this to true to use mock data for testing UI and flow
    private val useMockData = true

    fun setListening() {
        _uiState.value = UiState.Listening
    }

    fun setIdle() {
        _uiState.value = UiState.Idle
    }

    fun updateTranscript(text: String) {
        _transcript.value = text
    }

    fun generateLesson(
        transcriptText: String,
        whatsappNumber: String = "+910000000000"
    ) {
        if (transcriptText.isBlank()) return
        _uiState.value = UiState.Processing
        _transcript.value = transcriptText

        viewModelScope.launch {
            if (useMockData) {
                delay(2000) // Simulate network delay
                _uiState.value = UiState.Success(getMockLessonResponse(transcriptText))
                return@launch
            }

            try {
                val request = LessonRequest(
                    transcript = transcriptText,
                    language = detectLanguage(transcriptText),
                    whatsapp_number = whatsappNumber
                )
                val response = api.generateLesson(request)
                if (response.isSuccessful && response.body() != null) {
                    _uiState.value = UiState.Success(response.body()!!)
                } else {
                    _uiState.value = UiState.Error("Server error: ${response.code()}")
                }
            } catch (e: Exception) {
                _uiState.value = UiState.Error(e.localizedMessage ?: "Unknown error")
            }
        }
    }

    fun retry() {
        if (_transcript.value.isNotBlank()) {
            generateLesson(_transcript.value)
        } else {
            _uiState.value = UiState.Idle
        }
    }

    private fun detectLanguage(text: String): String {
        val devanagariRange = '\u0900'..'\u097F'
        return if (text.any { it in devanagariRange }) "hi" else "en"
    }

    private fun getMockLessonResponse(query: String): LessonResponse {
        return LessonResponse(
            success = true,
            language = "hi",
            lesson_text = "यहाँ आपका पाठ विवरण है।",
            lesson_structured = LessonStructured(
                grades = listOf(
                    GradeLesson(
                        grade = "Class 5",
                        subject = "Science",
                        topic = "Photosynthesis (प्रकाश संश्लेषण)",
                        activities = listOf(
                            Activity(10, "Introduction to Sunlight and Plants"),
                            Activity(15, "Drawing a leaf diagram"),
                            Activity(10, "Quiz on Chlorophyll")
                        ),
                        tip = "Use a real plant to show leaves to students."
                    )
                )
            ),
            latency_ms = 1200,
            error = null,
            message = "Success"
        )
    }
}
