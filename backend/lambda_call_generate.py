import json
import logging
import time
import os
import re
import urllib.request
import urllib.parse
import base64
import boto3
from typing import Dict, Any

logger = logging.getLogger()
logger.setLevel(logging.INFO)

# --- Global Cache for Lambda Container Reuse ---
# Stores { "transcript": {"lesson_text": "...", "expires_at": 123456} }
GeminiCache = {}
# -----------------------------------------------

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
    language = detect_language(transcript)
    
    # 1. Check Memory Cache first (Valid for 2 minutes)
    current_time = int(time.time())
    if transcript in GeminiCache:
        cached = GeminiCache[transcript]
        if current_time < cached["expires_at"]:
            logger.info(f"Returning CACHED lesson for transcript: '{transcript[:30]}...'")
            return {"lesson_text": cached["lesson_text"], "language": cached["language"]}
        else:
            del GeminiCache[transcript]

    # 2. Call Gemini
    api_key = os.environ.get("GEMINI_API_KEY", "").strip()
    lang_instruction = "महत्वपूर्ण: पूरा जवाब हिंदी में दें। कोई भी शब्द अंग्रेज़ी में न लिखें।" if language == "hi" else "Respond in English."
    full_prompt = f"{SYSTEM_PROMPT}\n\n{lang_instruction}\n\nTeacher's request: {transcript}"

    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"
    payload = {"contents": [{"parts": [{"text": full_prompt}]}]}
    data = json.dumps(payload).encode("utf-8")

    max_retries = 3
    for attempt in range(max_retries + 1):
        try:
            req = urllib.request.Request(url, data=data)
            req.add_header("Content-Type", "application/json")
            with urllib.request.urlopen(req, timeout=15) as response:
                res_data = json.loads(response.read().decode("utf-8"))
                lesson_text = res_data["candidates"][0]["content"]["parts"][0]["text"]
                
                # Save to Cache for exactly 2 minutes (120 seconds)
                GeminiCache[transcript] = {
                    "lesson_text": lesson_text,
                    "language": language,
                    "expires_at": current_time + 120
                }
                
                return {"lesson_text": lesson_text, "language": language}
        except urllib.error.HTTPError as e:
            if e.code == 429 and attempt < max_retries:
                wait_time = (2 ** attempt) + 1
                logger.warning(f"Gemini 429. Retrying in {wait_time}s... ({attempt + 1}/{max_retries})")
                time.sleep(wait_time)
                continue
            raise Exception("AI service is currently busy. Please call back in 30 seconds." if e.code == 429 else f"HTTP Error {e.code}: {e.reason}")
        except Exception as e:
            raise e


def update_call_with_lesson(call_sid: str, lesson: str, tts_lang: str):
    """
    Uses Twilio's REST API to inject the lesson TwiML into the live call.
    This is the key to making the lesson narration work asynchronously!
    """
    sid = os.environ.get("TWILIO_ACCOUNT_SID")
    token = os.environ.get("TWILIO_AUTH_TOKEN")
    if not sid or not token:
        logger.error("Twilio credentials missing — cannot update call")
        return

    # Build TwiML to say the lesson and hang up
    twiml = f'<?xml version="1.0" encoding="UTF-8"?><Response><Say language="{tts_lang}">{lesson}</Say><Hangup/></Response>'

    url = f"https://api.twilio.com/2010-04-01/Accounts/{sid}/Calls/{call_sid}.json"
    data = urllib.parse.urlencode({"Twiml": twiml}).encode("utf-8")
    auth = base64.b64encode(f"{sid}:{token}".encode()).decode()

    req = urllib.request.Request(url, data=data, method="POST")
    req.add_header("Authorization", f"Basic {auth}")
    req.add_header("Content-Type", "application/x-www-form-urlencoded")

    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            logger.info(f"Call updated successfully: {resp.status}")
    except Exception as e:
        logger.error(f"Failed to update call {call_sid}: {e}")


