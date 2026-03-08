package com.pathshala.ai.model

import com.google.gson.annotations.SerializedName

// ─── Auth Models ────────────────────────────────────────────────────────────

data class OtpRequest(
    @SerializedName("phone") val phone: String
)

data class OtpResponse(
    @SerializedName("success") val success: Boolean,
    @SerializedName("message") val message: String?
)

data class VerifyOtpRequest(
    @SerializedName("phone") val phone: String,
    @SerializedName("otp")   val otp: String
)

data class VerifyOtpResponse(
    @SerializedName("success") val success: Boolean,
    @SerializedName("token")   val token: String?,
    @SerializedName("teacher") val teacher: TeacherInfo?,
    @SerializedName("message") val message: String?
)

data class TeacherInfo(
    @SerializedName("phone")  val phone: String?,
    @SerializedName("name")   val name: String?,
    @SerializedName("school") val school: String?
)

// ─── Lesson Models ──────────────────────────────────────────────────────────

data class LessonRequest(
    @SerializedName("text")            val text: String? = null,
    @SerializedName("transcript")      val transcript: String? = null,
    @SerializedName("language")        val language: String,
    @SerializedName("whatsapp_number") val whatsapp_number: String
)

data class LessonResponse(
    @SerializedName("success")           val success: Boolean,
    @SerializedName("language")          val language: String?,
    @SerializedName("lesson_text")       val lesson_text: String?,
    @SerializedName("lesson_structured") val lesson_structured: LessonStructured?,
    @SerializedName("latency_ms")        val latency_ms: Long?,
    @SerializedName("error")            val error: String?,
    @SerializedName("message")          val message: String?
)

data class LessonStructured(
    @SerializedName("sections") val sections: List<GradeLesson>
)

data class GradeLesson(
    @SerializedName("grade")      val grade: String,
    @SerializedName("subject")    val subject: String,
    @SerializedName("activities") val activities: List<String>,
    @SerializedName("tip")        val tip: String
)
