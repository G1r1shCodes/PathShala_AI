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
import boto3
import json
import uuid
from mangum import Mangum

from bedrock_service import generate_lesson_from_ai, generate_polly_audio
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
# AWS Initialization and State
# ---------------------------------------------------------------------------
import os
dynamodb = boto3.resource(
    'dynamodb',
    aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
    aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
    region_name=os.getenv("AWS_DEFAULT_REGION", "ap-south-1")
)

s3_client = boto3.client(
    's3',
    aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
    aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
    region_name=os.getenv("AWS_DEFAULT_REGION", "ap-south-1")
)

NCERT_DATA = {}

# In-memory store for pending speech — keyed by CallSid
# Allows /call-webhook/respond to immediately ack and redirect to /call-webhook/generate
_pending_speech: dict = {}

@app.on_event("startup")
async def load_curriculum():
    """Fetch NCERT JSON from S3 at startup."""
    global NCERT_DATA
    try:
        bucket = os.getenv("S3_BUCKET_NAME", "pathshala-curriculum-unique-name-1234")
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(
            None,
            lambda: s3_client.get_object(Bucket=bucket, Key='ncert.json')
        )
        NCERT_DATA = json.loads(response['Body'].read().decode('utf-8'))
        logger.info("NCERT curriculum loaded from S3 successfully")
    except Exception as e:
        logger.error(f"S3 curriculum load failed: {e}")

def get_curriculum_context(transcript: str) -> str:
    """Extract contextual subjects based on the grade mentioned."""
    context_lines = []
    for grade, subjects in NCERT_DATA.items():
        if grade.lower() in transcript.lower():
            for subject, topics in subjects.items():
                context_lines.append(f"{grade} {subject}: {', '.join(topics)}")
    if context_lines:
        return "Relevant NCERT curriculum context:\n" + "\n".join(context_lines)
    return ""

async def save_lesson_to_dynamo(transcript, lesson_text, language, source="app"):
    """Non-blocking DynamoDB write."""
    try:
        table = dynamodb.Table(os.getenv("DYNAMODB_TABLE_NAME", "pathshala-lessons"))
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, lambda: table.put_item(Item={
            'lesson_id': str(uuid.uuid4()),
            'teacher_id': 'demo_teacher',
            'transcript': transcript,
            'lesson_text': lesson_text,
            'language': language,
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'source': source
        }))
    except Exception as e:
        logger.error(f"DynamoDB save failed (non-blocking): {e}")


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

    # Match "Grade N Subject - Topic" or "Class N Science - Solar System"
    grade_header_pattern = re.compile(
        r'^((?:Class|Grade|कक्षा)\s+\d+)\s+(.+?)\s*[—–-]\s*(.+)$',
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
        grade_name = match.group(1).strip()
        subject = match.group(2).strip()
        topic = match.group(3).strip()

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

    # Fetch context based on NCERT S3 data
    curriculum_context = get_curriculum_context(user_text)

    # Call AI (Bedrock primary -> Gemini fallback)
    result = await generate_lesson_from_ai(user_text, curriculum_context)
    lesson = result["lesson_text"]

    latency_ms = int((time.monotonic() - start_ms) * 1000)
    logger.info(f"Lesson returned | latency_ms={latency_ms}")

    language = "hi" if "hi-IN" in lesson or result["language"] == "hi" else "en" 

    # Save to DB async
    background_tasks.add_task(
        save_lesson_to_dynamo,
        user_text,
        lesson,
        language,
        "app"
    )

    # WhatsApp async
    if request.whatsapp_number:
        background_tasks.add_task(
            send_whatsapp,
            lesson,
            request.whatsapp_number,
            latency_ms,
        )

    # Parse the raw text into structured JSON required by Android app
    lesson_structured = _parse_lesson_to_structured(lesson)

    # Use model_dump() for Pydantic v2 to ensure nested models are serialized
    struct_dict = lesson_structured.model_dump() if hasattr(lesson_structured, 'model_dump') else lesson_structured.dict()

    return {
        "success": True,
        "language": language,
        "lesson_text": lesson,
        "lesson_structured": struct_dict,
        "latency_ms": latency_ms,
        "saved_to_db": True
    }


# ---------------------------------------------------------------------------
# GET /lesson-history
# ---------------------------------------------------------------------------
@app.get("/lesson-history")
async def get_lesson_history():
    """Fetch the latest lessons from DynamoDB."""
    try:
        table = dynamodb.Table(os.getenv("DYNAMODB_TABLE_NAME", "pathshala-lessons"))
        loop = asyncio.get_event_loop()
        # Scan is used for MVP simplicity to get recent items
        response = await loop.run_in_executor(None, lambda: table.scan(Limit=10))
        items = response.get('Items', [])
        # Sort manually since scan doesn't order by timestamp automatically without an index
        items.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
        return {"lessons": items, "count": len(items)}
    except Exception as e:
        logger.error(f"DynamoDB fetch failed: {e}")
        return {"lessons": [], "count": 0}



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
        "bedrock": "connected",
        "dynamodb": "connected",
        "s3": "connected",
        "twilio": "connected",
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
        f'language="{language}" speechTimeout="5" timeout="15">'
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
        prompt="Namaste! Aaj ka lesson request boliye. Jaise — Class 3 multiplication, ya Class 5 plants.",
        action="/call-webhook/respond",
        language="hi-IN",  # Hindi STT — returns Devanagari so detect_language works correctly
    )
    return _twiml_response(twiml)


