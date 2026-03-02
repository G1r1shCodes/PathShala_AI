# PathShala AI — MVP Product Requirements Document

**Version:** 1.0  
**Date:** March 2026  
**Track:** AI for Communities, Access & Public Impact  
**Hackathon:** AI for Bharat  
**Status:** Hackathon MVP — 48–72 Hour Build  

---

## Table of Contents

1. [Overview](#1-overview)
2. [Problem Statement](#2-problem-statement)
3. [MVP Goals](#3-mvp-goals)
4. [What Is Out of Scope](#4-what-is-out-of-scope)
5. [User Persona](#5-user-persona)
6. [Core Features](#6-core-features)
7. [Tech Stack](#7-tech-stack)
8. [System Architecture](#8-system-architecture)
9. [API Contracts](#9-api-contracts)
10. [AI Layer — Prompt Specification](#10-ai-layer--prompt-specification)
11. [WhatsApp Message Format](#11-whatsapp-message-format)
12. [Android App — Screen Specifications](#12-android-app--screen-specifications)
13. [Error Handling & Fallbacks](#13-error-handling--fallbacks)
14. [Team Responsibilities](#14-team-responsibilities)
15. [Build Timeline](#15-build-timeline)
16. [Demo Script](#16-demo-script)
17. [Definition of Done](#17-definition-of-done)
18. [Known Risks & Mitigations](#18-known-risks--mitigations)

---

## 1. Overview

PathShala AI is a voice-powered AI teaching assistant for rural Indian schoolteachers who manage 60 students across Grades 1–5 in a single classroom with no internet, no support staff, and no technology assistance.

The MVP validates one core hypothesis:

> **A rural teacher can speak naturally in Hindi or English and receive a structured, multi-grade lesson plan within 15 seconds — delivered via voice, app screen, and WhatsApp.**

### MVP Tagline
*"GitHub Copilot for India's 1.1 Lakh Rural Teachers"*

---

## 2. Problem Statement

### The Gap
India has **1,10,000 single-teacher schools**. One teacher manages Grades 1–5 simultaneously — 5 grade levels, 5 subjects, 60 students, in one room, with no internet.

Every existing EdTech solution targets students. No production AI tool exists for the teacher managing multi-grade classroom chaos.

### What the Teacher Needs Daily
- A lesson plan that works for all grades at the same time
- Activities that keep one grade occupied while another is taught
- Help they can access by voice, not by typing
- Something that works on their ₹2,000 phone

### What This MVP Proves
That a voice-first AI pipeline can generate practical, structured, multi-grade lesson plans in under 15 seconds — in Hindi and English — and deliver them across multiple channels.

---

## 3. MVP Goals

### Primary Goal
Prove the core pipeline works end-to-end, once, live, in front of judges.

```
Teacher speaks → system understands → lesson plan generated → 
delivered via voice + screen + WhatsApp
```

### Success Criteria

| Criteria | Target |
|---|---|
| End-to-end pipeline latency | < 15 seconds |
| Hindi voice input → Hindi lesson output | Works at least once |
| WhatsApp delivery | Message arrives during demo |
| Phone call pathway | Works at least once |
| App text fallback | Available and functional |
| Lesson plan quality | Contains parallel activities for 2+ grades |

---

## 4. What Is Out of Scope

The following will **not** be built for the hackathon MVP. Mention them as roadmap only.

| Feature | Status |
|---|---|
| Assignment grading / OCR | ❌ Roadmap |
| Offline AI / on-device models | ❌ Roadmap |
| Teacher login / auth system | ❌ Roadmap |
| Progress tracking / analytics | ❌ Roadmap |
| Multi-school support | ❌ Roadmap |
| Full 22-language support | ❌ Roadmap (Hindi + English only) |
| NCERT full curriculum database | ❌ Roadmap (light JSON only) |
| Student-facing features | ❌ Out of scope entirely |

---

## 5. User Persona

### Primary User: Sunita

- **Age:** 32  
- **Role:** Government school teacher, Sitapur, Uttar Pradesh  
- **Salary:** ₹25,000/month  
- **Device:** Android phone, ₹4,000–8,000 range  
- **Connectivity:** 2G/3G intermittent, no school wifi  
- **Languages:** Hindi primary, basic English  
- **Pain:** Spends 2+ hours every evening writing 5 separate lesson plans by hand  
- **Goal:** Spend 5 minutes planning and spend the rest of the evening resting  

### What Sunita Will Say (Demo Input)
```
"Aaj mujhe Class 1 ko vowels sikhane hain aur Class 3 ko multiplication table."
```
Translation: "Today I need to teach Class 1 vowels and Class 3 multiplication tables."

---

## 6. Core Features

The MVP has exactly **three features**. Build these. Nothing else.

---

### Feature 1: Voice-to-Lesson Pipeline

**What it does:** Teacher speaks a request → system returns a structured lesson plan within 15 seconds.

**Supported inputs:**
- Voice (Hindi or English) via Android SpeechRecognizer
- Text fallback (same input field, same backend)

**Expected output:**
- Structured lesson plan with parallel activities for each grade mentioned
- NCERT-aligned activities using only blackboard + notebooks
- Teaching tips grounded in rural classroom context

**Acceptance Criteria:**
- [ ] Accepts Hindi voice input and returns Hindi lesson plan
- [ ] Accepts English voice input and returns English lesson plan
- [ ] Response contains activities for all grades mentioned in input
- [ ] Each grade section has exactly 2 activities with time estimates
- [ ] Total response delivered in under 15 seconds
- [ ] Response under 200 words

---

### Feature 2: Dual Access — App + Phone Call

**App (Android):**
- Teacher taps mic button → speaks → lesson appears on screen → lesson read aloud
- Text input field visible at all times as fallback
- Loading indicator shown during AI processing

**Phone Call (Twilio):**
- Teacher calls Twilio number → speaks request → hears lesson spoken back
- Same FastAPI backend handles both channels
- One successful call during demo is sufficient

**Acceptance Criteria:**
- [ ] Android app voice → lesson → TTS playback works on demo device
- [ ] Text input → lesson works on demo device
- [ ] Twilio call → transcription → lesson → voice response works at least once
- [ ] Both channels hit same FastAPI backend

---

### Feature 3: WhatsApp Delivery

**What it does:** After lesson is generated, formatted lesson plan is sent to a WhatsApp number via Twilio WhatsApp Sandbox.

**Format:** Structured with emojis, dividers, and cultural tips (see Section 11).

**Acceptance Criteria:**
- [ ] WhatsApp message sent within 5 seconds of lesson generation
- [ ] Message uses the approved formatting template
- [ ] Message arrives on demo device visibly during the demo
- [ ] Screenshot available as fallback if delivery lags

---

## 7. Tech Stack

### Final Stack

| Layer | Technology | Justification |
|---|---|---|
| Android App | Kotlin + Jetpack Compose | Native voice + TTS, thin client |
| Voice Input | Android SpeechRecognizer | No external dependency |
| Voice Playback | Android TextToSpeech | Native, no latency |
| HTTP Client | Retrofit | Fast integration, standard |
| Backend | Python + FastAPI | Async, fast to build, clean routing |
| Backend Hosting | Render or Railway | Stable public URL — no ngrok |
| AI / LLM | Anthropic Claude via AWS Bedrock | Reliable, strong multilingual |
| Phone Calls | Twilio Voice API | Demo-friendly, fast setup |
| WhatsApp | Twilio WhatsApp Sandbox | No business approval needed |

### What Is NOT in the Stack

| Excluded | Reason |
|---|---|
| AWS IoT Greengrass | Not buildable in 48h; not needed for demo |
| Amazon Connect | Replaced by Twilio for speed and reliability |
| Amazon Transcribe | Replaced by Android SpeechRecognizer (app) + Twilio STT (calls) |
| DynamoDB / ElastiCache | No persistent state needed for MVP |
| Step Functions | No workflow orchestration needed at MVP scale |
| ngrok | Replaced by Render/Railway stable URL |

---

## 8. System Architecture

```
┌─────────────────────────────────────────────────────┐
│                  TEACHER INPUT                      │
│                                                     │
│   Android App             Phone Call                │
│   (Voice / Text)          (Twilio)                  │
└────────────┬──────────────────────┬─────────────────┘
             │                      │
             │  HTTP POST           │  Twilio Webhook
             ▼                      ▼
┌─────────────────────────────────────────────────────┐
│               FastAPI Backend (Render)              │
│                                                     │
│   POST /generate-lesson                             │
│   POST /call-webhook    (Twilio calls this)         │
│                                                     │
│   ┌─────────────────────────────────────────────┐  │
│   │           Lesson Generation Service         │  │
│   │                                             │  │
│   │   1. Receive transcript / text              │  │
│   │   2. Detect language (Hindi / English)      │  │
│   │   3. Inject system prompt + NCERT context   │  │
│   │   4. Call Claude via AWS Bedrock            │  │
│   │   5. Format response                        │  │
│   │   6. Trigger WhatsApp send (async)          │  │
│   │   7. Return lesson JSON                     │  │
│   └─────────────────────────────────────────────┘  │
└─────────┬─────────────────────────────┬─────────────┘
          │                             │
          ▼                             ▼
┌──────────────────┐          ┌─────────────────────┐
│  Claude Bedrock  │          │  Twilio WhatsApp     │
│  (Lesson Gen)    │          │  (Delivery)          │
└──────────────────┘          └─────────────────────┘
          │
          ▼
┌──────────────────────────────────────────────────────┐
│                 RESPONSE DELIVERY                    │
│                                                      │
│  App: JSON → display on screen + TTS playback        │
│  Call: TTS audio spoken back to teacher on phone     │
│  WhatsApp: Formatted lesson message sent             │
└──────────────────────────────────────────────────────┘
```

---

## 9. API Contracts

### POST `/generate-lesson`

**Purpose:** Receive teacher input from Android app, return lesson plan.

**Request:**
```json
{
  "transcript": "Aaj mujhe Class 1 ko vowels sikhane hain aur Class 3 ko multiplication table.",
  "language": "hi",
  "whatsapp_number": "+91XXXXXXXXXX"
}
```

**Response:**
```json
{
  "success": true,
  "language": "hi",
  "lesson_text": "...",
  "lesson_structured": {
    "grades": [
      {
        "grade": "Class 1",
        "subject": "Hindi",
        "topic": "Vowels",
        "activities": [
          { "duration_min": 10, "description": "Repeat after teacher: अ आ इ ई उ" },
          { "duration_min": 15, "description": "Students write each vowel 3 times in notebook" }
        ],
        "tip": "Use objects in the room that start with each vowel sound"
      },
      {
        "grade": "Class 3",
        "subject": "Math",
        "topic": "Multiplication Tables",
        "activities": [
          { "duration_min": 10, "description": "Write table of 3 on board, read together" },
          { "duration_min": 15, "description": "Students copy and solve 5 problems independently" }
        ],
        "tip": "While Class 3 works independently, teach Class 1 actively"
      }
    ]
  },
  "latency_ms": 4200
}
```

**Error Response:**
```json
{
  "success": false,
  "error": "LLM_TIMEOUT",
  "message": "Lesson generation timed out. Please try again.",
  "fallback_lesson": null
}
```

---

### POST `/call-webhook`

**Purpose:** Twilio calls this endpoint when a teacher calls the Twilio number.

**Twilio sends (form data):**
```
CallSid=CA...
SpeechResult=Class 2 Math fractions sikhao
Confidence=0.87
```

**Response:** TwiML XML
```xml
<?xml version="1.0" encoding="UTF-8"?>
<Response>
  <Say language="hi-IN" voice="Polly.Aditi">
    Class 2 Math ke liye aaj ka lesson plan...
  </Say>
</Response>
```

---

### POST `/health`

**Purpose:** Quick health check before demo.

**Response:**
```json
{
  "status": "ok",
  "bedrock": "connected",
  "twilio": "connected",
  "timestamp": "2026-03-01T10:00:00Z"
}
```

---

## 10. AI Layer — Prompt Specification

This is the most critical section. The prompt **is** the product.

---

### System Prompt (Lock This — Do Not Change During Demo)

```
You are a teaching assistant helping a rural Indian government school teacher.

The teacher manages a single classroom with students from multiple grades simultaneously.
The teacher has access to: one blackboard, student notebooks, chalk. No projector, no internet, no printed materials.

Your job is to generate a practical lesson plan that:
1. Assigns PARALLEL activities — one grade must be doing independent work while another is being taught directly. The teacher cannot give full attention to two grades at once.
2. Uses only low-resource materials (blackboard, notebooks, chalk).
3. Keeps instructions simple, specific, and actionable.
4. Includes one culturally grounded teaching tip per grade (use familiar objects, food, or daily life examples from rural India).

Output format — follow this exactly:

For each grade mentioned:
[Grade] [Subject] — [Topic]
• Activity 1 (X min): [what teacher does / what students do]
• Activity 2 (X min): [what teacher does / what students do]
Tip: [one practical teaching tip rooted in rural Indian context]

Constraints:
- Maximum 200 words total
- Each activity has a time estimate in minutes
- Do not use bullet points beyond the format above
- Do not add preamble or closing remarks
- If input is in Hindi (Devanagari script detected), respond entirely in Hindi
- If input is in English, respond in English
```

---

### Language Detection Logic (Backend — Python)

```python
import re

def detect_language(text: str) -> str:
    """Detect Hindi vs English from script."""
    devanagari_pattern = re.compile(r'[\u0900-\u097F]')
    if devanagari_pattern.search(text):
        return "hi"
    return "en"

def build_prompt(transcript: str) -> tuple[str, str]:
    language = detect_language(transcript)
    language_instruction = (
        "Respond entirely in Hindi (Devanagari script)." 
        if language == "hi" 
        else "Respond in English."
    )
    user_message = f"{language_instruction}\n\nTeacher's request: {transcript}"
    return user_message, language
```

---

### Claude Bedrock API Call (Python)

```python
import boto3
import json

bedrock = boto3.client("bedrock-runtime", region_name="ap-south-1")

SYSTEM_PROMPT = "..."  # Full system prompt from above

async def generate_lesson(transcript: str) -> dict:
    user_message, language = build_prompt(transcript)
    
    body = {
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": 400,
        "system": SYSTEM_PROMPT,
        "messages": [
            {"role": "user", "content": user_message}
        ]
    }
    
    response = bedrock.invoke_model(
        modelId="anthropic.claude-3-5-sonnet-20241022-v2:0",
        body=json.dumps(body)
    )
    
    result = json.loads(response["body"].read())
    lesson_text = result["content"][0]["text"]
    
    return {
        "lesson_text": lesson_text,
        "language": language
    }
```

---

### Sample Input → Expected Output

**Input (Hindi):**
```
Aaj mujhe Class 1 ko vowels sikhane hain aur Class 3 ko multiplication table.
```

**Expected Output (Hindi):**
```
Class 1 Hindi — Swar (Vowels)
• Activity 1 (10 min): Board par swar likhein: अ आ इ ई उ ऊ — bacche dohraayein
• Activity 2 (15 min): Har swar notebook mein 3 baar likhein (swatantra kaam)
Tip: Kamarey mein jo cheezein hain unka naam lekar swar bataayein — jaise "Aam" se आ

Class 3 Math — Pahade (Multiplication Tables)
• Activity 1 (10 min): Board par 3 ka pahada likhein — Class 1 ke sath likhte waqt Class 3 dekhta rahe
• Activity 2 (15 min): 5 sawaal notebook mein — 3x4, 3x7, 3x9 jaise
Tip: "3 rotiyan, 4 baar" jaisi kahani se pahada yaad dilwaayein
```

---

## 11. WhatsApp Message Format

Use this exact format for WhatsApp delivery. This is what judges will screenshot.

```
🏫 PathShala AI — Aaj ka Lesson Plan

📚 Class 1 Hindi — Swar (Vowels)
━━━━━━━━━━━━━━━━━━━━
• Board par likhein: अ आ इ ई उ (10 min)
• Notebook mein 3 baar likhein (15 min)
💡 Tip: Aam, Imli jaise objects se swar yaad dilwaayein

📐 Class 3 Math — Pahade
━━━━━━━━━━━━━━━━━━━━
• Board par 3 ka pahada milke padhein (10 min)
• 5 sawaal notebook mein solve karein (15 min)
💡 Tip: "3 rotiyan 4 baar = 12" — asli kahani se samjhaayein

━━━━━━━━━━━━━━━━━━━━
⏱ Generated in 4.2 seconds
🤖 PathShala AI — Voice se lesson, turant
```

**Rules for formatting:**
- Always start with `🏫 PathShala AI — Aaj ka Lesson Plan`
- Each grade section starts with relevant emoji + grade + subject + topic
- Divider line `━━━` between sections
- Each activity is a bullet with time in brackets
- Tip line uses 💡
- Footer shows generation time
- Match language of the request (Hindi lesson → Hindi WhatsApp)

---

## 12. Android App — Screen Specifications

### Single Screen Architecture

The app has **one screen**. No navigation. No login. No splash screen.

---

### Screen Layout (Top to Bottom)

```
┌──────────────────────────────────┐
│         PathShala AI             │  ← App title, centered
│   AI Co-Teacher for Rural India  │  ← Subtitle
├──────────────────────────────────┤
│                                  │
│   [ Text input field            ]│  ← Always visible, editable
│                                  │
├──────────────────────────────────┤
│                                  │
│         [🎤 TAP TO SPEAK]        │  ← Large mic button, centered
│                                  │
│   "या यहाँ टाइप करें"            │  ← Hint: "or type here"
│                                  │
├──────────────────────────────────┤
│                                  │
│   [Generating lesson plan...]   │  ← Loading indicator (hidden until needed)
│                                  │
├──────────────────────────────────┤
│                                  │
│   ┌────────────────────────────┐ │
│   │   Lesson plan appears here │ │  ← Scrollable lesson output
│   │   in card format           │ │
│   └────────────────────────────┘ │
│                                  │
│        [🔊 PLAY LESSON]          │  ← TTS button, appears after response
│                                  │
└──────────────────────────────────┘
```

---

### State Machine

| State | UI Shown |
|---|---|
| `IDLE` | Mic button active, text field active, no lesson visible |
| `LISTENING` | Mic button pulsing red, "Listening..." text |
| `PROCESSING` | Spinner + "Generating lesson plan..." text |
| `SUCCESS` | Lesson card visible, Play button visible |
| `ERROR` | Error message + retry button visible |

---

### Critical Android Implementation Notes

**SpeechRecognizer:**
```kotlin
// Run 20 times on demo device before hackathon to clear permission dialogs
val recognizer = SpeechRecognizer.createSpeechRecognizer(context)
val intent = Intent(RecognizerIntent.ACTION_RECOGNIZE_SPEECH).apply {
    putExtra(RecognizerIntent.EXTRA_LANGUAGE, "hi-IN")  // Hindi primary
    putExtra(RecognizerIntent.EXTRA_LANGUAGE_MODEL, RecognizerIntent.LANGUAGE_MODEL_FREE_FORM)
    putExtra(RecognizerIntent.EXTRA_LANGUAGE_PREFERENCE, "hi-IN")
    putExtra(RecognizerIntent.EXTRA_ONLY_RETURN_LANGUAGE_PREFERENCE, false)
}
```

**TextToSpeech — Hindi voice:**
```kotlin
// Set explicitly — do NOT rely on device locale
tts = TextToSpeech(context) { status ->
    if (status == TextToSpeech.SUCCESS) {
        val hindiLocale = Locale("hi", "IN")
        val result = tts.setLanguage(hindiLocale)
        if (result == TextToSpeech.LANG_MISSING_DATA) {
            // Fallback to English — log this
            tts.setLanguage(Locale.ENGLISH)
        }
    }
}
// Pre-download Hindi TTS voice pack on demo device before event
```

**Retrofit — Timeouts:**
```kotlin
// Set BEFORE first demo run — default 10s will cause LLM timeouts
val okHttpClient = OkHttpClient.Builder()
    .connectTimeout(30, TimeUnit.SECONDS)
    .readTimeout(30, TimeUnit.SECONDS)
    .writeTimeout(30, TimeUnit.SECONDS)
    .build()

val retrofit = Retrofit.Builder()
    .baseUrl(BuildConfig.BASE_URL)  // Never hardcode — use config
    .client(okHttpClient)
    .addConverterFactory(GsonConverterFactory.create())
    .build()
```

**Base URL — config file, not hardcoded:**
```kotlin
// local.properties or BuildConfig
BASE_URL=https://pathshala-ai.onrender.com/
// Do NOT write: BASE_URL=http://192.168.1.x:8000
```

---

## 13. Error Handling & Fallbacks

### For Every Failure Point — Prepared Response

| Failure | System Behavior | Demo Recovery Line |
|---|---|---|
| Mic not working | Text input field always visible | *"Voice and text use the same AI pipeline."* |
| Twilio call drops | Switch to app immediately | *"Same backend, different interface — let me show you on the app."* |
| WhatsApp delayed | Show pre-prepared screenshot | *"Delivery takes a few seconds — here's what it looks like."* |
| LLM timeout | Show retry button with friendly message | *"Let me retry — this occasionally happens under high load."* |
| Render/Railway down | Have local server + ngrok as emergency | Pre-test this scenario |
| Hindi TTS broken | Speak English TTS, explain in pitch | *"Production uses native Hindi TTS — I'll explain."* |

### Backend Error Handling (FastAPI)

```python
from fastapi import HTTPException
import asyncio

@app.post("/generate-lesson")
async def generate_lesson(request: LessonRequest):
    try:
        result = await asyncio.wait_for(
            call_bedrock(request.transcript),
            timeout=20.0  # Hard 20s ceiling
        )
        asyncio.create_task(send_whatsapp(result, request.whatsapp_number))
        return result
    except asyncio.TimeoutError:
        raise HTTPException(status_code=504, detail="LLM_TIMEOUT")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
```

---

## 14. Team Responsibilities

Recommended split for a 3–4 person team.

| Person | Responsibility | Priority |
|---|---|---|
| **Person 1 — Backend Lead** | FastAPI setup, `/generate-lesson` endpoint, Bedrock integration, prompt tuning | Highest — everything depends on this |
| **Person 2 — Android Dev** | Jetpack Compose UI, SpeechRecognizer, TextToSpeech, Retrofit integration | High |
| **Person 3 — Integrations** | Twilio Voice webhook, Twilio WhatsApp, Render/Railway deployment, NCERT JSON | High |
| **Person 4 — Demo & QA** | End-to-end testing, demo script rehearsal, fallback preparation, slide backup | Medium — starts after backend is stable |

### If 3 people: Person 3 and 4 merge. Person 3 handles integrations + demo prep.

### Dependency Order

```
Backend API working
        ↓
Android connects to backend
        ↓
Twilio webhook connected to backend
        ↓
WhatsApp delivery working
        ↓
End-to-end test (Hindi voice → lesson → WhatsApp)
        ↓
Demo rehearsal × 3
```

---

## 15. Build Timeline

### 48-Hour Schedule

| Hours | Milestone |
|---|---|
| 0–2h | Backend scaffolding: FastAPI running on Render, `/health` endpoint live |
| 2–6h | Bedrock integration working: raw text in → lesson text out |
| 6–10h | Prompt tuned: Hindi + English tested, parallel activities verified |
| 10–14h | Android app: UI built, Retrofit connected, text input → lesson display working |
| 14–18h | Android voice: SpeechRecognizer integrated, TTS playback working |
| 18–22h | Twilio Voice: phone call → webhook → lesson → TTS response working |
| 22–26h | Twilio WhatsApp: lesson → formatted message → delivery working |
| 26–34h | Full end-to-end testing, bug fixes, edge cases |
| 34–40h | Hindi demo sentence tested 20+ times, fallbacks rehearsed |
| 40–44h | Demo run × 3 with skeptical judge questions answered |
| 44–48h | Sleep. Freeze code. No new features. |

### Hard Rules for Last 12 Hours

- No new features after Hour 36
- No dependency upgrades
- No architecture changes
- Only bug fixes and demo rehearsal

---

## 16. Demo Script

### Exact 3-Minute Demo Flow

**0:00 — Setup (30 seconds)**

> *"India has 1,10,000 schools with exactly one teacher managing 60 students across 5 grades simultaneously. No internet. No assistant. Today, every single lesson plan is written by hand. PathShala AI changes that — by giving every teacher a voice-powered AI co-teacher available anytime, on any phone."*

**0:30 — App Demo (60 seconds)**

[Open app on demo phone]

> *"A teacher opens the app, taps the mic, and says:"*

[Tap mic — speak in Hindi]
```
"Aaj mujhe Class 1 ko vowels sikhane hain aur Class 3 ko multiplication table."
```

[Wait — loading indicator visible]

> *"The AI understands multi-grade context. It knows the teacher can't give full attention to two classes at once — so it designs parallel activities."*

[Lesson appears on screen]

> *"Class 1 has an independent writing activity. Class 3 gets direct teaching time. One teacher. Both classes. At the same time."*

[Tap PLAY — lesson read aloud in Hindi]

**1:30 — WhatsApp (30 seconds)**

[Show WhatsApp on demo phone]

> *"Simultaneously, the lesson is delivered to WhatsApp — formatted, structured, and ready to follow."*

[Message arrives or show screenshot]

**2:00 — Phone Call (45 seconds)**

> *"Now — what if the teacher doesn't have a smartphone? They just call."*

[Dial Twilio number live]

[Speak request — hear response]

> *"Feature phone. No app. No typing. Same AI pipeline."*

**2:45 — Stop**

> *"That's PathShala AI. One voice. One lesson. Every teacher. Every classroom."*

[Stop speaking. Let it land.]

---

### Q&A — Prepared Answers

**Q: "How is this different from ChatGPT?"**

> *"ChatGPT doesn't know what a multi-grade classroom is. Our system prompt encodes the constraint that the teacher has one blackboard, 5 grades, and 25 minutes. No general-purpose AI has that context by default. That structured classroom intelligence is the product."*

**Q: "What about offline?"**

> *"For the MVP, we're cloud-based via a phone call or app on mobile data. The offline architecture — using on-device models synced during connectivity windows — is our production roadmap. The core insight is that even 2G is enough for a voice call."*

**Q: "Can you scale to 1.1 lakh teachers?"**

> *"The backend is stateless FastAPI on serverless infrastructure. Claude Bedrock scales with demand. The bottleneck is teacher onboarding, not infrastructure."*

---

## 17. Definition of Done

The MVP is complete when all of the following are true:

### Backend
- [ ] `/generate-lesson` returns structured lesson in < 15 seconds
- [ ] Hindi input → Hindi output verified with 5 test cases
- [ ] English input → English output verified with 5 test cases
- [ ] `/call-webhook` returns valid TwiML
- [ ] WhatsApp message sends successfully
- [ ] Deployed on Render/Railway with stable public URL
- [ ] `/health` endpoint returns 200

### Android App
- [ ] Hindi TTS voice pack installed on demo device
- [ ] SpeechRecognizer permission dialogs cleared (run app 20+ times)
- [ ] Text input fallback functional
- [ ] Loading indicator visible during processing
- [ ] Retrofit timeouts set to 30 seconds
- [ ] App tested on mobile data (not just WiFi)
- [ ] APK installed on demo device — not emulator

### Integration
- [ ] Full pipeline tested: Hindi voice → lesson → WhatsApp delivery
- [ ] Phone call → lesson response tested
- [ ] Screenshot fallback for WhatsApp prepared
- [ ] Demo rehearsed 3 times end-to-end

---

## 18. Known Risks & Mitigations

| Risk | Probability | Mitigation |
|---|---|---|
| SpeechRecognizer fails on demo device | Medium | Text fallback always visible; rehearse switch seamlessly |
| LLM response > 15 seconds | Low-Medium | `max_tokens=400` + 20s timeout on backend |
| Twilio call audio quality poor | Medium | Demo on device with strong signal; have app demo as backup |
| WhatsApp delivery delayed | Low | Pre-saved screenshot ready; show during narrative |
| Render cold start (first request slow) | Medium | Hit `/health` endpoint 5 minutes before demo to warm server |
| Hindi TTS voice broken | Low | Pre-test and pre-download voice pack; English TTS as fallback |
| Venue WiFi blocking Twilio | Low-Medium | Demo app on mobile data, not venue WiFi |
| Backend crashes mid-demo | Very Low | Have local server + ngrok as emergency; know the switch |

---

## Appendix A — NCERT Context JSON (Minimal)

Pre-load this in your backend. Use it to inject curriculum context into the prompt.

```json
{
  "curriculum": {
    "Class 1": {
      "Hindi": ["Swar (Vowels)", "Vyanjan (Consonants)", "Simple Words"],
      "Math": ["Numbers 1-100", "Addition", "Subtraction", "Shapes"]
    },
    "Class 2": {
      "Hindi": ["Sentences", "Stories", "Reading"],
      "Math": ["Numbers 1-1000", "Multiplication intro", "Measurement"]
    },
    "Class 3": {
      "Hindi": ["Paragraphs", "Grammar basics"],
      "Math": ["Multiplication Tables", "Division intro", "Fractions intro"],
      "Science": ["Plants", "Animals", "Water", "Air"]
    },
    "Class 4": {
      "Math": ["Large Numbers", "Fractions", "Geometry"],
      "Science": ["Food", "Shelter", "Environment"]
    },
    "Class 5": {
      "Math": ["Decimals", "Percentages", "Area and Perimeter"],
      "Science": ["Human Body", "Ecosystem", "Simple Machines"]
    }
  }
}
```

---

*PathShala AI MVP PRD v1.0 — For Hackathon Use Only*  
*"Voice se lesson, turant."*
