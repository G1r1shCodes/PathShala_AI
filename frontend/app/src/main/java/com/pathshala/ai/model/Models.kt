package com.pathshala.ai.model

import com.google.gson.annotations.SerializedName

data class LessonRequest(
    @SerializedName("transcript")    val transcript: String,
    @SerializedName("language")      val language: String,
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
    @SerializedName("grades") val grades: List<GradeLesson>
)

data class GradeLesson(
    @SerializedName("grade")      val grade: String,
    @SerializedName("subject")    val subject: String,
    @SerializedName("topic")      val topic: String,
    @SerializedName("activities") val activities: List<Activity>,
    @SerializedName("tip")        val tip: String
)

data class Activity(
    @SerializedName("duration_min") val duration_min: Int,
    @SerializedName("description")  val description: String
)