def send_whatsapp_sync(lesson_text: str, whatsapp_number: str):
    try:
        sid = os.environ.get("TWILIO_ACCOUNT_SID")
        token = os.environ.get("TWILIO_AUTH_TOKEN")
        from_num = os.environ.get("TWILIO_WHATSAPP_FROM", "+14155238886")
        if not sid or not token:
            return
        url = f"https://api.twilio.com/2010-04-01/Accounts/{sid}/Messages.json"
        body = f"🏫 PathShala AI — Aaj ka Lesson Plan\n\n{lesson_text.strip()}\n\n━━━━━━━━━━━━━━━━━━━━\n🤖 PathShala AI"
        data = urllib.parse.urlencode({
            "From": f"whatsapp:{from_num}",
            "To": f"whatsapp:{whatsapp_number}",
            "Body": body
        }).encode("utf-8")
        req = urllib.request.Request(url, data=data)
        auth = base64.b64encode(f"{sid}:{token}".encode()).decode()
        req.add_header("Authorization", f"Basic {auth}")
        req.add_header("Content-Type", "application/x-www-form-urlencoded")
        urllib.request.urlopen(req)
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
    Called ASYNCHRONOUSLY by lambda_call_respond (InvocationType='Event').
    
    1. Generates lesson from Gemini.
    2. Updates the LIVE call via Twilio REST API so the teacher hears it.
    3. Sends WhatsApp as backup delivery.
    """
    try:
        # When invoked async by lambda_call_respond, payload is a dict directly
        call_sid = event.get("call_sid", "")
        speech_result = event.get("speech_result", "")
        lang_code = event.get("lang_code", "en")
        tts_lang = event.get("tts_lang", "en-US")

        # Fallback: also handle being invoked via API Gateway query string (for testing)
        if not speech_result:
            query_params = event.get("queryStringParameters", {}) or {}
            speech_result = urllib.parse.unquote(query_params.get("speech", ""))
            call_sid = query_params.get("call_sid", "")
            lang_code = detect_language(speech_result)
            tts_lang = "hi-IN" if lang_code == "hi" else "en-US"

        if not speech_result:
            logger.error("No speech_result in event")
            return {"statusCode": 400, "body": "Missing speech_result"}

        logger.info(f"Generating lesson for call_sid={call_sid}, speech='{speech_result}'")

        # 1. Generate lesson
        result = get_gemini_lesson(speech_result)
        lesson = result["lesson_text"]

        # 2. Push lesson audio back to the live call
        if call_sid:
            update_call_with_lesson(call_sid, lesson, tts_lang)
        else:
            logger.warning("No call_sid — skipping call update")

        # 3. Side effects — send WhatsApp to the caller who made the call
        # caller_number is passed by lambda_call_respond from Twilio's "From" field.
        # Falls back to TWILIO_WHATSAPP_TO env var (useful for app-triggered flows).
        caller_number = event.get("caller_number", "")
        whatsapp_target = caller_number or os.environ.get("TWILIO_WHATSAPP_TO", "")
        save_to_dynamo_sync(speech_result, lesson, lang_code)
        if whatsapp_target:
            send_whatsapp_sync(lesson, whatsapp_target)
        else:
            logger.warning("No WhatsApp target — skipping WhatsApp delivery")

        return {"statusCode": 200, "body": json.dumps({"success": True})}

    except Exception as e:
        logger.exception("Error in async generate handler")
        
        # If we fail, tell the caller so they don't wait in silence
        if 'call_sid' in locals() and call_sid:
            try:
                error_msg = "माफ़ कीजिये, अभी सर्वर व्यस्त है। कृपया 1 मिनट बाद दोबारा कॉल करें।" if 'tts_lang' in locals() and tts_lang == "hi-IN" else "Sorry, the AI service is currently busy. Please call back in 1 minute."
                update_call_with_lesson(call_sid, error_msg, locals().get('tts_lang', 'en-US'))
            except Exception as update_err:
                logger.error(f"Could not update call with error message: {update_err}")

        return {"statusCode": 500, "body": str(e)}
