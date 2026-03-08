import json
import logging
import os
import re
import boto3
import google.generativeai as genai

logger = logging.getLogger()
logger.setLevel(logging.INFO)

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
    import re
    sections = []
    current_section = None
    lines = lesson_text.strip().split("\n")
    for line in lines:
        line = line.strip()
        if not line:
            continue
        grade_match = re.match(r"^\[?(Class\s+\d+)\]?\s*(.*)", line, re.IGNORECASE)
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
        from twilio.rest import Client
        sid = os.environ.get("TWILIO_ACCOUNT_SID")
        token = os.environ.get("TWILIO_AUTH_TOKEN")
        from_num = os.environ.get("TWILIO_WHATSAPP_FROM", "+14155238886")
        if not sid or not token:
            logger.warning("Twilio credentials not set")
            return
            
        client = Client(sid, token)
        body = (
            f"🏫 PathShala AI — Aaj ka Lesson Plan\n\n"
            f"{lesson_text.strip()}\n\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"🤖 PathShala AI — Voice se lesson, turant"
        )
        client.messages.create(
            from_=f"whatsapp:{from_num}",
            to=f"whatsapp:{whatsapp_number}",
            body=body,
        )
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
                "source": {"S": "app"}
            }
        )
    except Exception as e:
        logger.error(f"DynamoDB save failed: {e}")

def get_gemini_lesson(transcript: str) -> dict:
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY missing")
        
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel(model_name="gemini-1.5-flash")
    
    language = detect_language(transcript)
    lang_instruction = "महत्वपूर्ण: पूरा जवाब हिंदी में दें। कोई भी शब्द अंग्रेज़ी में न लिखें।" if language == "hi" else "Respond in English."
    
    full_prompt = f"{SYSTEM_PROMPT}\n\n{lang_instruction}\n\nTeacher's request: {transcript}"
    
    response = model.generate_content(full_prompt)
    return {"lesson_text": response.text, "language": language}


# ---------------------------------------------------------------------------
# Lambda Handler
# ---------------------------------------------------------------------------
def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Standalone Lambda handler for /generate-lesson using Gemini only.
    No local imports required.
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

        # 1. Generate via Gemini
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
