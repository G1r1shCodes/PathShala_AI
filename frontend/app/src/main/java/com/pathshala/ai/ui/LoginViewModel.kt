package com.pathshala.ai.ui

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.pathshala.ai.model.OtpRequest
import com.pathshala.ai.model.VerifyOtpRequest
import com.pathshala.ai.network.RetrofitClient
import kotlinx.coroutines.Job
import kotlinx.coroutines.delay
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.launch

sealed class LoginState {
    object PhoneEntry : LoginState()
    object OtpSending : LoginState()
    data class OtpEntry(val phone: String) : LoginState()
    object Verifying : LoginState()
    data class Verified(val token: String?) : LoginState()
    data class Error(val message: String, val returnTo: LoginState) : LoginState()
}

class LoginViewModel : ViewModel() {

    private val _loginState = MutableStateFlow<LoginState>(LoginState.PhoneEntry)
    val loginState: StateFlow<LoginState> = _loginState

    private val _resendCooldown = MutableStateFlow(0)
    val resendCooldown: StateFlow<Int> = _resendCooldown

    private val api = RetrofitClient.instance
    private var phone: String = ""
    private var authToken: String? = null
    private var cooldownJob: Job? = null

    fun sendOtp(phoneNumber: String) {
        if (phoneNumber.length != 10) {
            _loginState.value = LoginState.Error(
                "Please enter a valid 10-digit phone number",
                LoginState.PhoneEntry
            )
            return
        }
        phone = phoneNumber
        _loginState.value = LoginState.OtpSending

        viewModelScope.launch {
            try {
                val response = api.requestOtp(OtpRequest(phone = "+91$phone"))
                if (response.isSuccessful && response.body()?.success == true) {
                    _loginState.value = LoginState.OtpEntry(phone)
                    startCooldown()
                } else {
                    val msg = response.body()?.message ?: "Failed to send OTP (${response.code()})"
                    _loginState.value = LoginState.Error(msg, LoginState.PhoneEntry)
                }
            } catch (e: Exception) {
                _loginState.value = LoginState.Error(
                    e.localizedMessage ?: "Network error. Check your connection.",
                    LoginState.PhoneEntry
                )
            }
        }
    }

    fun verifyOtp(otp: String) {
        if (otp.length != 4) {
            _loginState.value = LoginState.Error(
                "Please enter the 4-digit OTP",
                LoginState.OtpEntry(phone)
            )
            return
        }
        _loginState.value = LoginState.Verifying

        viewModelScope.launch {
            try {
                val response = api.verifyOtp(VerifyOtpRequest(phone = "+91$phone", otp = otp))
                if (response.isSuccessful && response.body()?.success == true) {
                    authToken = response.body()?.token
                    _loginState.value = LoginState.Verified(authToken)
                } else {
                    val msg = response.body()?.message ?: "Invalid OTP. Please try again."
                    _loginState.value = LoginState.Error(msg, LoginState.OtpEntry(phone))
                }
            } catch (e: Exception) {
                _loginState.value = LoginState.Error(
                    e.localizedMessage ?: "Network error. Check your connection.",
                    LoginState.OtpEntry(phone)
                )
            }
        }
    }

    fun resendOtp() {
        if (_resendCooldown.value > 0) return
        _loginState.value = LoginState.OtpSending

        viewModelScope.launch {
            try {
                val response = api.requestOtp(OtpRequest(phone = "+91$phone"))
                if (response.isSuccessful && response.body()?.success == true) {
                    _loginState.value = LoginState.OtpEntry(phone)
                    startCooldown()
                } else {
                    _loginState.value = LoginState.Error(
                        response.body()?.message ?: "Failed to resend OTP",
                        LoginState.OtpEntry(phone)
                    )
                }
            } catch (e: Exception) {
                _loginState.value = LoginState.Error(
                    e.localizedMessage ?: "Network error",
                    LoginState.OtpEntry(phone)
                )
            }
        }
    }

    fun dismissError() {
        val current = _loginState.value
        if (current is LoginState.Error) {
            _loginState.value = current.returnTo
        }
    }

    fun goBackToPhone() {
        cooldownJob?.cancel()
        _resendCooldown.value = 0
        _loginState.value = LoginState.PhoneEntry
    }

    private fun startCooldown() {
        cooldownJob?.cancel()
        cooldownJob = viewModelScope.launch {
            _resendCooldown.value = 30
            while (_resendCooldown.value > 0) {
                delay(1000)
                _resendCooldown.value = _resendCooldown.value - 1
            }
        }
    }
}
