```text
██████╗  █████╗ ████████╗██╗  ██╗███████╗██╗  ██╗ █████╗ ██╗      █████╗      █████╗ ██╗
██╔══██╗██╔══██╗╚══██╔══╝██║  ██║██╔════╝██║  ██║██╔══██╗██║     ██╔══██╗    ██╔══██╗██║
██████╔╝███████║   ██║   ███████║███████╗███████║███████║██║     ███████║    ███████║██║
██╔═══╝ ██╔══██║   ██║   ██╔══██║╚════██║██╔══██║██╔══██║██║     ██╔══██║    ██╔══██║██║
██║     ██║  ██║   ██║   ██║  ██║███████║██║  ██║██║  ██║███████╗██║  ██║    ██║  ██║██║
╚═╝     ╚═╝  ╚═╝   ╚═╝   ╚═╝  ╚═╝╚══════╝╚═╝  ╚═╝╚═╝  ╚═╝╚══════╝╚═╝  ╚═╝    ╚═╝  ╚═╝╚═╝
```

<p align="center">
  <img src="https://img.shields.io/badge/Hackathon-AI%20for%20Bharat-blue?style=for-the-badge">
  <img src="https://img.shields.io/badge/Android-Kotlin-7F52FF?style=for-the-badge&logo=kotlin&logoColor=white">
  <img src="https://img.shields.io/badge/Jetpack%20Compose-4285F4?style=for-the-badge">
  <img src="https://img.shields.io/badge/AWS-Lambda-FF9900?style=for-the-badge&logo=amazonaws&logoColor=white">
  <img src="https://img.shields.io/badge/Gemini-2.5%20Flash-4285F4?style=for-the-badge">
  <img src="https://img.shields.io/badge/Claude-3.5%20Sonnet-D97706?style=for-the-badge">
  <img src="https://img.shields.io/badge/Twilio-Voice%20%26%20WhatsApp-F22F46?style=for-the-badge&logo=twilio&logoColor=white">
</p>

<p align="center">
  <strong>AI for Bharat Project Submission Repo</strong>
</p>

<p align="center">
  <em>"GitHub Copilot for India's 1.1 Lakh Rural Teachers"</em>
</p>

---

PathShala AI is an AI-powered MVP designed to help rural teachers in India generate structured, multi-grade lesson plans in seconds. A teacher can speak their requirements naturally in Hindi or English, and the system instantly returns a high-quality, practical lesson plan.

## Project Context

India has **1,10,000 single-teacher schools** where one teacher manages Grades 1–5 simultaneously. Writing multiple lesson plans every evening creates a significant administrative burden.

PathShala AI acts as an AI co-teacher by generating context-aware, multi-grade lesson plans optimized for low-resource rural environments.

## Features

- Multilingual support (Hindi and English)
- Android application with voice input and text-to-speech
- Phone call interaction via Twilio
- WhatsApp lesson plan delivery
- NCERT-aligned lesson generation
- Response generation in under 15 seconds

## Tech Stack

| Category | Technology |
|---------|------------|
| Frontend | Kotlin, Jetpack Compose |
| Backend | AWS Lambda (Python) |
| AI Models | Gemini 2.5 Flash, Claude 3.5 Sonnet |
| Communication | Twilio Voice API, WhatsApp API |
| Networking | Retrofit |

## Testing the Prototype

Since the project currently uses a Twilio Trial account, only verified numbers can receive messages.

1. Open WhatsApp.
2. Send `join <message>` to `+14155238886`.
3. Wait for the confirmation message.
4. Use the Android app to request OTPs and receive lesson plans.

## Installation

### Download APK

1. Visit the Releases page.
2. Download the latest `PathShala-AI.apk`.
3. Install it on your Android device.

### Build from Source

1. Open Android Studio.
2. Open the `frontend/` directory.
3. Sync Gradle files.
4. Connect a device or emulator.
5. Run the application.

## Additional Documentation

For product requirements, user flows, and API contracts, refer to:

`PathShala_AI_MVP_PRD.md`
