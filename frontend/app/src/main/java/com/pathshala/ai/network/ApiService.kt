package com.pathshala.ai.network

import com.pathshala.ai.model.*
import okhttp3.OkHttpClient
import okhttp3.logging.HttpLoggingInterceptor
import retrofit2.Response
import retrofit2.Retrofit
import retrofit2.converter.gson.GsonConverterFactory
import retrofit2.http.Body
import retrofit2.http.GET
import retrofit2.http.Header
import retrofit2.http.POST
import java.util.concurrent.TimeUnit

interface ApiService {

    // Auth
    @POST("auth/request-otp")
    suspend fun requestOtp(@Body request: OtpRequest): Response<OtpResponse>

    @POST("auth/verify-otp")
    suspend fun verifyOtp(@Body request: VerifyOtpRequest): Response<VerifyOtpResponse>

    // Lessons
    @POST("lessons/generate")
    suspend fun generateLesson(@Body request: LessonRequest): Response<LessonResponse>

    @GET("lessons")
    suspend fun listLessons(@Header("Authorization") token: String): Response<List<LessonResponse>>

    // Teacher
    @GET("teacher")
    suspend fun getTeacher(@Header("Authorization") token: String): Response<TeacherInfo>
}

object RetrofitClient {
    private const val BASE_URL = "https://9ux3xn9vk6.execute-api.ap-south-1.amazonaws.com/dev/"

    val instance: ApiService by lazy {
        val logging = HttpLoggingInterceptor().apply {
            level = HttpLoggingInterceptor.Level.BODY
        }

        val okHttp = OkHttpClient.Builder()
            .connectTimeout(120, TimeUnit.SECONDS)
            .readTimeout(120, TimeUnit.SECONDS)
            .writeTimeout(120, TimeUnit.SECONDS)
            .addInterceptor(logging)
            .build()

        Retrofit.Builder()
            .baseUrl(BASE_URL)
            .client(okHttp)
            .addConverterFactory(GsonConverterFactory.create())
            .build()
            .create(ApiService::class.java)
    }
}
