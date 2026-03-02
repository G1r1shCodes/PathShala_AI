"""
bedrock_service.py — AWS Bedrock integration for PathShala AI

Handles:
  - Language detection (Hindi vs English)
  - Prompt construction (from PRD Section 10)
  - Async Bedrock / Claude call via run_in_executor (non-blocking)
  - WhatsApp placeholder (console print — Twilio not yet integrated)
"""

import re
import json
import asyncio
import time
import logging
from functools import partial

import boto3
from botocore.config import Config

from config import settings

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Bedrock client (module-level singleton — boto3 clients are thread-safe)
# ---------------------------------------------------------------------------
_bedrock_config = Config(
    region_name=settings.AWS_REGION,
    retries={"max_attempts": 1, "mode": "standard"},
)

bedrock_client = boto3.client(
    "bedrock-runtime",
    region_name=settings.AWS_REGION,
    config=_bedrock_config,
)

# ---------------------------------------------------------------------------
# System prompt — LOCKED per PRD Section 10. Do NOT modify.
# ---------------------------------------------------------------------------
SYSTEM_PROMPT = """You are a teaching assistant helping a rural Indian government school teacher.

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
- If input is in English, respond in English"""


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
# Synchronous Bedrock call — run inside executor to avoid blocking
# ---------------------------------------------------------------------------
def _invoke_bedrock_sync(user_message: str) -> str:
    """
    Blocking boto3 call. Must only be called via run_in_executor.
    Returns the raw lesson text from Claude.
    """
    body = {
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": 400,
        "system": SYSTEM_PROMPT,
        "messages": [
            {"role": "user", "content": user_message}
        ],
    }

    response = bedrock_client.invoke_model(
        modelId=settings.BEDROCK_MODEL_ID,
        body=json.dumps(body),
        contentType="application/json",
        accept="application/json",
    )

    result = json.loads(response["body"].read())
    lesson_text = result["content"][0]["text"]
    return lesson_text


# ---------------------------------------------------------------------------
# ✅ TEMP MOCK — swap import in main.py to use this during local dev testing.
#    No AWS credentials needed. Delete / re-comment when going live.
# ---------------------------------------------------------------------------
async def generate_lesson_from_ai(user_text: str) -> str:
    """TEMP MOCK RESPONSE for development — no Bedrock call."""
    return f"""
📚 Class 1 Hindi — Vowels
• Repeat after teacher: अ आ इ ई (10 min)
• Students trace vowels in notebook (10 min)
Tip: Use objects like apple, auto to relate sounds

📚 Class 3 Math — Multiplication
• Write table of 2 and 3 on board (10 min)
• Students practice orally in pairs (10 min)
Tip: Compare with counting groups of mangoes
"""


# ---------------------------------------------------------------------------
# Async wrapper — wraps blocking call in executor + 20s timeout
# (COMMENTED OUT during mock dev phase — uncomment when Bedrock is ready)
# ---------------------------------------------------------------------------
# async def generate_lesson_from_bedrock(transcript: str) -> dict:
#     """
#     Async entry point for lesson generation.
#
#     Uses asyncio.get_event_loop().run_in_executor() to run the boto3 call
#     in a thread pool, keeping the event loop non-blocking.
#
#     Wrapped with asyncio.wait_for(..., timeout=20.0) in main.py per PRD.
#
#     Returns:
#         {
#             "lesson_text": str,
#             "language": str   # "hi" or "en"
#         }
#     """
#     user_message, language = build_prompt(transcript)
#
#     logger.info(f"Calling Bedrock | language={language} | model={settings.BEDROCK_MODEL_ID}")
#
#     loop = asyncio.get_event_loop()
#     lesson_text = await loop.run_in_executor(
#         None,  # default ThreadPoolExecutor
#         partial(_invoke_bedrock_sync, user_message),
#     )
#
#     logger.info("Bedrock call succeeded")
#     return {
#         "lesson_text": lesson_text,
#         "language": language,
#     }


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
