package com.pathshala.ai.ui.theme

import androidx.compose.material3.*
import androidx.compose.runtime.Composable
import androidx.compose.ui.graphics.Color

private val LightColorScheme = lightColorScheme(
    primary         = Color(0xFFFF6B00),
    secondary       = Color(0xFF1B6B3A),
    background      = Color(0xFFFFFFFF),
    surface         = Color(0xFFFFF8F0),
    onPrimary       = Color.White,
    onSecondary     = Color.White,
    onBackground    = Color(0xFF212121),
    onSurface       = Color(0xFF212121),
)

@Composable
fun PathShalaTheme(content: @Composable () -> Unit) {
    MaterialTheme(
        colorScheme = LightColorScheme,
        content     = content
    )
}
