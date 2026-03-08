import json
import logging
import time
import os
import re
import urllib.parse
import boto3
import google.generativeai as genai
from typing import Dict, Any

logger = logging.getLogger()
logger.setLevel(logging.INFO)

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

def detect_language(text: str) -> str:
    devanagari = re.compile(r'[\u0900-\u097F]')
    return "hi" if devanagari.search(text) else "en"

def get_gemini_lesson(transcript: str) -> dict:
    api_key = os.environ.get("GEMINI_API_KEY")
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel(model_name="gemini-1.5-flash")
    language = detect_language(transcript)
    lang_instruction = "महत्वपूर्ण: पूरा जवाब हिंदी में दें। कोई भी शब्द अंग्रेज़ी में न लिखें।" if language == "hi" else "Respond in English."
    full_prompt = f"{SYSTEM_PROMPT}\n\n{lang_instruction}\n\nTeacher's request: {transcript}"
    
    response = model.generate_content(full_prompt)
    return {"lesson_text": response.text, "language": language}

def send_whatsapp_sync(lesson_text: str, whatsapp_number: str):
    try:
        from twilio.rest import Client
        sid = os.environ.get("TWILIO_ACCOUNT_SID")
        token = os.environ.get("TWILIO_AUTH_TOKEN")
        from_num = os.environ.get("TWILIO_WHATSAPP_FROM", "+14155238886")
        if not sid or not token: return
        client = Client(sid, token)
        body = f"🏫 PathShala AI — Aaj ka Lesson Plan\n\n{lesson_text.strip()}\n\n━━━━━━━━━━━━━━━━━━━━\n🤖 PathShala AI"
        client.messages.create(from_=f"whatsapp:{from_num}", to=f"whatsapp:{whatsapp_number}", body=body)
    except Exception as e:
        logger.error(f"WhatsApp failed: {e}")

def save_to_dynamo_sync(transcript: str, lesson_text: str, lang: str):
    try:
        dynamodb = boto3.client("dynamodb", region_name=os.environ.get("AWS_DEFAULT_REGION", "ap-south-1"))
        table = os.environ.get("DYNAMODB_TABLE_NAME", "pathshala-lessons")
        import uuid
        from datetime import datetime, timezone
        dynamodb.put_item(
            TableName=table,
            Item={
                "lesson_id": {"S": str(uuid.uuid4())},
                "timestamp": {"S": datetime.now(timezone.utc).isoformat()},
                "transcript": {"S": transcript},
                "lesson_text": {"S": lesson_text},
                "language": {"S": lang},
                "source": {"S": "call"}
            }
        )
    except Exception as e:
        logger.error(f"Dynamo save failed: {e}")

def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Standalone Lambda handler for the final Twilio /call-webhook/generate phase.
    Uses pure Gemini.
    """
    try:
        query_params = event.get("queryStringParameters", {}) or {}
        speech_result = query_params.get("speech", "")
        if not speech_result:
            twiml = '<?xml version="1.0" encoding="UTF-8"?><Response><Say language="hi-IN">Koi lesson request nahi mili.</Say></Response>'
            return {"statusCode": 200, "headers": {"Content-Type": "application/xml"}, "body": twiml}

        speech_result = urllib.parse.unquote(speech_result)
        lang_code = detect_language(speech_result)
        tts_lang = "hi-IN" if lang_code == "hi" else "en-US"

        # 1. Generate via Gemini
        try:
            result = get_gemini_lesson(speech_result)
            lesson = result["lesson_text"]
        except Exception as exc:
            logger.exception(f"Gemini failed for call: {exc}")
            twiml = '<?xml version="1.0" encoding="UTF-8"?><Response><Say language="hi-IN">Kuch galat ho gaya. Kripaya dobara call karein.</Say></Response>'
            return {"statusCode": 200, "headers": {"Content-Type": "application/xml"}, "body": twiml}

        # 2. Side effects
        demo_number = os.environ.get("TWILIO_WHATSAPP_TO")
        save_to_dynamo_sync(speech_result, lesson, lang_code)
        if demo_number:
            send_whatsapp_sync(lesson, demo_number)

        # 3. Twilio Response (Say fallback since Polly is complex to manage standalone)
        twiml = (
            '<?xml version="1.0" encoding="UTF-8"?>'
            "<Response>"
            f'<Say language="{tts_lang}">{lesson}</Say>'
            "</Response>"
        )
        return {"statusCode": 200, "headers": {"Content-Type": "application/xml"}, "body": twiml}
            
    except Exception as e:
        logger.exception("Error in generate webhook handler")
        return {"statusCode": 500, "body": str(e)}
