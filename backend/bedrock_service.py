"""
bedrock_service.py — AI integration for PathShala AI

Now uses Google Gemini API (gemini-2.0-flash) instead of AWS Bedrock.
Bedrock code is preserved below (commented out) for future switch-back.

Handles:
  - Language detection (Hindi vs English)
  - Prompt construction (from PRD Section 10)
  - Async Gemini call via run_in_executor (non-blocking)
  - WhatsApp delivery via Twilio SDK
"""

import re
import asyncio
import logging
from functools import partial

import google.generativeai as genai

from config import settings

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Gemini client — configured once at module level (model created lazily)
# ---------------------------------------------------------------------------
genai.configure(api_key=settings.GEMINI_API_KEY)

# ---------------------------------------------------------------------------
# System prompt — LOCKED per PRD Section 10. Do NOT modify.
# ---------------------------------------------------------------------------
SYSTEM_PROMPT = """You are a highly practical teaching assistant helping a rural Indian government school teacher.

Context: The teacher operates in a low-resource environment with only a blackboard, chalk, and student notebooks. No projectors, internet, or printed materials are available. The teacher may teach a single grade or manage multiple grades simultaneously in one classroom.

Your objective is to generate an actionable, focused lesson plan based EXCLUSIVELY on the teacher's request.

Key Rules:
1. STRICT GRADE ADHERENCE: ONLY generate a lesson for the explicitly requested grade(s) or class(es). DO NOT assume, invent, or add any other classes. If only one class is mentioned, provide a lesson only for that single class.
2. ACTIVITY STRUCTURE: Keep activities simple, highly specific, and actionable. If multiple grades are requested, assign PARALLEL activities (e.g., one grade does independent work while the other is taught directly). Limit each activity description to MAXIMUM 2 short sentences.
3. LOW-RESOURCE FOCUS: Use only the blackboard, notebooks, and chalk.
4. CULTURAL CONTEXT: Include one culturally grounded teaching tip per grade using familiar rural Indian examples (e.g., local crops, daily chores, festivals).

Output format — strictly follow this template with no preamble, conversational text, or closing remarks:

For each grade explicitly requested:
[Grade] [Subject] — [Topic]
• Activity 1 (X min): [Max 2 short sentences on what teacher/students do]
• Activity 2 (X min): [Max 2 short sentences on what teacher/students do]
💡 Tip: [One practical teaching tip rooted in the rural Indian context]

Constraints:
- Under 200 words total.
- You MUST use the exact bullet character '•' for activities, do NOT use '*'.
- Provide time estimates for every activity.
- If the teacher's input is in Hindi (Devanagari script), your entire response MUST be in Hindi.
- If the teacher's input is in English or Hinglish (Latin script), respond in English."""


# ---------------------------------------------------------------------------
# Language detection — from PRD Section 10 exactly
# ---------------------------------------------------------------------------
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


# ---------------------------------------------------------------------------
# Synchronous Gemini call — run inside executor to avoid blocking event loop
# ---------------------------------------------------------------------------
def _invoke_gemini_sync(user_message: str) -> str:
    """
    Blocking Gemini SDK call. Must only be called via run_in_executor.
    Creates the model lazily (no API call at import/startup time).
    Retries up to 3 times on ResourceExhausted, using the error's own retry_delay.
    """
    import time
    from google.api_core.exceptions import ResourceExhausted

    # Lazy model creation — avoids burning quota on server startup
    model = genai.GenerativeModel(model_name="gemini-2.5-flash")

    full_prompt = f"{SYSTEM_PROMPT}\n\n---\n\n{user_message}"
    gen_config = genai.GenerationConfig(
        max_output_tokens=2048,
        temperature=0.7,
    )

    last_exc = None
    for attempt in range(3):
        try:
            response = model.generate_content(full_prompt, generation_config=gen_config)
            return response.text
        except ResourceExhausted as exc:
            last_exc = exc
            # Parse the retry_delay seconds from gRPC error metadata if available
            wait = 60  # safe default
            try:
                for detail in exc.details():
                    if hasattr(detail, 'retry_delay'):
                        wait = max(detail.retry_delay.seconds + 5, 10)
                        break
            except Exception:
                pass
            logger.warning(f"Gemini rate limit (attempt {attempt + 1}/3) — waiting {wait}s")
            time.sleep(wait)
        except Exception as exc:
            raise exc

    raise last_exc


