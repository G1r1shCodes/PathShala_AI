# PathShala AI

**AI for Bharat Hackathon MVP**  
*"GitHub Copilot for India's 1.1 Lakh Rural Teachers"*

PathShala AI is an AI-powered MVP designed to help rural teachers in India generate structured, multi-grade lesson plans in seconds. A teacher can speak their requirements naturally in Hindi or English (e.g., "Aaj mujhe Class 1 ko vowels sikhane hain aur Class 3 ko multiplication table"), and the system instantly returns a high-quality, practical lesson plan.

## 🚀 Key Features

*   **Multilingual Support**: Primary focus on Hindi, with English support.
*   **Multi-Channel Delivery**:
    *   **Android App**: Voice input, screen display, and Text-to-Speech (TTS) playback.
    *   **Phone Call**: Direct integration over voice via Twilio.
    *   **WhatsApp**: Asynchronous delivery of structured lesson plans directly to the teacher's WhatsApp.
*   **Speed & Quality**: Generates context-aware, NCERT-aligned, rural-optimized plans in under 15 seconds using Anthropic Claude via AWS Bedrock.

## 🛠️ Tech Stack

*   **Backend**: Python, FastAPI
*   **Frontend**: Native Android (Kotlin, Retrofit)
*   **AI Engine**: Anthropic Claude 3.5 Sonnet (via AWS Bedrock)
*   **Communications**: Twilio Voice API & WhatsApp API

---

## 💻 Setup & Installation

The project is divided into two primary parts: the FastAPI backend and the Native Android app.

### 1. Backend

1.  Navigate to the backend directory:
    ```bash
    cd backend
    ```
2.  Set up a Python virtual environment and install dependencies:
    ```bash
    python -m venv venv
    venv\Scripts\activate  # On Windows
    pip install -r requirements.txt
    ```
3.  Configure Environment Variables:
    Copy the `.env.example` to `.env` and fill in the required keys:
    *   `AWS_ACCESS_KEY_ID` & `AWS_SECRET_ACCESS_KEY` (for Bedrock capability)
    *   `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, and `TWILIO_WHATSAPP_NUMBER`
4.  Run the server:
    ```bash
    uvicorn main:app --reload --host 0.0.0.0 --port 8000
    ```

### 2. Frontend (Android)

1.  Open **Android Studio**.
2.  Select **Open** and choose the `frontend/` directory of this repository.
3.  Sync Gradle files.
4.  Connect your Android device or start an emulator.
5.  Click **Run** to build and install the PathShala AI application on your device.

## 📖 Additional Context

For more detailed product requirements, user flow, and API contracts, please refer to the MVP PRD:
[PathShala AI MVP PRD](PathShala_AI_MVP_PRD.md)