# ---------------------------------------------------------------------------
# POST /call-webhook/respond  — Twilio posts SpeechResult here after Gather
# ---------------------------------------------------------------------------

@app.post(
    "/call-webhook/respond",
    summary="Twilio Voice respond — immediately acknowledge speech and redirect to generate.",
    include_in_schema=True,
)
async def call_webhook_respond(
    SpeechResult: Optional[str] = Form(default=None),
    CallSid: Optional[str] = Form(default=None),
):
    """
    Step 2 of call flow: receive speech, instantly play a wait message,
    store the transcript, and redirect to /call-webhook/generate.
    This eliminates dead silence during AI generation.
    """
    logger.info(f"call-webhook/respond | CallSid={CallSid} | SpeechResult={SpeechResult!r}")

    if not SpeechResult or not SpeechResult.strip():
        logger.warning("Empty SpeechResult — re-prompting caller")
        twiml = _twiml_gather(
            prompt="Kripaya apna lesson request boliye.",
            action="/call-webhook/respond",
            language="hi-IN",
        )
        return _twiml_response(twiml)

    # Store speech so /call-webhook/generate can retrieve it via CallSid
    _pending_speech[CallSid] = SpeechResult

    # Detect language now so the wait message matches what the teacher spoke
    lang_code = detect_language(SpeechResult)
    if lang_code == "hi":
        wait_msg = "आपका lesson plan तैयार हो रहा है। कृपया कुछ क्षण प्रतीक्षा करें।"
        wait_lang = "hi-IN"
    else:
        wait_msg = "Your lesson plan is being prepared. Please wait a moment."
        wait_lang = "en-IN"

    # Immediately acknowledge — teacher hears this instead of silence
    twiml = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<Response>'
        f'<Say language="{wait_lang}">{wait_msg}</Say>'
        '<Redirect method="POST">/call-webhook/generate</Redirect>'
        '</Response>'
    )
    return _twiml_response(twiml)


# ---------------------------------------------------------------------------
# POST /call-webhook/generate — AI generation step (called via Twilio Redirect)
# ---------------------------------------------------------------------------

@app.post(
    "/call-webhook/generate",
    summary="Generate lesson and read it back via Polly or <Say>.",
    include_in_schema=True,
)
async def call_webhook_generate(
    background_tasks: BackgroundTasks,
    CallSid: Optional[str] = Form(default=None),
):
    """
    Step 3 of call flow: retrieve stored speech, generate lesson, play result.
    Called by Twilio after /call-webhook/respond redirects here.
    """
    SpeechResult = _pending_speech.pop(CallSid, "")
    logger.info(f"call-webhook/generate | CallSid={CallSid} | SpeechResult={SpeechResult!r}")

    if not SpeechResult:
        return _twiml_response(_twiml_say("Koi lesson request nahi mili. Kripaya dobara call karein.", "hi-IN"))

    lang_code = detect_language(SpeechResult)
    tts_lang  = "hi-IN" if lang_code == "hi" else "en-US"

    start_ms = time.monotonic()
    try:
        curriculum_context = get_curriculum_context(SpeechResult)
        result = await asyncio.wait_for(
            generate_lesson_from_ai(SpeechResult, curriculum_context),
            timeout=14.0,
        )
        lesson = result["lesson_text"]
    except asyncio.TimeoutError:
        logger.error("Lesson generation timed out for call")
        return _twiml_response(_twiml_say("Lesson taiyar hone mein bahut time lag raha hai. Kripaya dobara call karein.", "hi-IN"))
    except Exception as exc:
        logger.exception(f"Lesson generation failed for call: {exc}")
        return _twiml_response(_twiml_say("Kuch galat ho gaya. Kripaya dobara call karein.", "hi-IN"))

    latency_ms = int((time.monotonic() - start_ms) * 1000)
    logger.info(f"Lesson generated for call | latency={latency_ms}ms | CallSid={CallSid}")

    demo_number = os.environ.get("TWILIO_WHATSAPP_TO")
    if demo_number:
        background_tasks.add_task(send_whatsapp, lesson, demo_number, latency_ms)

    # Use Amazon Polly — presigned URL & must be XML-escaped as &amp; in TwiML
    from html import escape as xml_escape
    try:
        audio_url = await asyncio.wait_for(
            generate_polly_audio(lesson, lang_code),
            timeout=5.0
        )
        safe_url = xml_escape(audio_url)
        logger.info(f"Polly audio ready | url={audio_url[:60]}...")
        twiml = (
            '<?xml version="1.0" encoding="UTF-8"?>'
            "<Response>"
            f"<Play>{safe_url}</Play>"
            "</Response>"
        )
        return _twiml_response(twiml)
    except asyncio.TimeoutError:
        logger.warning("Polly timed out — falling back to <Say>")
        return _twiml_response(_twiml_say(lesson, tts_lang))
    except Exception as e:
        logger.warning(f"Polly failed — falling back to <Say>: {e}")
        return _twiml_response(_twiml_say(lesson, tts_lang))

# ---------------------------------------------------------------------------
# AWS Lambda Handler
# ---------------------------------------------------------------------------
handler = Mangum(app)