# ---------------------------------------------------------------------------
# Async wrapper — the main entry point called by main.py routes
# ---------------------------------------------------------------------------
async def generate_lesson_from_ai(transcript: str) -> str:
    """
    Async lesson generation via Gemini API.
    Off-loads the blocking SDK call to a thread pool executor.
    Returns the raw lesson text string.
    """
    user_message, language = build_prompt(transcript)
    logger.info(f"Calling Gemini | language={language} | model=gemini-2.0-flash")

    loop = asyncio.get_event_loop()
    lesson_text = await loop.run_in_executor(
        None,
        partial(_invoke_gemini_sync, user_message),
    )

    logger.info("Gemini call succeeded")
    return lesson_text


# ---------------------------------------------------------------------------
# WhatsApp — real Twilio delivery (async, non-blocking via run_in_executor)
# ---------------------------------------------------------------------------

def _send_whatsapp_sync(lesson_text: str, whatsapp_number: str, latency_ms: int) -> str:
    """
    Blocking Twilio SDK call. Run only via run_in_executor — never call directly
    from an async route.
    Returns the Twilio message SID on success.
    """
    from twilio.rest import Client  # imported here so missing creds don't crash startup

    divider = "━━━━━━━━━━━━━━━━━━━━"
    body = (
        f"🏫 PathShala AI — Aaj ka Lesson Plan\n\n"
        f"{lesson_text.strip()}\n\n"
        f"{divider}\n"
        f"⏱ Generated in {latency_ms}ms\n"
        f"🤖 PathShala AI — Voice se lesson, turant"
    )

    client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
    message = client.messages.create(
        from_=f"whatsapp:{settings.TWILIO_WHATSAPP_FROM}",
        to=f"whatsapp:{whatsapp_number}",
        body=body,
    )
    return message.sid


async def send_whatsapp(lesson_text: str, whatsapp_number: str, latency_ms: int = 0) -> None:
    """
    Async wrapper — off-loads the blocking Twilio call to a thread pool.
    Errors are caught and logged so they never surface to the HTTP response.
    Falls back to console print if Twilio credentials are not configured.
    """
    # Graceful fallback when creds are absent (local dev without .env Twilio keys)
    if not settings.TWILIO_ACCOUNT_SID or not settings.TWILIO_AUTH_TOKEN:
        logger.warning("Twilio credentials not set — printing WhatsApp message to console")
        print("\n" + "=" * 60)
        print(f"[WhatsApp FALLBACK → console] → {whatsapp_number}")
        print("=" * 60)
        print(f"🏫 PathShala AI — Aaj ka Lesson Plan\n\n{lesson_text.strip()}")
        print("=" * 60 + "\n")
        return

    try:
        loop = asyncio.get_event_loop()
        sid = await loop.run_in_executor(
            None,
            lambda: _send_whatsapp_sync(lesson_text, whatsapp_number, latency_ms),
        )
        logger.info(f"WhatsApp sent to {whatsapp_number} | SID={sid}")
    except Exception as exc:
        logger.error(f"WhatsApp send failed for {whatsapp_number}: {exc}")


# ---------------------------------------------------------------------------
# ── BEDROCK CODE (preserved, commented out) ──────────────────────────────
# To switch back to Bedrock:
#   1. pip install boto3 botocore
#   2. Uncomment the block below
#   3. Replace generate_lesson_from_ai with generate_lesson_from_bedrock
# ---------------------------------------------------------------------------
# import json
# import boto3
# from botocore.config import Config
#
# _bedrock_config = Config(
#     region_name=settings.AWS_REGION,
#     retries={"max_attempts": 1, "mode": "standard"},
# )
# bedrock_client = boto3.client(
#     "bedrock-runtime",
#     region_name=settings.AWS_REGION,
#     config=_bedrock_config,
# )
#
# def _invoke_bedrock_sync(user_message: str) -> str:
#     body = {
#         "anthropic_version": "bedrock-2023-05-31",
#         "max_tokens": 400,
#         "system": SYSTEM_PROMPT,
#         "messages": [{"role": "user", "content": user_message}],
#     }
#     response = bedrock_client.invoke_model(
#         modelId=settings.BEDROCK_MODEL_ID,
#         body=json.dumps(body),
#         contentType="application/json",
#         accept="application/json",
#     )
#     result = json.loads(response["body"].read())
#     return result["content"][0]["text"]
#
# async def generate_lesson_from_bedrock(transcript: str) -> dict:
#     user_message, language = build_prompt(transcript)
#     loop = asyncio.get_event_loop()
#     lesson_text = await loop.run_in_executor(
#         None, partial(_invoke_bedrock_sync, user_message)
#     )
#     return {"lesson_text": lesson_text, "language": language}
