import json
import logging
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

# ---------------------------------------------------------------------------
# Logic extracted from bedrock_service.py and main.py
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

def detect_language(text: str) -> str:
    devanagari = re.compile(r'[\u0900-\u097F]')
    return "hi" if devanagari.search(text) else "en"

def _parse_lesson_to_structured(lesson_text: str) -> dict:
    sections = []
    current_section = None
    lines = lesson_text.strip().split("\n")
    for line in lines:
        line = line.strip()
        if not line:
            continue
        grade_match = re.match(r"^\[?(Class\s+\d+|Grade\s+\d+)\]?\s*[-—]?\s*(.*)", line, re.IGNORECASE)
        if grade_match:
            if current_section:
                sections.append(current_section)
            current_section = {
                "grade": grade_match.group(1).strip(),
                "subject": grade_match.group(2).strip().strip("—").strip(),
                "activities": [],
                "tip": ""
            }
        elif line.startswith("•") or line.startswith("-"):
            if current_section:
                current_section["activities"].append(line.lstrip("•-").strip())
        elif line.lower().startswith("tip:"):
            if current_section:
                current_section["tip"] = line[4:].strip()
        else:
            if current_section and not line.startswith("Note"):
                current_section["activities"].append(line)
    if current_section:
        sections.append(current_section)
    return {"sections": sections}

def send_whatsapp_sync(lesson_text: str, whatsapp_number: str):
    try:
        sid = os.environ.get("TWILIO_ACCOUNT_SID")
        token = os.environ.get("TWILIO_AUTH_TOKEN")
        from_num = os.environ.get("TWILIO_WHATSAPP_FROM", "+14155238886")
        if not sid or not token:
            logger.warning("Twilio credentials not set")
            return
            
        url = f"https://api.twilio.com/2010-04-01/Accounts/{sid}/Messages.json"
        
        body = (
            f"🏫 PathShala AI — Aaj ka Lesson Plan\n\n"
            f"{lesson_text.strip()}\n\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"🤖 PathShala AI — Voice se lesson, turant"
        )
        data = urllib.parse.urlencode({
            "From": f"whatsapp:{from_num}" if not from_num.startswith("whatsapp:") else from_num,
            "To": f"whatsapp:{whatsapp_number}" if not whatsapp_number.startswith("whatsapp:") else whatsapp_number,
            "Body": body
        }).encode("utf-8")
        
        req = urllib.request.Request(url, data=data)
        auth = base64.b64encode(f"{sid}:{token}".encode("utf-8")).decode("utf-8")
        req.add_header("Authorization", f"Basic {auth}")
        req.add_header("Content-Type", "application/x-www-form-urlencoded")
        
        with urllib.request.urlopen(req) as response:
            logger.info(f"Twilio REST status: {response.status}")
    except Exception as e:
        logger.error(f"WhatsApp failed: {e}")

def save_to_dynamo_sync(transcript: str, lesson_text: str, lang: str):
    try:
        # boto3 is built into AWS Lambda automatically, no pip install needed!
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
                "source": {"S": "app"}
            }
        )
    except Exception as e:
        logger.error(f"DynamoDB save failed: {e}")

def get_gemini_lesson(transcript: str) -> dict:
    import time
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

    api_key = os.environ.get("GEMINI_API_KEY", "").strip()
    if not api_key:
        raise ValueError("GEMINI_API_KEY missing")
        
    lang_instruction = "महत्वपूर्ण: पूरा जवाब हिंदी में दें। कोई भी शब्द अंग्रेज़ी में न लिखें।" if language == "hi" else "Respond in English."
    full_prompt = f"{SYSTEM_PROMPT}\n\n{lang_instruction}\n\nTeacher's request: {transcript}"
    
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-flash-latest:generateContent?key={api_key}"
    payload = {
        "contents": [{"parts": [{"text": full_prompt}]}]
    }
    
    data = json.dumps(payload).encode("utf-8")
    
    max_retries = 3
    for attempt in range(max_retries + 1):
        try:
            req = urllib.request.Request(url, data=data)
            req.add_header("Content-Type", "application/json")
            
            with urllib.request.urlopen(req) as response:
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
                wait_time = (2 ** attempt) + 1  # 1s, 3s, 7s...
                logger.warning(f"Gemini 429 error. Retrying in {wait_time}s... (Attempt {attempt + 1}/{max_retries})")
                time.sleep(wait_time)
                continue
            
            error_msg = f"HTTP Error {e.code}: {e.reason}"
            if e.code == 429:
                error_msg = "AI service is currently busy due to high traffic. Please try again in 30 seconds."
            raise Exception(error_msg)
        except Exception as e:
            raise e


# ---------------------------------------------------------------------------
# Lambda Handler
# ---------------------------------------------------------------------------
def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Standalone Lambda handler for /generate-lesson using pure standard libraries.
    ZERO pip dependencies required (boto3 is built-in, Gemini/Twilio use pure REST).
    """
    try:
        body = json.loads(event.get("body", "{}"))
        transcript = body.get("transcript", "").strip()
        whatsapp_number = body.get("whatsapp_number", None)
        
        if not transcript:
            return {
                "statusCode": 400,
                "body": json.dumps({"success": False, "error": "MISSING_TRANSCRIPT"})
            }

        # 1. Generate via Gemini REST API
        result = get_gemini_lesson(transcript)
        lesson_text = result["lesson_text"]
        language = result["language"]
        lesson_structured = _parse_lesson_to_structured(lesson_text)
        
        # 2. Side effects
        if whatsapp_number:
            send_whatsapp_sync(lesson_text, whatsapp_number)
            
        save_to_dynamo_sync(transcript, lesson_text, language)

        # 3. Response
        return {
            "statusCode": 200,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({
                "success": True,
                "language": language,
                "lesson_text": lesson_text,
                "lesson_structured": lesson_structured
            })
        }
    except Exception as e:
        logger.exception("Error in generate handler")
        return {
            "statusCode": 500,
            "body": json.dumps({"success": False, "error": str(e)})
        }
