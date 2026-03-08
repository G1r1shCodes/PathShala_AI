import json
import logging
import urllib.parse
import re
from typing import Dict, Any

logger = logging.getLogger()
logger.setLevel(logging.INFO)

def detect_language(text: str) -> str:
    devanagari = re.compile(r'[\u0900-\u097F]')
    return "hi" if devanagari.search(text) else "en"

def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Standalone Lambda handler for the Twilio /call-webhook/respond action
    Expects API Gateway HTTP proxy integration (x-www-form-urlencoded body)
    """
    try:
        body_str = event.get("body", "")
        if event.get("isBase64Encoded"):
            import base64
            body_str = base64.b64decode(body_str).decode("utf-8")
            
        parsed_body = urllib.parse.parse_qs(body_str)
        speech_result = parsed_body.get("SpeechResult", [""])[0]
        
        if not speech_result or not speech_result.strip():
            logger.warning("Empty SpeechResult — re-prompting caller")
            twiml = (
                '<?xml version="1.0" encoding="UTF-8"?>'
                '<Response>'
                '<Gather input="speech" action="/call-webhook/respond" timeout="3" speechTimeout="auto" language="hi-IN">'
                '<Say language="hi-IN">Kripaya apna lesson request boliye.</Say>'
                '</Gather>'
                '</Response>'
            )
            return {
                "statusCode": 200,
                "headers": {"Content-Type": "application/xml"},
                "body": twiml
            }

        lang_code = detect_language(speech_result)
        if lang_code == "hi":
            wait_msg = "आपका lesson plan तैयार हो रहा है। कृपया कुछ क्षण प्रतीक्षा करें।"
            wait_lang = "hi-IN"
        else:
            wait_msg = "Your lesson plan is being prepared. Please wait a moment."
            wait_lang = "en-IN"

        encoded_speech = urllib.parse.quote(speech_result)
        
        twiml = (
            '<?xml version="1.0" encoding="UTF-8"?>'
            '<Response>'
            f'<Say language="{wait_lang}">{wait_msg}</Say>'
            f'<Redirect method="POST">/call-webhook/generate?speech={encoded_speech}</Redirect>'
            '</Response>'
        )
        
        return {
            "statusCode": 200,
            "headers": {"Content-Type": "application/xml"},
            "body": twiml
        }
    except Exception as e:
        logger.exception("Error in respond handler")
        return {
            "statusCode": 500,
            "body": str(e)
        }
