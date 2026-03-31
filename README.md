# PathShala AI

**AI for Bharat Project Submission Repo**  
*"GitHub Copilot for India's 1.1 Lakh Rural Teachers"*

PathShala AI is an AI-powered MVP designed to help rural teachers in India generate structured, multi-grade lesson plans in seconds. A teacher can speak their requirements naturally in Hindi or English (e.g., "Aaj mujhe Class 1 ko vowels sikhane hain aur Class 3 ko multiplication table"), and the system instantly returns a high-quality, practical lesson plan.

## Project Context

India has **1,10,000 single-teacher schools** where one teacher manages Grades 1–5 simultaneously (60 students, 5 subjects) with no setup, internet, or support staff. Writing 5 lesson plans by hand every evening creates a crushing 2-hour daily administrative burden that drives teacher burnout.

PathShala AI solves this by giving every teacher an AI co-teacher. Unlike generic chatbots, the system encodes multi-grade pedagogic constraints (parallel activities) into an LLM and is accessible directly via Voice or Android App, specifically optimized for rural India's low-resource environments.

## 🚀 Key Features

*   **Multilingual Support**: Primary focus on Hindi, with English support.
*   **Multi-Channel Delivery**:
    *   **Android App**: Voice input, screen display, and Text-to-Speech playback. 
    *   **Phone Call**: Direct integration over voice via Twilio — built-in floating dialer FAB with interactive tooltip.
    *   **WhatsApp**: Asynchronous delivery of structured lesson plans directly to the teacher's WhatsApp.
*   **Speed & Quality**: Generates context-aware, NCERT-aligned, rural-optimized plans in under 15 seconds using powerful reasoning models.

## 🛠️ Tech Stack

*   **Backend Services**: AWS Lambda (Python serverless architecture)
*   **Frontend**: Native Android (Kotlin, Jetpack Compose, Retrofit)
*   **AI Engine**: Gemini 2.5 Flash / Claude 3.5 Sonnet
*   **Communications**: Twilio Voice API & WhatsApp API

---

## 🧪 Testing the Prototype (For Hackathon Judges)

Since this project currently uses a Twilio Trial account, we cannot send messages or OTPs to unverified numbers. To test the WhatsApp OTP and Lesson Plan delivery features yourself, please join our Twilio WhatsApp Sandbox first:

1. **Open WhatsApp** on your phone.
2. Send the message **`join become-neighbor`** to **`+14155238886`** (Twilio's Sandbox Number).
3. You will receive a confirmation message from Twilio that you have joined the Sandbox.
4. You can now use the Android App to request an OTP and generate lesson plans using your WhatsApp number!

---

## 💻 Setup & Installation

**Note**: The Python backend has been migrated to AWS Lambda and removed from this repository. This repo now exclusively hosts the Frontend Android App.

To test the application instantly without building:
1. Go to the [Releases page](https://github.com/G1r1shCodes/PathShala_AI/releases)
2. Download the latest `PathShala-AI.apk`
3. Install and run on your Android device.

### Frontend Development (Android)

If you wish to build the app from source:

1.  Open **Android Studio**.
2.  Select **Open** and choose the `frontend/` directory of this repository.
3.  Sync Gradle files.
4.  Connect your Android device or start an emulator.
5.  Click **Run** to build and install the PathShala AI application on your device.

## 📖 Additional Context

For more detailed product requirements, user flow, and API contracts, please refer to the MVP PRD:
[PathShala AI MVP PRD](PathShala_AI_MVP_PRD.md)
