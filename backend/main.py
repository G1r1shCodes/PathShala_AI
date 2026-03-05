"""
main.py — PathShala AI FastAPI backend

Endpoints:
  POST /generate-lesson    — Receive teacher input, return structured lesson plan
  POST /call-webhook       — Twilio Voice webhook: gather speech, return TwiML
  POST /call-webhook/respond — Twilio posts SpeechResult here after Gather
  GET  /health             — Health check for pre-demo warm-up

Design decisions:
  - boto3 Bedrock call runs in a thread-pool executor (non-blocking async)
  - Hard 20-second ceiling via asyncio.wait_for
  - WhatsApp send fired as a background task (non-blocking)
  - No auth, no DB, no caching — MVP only
"""
import asyncio
import logging
import time
from datetime import datetime, timezone
from typing import Optional

from fastapi import FastAPI, HTTPException, BackgroundTasks, Form, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from pydantic import BaseModel, Field

from bedrock_service import generate_lesson_from_ai  # ✅ MOCK — swap for generate_lesson_from_bedrock when Bedrock is ready
# from bedrock_service import generate_lesson_from_bedrock  # ← real Bedrock call
from bedrock_service import send_whatsapp, detect_language
from config import settings

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# FastAPI app
# ---------------------------------------------------------------------------
app = FastAPI(
    title="PathShala AI",
    description="Voice-powered lesson planning assistant for rural Indian teachers.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],   # Tighten per-env in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Root — Redirect to /docs
# ---------------------------------------------------------------------------

@app.get("/", include_in_schema=False)
async def root():
    """Redirect root to OpenAPI docs."""
    from fastapi.responses import RedirectResponse
    return RedirectResponse(url="/docs")


# ---------------------------------------------------------------------------
# Pydantic models — request / response per PRD Section 9
# ---------------------------------------------------------------------------

class LessonRequest(BaseModel):
    # ✅ "text" field — used by mock dev mode and Android integration
    text: Optional[str] = Field(
        default=None,
        description="Short-form teacher request (dev/Android field)",
        example="Aaj mujhe Class 1 ko vowels aur Class 3 ko multiplication sikhana hai",
    )
    # Original PRD field — kept for full Bedrock integration
    transcript: Optional[str] = Field(
        default=None,
        description="Teacher's spoken or typed request (Hindi or English)",
        example="Aaj mujhe Class 1 ko vowels sikhane hain aur Class 3 ko multiplication table.",
    )
    language: Optional[str] = Field(
        default=None,
        description="Hint from client: 'hi' or 'en'. Backend auto-detects if omitted.",
        example="hi",
    )
    whatsapp_number: Optional[str] = Field(
        default=None,
        description="Target WhatsApp number for delivery (e.g. +91XXXXXXXXXX)",
        example="+91XXXXXXXXXX",
    )


class Activity(BaseModel):
    duration_min: int
    description: str


class GradeSection(BaseModel):
    grade: str
    subject: str
    topic: str
    activities: list[Activity]
    tip: str


class LessonStructured(BaseModel):
    grades: list[GradeSection]


class LessonResponse(BaseModel):
    success: bool
    language: str
    lesson_text: str
    lesson_structured: LessonStructured
    latency_ms: int


class ErrorResponse(BaseModel):
    success: bool = False
    error: str
    message: str
    fallback_lesson: None = None


# ---------------------------------------------------------------------------
# Helpers — parse flat lesson text into structured JSON
# ---------------------------------------------------------------------------

def _parse_lesson_to_structured(lesson_text: str) -> LessonStructured:
    """
    Best-effort parser: converts Claude's formatted text output into
    the structured GradeSection list.

    Claude is instructed to follow:
      [Grade] [Subject] — [Topic]
      • Activity 1 (X min): ...
      • Activity 2 (X min): ...
      Tip: ...

    Falls back to a single-grade wrapper if parsing fails, ensuring the
    response schema is always valid.
    """
    import re

    grades: list[GradeSection] = []

    # Match "Grade N" or "Class N" etc.
    grade_header_pattern = re.compile(
        r'^(?:Class|Grade|कक्षा)\s+\d+\s+(.+?)\s*[—–-]\s*(.+)$',
        re.MULTILINE | re.IGNORECASE,
    )
    # Match "• Activity 1 (15 min): " or "Activity 1 (15 min): "
    activity_pattern = re.compile(
        r'^(?:[•*\-]\s*)?Activity\s*\d*\s*\((\d+)\s*min\)\s*[:\-]?\s*(.+)',
        re.MULTILINE | re.IGNORECASE,
    )
    bullet_pattern = re.compile(r'^(?:[•*\-])\s*(.+?)\s*\((\d+)\s*min\)\s*[:\-]?\s*(.*)', re.MULTILINE | re.IGNORECASE)
    tip_pattern = re.compile(r'^(?:Tip|टिप्स?|Note)\s*[:\-]\s*(.+)', re.MULTILINE | re.IGNORECASE)

    headers = list(grade_header_pattern.finditer(lesson_text))

    if not headers:
        # Fallback: wrap entire text as a single unparsed section
        return LessonStructured(grades=[
            GradeSection(
                grade="Multi-grade",
                subject="General",
                topic="Lesson",
                activities=[Activity(duration_min=25, description=lesson_text.strip())],
                tip="Follow the plan above step by step.",
            )
        ])

    for i, match in enumerate(headers):
        # Fallback if the header is just "Class 1" without subject/topic
        grade_name = match.group(0).split('—')[0].split('-')[0].strip()
        subject = match.group(1).strip() if match.lastindex >= 1 else "General"
        topic = match.group(2).strip() if match.lastindex >= 2 else "Lesson"

        # Extract the block of text for this grade section
        start = match.end()
        end = headers[i + 1].start() if i + 1 < len(headers) else len(lesson_text)
        block = lesson_text[start:end]

        # Parse activities — try the Activity N (X min): pattern first
        activities: list[Activity] = []
        for act_match in activity_pattern.finditer(block):
            activities.append(Activity(
                duration_min=int(act_match.group(1)),
                description=act_match.group(2).strip(),
            ))

        # Fallback: try bullet pattern "• text (X min)"
        if not activities:
            for bull_match in bullet_pattern.finditer(block):
                desc = bull_match.group(1).strip()
                if bull_match.group(3):
                    desc = f"{desc}: {bull_match.group(3).strip()}"
                activities.append(Activity(
                    duration_min=int(bull_match.group(2)),
                    description=desc,
                ))

        # Fallback: grab all bullet lines
        if not activities:
            for line in block.splitlines():
                line = line.strip()
                if line.startswith("•") or line.startswith("-"):
                    activities.append(Activity(duration_min=10, description=line.lstrip("•- ").strip()))

        if not activities:
            activities.append(Activity(duration_min=25, description=block.strip()))

        # Parse tip
        tip_match = tip_pattern.search(block)
        tip = tip_match.group(1).strip() if tip_match else "Observe student responses and adjust pace."

        grades.append(GradeSection(
            grade=grade_name,
            subject=subject,
            topic=topic,
            activities=activities,
            tip=tip,
        ))

    return LessonStructured(grades=grades)


# ---------------------------------------------------------------------------
# POST /generate-lesson
# ---------------------------------------------------------------------------

@app.post(
    "/generate-lesson",
    summary="Generate a multi-grade lesson plan from a teacher's voice transcript.",
)
async def generate_lesson(request: LessonRequest, background_tasks: BackgroundTasks):
    """
    ✅ MOCK MODE: calls generate_lesson_from_ai (no Bedrock needed).
    Swap import at top of file to switch to real Bedrock call.
    """
    # Use whichever field the client sends
    user_text = request.text or request.transcript or ""

    if not user_text.strip():
        raise HTTPException(status_code=422, detail="Provide 'text' or 'transcript'")

    start_ms = time.monotonic()
    logger.info(f"POST /generate-lesson | input length={len(user_text)}")

    # ✅ Mock call — no AWS, instant response
    lesson = await generate_lesson_from_ai(user_text)

    latency_ms = int((time.monotonic() - start_ms) * 1000)
    logger.info(f"Lesson returned | latency_ms={latency_ms}")

    # WhatsApp — real Twilio send (non-blocking background task)
    if request.whatsapp_number:
        background_tasks.add_task(
            send_whatsapp,
            lesson,
            request.whatsapp_number,
            latency_ms,
        )

    # Parse the raw text into structured JSON required by Android app
    language = "hi" if "hi-IN" in lesson else "en" 
    lesson_structured = _parse_lesson_to_structured(lesson)

    # Use model_dump() for Pydantic v2 to ensure nested models are serialized
    struct_dict = lesson_structured.model_dump() if hasattr(lesson_structured, 'model_dump') else lesson_structured.dict()

    return {
        "success": True,
        "language": language,
        "lesson_text": lesson,
        "lesson_structured": struct_dict,
        "latency_ms": latency_ms
    }


# ---------------------------------------------------------------------------
# Original full-schema route (COMMENTED OUT — restore when Bedrock is live)
# ---------------------------------------------------------------------------
# @app.post("/generate-lesson-full", response_model=LessonResponse)
# async def generate_lesson_full(request: LessonRequest, background_tasks: BackgroundTasks):
#     start_ms = time.monotonic()
#     try:
#         bedrock_result = await asyncio.wait_for(
#             generate_lesson_from_bedrock(request.transcript),
#             timeout=20.0,
#         )
#     except asyncio.TimeoutError:
#         raise HTTPException(status_code=504, detail={"success": False, "error": "LLM_TIMEOUT",
#             "message": "Lesson generation timed out. Please try again.", "fallback_lesson": None})
#     except Exception as exc:
#         raise HTTPException(status_code=500, detail={"success": False, "error": "BEDROCK_ERROR",
#             "message": str(exc), "fallback_lesson": None})
#     lesson_text = bedrock_result["lesson_text"]
#     language = bedrock_result["language"]
#     lesson_structured = _parse_lesson_to_structured(lesson_text)
#     latency_ms = int((time.monotonic() - start_ms) * 1000)
#     if request.whatsapp_number:
#         background_tasks.add_task(send_whatsapp_placeholder, lesson_text, request.whatsapp_number, language)
#     return LessonResponse(success=True, language=language, lesson_text=lesson_text,
#         lesson_structured=lesson_structured, latency_ms=latency_ms)


# ---------------------------------------------------------------------------
# GET /health
# ---------------------------------------------------------------------------

@app.get(
    "/health",
    summary="Health check — hit this 5 minutes before the demo to warm the server.",
)
async def health():
    """
    Returns Bedrock and Twilio connection status.
    """
    return {
        "status": "ok",
        "gemini": "connected",
        "twilio": "connected",
        "model": "gemini-2.5-flash",
        "region": "global",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


# ---------------------------------------------------------------------------
# TwiML helpers
# ---------------------------------------------------------------------------

def _twiml_gather(prompt: str, action: str, language: str = "hi-IN", retries: int = 0) -> str:
    """
    Returns TwiML that:
    1. Says a prompt to the caller
    2. Opens a <Gather> to capture speech and POST it to `action`
    """
    return (
        '<?xml version="1.0" encoding="UTF-8"?>'
        "<Response>"
        f'<Gather input="speech" action="{action}" method="POST" '
        f'language="{language}" speechTimeout="3" timeout="8">'
        f'<Say language="{language}">{prompt}</Say>'
        "</Gather>"
        # If Gather times out with no speech, fall through to retry or end
        f'<Say language="{language}">'
        f'{"Kripaya dobara bolein." if language == "hi-IN" else "Sorry, I did not catch that. Please try again."}'
        "</Say>"
        "</Response>"
    )


def _twiml_say(lesson_text: str, language: str = "hi-IN") -> str:
    """Returns TwiML that reads the lesson aloud."""
    # Strip markdown-ish characters that TTS reads awkwardly
    import re
    clean = re.sub(r'[*_`#•]', '', lesson_text).strip()
    return (
        '<?xml version="1.0" encoding="UTF-8"?>'
        "<Response>"
        f'<Say language="{language}">{clean}</Say>'
        "</Response>"
    )


def _twiml_response(xml: str) -> Response:
    """Wrap TwiML string in a FastAPI Response with correct Content-Type."""
    return Response(content=xml, media_type="application/xml")


# ---------------------------------------------------------------------------
# POST /call-webhook  — Entry point when teacher first calls the Twilio number
# ---------------------------------------------------------------------------

@app.post(
    "/call-webhook",
    summary="Twilio Voice entry point — greet caller and open speech Gather.",
    include_in_schema=True,
)
async def call_webhook():
    """
    Step 1 of the call flow.
    Twilio hits this when the teacher dials in.
    We greet in Hindi and start listening.
    """
    logger.info("Incoming call — opening Gather")
    twiml = _twiml_gather(
        prompt="Namaste! Please speak your lesson request in Hindi or English. For example — Class 1 vowels aur Class 3 multiplication.",
        action="/call-webhook/respond",
        language="en-US",  # Use English STT — detect_language() handles Hindi/English from transcript content
    )
    return _twiml_response(twiml)


# ---------------------------------------------------------------------------
# POST /call-webhook/respond  — Twilio posts SpeechResult here after Gather
# ---------------------------------------------------------------------------

@app.post(
    "/call-webhook/respond",
    summary="Twilio Voice respond — receive speech, generate lesson, read aloud.",
    include_in_schema=True,
)
async def call_webhook_respond(
    background_tasks: BackgroundTasks,
    SpeechResult: Optional[str] = Form(default=None),
    Confidence: Optional[str] = Form(default=None),
    CallSid: Optional[str] = Form(default=None),
):
    """
    Step 2 of the call flow.
    Receives the transcribed speech from Twilio Gather.
    Passes it through generate_lesson_from_ai(), returns TwiML <Say>.

    If SpeechResult is empty — re-prompt the caller (max 2 natural retries
    are handled by Twilio's Gather retry loop via the action URL).
    """
    logger.info(f"call-webhook/respond | CallSid={CallSid} | Confidence={Confidence}")
    logger.info(f"SpeechResult: {SpeechResult!r}")

    # — Empty speech: ask again —
    if not SpeechResult or not SpeechResult.strip():
        logger.warning("Empty SpeechResult — re-prompting caller")
        twiml = _twiml_gather(
            prompt="Sorry, I did not catch that. Please tell me your lesson request — for example, Class 1 vowels and Class 3 multiplication.",
            action="/call-webhook/respond",
            language="en-US",
        )
        return _twiml_response(twiml)

    # — Detect language for correct TTS voice —
    lang_code = detect_language(SpeechResult)          # "hi" or "en"
    tts_lang  = "hi-IN" if lang_code == "hi" else "en-US"

    # — Generate lesson (mock or Bedrock) —
    try:
        lesson = await asyncio.wait_for(
            generate_lesson_from_ai(SpeechResult),
            timeout=20.0,
        )
    except asyncio.TimeoutError:
        logger.error("Lesson generation timed out for call")
        error_msg = (
            "Maafi chahte hain, thoda time lag raha hai. Dobara call karein."
            if tts_lang == "hi-IN"
            else "Sorry, lesson generation timed out. Please call again."
        )
        return _twiml_response(_twiml_say(error_msg, tts_lang))
    except Exception as exc:
        logger.exception(f"Lesson generation failed for call: {exc}")
        return _twiml_response(_twiml_say(
            "Kuch gadbad ho gayi. Kripaya dobara call karein.",
            tts_lang,
        ))

    logger.info(f"Lesson generated for call | lang={tts_lang} | CallSid={CallSid}")
    
    # Send WhatsApp concurrently as a background task
    demo_number = settings.TWILIO_WHATSAPP_TO or "+916369631956" # Falls back if not set in env
    background_tasks.add_task(send_whatsapp, lesson, demo_number, 0)

    return _twiml_response(_twiml_say(lesson, tts_lang))
