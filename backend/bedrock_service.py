"""
bedrock_service.py — AI integration for PathShala AI

Handles:
  - Language detection (Hindi vs English)
  - Prompt construction with NCERT context
  - AWS Bedrock (Claude 3.5 Sonnet) as primary
  - Google Gemini (gemini-2.5-flash) as fallback
  - Amazon Polly TTS logic
  - WhatsApp delivery via Twilio SDK
"""

import re
import os
import json
import uuid
import asyncio
import logging
from functools import partial

import boto3
from botocore.config import Config
import google.generativeai as genai

from config import settings

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Clients Configuration
# ---------------------------------------------------------------------------
genai.configure(api_key=settings.GEMINI_API_KEY)
gemini_model = genai.GenerativeModel(model_name="gemini-1.5-flash")

_bedrock_config = Config(
    region_name=os.getenv("AWS_DEFAULT_REGION", "ap-south-1"),
    retries={"max_attempts": 1, "mode": "standard"},
)

bedrock_client = boto3.client(
    "bedrock-runtime",
    aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
    aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
    region_name=os.getenv("AWS_DEFAULT_REGION", "ap-south-1"),
    config=_bedrock_config,
)

polly_client = boto3.client(
    "polly",
    aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
    aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
    region_name=os.getenv("AWS_DEFAULT_REGION", "ap-south-1")
)

s3_client = boto3.client(
    "s3",
    aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
    aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
    region_name=os.getenv("AWS_DEFAULT_REGION", "ap-south-1")
)

S3_BUCKET_NAME = os.getenv("S3_BUCKET_NAME", "pathshala-curriculum-unique-name-1234")

# ---------------------------------------------------------------------------
# System prompt — PRD Section 11 Exactly
# ---------------------------------------------------------------------------
SYSTEM_PROMPT = """You are a teaching assistant helping a rural Indian government school teacher.

The teacher manages a single classroom with students from multiple grades 
simultaneously. The teacher has access to: one blackboard, student notebooks, 
chalk. No projector, no internet, no printed materials.

Your job is to generate a practical lesson plan that:
1. Assigns PARALLEL activities — one grade must be doing independent work 
   while another is being taught directly. The teacher cannot give full 
   attention to two grades at once.
2. Uses only low-resource materials (blackboard, notebooks, chalk).
3. Keeps instructions simple, specific, and actionable.
4. Includes one culturally grounded teaching tip per grade using familiar 
   objects, food, or daily life examples from rural India.

Output format — follow this exactly:
[Grade] [Subject] — [Topic]
• Activity 1 (X min): description
• Activity 2 (X min): description
Tip: one practical teaching tip

Constraints:
- ONLY generate a lesson plan for the specific grade(s) requested by the teacher. DO NOT hallucinate or generate plans for grades that were not mentioned.
- Maximum 200 words total
- Each activity has a time estimate in minutes
- No preamble or closing remarks
- If input is in Hindi (Devanagari script), respond entirely in Hindi
- If input is in English, respond in English"""


# ---------------------------------------------------------------------------
# Language detection & Context from PRD Section 11
# ---------------------------------------------------------------------------
def detect_language(text: str) -> str:
    devanagari = re.compile(r'[\u0900-\u097F]')
    return "hi" if devanagari.search(text) else "en"

def build_user_message(transcript: str, curriculum_context: str = "") -> tuple[str, str]:
    language = detect_language(transcript)
    
    lang_instruction = (
        "महत्वपूर्ण: पूरा जवाब हिंदी में दें। कोई भी शब्द अंग्रेज़ी में न लिखें।"
        if language == "hi"
        else "Respond in English."
    )
    
    message = f"{lang_instruction}\n\n{curriculum_context}\n\nTeacher's request: {transcript}"
    return message, language


# ---------------------------------------------------------------------------
# primary: Bedrock Call
# ---------------------------------------------------------------------------
def _invoke_bedrock_sync(user_message: str) -> str:
    body = {
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": 400,
        "system": SYSTEM_PROMPT,
        "messages": [{"role": "user", "content": user_message}]
    }
    response = bedrock_client.invoke_model(
        modelId=os.getenv("BEDROCK_MODEL_ID", "anthropic.claude-3-5-sonnet-20241022-v2:0"),
        body=json.dumps(body)
    )
    result = json.loads(response["body"].read())
    return result["content"][0]["text"]

async def generate_lesson_from_bedrock(user_message: str) -> str:
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, partial(_invoke_bedrock_sync, user_message))


# ---------------------------------------------------------------------------
# fallback: Gemini Call
# ---------------------------------------------------------------------------
def _invoke_gemini_sync(user_message: str) -> str:
    full_prompt = f"{SYSTEM_PROMPT}\n\n---\n\n{user_message}"
    response = gemini_model.generate_content(full_prompt)
    return response.text

async def generate_lesson_from_gemini(user_message: str) -> str:
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, partial(_invoke_gemini_sync, user_message))


# ---------------------------------------------------------------------------
# Core Entrypoint (PRD Section 14)
# ---------------------------------------------------------------------------
async def generate_lesson_from_ai(transcript: str, curriculum_context: str = "") -> dict:
    user_message, language = build_user_message(transcript, curriculum_context)
    try:
        logger.info("Calling PRIMARY: AWS Bedrock")
        lesson_text = await generate_lesson_from_bedrock(user_message)
    except Exception as e:
        logger.warning(f"Bedrock unavailable, using FALLBACK (Gemini): {e}")
        lesson_text = await generate_lesson_from_gemini(user_message)
        
    return {"lesson_text": lesson_text, "language": language}


# ---------------------------------------------------------------------------
# AWS Polly (PRD Section 9)
# ---------------------------------------------------------------------------
def _generate_polly_sync(text: str, language: str) -> str:
    voice_id = "Aditi" if language == "hi" else "Joanna"
    lang_code = "hi-IN" if language == "hi" else "en-US"
    
    response = polly_client.synthesize_speech(
        Text=text[:1500],  # Polly limit
        OutputFormat='mp3',
        VoiceId=voice_id,
        LanguageCode=lang_code
    )
    
    audio_key = f"audio/{uuid.uuid4()}.mp3"
    s3_client.put_object(
        Bucket=S3_BUCKET_NAME,
        Key=audio_key,
        Body=response['AudioStream'].read(),
        ContentType='audio/mpeg'
    )
    
    # Needs to be a public URL or presigned URL for Twilio to access
    presigned_url = s3_client.generate_presigned_url(
        'get_object',
        Params={'Bucket': S3_BUCKET_NAME, 'Key': audio_key},
        ExpiresIn=3600  # Valid for 1 hour
    )
    return presigned_url

async def generate_polly_audio(text: str, language: str) -> str:
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, partial(_generate_polly_sync, text, language))


# ---------------------------------------------------------------------------
# WhatsApp Delivery (unchanged from MVP, adapted slightly)
# ---------------------------------------------------------------------------
def _send_whatsapp_sync(lesson_text: str, whatsapp_number: str, latency_ms: int) -> str:
    from twilio.rest import Client
    divider = "━━━━━━━━━━━━━━━━━━━━"
    body = (
        f"🏫 PathShala AI — Aaj ka Lesson Plan\n\n"
        f"{lesson_text.strip()}\n\n"
        f"{divider}\n"
        f"⏱ Generated in {latency_ms//1000}.{latency_ms%1000}s | 💾 Saved to history\n"
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
    if not settings.TWILIO_ACCOUNT_SID or not settings.TWILIO_AUTH_TOKEN:
        logger.warning(f"Twilio credentials not set — would send {whatsapp_number}")
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
